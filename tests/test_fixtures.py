import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from covdiff_lite.calibration import load_fixture, run_calibration
from covdiff_lite.environment import inspect_environment


ROOT = Path(__file__).resolve().parents[1]


class ManifestTests(unittest.TestCase):
    def test_calibration_has_two_cases_per_family(self):
        families = {}
        for path in (ROOT / 'fixtures/calibration').glob('*.json'):
            manifest, _ = load_fixture(path)
            families[manifest['family']] = families.get(manifest['family'], 0) + 1
        self.assertEqual(len(families), 8)
        self.assertEqual(set(families.values()), {2})

    def test_changed_source_invalidates_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for path in (ROOT / 'fixtures/smoke').iterdir():
                shutil.copyfile(path, root / path.name)
            source = root / 'smoke.c'
            source.write_text(source.read_text() + '// changed\n')
            with self.assertRaisesRegex(ValueError, 'Stale oracle'):
                load_fixture(root / 'smoke.json')


@unittest.skipUnless(inspect_environment()['ready'], 'requires both matched toolchains; use scripts/env.sh test')
class IntegrationTests(unittest.TestCase):
    def test_all_fixtures_and_fresh_run_requirement(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'run'
            with contextlib.redirect_stdout(io.StringIO()):
                summary = run_calibration(ROOT / 'fixtures/calibration', output)
            self.assertEqual(summary['passed'], 16, summary['results'])
            self.assertEqual(summary['comparable_lines'], 63)
            for result in summary['results']:
                self.assertTrue(result['llvm_display_check']['matched'])
                directory = output / 'cases' / result['case_id']
                self.assertEqual(len(list((directory / 'gcov').glob('*.gcov.json.gz'))), 1)
                self.assertTrue((directory / 'llvm-cov/case.profraw').exists())
                for name in ('gcov', 'llvm-cov'):
                    commands = json.loads((directory / name / 'commands.json').read_text())
                    self.assertTrue(all(command['exit_code'] == 0 for command in commands))
            with self.assertRaises(FileExistsError):
                run_calibration(ROOT / 'fixtures/calibration', output)

    def test_equal_but_wrong_functional_outputs_fail_both_tools(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = root / 'fixtures'
            fixture.mkdir()
            for path in (ROOT / 'fixtures/smoke').iterdir():
                shutil.copyfile(path, fixture / path.name)
            path = fixture / 'smoke.json'
            manifest = json.loads(path.read_text())
            manifest['expected_output']['stdout'] = 'incorrect oracle\n'
            path.write_text(json.dumps(manifest))
            with contextlib.redirect_stdout(io.StringIO()):
                summary = run_calibration(fixture, root / 'run')
            result = summary['results'][0]
            self.assertEqual(result['status'], 'pipeline_failure')
            self.assertEqual(len(result['errors']), 2)
            self.assertEqual({error['stage'] for error in result['errors']}, {'functional_output'})
            self.assertEqual(result['mismatches'], [])
