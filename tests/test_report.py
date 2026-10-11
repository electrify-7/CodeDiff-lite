"""Report checks use labelled synthetic observations, never experimental results."""

import copy
import hashlib
import json
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from covdiff_lite.compare import compare_observations
from covdiff_lite.io import write_json
from covdiff_lite.repeat import classify, semantic_signature
from covdiff_lite.report import generate_report, load_suite, script_json


class DataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_data = False
        self.data = ''
        self.external = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'script' and attrs.get('id') == 'report-data':
            self.in_data = True
        if tag in ('script', 'link'):
            self.external.extend(v for k, v in attrs.items() if k in ('src', 'href'))

    def handle_endtag(self, tag):
        if tag == 'script':
            self.in_data = False

    def handle_data(self, value):
        if self.in_data:
            self.data += value


def synthetic_analysis(root, failed=False, unstable=False):
    root.mkdir()
    source = 'int main(void) {\n  return 0; /* </script><img src=x onerror=alert(1)> @@TITLE@@ */\n}\n'
    manifest = {'schema_version': 1, 'case_id': 'synthetic_case', 'family': 'synthetic',
        'origin': 'handwritten_calibration', 'source': 'case.c',
        'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
        'expected_output': {'stdout': '</script> & <output>\n', 'exit_code': 0},
        'lines': {'2': {'count': 0, 'allow_elided': False, 'statement_id': 'return'}}}
    directory = root / 'cases/synthetic_case'
    directory.mkdir(parents=True)
    (directory / 'case.c').write_text(source)
    write_json(directory / 'manifest.json', manifest)
    reports = {'gcov': {'lines': {'2': {'state': 'reported', 'count': 0, 'covered': False}}},
               'llvm-cov': {'lines': {}}}
    errors = [{'tool': 'gcov', 'stage': 'compile', 'message': '<failed> & unsafe'}] if failed else []
    if failed:
        del reports['gcov']
    assessments, signatures, failures = [], [], []
    for i in range(3):
        current = copy.deepcopy(reports)
        if unstable and i == 1:
            current['llvm-cov']['lines']['2'] = {'state': 'reported', 'count': 2, 'covered': True}
        a = compare_observations(manifest, source, current, {}, True)
        sig = semantic_signature({'reports': current, 'errors': errors})
        assessments.append(a); signatures.append(sig); failures.append(errors)
        repeat = directory / f'repeat-{i}'
        repeat.mkdir()
        write_json(repeat / 'analysis.json', {'assessment': a, 'signature': sig, 'errors': errors, 'oracle_trusted': True})
        write_json(repeat / 'normalized.json', {'schema_version': 1, 'tools': current})
        for tool in current:
            tool_dir = repeat / tool
            tool_dir.mkdir()
            write_json(tool_dir / 'commands.json', [{'stage': 'execute', 'exit_code': 0}])
            (tool_dir / 'execute.stdout').write_text(manifest['expected_output']['stdout'])
            (tool_dir / 'case').write_bytes(b'large binary deliberately excluded')
    a = assessments[0]
    result = {'case_id': manifest['case_id'], 'family': manifest['family'],
        'classification': classify(assessments, signatures, failures), 'runs': 3,
        'stable': len(set(signatures)) == 1, 'signatures': signatures,
        'manual_review': 'pending', 'first_pass_seconds': .1, 'repeat_seconds': .2,
        **{k: a[k] for k in ('comparable_lines', 'mapping_differences', 'oracle_mismatches',
                             'raw_count_disagreements', 'raw_binary_disagreements')}}
    write_json(directory / 'analysis.json', result)
    write_json(root / 'summary.json', {'schema_version': 1, 'cases': 1, 'results': [result],
        'classification_counts': {result['classification']: 1}, 'comparable_lines': a['comparable_lines'],
        'oracle_mismatches': a['oracle_mismatches'], 'coverage_collections': 3})
    write_json(root / 'environment.json', {'schema_version': 1, 'tools': {}})
    return root


