import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path

from covdiff_lite.calibration import load_fixture, run_calibration
from covdiff_lite.environment import inspect_environment
from covdiff_lite.generator import generate_dataset, make_case, validate_generated_manifest
from covdiff_lite.oracle import interpret
from covdiff_lite.templates import FAMILIES, build_program, parameters_for
from covdiff_lite.validation import validate_oracles


def oracle(family, parameters):
    return interpret(build_program(family, parameters))


class OracleSemanticsTests(unittest.TestCase):
    def test_all_loop_boundaries_and_styles(self):
        for p in parameters_for('loops'):
            expected = oracle('loops', p)
            iterations = max(1, p['limit']) if p['style'] == 'do' else p['limit']
            self.assertEqual(expected['statements']['loop_body'], iterations)
            self.assertEqual(expected['expected_output']['stdout'], f"{iterations * p['amount']}\n")
            condition = expected['decisions']['loop_condition']
            self.assertEqual(condition['false'], 1)
            self.assertEqual(condition['true'], iterations - (p['style'] == 'do'))

    def test_exhaustive_short_circuit_truth_table(self):
        for p in parameters_for('short_circuit'):
            expected = oracle('short_circuit', p)
            left, right = p['x'] > 0, p['y'] > 0
            chosen = (left and right) if p['op'] == '&&' else (left or right)
            skipped = not left if p['op'] == '&&' else left
            self.assertEqual(expected['decisions']['right_operand']['not_evaluated'], int(skipped))
            self.assertEqual(expected['decisions']['right_operand']['true'] + expected['decisions']['right_operand']['false'], int(not skipped))
            self.assertEqual(expected['statements']['then_body'], int(chosen))
            self.assertEqual(expected['expected_output']['stdout'], f"{p['amount'] if chosen else p['amount'] + 1}\n")

    def test_selected_switch_case_and_fallthrough_are_distinct(self):
        for p in parameters_for('switch'):
            expected = oracle('switch', p)
            zero = int(p['selector'] == 0)
            one = int(p['selector'] == 1 or (p['selector'] == 0 and p['fallthrough']))
            default = int(p['selector'] == 2)
            self.assertEqual(expected['statements']['case_zero'], zero)
            self.assertEqual(expected['statements']['case_one'], one)
            self.assertEqual(expected['statements']['default_body'], default)
            self.assertEqual(sum(expected['switches']['dispatch'].values()), 1)
            self.assertEqual(expected['expected_output']['stdout'], f"{p['amount'] * (zero + one * 2 + default * 3)}\n")

    def test_macro_execution_counts_and_constant_elision(self):
        for p in parameters_for('macros'):
            expected = oracle('macros', p)
            self.assertEqual(expected['statements']['macro_invocation'], p['enabled'] * p['repetitions'])
            self.assertEqual(expected['statements']['disabled_body'], (1 - p['enabled']) * p['repetitions'])
            self.assertEqual(expected['expected_output']['stdout'], f"{p['repetitions'] * (p['amount'] if p['enabled'] else 1)}\n")
        for p in parameters_for('constants'):
            _, manifest = make_case('constants', p, 7)
            dead = [row for row in manifest['lines'].values() if row['allow_elided']]
            self.assertEqual(len(dead), 1)
            self.assertEqual(dead[0]['count'], 0)
            self.assertEqual(manifest['expected_output']['stdout'], f"{p['amount'] if p['enabled'] else p['amount'] + 1}\n")

    def test_nested_and_ternary_outputs(self):
        for p in parameters_for('if_else'):
            expected = oracle('if_else', p)
            if p['x'] <= p['threshold']:
                value = p['amount'] + 1
                if p['nested']:
                    self.assertEqual(expected['decisions']['inner']['true'] + expected['decisions']['inner']['false'], 0)
            else:
                value = p['amount'] * (2 if p['x'] == 1 else 3) if p['nested'] else p['amount']
            self.assertEqual(expected['expected_output']['stdout'], f'{value}\n')
        for p in parameters_for('ternary'):
            expected = oracle('ternary', p)
            value = p['amount'] if p['x'] > p['threshold'] else -p['amount']
            self.assertEqual(expected['expected_output']['stdout'], f'{value}\n')
            self.assertEqual(expected['statements']['ternary_assignment'], 1)


