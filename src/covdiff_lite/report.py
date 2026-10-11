"""Read-only offline HTML reports with portable source and measurement evidence."""

import hashlib
import html
import json
import re
import shlex
import shutil
from collections import Counter
from pathlib import Path

from .calibration import MISSING, load_fixture
from .io import write_json
from .issues import check_symptom


ASSETS = Path(__file__).with_name('report_assets')
TOOLS = ('gcov', 'llvm-cov')


def read_json(path):
    return json.loads(path.read_text())


def script_json(value):
    # A JSON script element is still parsed by the HTML tokenizer.
    return (json.dumps(value, separators=(',', ':')).replace('&', '\\u0026')
            .replace('<', '\\u003c').replace('>', '\\u003e')
            .replace('\u2028', '\\u2028').replace('\u2029', '\\u2029'))


def analysis_directory(path):
    path = path.resolve()
    return path / 'analysis' if (path / 'analysis/summary.json').is_file() else path


def load_suite(path, identifier, label, review_path=None):
    path = analysis_directory(path)
    summary = read_json(path / 'summary.json')
    if summary.get('schema_version') != 1 or not summary.get('results'):
        raise ValueError('Report requires a completed analysis with schema version 1')
    environment = read_json(path / 'environment.json')
    reviews = {}
    review = read_json(review_path) if review_path else None
    if review:
        if review.get('schema_version') != 1 or not review.get('original_classifications_unchanged'):
            raise ValueError('Unsupported review overlay')
        reviews = {item['case_id']: item for item in review['reviews']}
        if len(reviews) != len(review['reviews']):
            raise ValueError('Duplicate case in review overlay')
    cases, files = [], []
    base = Path('evidence') / identifier

    def retain(source, relative):
        if not source.is_file():
            return None
        if source.is_symlink() or not source.resolve().is_relative_to(path):
            raise ValueError('Evidence must be a regular file inside its analysis directory')
        target = base / relative
        files.append((source, target))
        return target.as_posix()

    links = {name: retain(path / name, Path(name)) for name in
             ('summary.json', 'environment.json', 'config.json', 'cases.csv', 'observations.csv', 'results.jsonl')}
    seen = set()
    for result in summary['results']:
        case_id = result['case_id']
        if not re.fullmatch(r'[a-z][a-z0-9_]*', case_id) or case_id in seen:
            raise ValueError('Invalid or duplicate report case ID')
        seen.add(case_id)
        directory = path / 'cases' / case_id
        manifest, source = load_fixture(directory / 'manifest.json')
        if manifest['case_id'] != case_id or manifest['family'] != result['family']:
            raise ValueError('Case summary does not match manifest')
        overlay = reviews.get(case_id)
        if overlay and (overlay['source_sha256'] != manifest['source_sha256']
                        or overlay['classification_retained'] != result['classification']
                        or overlay['runs'] != result['runs'] or overlay['stable'] != result['stable']):
            raise ValueError('Review overlay does not match the saved case')
        case_base = Path('cases') / case_id
        evidence = {name: retain(directory / name, case_base / name) for name in
                    ('case.c', 'manifest.json', 'analysis.json', 'reproduce.sh')}
        repeats = []
        source_lines = source.read_text().splitlines()
        annotations = None
        for index in range(result['runs']):
            repeat = directory / f'repeat-{index}'
            assessment = read_json(repeat / 'analysis.json')
            normalized = read_json(repeat / 'normalized.json')
            rows = assessment['assessment']['lines']
            if len(rows) != len(source_lines) or any(row['line'] != n or row['source'] != source_lines[n-1]
                    or row['expected'] != manifest['lines'].get(str(n)) for n, row in enumerate(rows, 1)):
                raise ValueError('Report observations do not match their frozen source/oracle')
            if assessment['signature'] != result['signatures'][index]:
                raise ValueError('Report repeat signature differs from case summary')
            for tool in TOOLS:
                report = normalized['tools'].get(tool)
                if report and any(row[tool] != report['lines'].get(str(row['line']), MISSING) for row in rows):
                    raise ValueError('Normalized report differs from the saved line assessment')
            if annotations is None:
                annotations = [{key: row[key] for key in ('line', 'source', 'expected', 'role')} for row in rows]
            repeat_links = {}
            for name in ('analysis.json', 'normalized.json'):
                repeat_links[name] = retain(repeat / name, case_base / f'repeat-{index}' / name)
            observations, outputs, branches = {}, {}, {}
            for tool in TOOLS:
                tool_dir = repeat / tool
                report = normalized['tools'].get(tool)
                observations[tool] = report['lines'] if report else None
                branches[tool] = ({'arcs_by_line': {n: line['branches'] for n, line in report['lines'].items()
                    if line.get('branches')}} if tool == 'gcov' else
                    {'regions': report.get('branches', []), 'expansions': report.get('expansions', [])}) if report else None
                commands_path = tool_dir / 'commands.json'
                commands = read_json(commands_path) if commands_path.exists() else []
                executions = [command for command in commands if command['stage'] == 'execute']
                stdout_path = tool_dir / 'execute.stdout'
                outputs[tool] = {'stdout': stdout_path.read_text() if stdout_path.exists() else None,
                                 'exit_code': executions[-1]['exit_code'] if executions else None}
                retained = {}
                # Reports, logs and source are portable; large binaries/profiles stay in the run archive.
                if tool_dir.exists():
                    for item in sorted(tool_dir.iterdir()):
                        if item.name in ('commands.json', 'case.gcov.json.gz', 'coverage.json') or item.suffix in ('.stdout', '.stderr'):
                            retained[item.name] = retain(item, case_base / f'repeat-{index}' / tool / item.name)
                repeat_links[tool] = retained
            repeats.append({'signature': assessment['signature'], 'errors': assessment['errors'],
                            'oracle_trusted': assessment['oracle_trusted'], 'findings': assessment['assessment']['findings'],
                            'observations': observations, 'outputs': outputs, 'branches': branches, 'evidence': repeat_links})
        if not repeats:
            raise ValueError('Report case has no coverage collections')
        if overlay:
            by_line = {row['line']: row for row in annotations}
            for observation in overlay['observations']:
                row = by_line.get(observation['line'])
                if row is None or row['source'] != observation['source'] or row['expected'] != observation['expected']:
                    raise ValueError('Review source observation does not match its case')
                for tool in TOOLS:
                    observed = repeats[0]['observations'][tool]
                    if observed is None or observation[tool] != observed.get(str(row['line']), MISSING):
                        raise ValueError('Review tool observation does not match the saved collection')
        cases.append({'case_id': case_id, 'family': result['family'], 'origin': manifest.get('origin', 'unspecified'),
            'classification': result['classification'], 'stable': result['stable'], 'runs': result['runs'],
            'comparable_lines': result['comparable_lines'], 'oracle_mismatches': result['oracle_mismatches'],
            'mapping_differences': result['mapping_differences'], 'raw_count_disagreements': result['raw_count_disagreements'],
            'raw_binary_disagreements': result['raw_binary_disagreements'], 'first_pass_seconds': result['first_pass_seconds'],
            'repeat_seconds': result['repeat_seconds'], 'source_sha256': manifest['source_sha256'],
            'expected_output': manifest['expected_output'], 'parameters': manifest.get('parameters', {}),
            'lines': annotations, 'repeats': repeats, 'review': overlay,
            'review_status': overlay['review_status'] if overlay else result['manual_review'],
            'oracle_validation': result.get('oracle_validation'), 'oracle_branches': manifest.get('branches', []),
            'issue': manifest.get('documented_issue'), 'evidence': evidence})
    if set(reviews) - seen:
        raise ValueError('Review overlay refers to cases outside this analysis')
    if summary['cases'] != len(cases) or dict(Counter(c['classification'] for c in cases)) != summary['classification_counts']:
        raise ValueError('Report summary counts differ from case classifications')
    if review_path:
        files.append((review_path, base / 'review.json'))
        links['review.json'] = (base / 'review.json').as_posix()
    context = {}
    for name in ('experiment.json', 'documented-issues.json', 'layout-results.json'):
        candidate = path / name if (path / name).exists() else path.parent / name
        if candidate.is_file():
            context[name] = read_json(candidate)
            files.append((candidate, base / name))
            links[name] = (base / name).as_posix()
    if 'layout-results.json' in context:
        pairs = context['layout-results.json']['results']
        paired_ids = {item[key] for item in pairs for key in ('base_case_id', 'variant_case_id')}
        if paired_ids != seen:
            raise ValueError('Layout pairs do not match the report cases')
    if 'documented-issues.json' in context:
        recorded = {item['case_id']: item for item in context['documented-issues.json']['results']}
        for case, result in zip(cases, summary['results']):
            manifest, _ = load_fixture(path / 'cases' / case['case_id'] / 'manifest.json')
            verified = check_symptom(manifest, result)
            if recorded.get(case['case_id']) != verified:
                raise ValueError('Documented symptom metadata does not match saved findings')
            case['documented_check'] = verified
    return {'id': identifier, 'label': label, 'summary': {k: v for k, v in summary.items() if k != 'results'},
            'environment': environment, 'cases': cases, 'evidence': links, 'context': context}, files


