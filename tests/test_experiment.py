import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from covdiff_lite.environment import inspect_environment
from covdiff_lite.experiment import load_config, run_experiment

ROOT = Path(__file__).resolve().parents[1]


class ExperimentConfigTests(unittest.TestCase):
    def test_frozen_configs_are_balanced_and_sequential(self):
        pilot = load_config(ROOT / 'configs/pilot.json')
        main = load_config(ROOT / 'configs/main.json')
        self.assertEqual(pilot['per_family'] * 8, 40)
        self.assertEqual(main['per_family'] * 8, 320)
        self.assertEqual(main['workers'], 1)

    def test_invalid_config_does_not_create_run_artifacts(self):
        original = load_config(ROOT / 'configs/pilot.json')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / 'config.json'
            for key, value in [('workers', 4), ('seed', -1), ('per_family', 65),
                               ('control_fraction', float('nan')), ('unexpected', 1)]:
                config.write_text(json.dumps({**original, key: value}))
                with self.assertRaises(ValueError):
                    run_experiment(config, root / 'should-not-exist')
                self.assertFalse((root / 'should-not-exist').exists())


@unittest.skipUnless(inspect_environment()['ready'], 'requires pinned compilers in Docker')
class ExperimentIntegrationTests(unittest.TestCase):
    def test_one_command_pipeline_retains_data_and_resource_measurements(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = load_config(ROOT / 'configs/pilot.json')
            config['per_family'] = 1
            path = root / 'config.json'
            path.write_text(json.dumps(config))
            with contextlib.redirect_stdout(io.StringIO()):
                result = run_experiment(path, root / 'result')
            self.assertEqual(result['programs'], 8)
            self.assertEqual(result['valid_first_pass_cases'], 8)
            self.assertEqual(result['oracle_mismatches'], {'gcov': 0, 'llvm-cov': 0})
            self.assertGreater(result['maximum_individual_child_rss_kib'], 0)
            self.assertGreater(result['artifact_logical_bytes_before_summary'], 0)
            self.assertTrue((root / 'result/analysis/observations.csv').exists())
            self.assertTrue((root / 'result/dataset/dataset.json').exists())
            self.assertTrue((root / 'result/report/index.html').exists())
            self.assertGreater(result['report_seconds'], 0)
            self.assertEqual(result['html_report'], 'report/index.html')
            report = json.loads((root / 'result/report/report.json').read_text())
            self.assertEqual(report['suites'][0]['cases'], 8)
            self.assertFalse(report['measurement_data_changed'])
            self.assertTrue((root / 'result/empirical/figures/families.svg').exists())
            self.assertTrue((root / 'result/report/empirical/index.html').exists())
            self.assertEqual(result['empirical_report'], 'empirical/index.html')
            with self.assertRaises(FileExistsError):
                run_experiment(path, root / 'result')
