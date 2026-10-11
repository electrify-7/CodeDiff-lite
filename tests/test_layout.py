import contextlib
import copy
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from covdiff_lite.calibration import load_fixture
from covdiff_lite.controls import compare_statements, run_layout_controls
from covdiff_lite.environment import inspect_environment
from covdiff_lite.generator import generate_dataset, make_case, selected_parameters, validate_generated_manifest
from covdiff_lite.layout import c_tokens, generate_layout_controls, make_layout_case, transform_braces
from covdiff_lite.review import review_analysis, unresolved_pattern
from covdiff_lite.templates import FAMILIES


class LayoutManifestTests(unittest.TestCase):
    def test_all_families_keep_tokens_oracles_and_precise_statement_locations(self):
        for family in FAMILIES:
            for p in selected_parameters(family, 2, 20261010):
                original, base = make_case(family, p, 20261010)
                source, variant = make_layout_case(family, p, 20261010)
                self.assertNotEqual(source, original)
                self.assertEqual(c_tokens(original), c_tokens(source))
                self.assertEqual(base['oracle'], variant['oracle'])
                self.assertEqual(base['expected_output'], variant['expected_output'])
                validate_generated_manifest(variant, source)
                base_statements = {entry['statement_id']: original.splitlines()[int(n)-1]
                                   for n, entry in base['lines'].items()}
                for n, entry in variant['lines'].items():
                    self.assertEqual(source.splitlines()[int(n)-1], base_statements[entry['statement_id']])
                    self.assertEqual(entry['column'], len(source.splitlines()[int(n)-1]) - len(source.splitlines()[int(n)-1].lstrip()) + 1)

    def test_layout_manifest_cannot_forge_counts_provenance_or_source(self):
        p = selected_parameters('loops', 2, 0)[1]
        source, manifest = make_layout_case('loops', p, 0)
        for change in ('count', 'parent', 'source'):
            mutated = copy.deepcopy(manifest)
            changed_source = source
            if change == 'count':
                mutated['lines'][next(iter(mutated['lines']))]['count'] += 1
            elif change == 'parent':
                mutated['layout_control']['parent_source_sha256'] = '0' * 64
            else:
                changed_source += '// unreviewed source change\n'
                mutated['source_sha256'] = hashlib.sha256(changed_source.encode()).hexdigest()
            with self.assertRaises(ValueError):
                validate_generated_manifest(mutated, changed_source)

    def test_directives_and_braces_inside_literals_are_unchanged(self):
        source = '#define ADD(x) do { x++; } while (0)\nint main(void) {\n    printf("{ }");\n}\n'
        roles = {str(n): {'role': role, 'semantic_id': None}
                 for n, role in enumerate(('macro_definition', 'structure', 'statement', 'structure'), 1)}
        transformed, _, _ = transform_braces(source, roles)
        self.assertEqual(transformed.splitlines()[0], source.splitlines()[0])
        self.assertIn('    printf("{ }");', transformed)
        self.assertEqual(c_tokens(source), c_tokens(transformed))

    def test_dataset_has_sixteen_pairs_and_a_true_constant_macro_control(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            generate_dataset(root / 'main', 40, 20261010)
            result = generate_layout_controls(root / 'main', root / 'controls')
            self.assertEqual(result['pair_count'], 16)
            self.assertEqual(result['programs'], 32)
            constants = [p for p in result['pairs'] if p['family'] == 'constants']
            self.assertTrue(any(p['parameters']['form'] == 'macro' and p['parameters']['enabled'] == 1 for p in constants))
            for path in (root / 'controls/cases').glob('*.json'):
                load_fixture(path)
            index_path = root / 'main/dataset.json'
            index = json.loads(index_path.read_text())
            index['dataset_sha256'] = '0' * 64
            index_path.write_text(json.dumps(index))
            with self.assertRaises(ValueError):
                generate_layout_controls(root / 'main', root / 'invalid')
            self.assertFalse((root / 'invalid').exists())


class PairedComparisonTests(unittest.TestCase):
    def test_equal_but_incorrect_counts_do_not_pass_a_pair(self):
        observed = {'state': 'reported', 'count': 2}
        side = {'s': {'line': 1, 'expected': 1, 'allow_elided': False,
                      'gcov': observed, 'llvm-cov': observed}}
        result = compare_statements(side, side)
        self.assertTrue(result[0]['observations_equal'])
        self.assertFalse(result[0]['oracle_counts_correct'])

    def test_only_explicitly_elided_zero_statements_allow_missing_mappings(self):
        missing = {'state': 'not_reported', 'count': None}
        side = {'s': {'line': 1, 'expected': 0, 'allow_elided': True,
                      'gcov': missing, 'llvm-cov': {'state': 'reported', 'count': 0}}}
        self.assertTrue(compare_statements(side, side)[0]['oracle_counts_correct'])
        changed = copy.deepcopy(side)
        changed['s']['allow_elided'] = False
        self.assertFalse(compare_statements(changed, changed)[0]['oracle_counts_correct'])

    def test_new_or_scored_findings_require_further_inspection(self):
        manifest = {'family': 'constants', 'parameters': {'enabled': 1}}
        row = {'expected': None, 'source': 'if (1) {', 'role': 'condition'}
        self.assertEqual(unresolved_pattern(manifest, row), 'constant_condition_header')
        self.assertEqual(unresolved_pattern(manifest, {**row, 'expected': {'count': 0}}), 'requires_manual_inspection')
        self.assertEqual(unresolved_pattern(manifest, {**row, 'source': 'unexpected();'}), 'requires_manual_inspection')

    def test_layout_review_is_restricted_to_verified_unscored_syntax(self):
        manifest = {'family': 'if_else', 'layout_control': {'version': 1}}
        row = {'expected': None, 'source': 'int main(void)', 'role': 'structure'}
        self.assertEqual(unresolved_pattern(manifest, row), 'separate_function_header')
        self.assertEqual(unresolved_pattern(manifest, {**row, 'source': 'else'}), 'separate_else_keyword')
        self.assertEqual(unresolved_pattern(manifest, {**row, 'expected': {'count': 0}}), 'requires_manual_inspection')
        self.assertEqual(unresolved_pattern({'family': 'if_else'}, row), 'requires_manual_inspection')


@unittest.skipUnless(inspect_environment()['ready'], 'requires pinned compilers in Docker')
class LayoutIntegrationTests(unittest.TestCase):
    def test_pairs_match_traces_and_counts_and_audit_detects_corrupted_evidence(self):
        with tempfile.TemporaryDirectory() as temporary, contextlib.redirect_stdout(io.StringIO()):
            root = Path(temporary)
            generate_dataset(root / 'main', 40, 20261010)
            result = run_layout_controls(root / 'main', root / 'controls')
            self.assertEqual(result['pairs_passed'], 16)
            self.assertEqual(result['coverage_collections'], 96)
            self.assertEqual(result['oracle_mismatches'], {'gcov': 0, 'llvm-cov': 0})
            analysis = root / 'controls/analysis'
            review = review_analysis(analysis, root / 'review.json')
            self.assertEqual(review['paired_collections_audited'], 96)
            self.assertTrue(review['raw_evidence_checks_passed'])
            self.assertEqual(review['cases_requiring_further_inspection'], 0)
            selected = next((analysis / 'cases').glob('*/repeat-0/analysis.json'))
            record = json.loads(selected.read_text())
            row = next(row for row in record['assessment']['lines'] if row['gcov']['count'] is not None)
            row['gcov']['count'] += 1
            selected.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, 'raw report/normalized'):
                review_analysis(analysis, root / 'should-not-pass.json')
            self.assertFalse((root / 'should-not-pass.json').exists())
