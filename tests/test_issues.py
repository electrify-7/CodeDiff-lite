import contextlib
import copy
import io
import tempfile
import unittest
from pathlib import Path

from covdiff_lite.calibration import load_fixture
from covdiff_lite.environment import inspect_environment
from covdiff_lite.issues import check_symptom, reproduce_issues

ROOT = Path(__file__).resolve().parents[1]


class IssueSymptomTests(unittest.TestCase):
    def setUp(self):
        self.manifest, _ = load_fixture(ROOT / 'fixtures/issues/llvm_140427.json')
        line = int(next(iter(self.manifest['lines'])))
        self.result = {'runs': 3, 'stable': True, 'errors': [[], [], []],
                       'findings': [{'kind': 'oracle_count', 'tool': 'llvm-cov',
                                     'line': line, 'expected': 1, 'actual': 4}]}

    def test_only_the_documented_tool_and_location_count_as_reproduction(self):
        self.assertTrue(check_symptom(self.manifest, self.result)['passed'])
        for key, value in [('tool', 'gcov'), ('line', 999), ('actual', 1)]:
            changed = copy.deepcopy(self.result)
            changed['findings'][0][key] = value
            self.assertFalse(check_symptom(self.manifest, changed)['passed'])

    def test_failed_unstable_or_unconfirmed_runs_do_not_count(self):
        for key, value in [('runs', 1), ('stable', False), ('errors', [[{'stage': 'compile'}]])]:
            changed = {**self.result, key: value}
            self.assertFalse(check_symptom(self.manifest, changed)['passed'])

    def test_controls_require_no_scored_oracle_contradictions(self):
        control = copy.deepcopy(self.manifest)
        control['documented_issue']['role'] = 'negative_control'
        self.assertFalse(check_symptom(control, self.result)['passed'])
        self.assertTrue(check_symptom(control, {**self.result, 'findings': []})['passed'])


@unittest.skipUnless(inspect_environment()['ready'], 'requires pinned compilers in Docker')
class DocumentedIssueIntegrationTests(unittest.TestCase):
    def test_two_patterns_and_corrective_control_against_real_tools(self):
        with tempfile.TemporaryDirectory() as temporary, contextlib.redirect_stdout(io.StringIO()):
            summary = reproduce_issues(ROOT / 'fixtures/issues', Path(temporary) / 'issues')
        self.assertEqual(summary['distinct_patterns_reproduced'], 2)
        self.assertTrue(summary['all_checks_passed'])
        results = {r['case_id']: r for r in summary['results']}
        self.assertEqual(results['llvm_140427_control']['status'], 'control_passed')
        self.assertEqual(results['llvm_140427_never']['matching_findings'][0]['kind'], 'oracle_binary')
