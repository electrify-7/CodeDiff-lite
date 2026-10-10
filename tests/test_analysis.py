import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from covdiff_lite.analysis import run_analysis
from covdiff_lite.compare import compare_observations
from covdiff_lite.environment import inspect_environment
from covdiff_lite.generator import generate_dataset
from covdiff_lite.repeat import classify, semantic_signature


VERSIONS = {'gcov': '11.4.0', 'llvm-cov': '14.0.0'}
ROOT = Path(__file__).resolve().parents[1]


def report(count, line='1'):
    lines = {} if count is None else {line: {'state': 'reported', 'count': count, 'covered': count > 0}}
    return {'lines': lines, 'branches': [], 'expansions': []}


def compare(expected, gcc, llvm, text='result += 1;', **metadata):
    manifest = {'lines': {'1': expected} if expected is not None else {}, **metadata}
    return compare_observations(manifest, text, {'gcov': report(gcc), 'llvm-cov': report(llvm)}, VERSIONS)


class ComparisonTests(unittest.TestCase):
    def test_shared_binary_error_is_found_without_tool_disagreement(self):
        assessment = compare({'count': 0}, 1, 1)
        self.assertEqual(assessment['raw_count_disagreements'], 0)
        self.assertEqual(assessment['oracle_mismatches'], {'gcov': 1, 'llvm-cov': 1})
        self.assertEqual({f['kind'] for f in assessment['findings']}, {'oracle_binary'})
        self.assertEqual(classify([assessment] * 3, ['same'] * 3, [[], [], []]), 'probable_incorrect_coverage_report')

    def test_exact_counts_detect_errors_with_equal_binary_coverage(self):
        assessment = compare({'count': 3}, 3, 4)
        self.assertEqual(assessment['raw_count_disagreements'], 1)
        self.assertEqual(assessment['raw_binary_disagreements'], 0)
        self.assertEqual(assessment['findings'][0]['kind'], 'oracle_count')

    def test_no_probable_bug_without_three_confirmations(self):
        assessment = compare({'count': 0}, 1, 1)
        self.assertEqual(classify([assessment], ['same'], [[]]), 'unresolved_disagreement')

    def test_unstable_observations_take_precedence(self):
        assessment = compare({'count': 0}, 1, 1)
        self.assertEqual(classify([assessment] * 3, ['a', 'b', 'a'], [[], [], []]), 'unstable_or_non_reproducible')

    def test_missing_is_unresolved_and_excluded(self):
        assessment = compare({'count': 0}, None, 0)
        self.assertEqual(assessment['comparable_lines'], 0)
        self.assertEqual(assessment['mapping_differences'], 1)
        self.assertEqual(assessment['oracle_mismatches'], {'gcov': 0, 'llvm-cov': 0})
        self.assertEqual(assessment['findings'][0]['assessment'], 'unresolved_disagreement')
        self.assertIsNone(assessment['lines'][0]['gcov']['count'])

    def test_constant_rule_is_narrow_and_cannot_hide_wrong_counts(self):
        correct = compare({'count': 0, 'allow_elided': True}, None, 0, family='constants')
        self.assertEqual(correct['findings'][0]['rule_id'], 'constant_dead_body_elision_v1')
        wrong = compare({'count': 0, 'allow_elided': True}, None, 1, family='constants')
        self.assertNotIn('rule_id', wrong['findings'][0])
        self.assertEqual(wrong['findings'][0]['assessment'], 'candidate_incorrect_report')
        self.assertEqual(compare({'count': 0}, None, 0, family='macros')['findings'][0]['assessment'], 'unresolved_disagreement')

    def test_scored_case_label_is_never_hidden_as_a_convention(self):
        assessment = compare({'count': 1, 'role': 'case_label'}, 4, 1, text='case 0:')
        self.assertEqual(assessment['findings'][0]['assessment'], 'candidate_incorrect_report')
        self.assertNotIn('rule_id', assessment['findings'][0])

    def test_macro_family_is_not_a_blanket_exclusion(self):
        assessment = compare({'count': 0}, 0, 1, text='ADD_TO(result, 1);', family='macros')
        self.assertEqual(assessment['findings'][0]['assessment'], 'candidate_incorrect_report')

    def test_unknown_tool_versions_do_not_receive_convention_rules(self):
        assessment = compare_observations({'lines': {}}, '}', {'gcov': report(None), 'llvm-cov': report(1)},
                                          {'gcov': '99', 'llvm-cov': '99'})
        self.assertEqual(assessment['findings'][0]['assessment'], 'unresolved_disagreement')

    def test_complete_agreement_and_pipeline_failures(self):
        assessment = compare({'count': 1}, 1, 1)
        self.assertEqual(classify([assessment], ['a'], [[]]), 'complete_agreement')
        self.assertEqual(classify([assessment], ['a'], [[{'stage': 'compile'}]]), 'pipeline_failure')


