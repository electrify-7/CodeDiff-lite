"""One command for new measurements, separate controls, audits and publication."""

import time
from pathlib import Path

from .calibration import load_fixture
from .controls import run_layout_controls
from .empirical import generate_empirical
from .environment import inspect_environment
from .experiment import load_config, run_experiment
from .figures import require_matplotlib
from .generator import selected_parameters
from .io import write_json
from .issues import reproduce_issues
from .report import generate_report
from .review import review_analysis


def validate_pipeline_config(config_path):
    config = load_config(config_path)
    constants = selected_parameters('constants', config['per_family'], config['seed'])
    if config['per_family'] < 2 or not any(p['form'] == 'macro' and p['enabled'] == 1 for p in constants):
        raise ValueError('Full pipeline requires two contrasting cases per family and a true constant-macro '
                         'case for layout controls; use configs/main.json or configs/demo.json.')
    return config


def run_pipeline(config_path: Path, output: Path, issue_fixtures: Path) -> dict:
    config = validate_pipeline_config(config_path)
    if output.exists():
        raise FileExistsError(output)
    require_matplotlib()
    environment = inspect_environment()
    if not environment['ready']:
        raise ValueError('Environment is not ready: ' + '; '.join(environment['errors']))
    manifests = [load_fixture(path)[0] for path in sorted(issue_fixtures.glob('*.json'))]
    if not manifests or any('documented_issue' not in m for m in manifests):
        raise ValueError('Full pipeline requires documented issue fixtures')
    if len({m['documented_issue']['id'] for m in manifests if m['documented_issue'].get('role') != 'negative_control'}) < 2:
        raise ValueError('Full pipeline requires at least two distinct documented problem patterns')
    output.mkdir(parents=True)
    started = time.monotonic()
    summary = {'schema_version': 1, 'purpose': 'full_reproducible_pipeline', 'config': config,
               'completed': False, 'stages': {}, 'errors': [], 'artifacts': {}}

    def stage(name, work):
        stage_started = time.monotonic()
        try:
            value = work()
        except (ValueError, OSError, KeyError, TypeError) as error:
            summary['stages'][name] = {'status': 'failed', 'seconds': time.monotonic()-stage_started,
                                      'error': str(error)}
            summary['errors'].append({'stage': name, 'message': str(error)})
            write_json(output / 'pipeline.json', summary)
            raise
        summary['stages'][name] = {'status': 'complete', 'seconds': time.monotonic()-stage_started}
        write_json(output / 'pipeline.json', summary)
        return value

    measurement = stage('primary_experiment', lambda: run_experiment(config_path, output / 'experiment', publish=False))
    issues = stage('documented_issues', lambda: reproduce_issues(issue_fixtures, output / 'documented-issues'))
    layout = stage('layout_controls', lambda: run_layout_controls(output / 'experiment/dataset', output / 'layout-controls'))
    reviews = output / 'reviews'; reviews.mkdir()
    overlays = {}
    # Audits can require manual inspection or fail on incomplete raw data. Preserve that fact and still publish failures.
    for name, path in [('primary', output / 'experiment/analysis'), ('layout', output / 'layout-controls/analysis')]:
        audit_started = time.monotonic()
        try:
            review = review_analysis(path, reviews / (name + '.json'))
            overlays[name] = reviews / (name + '.json')
            summary['stages'][name + '_review'] = {'status': 'complete', 'seconds': time.monotonic()-audit_started,
                'cases_requiring_further_inspection': review['cases_requiring_further_inspection']}
        except (ValueError, OSError, KeyError, TypeError) as error:
            summary['stages'][name + '_review'] = {'status': 'failed', 'seconds': time.monotonic()-audit_started, 'error': str(error)}
            summary['errors'].append({'stage': name + '_review', 'message': str(error)})
        write_json(output / 'pipeline.json', summary)
    empirical = stage('empirical_analysis', lambda: generate_empirical(output / 'experiment/analysis', output / 'empirical',
        overlays.get('primary'), output / 'documented-issues', output / 'layout-controls', overlays.get('layout'),
        dashboard_href='../report/index.html'))
    report = stage('offline_dashboard', lambda: generate_report(output / 'experiment/analysis', output / 'report',
        overlays.get('primary'), output / 'documented-issues', output / 'layout-controls', overlays.get('layout'),
        empirical=output / 'empirical'))
    failed_measurements = any(measurement['classification_counts'].get(c, 0)
        for c in ('pipeline_failure', 'unstable_or_non_reproducible'))
    summary.update({'completed': True, 'checks_passed': not summary['errors'] and not failed_measurements
                    and issues['all_checks_passed'] and issues['distinct_patterns_reproduced'] >= 2
                    and layout['pairs_passed'] == layout['pairs'],
        'elapsed_seconds': time.monotonic()-started, 'primary_programs': measurement['programs'],
        'primary_dataset_sha256': measurement['dataset_sha256'],
        'documented_patterns_reproduced': issues['distinct_patterns_reproduced'], 'layout_pairs_passed': layout['pairs_passed'],
        'cases_requiring_manual_inspection': sum(summary['stages'].get(name + '_review', {}).get('cases_requiring_further_inspection', 0)
                                                for name in ('primary', 'layout')),
        'artifacts': {'dashboard': 'report/' + report['index'], 'empirical_analysis': 'empirical/' + empirical['index'],
                      'markdown': 'empirical/' + empirical['markdown'], 'figures': 'empirical/figures',
                      'primary_raw_evidence': 'experiment/analysis', 'reviews': 'reviews'},
        'measurement_scope': 'Fresh configured corpus; documented fixtures and layout controls are separate suites. '
                             'Stage wall times include their own overhead; primary resource measurements exclude publication.'})
    write_json(output / 'pipeline.json', summary)
    return summary
