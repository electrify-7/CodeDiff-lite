import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from covdiff_lite.environment import inspect_environment
from covdiff_lite.pipeline import run_pipeline, validate_pipeline_config


ROOT = Path(__file__).resolve().parents[1]


class PipelinePreflightTests(unittest.TestCase):
    def test_main_and_demo_have_required_layout_controls(self):
        for name in ('main', 'demo'):
            config = validate_pipeline_config(ROOT / 'configs' / (name + '.json'))
            self.assertGreaterEqual(config['per_family'], 2)

    def test_insufficient_pilot_is_refused_before_measurement(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'never-created'
            with self.assertRaisesRegex(ValueError, 'constant-macro'):
                run_pipeline(ROOT / 'configs/pilot.json', output, ROOT / 'fixtures/issues')
            self.assertFalse(output.exists())

    def test_unready_environment_creates_no_partial_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'never-created'
            with patch('covdiff_lite.pipeline.inspect_environment', return_value={'ready': False, 'errors': ['missing compiler']}):
                with self.assertRaisesRegex(ValueError, 'missing compiler'):
                    run_pipeline(ROOT / 'configs/demo.json', output, ROOT / 'fixtures/issues')
            self.assertFalse(output.exists())


@unittest.skipUnless(inspect_environment()['ready'], 'requires pinned compilers in Docker')
class PipelineIntegrationTests(unittest.TestCase):
    def test_full_pipeline_runs_controls_and_publishes_all_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'complete'
            with contextlib.redirect_stdout(io.StringIO()):
                result = run_pipeline(ROOT / 'configs/demo.json', output, ROOT / 'fixtures/issues')
            self.assertTrue(result['completed'])
            self.assertTrue(result['checks_passed'])
            self.assertEqual(result['primary_programs'], 48)
            self.assertEqual(result['documented_patterns_reproduced'], 2)
            self.assertEqual(result['layout_pairs_passed'], 16)
            self.assertEqual(result['cases_requiring_manual_inspection'], 0)
            self.assertEqual(len(result['stages']), 7)
            for name, relative in result['artifacts'].items():
                self.assertTrue((output / relative).exists(), name)
            self.assertTrue((output / 'report/empirical/figures/runtime.svg').is_file())
            with self.assertRaises(FileExistsError):
                run_pipeline(ROOT / 'configs/demo.json', output, ROOT / 'fixtures/issues')