class GeneratorTests(unittest.TestCase):
    def test_regeneration_is_byte_identical_and_seed_changes_selection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = generate_dataset(root / 'first', 5, 10)
            second = generate_dataset(root / 'second', 5, 10)
            third = generate_dataset(root / 'third', 5, 11)
            self.assertEqual(first, second)
            self.assertNotEqual(first['case_ids'], third['case_ids'])
            for path in (root / 'first').rglob('*'):
                if path.is_file():
                    self.assertEqual(path.read_bytes(), (root / 'second' / path.relative_to(root / 'first')).read_bytes())
            with self.assertRaises(FileExistsError):
                generate_dataset(root / 'first', 5, 10)

    def test_main_corpus_is_balanced_and_all_sources_are_unique(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'generated'
            summary = generate_dataset(root)
            self.assertEqual(summary['programs'], 320)
            self.assertEqual(summary['families'], {family: 40 for family in FAMILIES})
            self.assertEqual(len(set(summary['source_hashes'])), 320)
            for path in (root / 'cases').glob('*.json'):
                manifest, source = load_fixture(path)
                text = source.read_text().splitlines()
                self.assertEqual(len(manifest['line_roles']), len(text))
                for number, row in manifest['lines'].items():
                    self.assertIn('// @id ' + row['statement_id'], text[int(number) - 1])
                    self.assertIn(row['statement_id'], manifest['oracle']['statement_counts'])
                self.assertTrue(all(branch['source_span']['line'] <= len(text) for branch in manifest['branches']))

    def test_inconsistent_manifest_is_rejected_even_with_unchanged_hash(self):
        source, manifest = make_case('loops', {'limit': 3, 'amount': 2, 'style': 'while'}, 1)
        for mutation in ('count', 'output', 'events'):
            changed = copy.deepcopy(manifest)
            if mutation == 'count':
                next(iter(changed['lines'].values()))['count'] = 99
            elif mutation == 'output':
                changed['expected_output']['stdout'] = 'wrong\n'
            else:
                changed['oracle']['trace_events'] = []
            with self.assertRaises(ValueError):
                validate_generated_manifest(changed, source)

    def test_invalid_parameters_seed_and_counts_do_not_create_outputs(self):
        with self.assertRaises(ValueError):
            make_case('loops', {'limit': 100, 'amount': 2, 'style': 'while'}, 1)
        with self.assertRaises(ValueError):
            make_case('if_else', {'x': 0, 'threshold': 0, 'amount': 1, 'nested': 1}, 1)
        with tempfile.TemporaryDirectory() as temporary:
            for count, seed in [(0, 1), (1000, 1), (5, -1)]:
                destination = Path(temporary) / f'{count}_{seed}'
                with self.assertRaises(ValueError):
                    generate_dataset(destination, count, seed)
                self.assertFalse(destination.exists())


@unittest.skipUnless(inspect_environment()['ready'], 'requires pinned compilers in Docker')
class GeneratedIntegrationTests(unittest.TestCase):
    def test_contrasting_generated_controls_match_trace_and_coverage(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            generate_dataset(root / 'generated', 2, 20261010)
            with contextlib.redirect_stdout(io.StringIO()):
                trace = validate_oracles(root / 'generated/cases', root / 'trace')
                coverage = run_calibration(root / 'generated/cases', root / 'coverage')
            self.assertEqual(trace['passed'], 16, trace['results'])
            self.assertEqual(coverage['passed'], 16, coverage['results'])
            self.assertFalse(trace['coverage_collected'])