class SignatureTests(unittest.TestCase):
    def test_signatures_ignore_paths_in_expansions_and_timing(self):
        first = {'reports': {'llvm-cov': report(1)}, 'errors': [], 'duration_seconds': 1}
        first['reports']['llvm-cov']['expansions'] = [{'filenames': ['/run/one/case.c'], 'source_region': [1, 1]}]
        second = copy.deepcopy(first)
        second['duration_seconds'] = 99
        second['reports']['llvm-cov']['expansions'][0]['filenames'] = ['/run/two/case.c']
        self.assertEqual(semantic_signature(first), semantic_signature(second))
        second['reports']['llvm-cov']['lines']['1']['count'] = 2
        self.assertNotEqual(semantic_signature(first), semantic_signature(second))

    def test_signatures_include_outputs_and_branch_counts(self):
        execution = {'reports': {'gcov': report(1)}, 'errors': [], 'functional_outputs': {'gcov': {'stdout': '1', 'exit_code': 0}}}
        changed = copy.deepcopy(execution)
        changed['functional_outputs']['gcov']['stdout'] = '2'
        self.assertNotEqual(semantic_signature(execution), semantic_signature(changed))
        changed = copy.deepcopy(execution)
        changed['reports']['gcov']['lines']['1']['branches'] = [{'count': 2}]
        self.assertNotEqual(semantic_signature(execution), semantic_signature(changed))


@unittest.skipUnless(inspect_environment()['ready'], 'requires pinned compilers in Docker')
class AnalysisIntegrationTests(unittest.TestCase):
    def test_generated_cases_validate_oracles_and_confirm_findings(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            generate_dataset(root / 'input', 2, 17)
            with contextlib.redirect_stdout(io.StringIO()):
                summary = run_analysis(root / 'input/cases', root / 'analysis')
            self.assertEqual(summary['cases'], 16)
            self.assertEqual(summary['valid_first_pass_cases'], 16)
            self.assertEqual(summary['oracle_mismatches'], {'gcov': 0, 'llvm-cov': 0})
            self.assertNotIn('pipeline_failure', summary['classification_counts'])
            for result in summary['results']:
                self.assertTrue(result['oracle_validation']['passed'])
                if result['findings']:
                    self.assertEqual(result['runs'], 3)
                    self.assertTrue(result['stable'])
            selected = summary['results'][0]
            manifest_path = root / 'analysis/cases' / selected['case_id'] / 'manifest.json'
            with contextlib.redirect_stdout(io.StringIO()):
                reproduction = run_analysis(None, root / 'reproduced', case=manifest_path)
            self.assertEqual(reproduction['results'][0]['classification'], selected['classification'])
            self.assertTrue((root / 'analysis/cases.csv').exists())
            self.assertTrue((root / 'analysis/observations.csv').exists())

    def test_synthetic_report_mutation_is_confirmed_in_fresh_directories(self):
        # This is classifier validation, never a real-tool bug finding.
        from covdiff_lite.calibration import execute_case as actual_execution

        def mutated(manifest, source, directory, tools):
            result = actual_execution(manifest, source, directory, tools)
            line = next(iter(manifest['lines']))
            result['reports']['llvm-cov']['lines'][line]['count'] += 1
            return result

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch('covdiff_lite.analysis.execute_case', side_effect=mutated), contextlib.redirect_stdout(io.StringIO()):
                summary = run_analysis(ROOT / 'fixtures/smoke', root / 'analysis')
            result = summary['results'][0]
            self.assertEqual(result['classification'], 'probable_incorrect_coverage_report')
            self.assertEqual(result['runs'], 3)
            for index in range(3):
                self.assertTrue((root / 'analysis/cases/smoke' / f'repeat-{index}/gcov/case.gcda').exists())
