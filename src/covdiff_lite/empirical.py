"""Derive auditable empirical tables and figures from frozen saved observations."""

import csv
import hashlib
import html
import math
import shutil
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from .calibration import MISSING
from .figures import CLASSIFICATIONS, LABELS, plot_tables, require_matplotlib
from .io import write_json
from .report import analysis_directory, load_suite, read_json


TOOLS = ('gcov', 'llvm-cov')


def write_csv(path, rows, fields):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def timing_statistics(values):
    if any(not math.isfinite(value) or value < 0 for value in values):
        raise ValueError('Invalid saved duration')
    return {'n': len(values), 'mean_seconds': statistics.mean(values) if values else None,
            'median_seconds': statistics.median(values) if values else None,
            'p95_seconds': sorted(values)[math.ceil(len(values)*.95)-1] if values else None,
            'total_seconds': sum(values)}


def summarize_suite(suite, path):
    """Count first-pass source locations once; command successes retain their own denominator."""
    families, rules, patterns = defaultdict(Counter), Counter(), Counter()
    pipeline, timings, exclusions = defaultdict(Counter), [], Counter()
    case_counts, valid_classifications = Counter(), Counter()
    failures, repeated, stable, valid_cases, oracle_trace_cases = 0, 0, 0, 0, 0
    scored_tool_counts, scored_tool_errors, comparable_tool_errors = Counter(), Counter(), Counter()
    hashes = []
    for case in suite['cases']:
        case_counts[case['classification']] += 1
        hashes.append(case['source_sha256'])
        family = families[case['family']]
        family['programs'] += 1
        family[case['classification']] += 1
        repeat = case['repeats'][0]
        valid = (not repeat['errors'] and repeat['oracle_trusted'] and
                 all(repeat['observations'][t] is not None and repeat['outputs'][t] == case['expected_output'] for t in TOOLS))
        valid_cases += valid
        family['valid_first_pass_cases'] += valid
        if valid:
            valid_classifications[case['classification']] += 1
        failures += case['classification'] == 'pipeline_failure'
        repeated += case['runs'] > 1
        stable += case['stable'] is True
        if case['oracle_validation']:
            oracle_trace_cases += case['oracle_validation']['passed'] is True
        timings.append({'case_id': case['case_id'], 'family': case['family'], 'valid_first_pass': valid,
                        'runs': case['runs'], 'first_pass_seconds': case['first_pass_seconds'],
                        'repeat_seconds': case['repeat_seconds']})
        for row in case['lines']:
            family['source_lines'] += 1
            expected = row['expected']
            observations = {tool: (repeat['observations'][tool] or {}).get(str(row['line']), MISSING) for tool in TOOLS}
            both = all(repeat['observations'][tool] is not None and observations[tool]['state'] == 'reported' for tool in TOOLS)
            if expected is None:
                family['unscored_lines'] += 1
                exclusions['unscored_source'] += 1
            else:
                family['annotated_lines'] += 1
                if both:
                    family['comparable_lines'] += 1
                    if valid:
                        family['valid_comparable_lines'] += 1
                else:
                    family['unmapped_oracle_lines'] += 1
                    reason = ('unavailable_tool_report' if any(repeat['observations'][t] is None for t in TOOLS)
                              else 'allowed_dead_body_elision' if expected.get('allow_elided')
                              else 'unresolved_missing_oracle_mapping')
                    exclusions[reason] += 1
                for tool in TOOLS:
                    if observations[tool]['state'] == 'reported':
                        family[tool + '_reported_oracle_lines'] += 1
                        if valid:
                            scored_tool_counts[tool] += 1
                            wrong = observations[tool]['count'] != expected['count']
                            scored_tool_errors[tool] += wrong
                            comparable_tool_errors[tool] += wrong and both
            if valid:
                left, right = observations['gcov'], observations['llvm-cov']
                family['mapping_differences'] += left['state'] != right['state']
                family['raw_count_disagreements'] += both and left['count'] != right['count']
                family['raw_binary_disagreements'] += both and left['covered'] != right['covered']
        if valid:
            rules.update(f['rule_id'] for f in repeat['findings'] if f.get('rule_id'))
        if case['review']:
            patterns.update(o['pattern'] for o in case['review']['observations'])
        for index, collection in enumerate(case['repeats']):
            for tool in TOOLS:
                directory = path / 'cases' / case['case_id'] / f'repeat-{index}' / tool
                commands_path = directory / 'commands.json'
                commands = read_json(commands_path) if commands_path.exists() else []
                for period in (['first_pass', 'all_collections'] if index == 0 else ['all_collections']):
                    for command in commands:
                        row = pipeline[(period, tool, command['stage'])]
                        passed = command['exit_code'] == command.get('expected_exit', 0) and not command.get('timed_out', False)
                        row['attempted'] += 1; row['succeeded'] += passed
                        row['failures'] += not passed; row['timeouts'] += command.get('timed_out', False)
                        row['seconds'] += command.get('duration_seconds', 0)
                    executed = any(c['stage'] == 'execute' for c in commands)
                    if executed:
                        row = pipeline[(period, tool, 'functional_output')]
                        matches = collection['outputs'][tool] == case['expected_output']
                        row['attempted'] += 1; row['succeeded'] += matches; row['failures'] += not matches
                    extraction = 'extract' if tool == 'gcov' else 'export'
                    extracted = any(c['stage'] == extraction and c['exit_code'] == c.get('expected_exit', 0)
                                    and not c.get('timed_out', False) for c in commands)
                    if extracted:
                        row = pipeline[(period, tool, 'parsed_report')]
                        parsed = collection['observations'][tool] is not None
                        row['attempted'] += 1; row['succeeded'] += parsed; row['failures'] += not parsed
                    if tool == 'llvm-cov' and collection['observations'][tool] is not None:
                        row = pipeline[(period, tool, 'normalization_validation')]
                        passed = not any(e['tool'] == tool and e['stage'] == 'normalization_validation' for e in collection['errors'])
                        row['attempted'] += 1; row['succeeded'] += passed; row['failures'] += not passed
    totals = Counter()
    for family in families.values():
        totals.update({key: value for key, value in family.items() if key not in CLASSIFICATIONS})
    saved = suite['summary']
    # Failed first passes remain in case totals, but do not enter agreement/disagreement rates.
    expected_comparable = sum(family['valid_comparable_lines'] for family in families.values())
    for key, actual in [('comparable_lines', expected_comparable), ('mapping_differences', totals['mapping_differences']),
                        ('raw_count_disagreements', totals['raw_count_disagreements']),
                        ('raw_binary_disagreements', totals['raw_binary_disagreements'])]:
        if key in saved and saved[key] != actual:
            raise ValueError(f'Saved summary differs from empirical observations: {key}')
    if saved['oracle_mismatches'] != {tool: scored_tool_errors[tool] for tool in TOOLS}:
        raise ValueError('Saved oracle totals differ from empirical observations')
    valid_times = [row['first_pass_seconds'] for row in timings if row['valid_first_pass']]
    repeat_times = [row['repeat_seconds'] for row in timings if row['valid_first_pass']]
    metrics = {'id': suite['id'], 'label': suite['label'], 'programs': len(suite['cases']),
        'unique_sources': len(set(hashes)), 'valid_first_pass_cases': valid_cases,
        'oracle_trace_cases_passed': oracle_trace_cases, 'classifications': dict(case_counts),
        'valid_classifications': dict(valid_classifications), 'repeated_cases': repeated, 'stable_cases': stable,
        'unstable_cases': case_counts['unstable_or_non_reproducible'], 'pipeline_failure_cases': failures,
        'coverage_collections': sum(c['runs'] for c in suite['cases']), 'locations': dict(totals),
        'excluded_locations': dict(exclusions), 'scored_observations_per_tool': dict(scored_tool_counts),
        'oracle_mismatches': {tool: scored_tool_errors[tool] for tool in TOOLS},
        'comparable_oracle_mismatches': {tool: comparable_tool_errors[tool] for tool in TOOLS},
        'convention_rule_observations': dict(rules), 'review_patterns': dict(patterns),
        'review_statuses': dict(Counter(c['review_status'] for c in suite['cases'])),
        'first_pass_timing': timing_statistics(valid_times), 'confirmation_timing': timing_statistics(repeat_times),
        'all_attempted_first_pass_timing': timing_statistics([row['first_pass_seconds'] for row in timings]),
        'branches': {'mapping_status': 'not_implemented', 'comparable_outcomes': 0},
        'environment': suite['environment'], 'experiment': suite['context'].get('experiment.json'),
        'documented_issues': suite['context'].get('documented-issues.json'),
        'layout_controls': suite['context'].get('layout-results.json')}
    stages = [{'period': period, 'tool': tool, 'stage': stage, **{k: counter[k] for k in
                ('attempted', 'succeeded', 'failures', 'timeouts', 'seconds')}}
              for (period, tool, stage), counter in sorted(pipeline.items())]
    return metrics, families, stages, timings