class ReportTests(unittest.TestCase):
    def test_json_script_escapes_html_and_round_trips(self):
        value = {'source': '</script><script>alert(1)</script>&\u2028\u2029'}
        encoded = script_json(value)
        self.assertNotIn('<', encoded)
        self.assertNotIn('&', encoded)
        self.assertEqual(json.loads(encoded), value)

    def test_portable_bundle_preserves_missing_zero_source_and_frozen_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); analysis = synthetic_analysis(root / 'input')
            before = {p: p.read_bytes() for p in analysis.rglob('*') if p.is_file()}
            result = generate_report(analysis, root / 'report')
            parser = DataParser(); parser.feed((root / 'report/index.html').read_text())
            data = json.loads(parser.data); case = data['suites'][0]['cases'][0]
            self.assertIn('</script>', case['lines'][1]['source'])
            self.assertIn('@@TITLE@@', case['lines'][1]['source'])
            self.assertEqual(case['repeats'][0]['observations']['gcov']['2']['count'], 0)
            self.assertEqual(case['repeats'][0]['observations']['llvm-cov'], {})
            self.assertEqual(case['classification'], 'unresolved_disagreement')
            self.assertEqual(case['review_status'], 'pending')
            for asset in parser.external:
                self.assertTrue((root / 'report' / asset).is_file())
                self.assertNotIn('://', asset)
            for _, relative in load_suite(analysis, 'main', 'Test')[1]:
                self.assertTrue((root / 'report' / relative).is_file())
            self.assertFalse(list((root / 'report').rglob('case')))
            self.assertFalse(result['measurement_data_changed'])
            self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_failed_tool_is_unavailable_and_unstable_repeats_stay_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            failed, _ = load_suite(synthetic_analysis(root / 'failed', failed=True), 'main', 'Test')
            self.assertEqual(failed['cases'][0]['classification'], 'pipeline_failure')
            self.assertIsNone(failed['cases'][0]['repeats'][0]['observations']['gcov'])
            unstable, _ = load_suite(synthetic_analysis(root / 'unstable', unstable=True), 'main', 'Test')
            c = unstable['cases'][0]
            self.assertEqual(c['classification'], 'unstable_or_non_reproducible')
            self.assertFalse(c['stable'])
            self.assertEqual(c['repeats'][1]['observations']['llvm-cov']['2']['count'], 2)
            self.assertEqual(c['repeats'][0]['observations']['llvm-cov'], {})

    def test_review_overlay_requires_matching_source_classification_and_observations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); analysis = synthetic_analysis(root / 'input')
            manifest = json.loads((analysis / 'cases/synthetic_case/manifest.json').read_text())
            case = {'case_id': 'synthetic_case', 'family': 'synthetic', 'source_sha256': manifest['source_sha256'],
                'runs': 3, 'stable': True, 'classification_retained': 'unresolved_disagreement',
                'review_status': 'reviewed_mapping_unresolved', 'decision': 'Unresolved.', 'observations': []}
            review = {'schema_version': 1, 'original_classifications_unchanged': True, 'reviews': [case]}
            path = root / 'review.json'; write_json(path, review)
            suite, _ = load_suite(analysis, 'main', 'Test', path)
            self.assertEqual(suite['cases'][0]['review_status'], 'reviewed_mapping_unresolved')
            observations = json.loads((analysis / 'cases/synthetic_case/repeat-0/analysis.json').read_text())['assessment']['lines']
            observation = {k: observations[1][k] for k in ('line', 'source', 'expected', 'gcov', 'llvm-cov')}
            review['reviews'][0]['observations'] = [observation]
            write_json(path, review)
            load_suite(analysis, 'main', 'Test', path)
            forged = copy.deepcopy(review)
            forged['reviews'][0]['observations'][0]['gcov']['count'] = 9
            write_json(path, forged)
            with self.assertRaisesRegex(ValueError, 'Review tool observation'):
                load_suite(analysis, 'main', 'Test', path)
            for key, value in [('source_sha256', 'stale'), ('classification_retained', 'complete_agreement'),
                               ('observations', [{'line': 2, 'source': 'stale source', 'expected': None}])]:
                altered = copy.deepcopy(review); altered['reviews'][0][key] = value; write_json(path, altered)
                with self.assertRaises(ValueError):
                    generate_report(analysis, root / 'never-created', path)
                self.assertFalse((root / 'never-created').exists())

    def test_invalid_evidence_and_existing_output_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); analysis = synthetic_analysis(root / 'input')
            output = root / 'existing'; output.mkdir()
            with self.assertRaises(FileExistsError):
                generate_report(analysis, output)
            normalized = analysis / 'cases/synthetic_case/repeat-0/normalized.json'
            value = json.loads(normalized.read_text()); value['tools']['gcov']['lines']['2']['count'] = 5
            write_json(normalized, value)
            with self.assertRaisesRegex(ValueError, 'Normalized report'):
                generate_report(analysis, root / 'never-created')
            self.assertFalse((root / 'never-created').exists())

    def test_stale_summary_and_symlinked_evidence_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); analysis = synthetic_analysis(root / 'input')
            summary_path = analysis / 'summary.json'; summary = json.loads(summary_path.read_text())
            summary['cases'] = 2; write_json(summary_path, summary)
            with self.assertRaisesRegex(ValueError, 'summary counts'):
                load_suite(analysis, 'main', 'Test')
            summary['cases'] = 1; write_json(summary_path, summary)
            external = root / 'external.json'; external.write_text('{}')
            (analysis / 'config.json').symlink_to(external)
            with self.assertRaisesRegex(ValueError, 'regular file'):
                load_suite(analysis, 'main', 'Test')
