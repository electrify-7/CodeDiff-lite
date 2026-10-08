import gzip
import json
import tempfile
import unittest
from pathlib import Path

from covdiff_lite.calibration import compare_lines, validate_llvm_display
from covdiff_lite.parsers.gcov import parse_gcov
from covdiff_lite.parsers.llvm import parse_llvm, segment_lines


class SegmentTests(unittest.TestCase):
    def test_region_continuation_and_endpoint(self):
        lines = segment_lines([[2, 1, 3, True, True, False], [4, 2, 0, False, False, False]], 6)
        self.assertEqual({k: v['count'] for k, v in lines.items()}, {'2': 3, '3': 3, '4': 3})

    def test_unexecuted_region_is_reported_zero(self):
        lines = segment_lines([[2, 1, 0, True, True, False], [2, 8, 0, False, False, False]], 3)
        self.assertEqual(lines['2']['count'], 0)
        self.assertFalse(lines['2']['covered'])
        self.assertNotIn('1', lines)

    def test_gap_entry_does_not_override_body_count(self):
        lines = segment_lines([[2, 1, 1, True, True, False], [2, 9, 9, True, True, True],
                               [3, 1, 0, False, False, False]], 3)
        self.assertEqual(lines['2']['count'], 1)

    def test_skipped_region_suppresses_mapping(self):
        lines = segment_lines([[1, 1, 1, True, True, False], [2, 1, 0, False, True, False],
                               [3, 1, 1, True, True, False]], 3)
        self.assertNotIn('2', lines)

    def test_non_entry_segment_does_not_mark_a_line(self):
        self.assertEqual(segment_lines([[2, 3, 8, True, False, False]], 2), {})

    def test_multiple_regions_use_valid_entries(self):
        lines = segment_lines([[2, 1, 0, True, True, False], [2, 4, 2, True, True, False]], 2)
        self.assertEqual(lines['2']['count'], 2)
        self.assertTrue(lines['2']['multiple_regions'])

    def test_rejects_unsupported_and_unsorted_segments(self):
        for segments in ([[1, 1, 0, True, True]], [[2, 1, 1, True, True, False], [1, 1, 1, True, True, False]],
                         [[1, 1, -1, True, True, False]], [[1, 1, 0, 1, True, False]]):
            with self.subTest(segments=segments), self.assertRaises(ValueError):
                segment_lines(segments, 3)


class FileParserTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'case.c'
        self.source.write_text('int main(void) {\n    return 0;\n}\n')

    def test_gcov_retains_zero_partial_blocks_and_branches(self):
        path = self.root / 'case.gcov.json.gz'
        report = {'format_version': '1', 'current_working_directory': str(self.root), 'files': [
            {'file': 'case.c', 'lines': [{'line_number': 2, 'count': 0, 'unexecuted_block': True,
                                        'branches': [{'count': 0, 'fallthrough': True}]}]}]}
        with gzip.open(path, 'wt') as stream:
            json.dump(report, stream)
        parsed = parse_gcov(path, self.source)
        self.assertEqual(parsed['lines']['2']['count'], 0)
        self.assertTrue(parsed['lines']['2']['unexecuted_block'])
        self.assertEqual(len(parsed['lines']['2']['branches']), 1)
        self.assertNotIn('1', parsed['lines'])

    def test_gcov_rejects_version_and_wrong_source(self):
        for version, file in [('2', str(self.source)), ('1', 'other.c')]:
            path = self.root / 'case.gcov.json.gz'
            with gzip.open(path, 'wt') as stream:
                json.dump({'format_version': version, 'files': [{'file': file, 'lines': []}]}, stream)
            with self.assertRaises(ValueError):
                parse_gcov(path, self.source)

    def test_llvm_preserves_branches_and_expansions(self):
        path = self.root / 'llvm.json'
        path.write_text(json.dumps({'type': 'llvm.coverage.json.export', 'version': '2.0.1', 'data': [{'files': [{
            'filename': str(self.source), 'segments': [[1, 1, 1, True, True, False], [3, 2, 0, False, False, False]],
            'branches': [[1, 1, 1, 2, 1, 0]], 'expansions': [{'test': 'preserved'}], 'summary': {}}]}]}))
        parsed = parse_llvm(path, self.source)
        self.assertEqual(parsed['lines']['2']['count'], 1)
        self.assertEqual(parsed['expansions'], [{'test': 'preserved'}])
        self.assertEqual(len(parsed['branches']), 1)

    def test_llvm_rejects_unknown_schema(self):
        path = self.root / 'llvm.json'
        path.write_text(json.dumps({'type': 'llvm.coverage.json.export', 'version': '3.0.0'}))
        with self.assertRaises(ValueError):
            parse_llvm(path, self.source)


class CalibrationComparisonTests(unittest.TestCase):
    def test_both_tools_can_agree_and_contradict_oracle(self):
        manifest = {'lines': {'2': {'count': 0}}}
        reports = {name: {'lines': {'2': {'state': 'reported', 'count': 1, 'covered': True}}}
                   for name in ('gcov', 'llvm-cov')}
        result = compare_lines(manifest, reports)
        self.assertEqual(len(result['mismatches']), 2)
        self.assertEqual(result['comparable_lines'], 1)

    def test_missing_is_not_zero(self):
        result = compare_lines({'lines': {'2': {'count': 0}}}, {'gcov': {'lines': {}}, 'llvm-cov': {'lines': {}}})
        self.assertIsNone(result['lines']['2']['gcov']['count'])
        self.assertEqual(len(result['mismatches']), 2)
        self.assertEqual(result['comparable_lines'], 0)

    def test_explicit_constant_elision_is_unscored(self):
        result = compare_lines({'lines': {'2': {'count': 0, 'allow_elided': True}}},
                               {'gcov': {'lines': {}}, 'llvm-cov': {'lines': {}}})
        self.assertEqual(result['mismatches'], [])
        self.assertEqual(result['comparable_lines'], 0)

    def test_failed_tool_does_not_create_coverage_findings(self):
        result = compare_lines({'lines': {'2': {'count': 1}}}, {})
        self.assertEqual(result['mismatches'], [])
        self.assertEqual(result['lines']['2']['gcov']['state'], 'unsupported')

    def test_macro_file_view_can_have_more_lines_than_summary(self):
        report = {'lines': {'1': {'count': 1}, '3': {'count': 1}},
                  'summary': {'lines': {'count': 1, 'covered': 1}}, 'expansions': [{'source_region': []}]}
        result = validate_llvm_display(report, '1|1|#define FOO\n3|1|FOO;\n')
        self.assertTrue(result['matched'])
        self.assertEqual(result['summary_scope'], 'function_views_with_expansions')

    def test_display_mismatch_is_still_detected_for_macros(self):
        report = {'lines': {'3': {'count': 0}}, 'summary': {'lines': {'count': 1, 'covered': 0}},
                  'expansions': [{'source_region': []}]}
        self.assertFalse(validate_llvm_display(report, '3|1|FOO;\n')['matched'])