def markdown_table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(map(str, headers)) + ' |',
                      '| ' + ' | '.join('---' for _ in headers) + ' |'] +
                     ['| ' + ' | '.join(str(value).replace('|', '\\|').replace('\n', ' ') for value in row) + ' |' for row in rows])


def analysis_sections(metrics):
    main = metrics['suites'][0]; loc = main['locations']; classes = main['classifications']
    common = loc.get('valid_comparable_lines', 0)
    sections = [('Result and interpretation', [
        f"The primary dataset contains {main['programs']} programs and {main['unique_sources']} distinct source hashes. "
        f"{main['valid_first_pass_cases']} programs passed both functional pipelines and the trusted-oracle checks. "
        f"There are {common} valid mutually reported oracle locations and "
        f"{sum(main['oracle_mismatches'].values())} contradictory tool–location observations.",
        f"The mutually exclusive case totals include {classes.get('known_convention_difference', 0)} known-convention cases, "
        f"{classes.get('unresolved_disagreement', 0)} unresolved cases, "
        f"{classes.get('probable_incorrect_coverage_report', 0)} probable incorrect reports, "
        f"{main['unstable_cases']} unstable cases, and {main['pipeline_failure_cases']} pipeline failures. "
        "Unresolved mappings are not established tool bugs. Agreement at these finite oracle locations is not a general reliability estimate."], []),
        ('Denominators and reporting conventions', [
        f"{loc.get('source_lines', 0)} source lines comprise {loc.get('annotated_lines', 0)} annotated oracle locations "
        f"and {loc.get('unscored_lines', 0)} unscored locations. "
        f"{loc.get('unmapped_oracle_lines', 0)} annotated locations lack a mapping in at least one tool. Missing is never zero.",
        f"{loc.get('raw_count_disagreements', 0)} raw count differences include {loc.get('raw_binary_disagreements', 0)} binary differences; "
        f"{loc.get('mapping_differences', 0)} missing/present differences are counted separately. "
        "Raw observations cover unscored lines as well as statements. Convention observations count matched findings, not independent bugs."],
        [('Tool', 'Reported oracle locations in valid cases', 'Contradictions', 'Contradictions on common locations'),
         *[(tool, main['scored_observations_per_tool'].get(tool, 0), main['oracle_mismatches'][tool],
            main['comparable_oracle_mismatches'][tool]) for tool in TOOLS]]),
        ('Repeatability and review', [
        f"{main['repeated_cases']} cases were repeated; {main['stable_cases']} had stable saved signatures. "
        f"There were {main['coverage_collections']} paired collections. A paired collection builds and runs both coverage pipelines; "
        "separate noncoverage oracle traces are not included in that count.",
        "Review overlays retain original classifications. Reviewed unresolved patterns remain unresolved; any pending or manual inspection statuses remain visible."],
        [('Review status', 'Cases'), *sorted(main['review_statuses'].items())])]
    sections.append(('Convention rules and unresolved patterns', [
        'Each main-dataset difference is retained with its matched frozen rule or unresolved review pattern. '
        'These counts describe observations, not independent defects. Empty review-pattern counts mean no overlay was supplied.'],
        [('Rule or reviewed pattern', 'Observations'),
         *sorted(main['convention_rule_observations'].items()), *sorted(main['review_patterns'].items())]))
    for additional in metrics['suites'][1:]:
        issue = additional['documented_issues']; layout = additional['layout_controls']
        if issue:
            sections.append(('Separate documented issue fixtures', [
                f"{issue['distinct_patterns_reproduced']} distinct documented patterns reproduced across {issue['cases']} fixtures. "
                "Positive variants and the corrective control are separate from the generated primary corpus. "
                "A positive variant is not another independent bug."],
                [('Fixture', 'Tool', 'Role', 'Symptom check'), *[(r['case_id'], r['tool'], r['role'], r['status']) for r in issue['results']]]))
        if layout:
            sections.append(('Separate paired layout controls', [
                f"{layout['pairs_passed']}/{layout['pairs']} pairs passed over {layout['compared_statement_pairs']} semantic statement pairs. "
                f"Mapping totals changed in {layout['pairs_with_mapping_total_change']} pairs and case classifications in "
                f"{layout['pairs_with_classification_change']} pairs. These changes are evidence of layout-sensitive reporting and rule matching, not new bugs.",
                "The same scored statement observations can coexist with different displayed source mappings. "
                "Frozen convention rules are deliberately not broadened to absorb new layouts."], []))
    timing = main['first_pass_timing']; experiment = main['experiment'] or {}
    sections.append(('Time and resource scope', [
        f"Valid first-pass timing includes {timing['n']} cases: mean {timing['mean_seconds']}, "
        f"median {timing['median_seconds']}, nearest-rank p95 {timing['p95_seconds']} seconds. "
        f"Confirmation collections total {main['confirmation_timing']['total_seconds']:.6f} seconds.",
        f"Recorded generation/analysis wall time: {experiment.get('elapsed_seconds', 'not available')} seconds. "
        "Case coverage timings exclude the earlier oracle-trace phase; total analysis time includes it. "
        "Figures/reporting costs and Docker startup/build are separate. Command-stage time sums do not substitute for wall time.",
        "RSS is the recorded maximum individual child, not aggregate memory. Container cgroup memory and artifact allocation are separate measures. "
        "Resource values belong to their saved experiment context, not to this post-processing run."],
        [('Saved measurement', 'Value', 'Unit'),
         *[(label, experiment.get(key, 'not recorded'), unit) for key, label, unit in (
             ('generation_seconds', 'Generation time', 'seconds'),
             ('analysis_seconds', 'Analysis including traces and repeats', 'seconds'),
             ('elapsed_seconds', 'Generation + analysis wall time', 'seconds'),
             ('maximum_individual_child_rss_kib', 'Maximum individual child RSS', 'KiB'),
             ('cgroup_memory_peak_bytes', 'Container cgroup peak memory', 'bytes'),
             ('cgroup_memory_limit_bytes', 'Container cgroup memory limit', 'bytes'),
             ('artifact_logical_bytes_before_summary', 'Pre-publication logical artifacts', 'bytes'),
             ('artifact_allocated_bytes_before_summary', 'Pre-publication allocated artifacts', 'bytes'))]]))
    sections.append(('Scope and limitations', [
        "The experiment uses finite deterministic C11 templates, one compiler/reporter version pair, -O0, bounded inputs, and one machine. "
        "Programs within a template family are related; case rates are descriptive and do not assume independent random sampling.",
        "The semantic oracle is derived from templates and independently checked with execution traces, but an oracle or shared parser error remains possible. "
        "Native LLVM display checks and raw gcov evidence provide cross-checks. Unscored locations are excluded instead of assigned invented expected counts.",
        "Semantic branch alignment and MC/DC are not implemented. Comparable branch outcomes are zero. Automatic reduction is not implemented. "
        "No previously unknown bug is claimed by this analysis."], []))
    return sections


