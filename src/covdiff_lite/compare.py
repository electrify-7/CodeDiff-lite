"""Compare every source observation while scoring only explicit oracle locations."""

from .calibration import MISSING
from .conventions import explain


def compare_observations(manifest: dict, source: str, reports: dict, versions: dict,
                         oracle_trusted=True) -> dict:
    rows, findings = [], []
    comparable = 0
    raw_disagreements = 0
    binary_disagreements = 0
    mapping_differences = 0
    oracle_mismatches = {'gcov': 0, 'llvm-cov': 0}
    for number, text in enumerate(source.splitlines(), 1):
        expected = manifest['lines'].get(str(number))
        observations = {name: reports.get(name, {}).get('lines', {}).get(str(number), MISSING).copy()
                        for name in ('gcov', 'llvm-cov')}
        gcc, llvm = observations['gcov'], observations['llvm-cov']
        both_reported = all(item['state'] == 'reported' for item in observations.values())
        mapping_difference = gcc['state'] != llvm['state']
        count_difference = both_reported and gcc['count'] != llvm['count']
        if count_difference:
            raw_disagreements += 1
            binary_disagreements += gcc['covered'] != llvm['covered']
        if mapping_difference:
            mapping_differences += 1
        if expected is not None and both_reported:
            comparable += 1
        row = {'line': number, 'source': text, 'expected': expected,
               'gcov': gcc, 'llvm-cov': llvm, 'comparable': expected is not None and both_reported,
               'role': manifest.get('line_roles', {}).get(str(number), {}).get('role', 'unannotated'),
               'findings': []}
        if expected is not None:
            for name, observed in observations.items():
                if observed['state'] == 'reported' and observed['count'] != expected['count']:
                    binary_difference = (observed['count'] > 0) != (expected['count'] > 0)
                    finding = {'line': number, 'kind': 'oracle_binary' if binary_difference else 'oracle_count',
                               'tool': name, 'expected': expected['count'], 'actual': observed['count'],
                               'assessment': 'candidate_incorrect_report' if oracle_trusted else 'unresolved_disagreement'}
                    row['findings'].append(finding)
                    oracle_mismatches[name] += 1
        missing_expected = expected is not None and not both_reported
        if mapping_difference or count_difference or missing_expected:
            rule = explain(manifest, number, text, expected, observations, versions)
            difference_kind = 'tool_binary' if both_reported and gcc['covered'] != llvm['covered'] else 'tool_count'
            finding = {'line': number, 'kind': 'mapping' if mapping_difference or missing_expected else difference_kind,
                       'tool': 'both', 'assessment': 'known_convention_difference' if rule else 'unresolved_disagreement'}
            if rule:
                finding.update(rule)
            # Oracle contradictions already explain a difference in reported counts.
            if rule or not row['findings'] or mapping_difference or missing_expected:
                row['findings'].append(finding)
        findings.extend(row['findings'])
        rows.append(row)
    branches = {'mapping_status': 'not_implemented', 'comparable_outcomes': 0,
                'gcov_arcs': sum(len(item.get('branches', [])) for item in reports.get('gcov', {}).get('lines', {}).values()),
                'llvm_regions': len(reports.get('llvm-cov', {}).get('branches', [])),
                'llvm_expansion_regions': sum(len(item.get('branches', [])) for item in reports.get('llvm-cov', {}).get('expansions', []))}
    return {'schema_version': 1, 'lines': rows, 'findings': findings, 'comparable_lines': comparable,
            'excluded_lines': len(rows) - comparable, 'raw_count_disagreements': raw_disagreements,
            'raw_binary_disagreements': binary_disagreements,
            'mapping_differences': mapping_differences, 'oracle_mismatches': oracle_mismatches,
            'branches': branches}