def generate_report(analysis: Path, output: Path, review: Path | None = None,
                    documented_issues: Path | None = None, layout_controls: Path | None = None,
                    layout_review: Path | None = None, empirical: Path | None = None) -> dict:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(output)
    if layout_review and not layout_controls:
        raise ValueError('Layout review requires a layout-control analysis')
    root = analysis_directory(analysis)
    experiment = read_json(root.parent / 'experiment.json') if (root.parent / 'experiment.json').exists() else {}
    kind = experiment.get('config', {}).get('experiment_kind')
    label = {'main': 'Main experiment', 'pilot': 'Pilot experiment'}.get(kind, 'Coverage analysis')
    requests = [(analysis, 'main', label, review)]
    if documented_issues:
        requests.append((documented_issues, 'issues', 'Documented issues', None))
    if layout_controls:
        requests.append((layout_controls, 'layout', 'Layout controls', layout_review))
    suites, files = [], []
    for path, identifier, label, overlay in requests:
        suite, retained = load_suite(path, identifier, label, overlay)
        for case in suite['cases']:
            manifest = output / case['evidence']['manifest.json']
            argument = str(manifest.relative_to(Path.cwd())) if manifest.is_relative_to(Path.cwd()) else str(manifest)
            case['reproduction_command'] = shlex.join(['bash', 'scripts/env.sh', 'analyze', '--case', argument,
                                                      '--output', 'runs/reproduced-' + case['case_id']])
        suites.append(suite)
        files.extend(retained)
    empirical_metrics = None
    if empirical:
        if output.is_relative_to(empirical.resolve()) or any(p.is_symlink() for p in empirical.rglob('*')):
            raise ValueError('Empirical bundle must be regular files outside the report output')
        empirical_metrics = read_json(empirical / 'metrics.json')
        if empirical_metrics.get('schema_version') != 1:
            raise ValueError('Unsupported empirical metrics schema')
        recorded = empirical_metrics['input_evidence_sha256']
        for path, identifier, _, _ in requests:
            digest = hashlib.sha256((analysis_directory(path) / 'summary.json').read_bytes()).hexdigest()
            if recorded.get(f'evidence/{identifier}/summary.json') != digest:
                raise ValueError('Empirical analysis does not match dashboard measurements')
        if {s['id'] for s in empirical_metrics['suites']} != {s['id'] for s in suites}:
            raise ValueError('Empirical and dashboard datasets differ')
    data = {'schema_version': 1, 'suites': suites, 'branch_mapping': 'not_implemented',
            'empirical_link': 'empirical/index.html' if empirical else None}
    # Validate assets before creating output so missing packaged resources leave no partial bundle.
    template = (ASSETS / 'index.html').read_text()
    for name in ('dashboard.css', 'dashboard.js'):
        if not (ASSETS / name).is_file():
            raise FileNotFoundError(ASSETS / name)
    output.mkdir(parents=True)
    for source, relative in files:
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for name in ('dashboard.css', 'dashboard.js'):
        shutil.copyfile(ASSETS / name, output / name)
    rendered = template.replace('@@TITLE@@', html.escape(suites[0]['label'])).replace('@@DATA@@', script_json(data))
    (output / 'index.html').write_text(rendered)
    if empirical:
        from .empirical import write_analysis_pages, write_publication_manifest
        from .figures import read_table
        copied = output / 'empirical'
        shutil.copytree(empirical, copied)
        empirical_metrics['dashboard_href'] = '../index.html'
        write_json(copied / 'metrics.json', empirical_metrics)
        write_analysis_pages(copied, empirical_metrics, read_table(copied / 'tables/pipeline-stages.csv'))
        write_publication_manifest(copied)
    result = {'schema_version': 1, 'purpose': 'offline_coverage_dashboard', 'index': 'index.html',
        'suites': [{'id': s['id'], 'label': s['label'], 'cases': len(s['cases'])} for s in suites],
        'evidence_files': len(files), 'measurement_data_changed': False,
        'input_summary_sha256': {identifier: hashlib.sha256((analysis_directory(path) / 'summary.json').read_bytes()).hexdigest()
                                 for path, identifier, _, _ in requests},
        'asset_sha256': {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                         for name in ('index.html', 'dashboard.css', 'dashboard.js')}}
    if empirical:
        result['empirical_index'] = 'empirical/index.html'
    write_json(output / 'report.json', result)
    return result
