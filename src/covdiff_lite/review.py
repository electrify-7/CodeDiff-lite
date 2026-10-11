"""Audit saved evidence and retain unresolved semantics without reclassifying it."""

import gzip
import json
import re
from collections import Counter
from pathlib import Path

from .calibration import load_fixture
from .conventions import explain
from .io import write_json
from .repeat import semantic_signature


def unresolved_pattern(manifest, row):
    if row['expected'] is not None:
        return 'requires_manual_inspection'
    text = row['source'].strip()
    if 'layout_control' in manifest and row['role'] == 'structure':
        if text == 'int main(void)':
            return 'separate_function_header'
        if text == 'else':
            return 'separate_else_keyword'
    if manifest['family'] == 'constants':
        if row['role'] == 'condition' and text.startswith('if ('):
            return 'constant_condition_header'
        if row['role'] == 'macro_definition' and text == f"#define FLAG {manifest['parameters']['enabled']}":
            return 'constant_macro_definition'
    if (manifest['family'] == 'loops' and manifest['parameters']['style'] == 'do'
            and row['role'] == 'condition' and text in ('do {', 'do')):
        return 'do_loop_header'
    return 'requires_manual_inspection'


def raw_counts(directory):
    with gzip.open(directory / 'gcov/case.gcov.json.gz', 'rt') as stream:
        gcov = json.load(stream)
    files = [entry for entry in gcov['files'] if Path(entry['file']).name == 'case.c']
    if len(files) != 1:
        raise ValueError('Review expected exactly one raw gcov source record')
    counts = {'gcov': {str(line['line_number']): line['count'] for line in files[0]['lines']}, 'llvm-cov': {}}
    for line in (directory / 'llvm-cov/show.stdout').read_text().splitlines():
        match = re.match(r'^\s*(\d+)\|\s*(\d+)\|', line)
        if match:
            counts['llvm-cov'][str(int(match[1]))] = int(match[2])
    return counts


def review_analysis(analysis: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(output)
    summary = json.loads((analysis / 'summary.json').read_text())
    environment = json.loads((analysis / 'environment.json').read_text())
    versions = {'gcov': environment['tools']['gcov']['version'],
                'llvm-cov': environment['tools']['llvm_cov']['version']}
    patterns, rules, reviews, raw_disagreements = Counter(), Counter(), [], []
    audited_runs = audited_locations = 0
    for result in summary['results']:
        directory = analysis / 'cases' / result['case_id']
        manifest, source = load_fixture(directory / 'manifest.json')
        source_lines = source.read_text().splitlines()
        confirmed = result['runs'] >= 3 and result['stable'] is True and not any(result['errors'])
        first_rows = None
        for index in range(result['runs']):
            repeat = directory / f'repeat-{index}'
            evidence = json.loads((repeat / 'analysis.json').read_text())
            rows = evidence['assessment']['lines']
            if index == 0:
                first_rows = rows
            counts = raw_counts(repeat)
            outputs = {}
            for row in rows:
                number = str(row['line'])
                if row['source'] != source_lines[row['line'] - 1] or row['expected'] != manifest['lines'].get(number):
                    raise ValueError('Saved assessment differs from its source/oracle')
                for tool in counts:
                    if row[tool]['count'] != counts[tool].get(number):
                        raise ValueError('Review found a raw report/normalized observation contradiction')
                    audited_locations += 1
                    if row['expected'] is not None and row[tool]['count'] is not None and row[tool]['count'] != row['expected']['count']:
                        confirmed = False
                for finding in row['findings']:
                    if 'rule_id' in finding:
                        rule = explain(manifest, row['line'], row['source'], row['expected'],
                                       {tool: row[tool] for tool in counts}, versions)
                        if not rule or rule['rule_id'] != finding['rule_id']:
                            raise ValueError('Saved convention rule no longer matches its evidence')
            if evidence['signature'] != result['signatures'][index]:
                raise ValueError('Saved repeat signature differs from case summary')
            for tool in counts:
                if (repeat / tool / 'execute.stdout').read_text() != manifest['expected_output']['stdout']:
                    raise ValueError('Saved functional witness contradicts oracle')
                commands = json.loads((repeat / tool / 'commands.json').read_text())
                if any(c['timed_out'] or c['exit_code'] != c['expected_exit'] for c in commands):
                    raise ValueError('Review found a failed command')
                executions = [c for c in commands if c['stage'] == 'execute']
                if len(executions) != 1 or executions[0]['exit_code'] != manifest['expected_output']['exit_code']:
                    raise ValueError('Saved program exit contradicts oracle')
                outputs[tool] = {'stdout': (repeat / tool / 'execute.stdout').read_text(),
                                 'exit_code': executions[0]['exit_code']}
            normalized = json.loads((repeat / 'normalized.json').read_text())
            if semantic_signature({'reports': normalized['tools'], 'errors': evidence['errors'],
                                   'functional_outputs': outputs}) != evidence['signature']:
                raise ValueError('Recomputed semantic signature differs from saved evidence')
            audited_runs += 1
        observations = []
        for row in first_rows:
            for finding in row['findings']:
                if 'rule_id' in finding:
                    rules[finding['rule_id']] += 1
                if finding['assessment'] in ('unresolved_disagreement', 'candidate_incorrect_report'):
                    pattern = unresolved_pattern(manifest, row)
                    patterns[pattern] += 1
                    observations.append({'line': row['line'], 'source': row['source'], 'role': row['role'],
                        'expected': row['expected'], 'gcov': row['gcov'], 'llvm-cov': row['llvm-cov'],
                        'pattern': pattern, 'finding': finding})
            if (row['gcov']['count'] is not None and row['llvm-cov']['count'] is not None
                    and row['gcov']['count'] != row['llvm-cov']['count']):
                raw_disagreements.append({'case_id': result['case_id'], 'line': row['line'], 'role': row['role'],
                    'source': row['source'], 'expected': row['expected'],
                    'gcov': row['gcov']['count'], 'llvm-cov': row['llvm-cov']['count'], 'findings': row['findings']})
        if observations:
            reviewed = confirmed and all(o['pattern'] != 'requires_manual_inspection' for o in observations)
            reviews.append({'case_id': result['case_id'], 'family': result['family'],
                'source_sha256': manifest['source_sha256'], 'runs': result['runs'], 'stable': result['stable'],
                'classification_retained': result['classification'],
                'review_status': 'reviewed_mapping_unresolved' if reviewed else 'requires_manual_inspection',
                'decision': 'Retain original classification; no universal count assigned to unscored mappings.',
                'observations': observations})
    report = {'schema_version': 1, 'purpose': 'saved_evidence_audit_and_mapping_review',
              'original_classifications_unchanged': True, 'cases_audited': summary['cases'],
              'paired_collections_audited': audited_runs, 'source_line_tool_observations_audited': audited_locations,
              'raw_evidence_checks_passed': True, 'convention_rules_rechecked': dict(rules),
              'reviewed_cases': len(reviews), 'unresolved_observation_patterns': dict(patterns),
              'cases_requiring_further_inspection': sum(r['review_status'] == 'requires_manual_inspection' for r in reviews),
              'raw_count_disagreements': raw_disagreements, 'reviews': reviews}
    write_json(output, report)
    return report