def write_analysis_pages(output, metrics, stages):
    sections = analysis_sections(metrics)
    main = metrics['suites'][0]
    families = metrics['family_rows']
    sections.insert(2, ('Results by construct', [],
        [('Family', 'Programs', 'Comparable', 'Scored unmapped', 'Known convention', 'Unresolved'),
         *[(r['family'], r['programs'], r['comparable_lines'], r['unmapped_oracle_lines'],
            r['known_convention_difference'], r['unresolved_disagreement']) for r in families]]))
    sections.insert(3, ('Pipeline success denominators', [
        'First-pass stages below use attempted commands or available outputs/reports as their denominators. '
        'A stage never reached is not a failed attempt. All-collection totals, failures and timeouts are retained in pipeline-stages.csv.'],
        [('Tool', 'Stage', 'Successful / attempted'), *[(r['tool'], r['stage'], f"{r['succeeded']} / {r['attempted']}")
          for r in stages if r['period'] == 'first_pass']]))
    md, body = ['# CovDiff-Lite empirical analysis\n'], []
    for title, paragraphs, table in sections:
        md.append('## ' + title + '\n')
        body.append('<section><h2>' + html.escape(title) + '</h2>')
        for paragraph in paragraphs:
            md.append(paragraph + '\n'); body.append('<p>' + html.escape(paragraph) + '</p>')
        if table:
            md.append(markdown_table(table[0], table[1:]) + '\n')
            body.append('<div class="scroll"><table><thead><tr>' + ''.join('<th>'+html.escape(str(v))+'</th>' for v in table[0]) + '</tr></thead><tbody>')
            body.extend('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in row)+'</tr>' for row in table[1:])
            body.append('</tbody></table></div>')
        body.append('</section>')
    md.append('## Figures and provenance\n')
    for name in ('classifications', 'families', 'denominators', 'runtime'):
        md.append(f'![{name}](figures/{name}.svg)\n')
        body.append(f'<figure><img src="figures/{name}.svg" alt="Primary dataset: {name}"><figcaption><a href="figures/{name}.png">PNG</a> · <a href="figures/{name}.svg">SVG</a></figcaption></figure>')
    md.append('Machine-readable metrics and original measurement environments: [metrics.json](metrics.json). '
              'Plot inputs: [tables/](tables/). Figures can be regenerated using the plots command.\n')
    body.append('<p><a href="metrics.json">Metrics and provenance</a> · <a href="analysis.md">Markdown analysis</a> · <a href="tables/">CSV plotting inputs</a></p>')
    if metrics.get('dashboard_href'):
        body.insert(0, '<p><a href="'+html.escape(metrics['dashboard_href'], quote=True)+'">Open source comparison dashboard →</a></p>')
        md.insert(1, '[Source comparison dashboard](' + metrics['dashboard_href'] + ')\n')
    (output / 'analysis.md').write_text('\n'.join(md))
    style = 'body{font:16px/1.6 system-ui,sans-serif;color:#19313b;background:#f6f8f7;margin:0}main{max-width:1050px;margin:auto;padding:40px 24px}h1{font-size:34px}h2{margin-top:35px;font-size:22px}a{color:#12776d}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:9px 12px;text-align:left;border-bottom:1px solid #d9e1de}th{background:#e8efeb}.scroll{overflow:auto}figure{background:white;margin:25px 0;padding:12px;border:1px solid #d9e1de;border-radius:8px}img{width:100%;height:auto}figcaption{font-size:12px}section{break-inside:avoid}'
    (output / 'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CovDiff-Lite empirical analysis</title><style>'+style+'</style><main><h1>CovDiff-Lite empirical analysis</h1>'+''.join(body)+'</main></html>')


def write_publication_manifest(output):
    write_json(output / 'publication.json', {'schema_version': 1,
        'artifact_sha256': {str(path.relative_to(output)): hashlib.sha256(path.read_bytes()).hexdigest()
                           for path in sorted(output.rglob('*')) if path.is_file() and path.name != 'publication.json'}})


def generate_empirical(analysis: Path, output: Path, review: Path | None = None,
                       documented_issues: Path | None = None, layout_controls: Path | None = None,
                       layout_review: Path | None = None, dashboard_href: str | None = None):
    if output.exists():
        raise FileExistsError(output)
    if layout_review and not layout_controls:
        raise ValueError('Layout review requires layout controls')
    require_matplotlib()
    requests = [(analysis, 'main', 'Primary dataset', review)]
    if documented_issues:
        requests.append((documented_issues, 'issues', 'Documented fixtures', None))
    if layout_controls:
        requests.append((layout_controls, 'layout', 'Paired layout controls', layout_review))
    loaded, evidence_hashes, evidence_digests = [], {}, {}
    for path, identifier, label, overlay in requests:
        suite, evidence = load_suite(path, identifier, label, overlay)
        loaded.append((suite, summarize_suite(suite, analysis_directory(path))))
        digest = hashlib.sha256()
        for source, relative in sorted(evidence, key=lambda item: str(item[1])):
            file_digest = hashlib.sha256(source.read_bytes()).hexdigest()
            digest.update(str(relative).encode() + b'\0' + file_digest.encode() + b'\n')
            if len(relative.parts) == 3:
                evidence_hashes[str(relative)] = file_digest
        evidence_digests[identifier] = {'files': len(evidence), 'sha256': digest.hexdigest(),
            'algorithm': 'SHA256 of sorted relative-path + NUL + file-SHA256 + newline records'}
    output.mkdir(parents=True)
    tables = output / 'tables'; tables.mkdir()
    primary, (_, families, stages, timing) = loaded[0]
    fields = ['family', 'programs', 'valid_first_pass_cases', 'source_lines', 'annotated_lines',
              'comparable_lines', 'valid_comparable_lines', 'unmapped_oracle_lines', 'unscored_lines',
              'gcov_reported_oracle_lines', 'llvm-cov_reported_oracle_lines', 'mapping_differences',
              'raw_count_disagreements', 'raw_binary_disagreements', *CLASSIFICATIONS]
    family_rows = [{'family': name, **{field: counts[field] for field in fields[1:]}} for name, counts in sorted(families.items())]
    write_csv(tables / 'families.csv', family_rows, fields)
    write_csv(tables / 'classifications.csv', [{'classification': c, 'label': label, 'cases': primary['summary']['classification_counts'].get(c, 0)} for c, label in zip(CLASSIFICATIONS, LABELS)], ['classification', 'label', 'cases'])
    write_csv(tables / 'timing.csv', timing, ['case_id', 'family', 'valid_first_pass', 'runs', 'first_pass_seconds', 'repeat_seconds'])
    write_csv(tables / 'pipeline-stages.csv', stages, ['period', 'tool', 'stage', 'attempted', 'succeeded', 'failures', 'timeouts', 'seconds'])
    write_csv(tables / 'convention-rules.csv', [{'rule_id': k, 'observations': v} for k, v in sorted(loaded[0][1][0]['convention_rule_observations'].items())], ['rule_id', 'observations'])
    write_csv(tables / 'review-patterns.csv', [{'pattern': k, 'observations': v} for k, v in sorted(loaded[0][1][0]['review_patterns'].items())], ['pattern', 'observations'])
    for path, identifier, _, overlay in requests:
        raw = analysis_directory(path)
        for name in ('cases.csv', 'observations.csv'):
            if (raw / name).is_file():
                shutil.copyfile(raw / name, tables / (identifier + '-' + name))
    for suite, _ in loaded[1:]:
        if suite['context'].get('documented-issues.json'):
            write_csv(tables / 'documented-issues.csv', suite['context']['documented-issues.json']['results'], ['case_id', 'issue_id', 'tool', 'role', 'line', 'status', 'passed', 'url'])
        if suite['context'].get('layout-results.json'):
            rows = [{'pair_id': p['pair_id'], 'family': p['family'], 'passed': p['passed'],
                     'statements': len(p['statements']), 'base_mapping_differences': p['mapping_differences']['base'],
                     'variant_mapping_differences': p['mapping_differences']['variant'],
                     'base_classification': p['classifications']['base'], 'variant_classification': p['classifications']['variant']}
                    for p in suite['context']['layout-results.json']['results']]
            write_csv(tables / 'layout-pairs.csv', rows, list(rows[0]) if rows else ['pair_id'])
    metrics = {'schema_version': 1, 'purpose': 'frozen_evidence_empirical_analysis',
        'suites': [result[0] for _, result in loaded], 'family_rows': family_rows,
        'input_evidence_sha256': evidence_hashes, 'input_evidence_digests': evidence_digests,
        'dashboard_href': dashboard_href,
        'denominator_policy': 'Case counts include failures; agreement rates and raw differences use valid first passes. '
                              'Tool/location denominators differ from mutually reported locations. Repeats and additional suites stay separate.',
        'measurement_data_changed': False}
    metrics['figures'] = plot_tables(tables, output / 'figures')
    write_json(output / 'metrics.json', metrics)
    write_analysis_pages(output, metrics, stages)
    write_publication_manifest(output)
    return {'schema_version': 1, 'index': 'index.html', 'markdown': 'analysis.md',
            'programs': metrics['suites'][0]['programs'], 'suites': len(loaded),
            'figures': metrics['figures']['files'], 'measurement_data_changed': False}
