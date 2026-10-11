import copy
import hashlib
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from covdiff_lite.empirical import generate_empirical, summarize_suite, timing_statistics
from covdiff_lite.report import generate_report, load_suite
from covdiff_lite.io import write_json
from test_report import synthetic_analysis


class EmpiricalTests(unittest.TestCase):
    def test_denominators_distinguish_missing_zero_and_unscored_locations(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = synthetic_analysis(Path(tmp) / 'input')
            suite, _ = load_suite(path, 'main', 'Synthetic')
            metrics, families, _, _ = summarize_suite(suite, path)
            self.assertEqual(metrics['programs'], 1)
            self.assertEqual(metrics['locations']['source_lines'], 3)
            self.assertEqual(metrics['locations']['annotated_lines'], 1)
            self.assertEqual(metrics['locations']['unscored_lines'], 2)
            self.assertEqual(metrics['locations'].get('comparable_lines', 0), 0)
            self.assertEqual(metrics['locations']['unmapped_oracle_lines'], 1)
            self.assertEqual(metrics['scored_observations_per_tool']['gcov'], 1)
            self.assertEqual(metrics['oracle_mismatches'], {'gcov': 0, 'llvm-cov': 0})

    def test_shared_wrong_counts_are_not_hidden_by_tool_agreement(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = synthetic_analysis(Path(tmp) / 'input')
            suite, _ = load_suite(path, 'main', 'Synthetic')
            case = suite['cases'][0]
            case['classification'] = 'probable_incorrect_coverage_report'
            observed = {'2': {'state': 'reported', 'count': 1, 'covered': True}}
            case['repeats'][0]['observations'] = {'gcov': observed, 'llvm-cov': copy.deepcopy(observed)}
            suite['summary']['oracle_mismatches'] = {'gcov': 1, 'llvm-cov': 1}
            suite['summary']['comparable_lines'] = 1
            metrics, _, _, _ = summarize_suite(suite, path)
            self.assertEqual(metrics['locations']['valid_comparable_lines'], 1)
            self.assertEqual(metrics['locations'].get('raw_count_disagreements', 0), 0)
            self.assertEqual(metrics['oracle_mismatches'], {'gcov': 1, 'llvm-cov': 1})
            self.assertEqual(metrics['comparable_oracle_mismatches'], {'gcov': 1, 'llvm-cov': 1})

    def test_failed_cases_stay_in_totals_and_unreached_stages_are_not_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = synthetic_analysis(Path(tmp) / 'input', failed=True)
            directory = path / 'cases/synthetic_case/repeat-0/gcov'; directory.mkdir()
            write_json(directory / 'commands.json', [{'stage': 'compile', 'exit_code': 1,
                'expected_exit': 0, 'timed_out': False, 'duration_seconds': .01}])
            suite, _ = load_suite(path, 'main', 'Synthetic')
            metrics, _, stages, _ = summarize_suite(suite, path)
            self.assertEqual(metrics['programs'], 1)
            self.assertEqual(metrics['pipeline_failure_cases'], 1)
            self.assertEqual(metrics['valid_first_pass_cases'], 0)
            self.assertEqual(metrics['first_pass_timing']['n'], 0)
            first = [r for r in stages if r['period'] == 'first_pass' and r['tool'] == 'gcov']
            self.assertEqual(len(first), 1)
            self.assertEqual(first[0]['stage'], 'compile')
            self.assertEqual((first[0]['attempted'], first[0]['succeeded']), (1, 0))

    def test_timing_uses_nearest_rank_and_empty_is_not_zero(self):
        self.assertEqual(timing_statistics(list(range(1, 21)))['p95_seconds'], 19)
        self.assertIsNone(timing_statistics([])['mean_seconds'])
        with self.assertRaises(ValueError):
            timing_statistics([float('nan')])

    def test_figures_publication_hashes_and_portable_dashboard_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); path = synthetic_analysis(root / 'input')
            before = {p: p.read_bytes() for p in path.rglob('*') if p.is_file()}
            result = generate_empirical(path, root / 'empirical', dashboard_href='../dashboard/index.html')
            self.assertEqual(result['programs'], 1)
            self.assertEqual(len(result['figures']), 8)
            for name in result['figures']:
                p = root / 'empirical/figures' / name
                if p.suffix == '.svg':
                    self.assertTrue(ET.parse(p).getroot().tag.endswith('svg'))
                else:
                    self.assertTrue(p.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'))
            publication = json.loads((root / 'empirical/publication.json').read_text())
            for name, digest in publication['artifact_sha256'].items():
                self.assertEqual(hashlib.sha256((root / 'empirical' / name).read_bytes()).hexdigest(), digest)
            report = generate_report(path, root / 'dashboard', empirical=root / 'empirical')
            self.assertEqual(report['empirical_index'], 'empirical/index.html')
            copied = root / 'dashboard/empirical'
            self.assertIn('href="../index.html"', (copied / 'index.html').read_text())
            self.assertIn('Empirical analysis', (root / 'dashboard/index.html').read_text())
            manifest = json.loads((copied / 'publication.json').read_text())
            for name, digest in manifest['artifact_sha256'].items():
                self.assertEqual(hashlib.sha256((copied / name).read_bytes()).hexdigest(), digest)
            self.assertEqual(before, {p: p.read_bytes() for p in before})
            metrics = json.loads((root / 'empirical/metrics.json').read_text())
            metrics['input_evidence_sha256']['evidence/main/summary.json'] = 'stale'
            write_json(root / 'empirical/metrics.json', metrics)
            with self.assertRaisesRegex(ValueError, 'does not match'):
                generate_report(path, root / 'should-not-exist', empirical=root / 'empirical')
            self.assertFalse((root / 'should-not-exist').exists())
