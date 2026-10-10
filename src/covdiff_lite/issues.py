"""Verify the documented symptom, rather than treating any finding as a reproduction."""

from pathlib import Path

from .analysis import run_analysis
from .calibration import load_fixture
from .io import write_json


def check_symptom(manifest: dict, result: dict) -> dict:
    issue = manifest['documented_issue']
    if issue.get('symptom') != 'reported_count_exceeds_expected':
        raise ValueError('Unsupported documented issue symptom')
    locations = [int(n) for n, entry in manifest['lines'].items()
                 if entry.get('statement_id') == issue['statement_id']]
    if len(locations) != 1:
        raise ValueError('Documented symptom must identify exactly one oracle location')
    line = locations[0]
    confirmed = (result['runs'] >= 3 and result['stable'] is True
                 and not any(result['errors']))
    mismatches = [finding for finding in result['findings']
                  if finding['kind'] in ('oracle_count', 'oracle_binary')]
    matching = [finding for finding in mismatches
                if finding['tool'] == issue['tool'] and finding['line'] == line
                and finding['actual'] > finding['expected']]
    control = issue.get('role') == 'negative_control'
    passed = confirmed and (not mismatches if control else bool(matching))
    return {'case_id': manifest['case_id'], 'issue_id': issue['id'], 'url': issue['url'],
            'role': 'negative_control' if control else 'positive', 'line': line,
            'tool': issue['tool'], 'passed': passed,
            'status': ('control_passed' if control else 'reproduced') if passed else 'not_confirmed',
            'matching_findings': matching}


def reproduce_issues(fixtures: Path, output: Path) -> dict:
    manifests = {m['case_id']: m for m, _ in
                 (load_fixture(path) for path in sorted(fixtures.glob('*.json')))}
    if not manifests or any('documented_issue' not in m for m in manifests.values()):
        raise ValueError('Expected documented issue fixtures with symptom metadata')
    analysis = run_analysis(fixtures, output, control_fraction=1)
    results = [check_symptom(manifests[r['case_id']], r) for r in analysis['results']]
    reproduced = sorted({r['issue_id'] for r in results if r['status'] == 'reproduced'})
    summary = {'schema_version': 1, 'cases': len(results),
               'distinct_patterns_reproduced': len(reproduced), 'reproduced_issue_ids': reproduced,
               'all_checks_passed': all(r['passed'] for r in results), 'results': results}
    write_json(output / 'documented-issues.json', summary)
    return summary
