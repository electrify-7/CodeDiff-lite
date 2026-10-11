"""Execute paired controls and compare relocated statements by semantic ID."""

import json
from pathlib import Path

from .analysis import run_analysis
from .calibration import MISSING
from .io import write_json
from .layout import generate_layout_controls


def statement_observations(directory: Path):
    manifest = json.loads((directory / 'manifest.json').read_text())
    normalized = json.loads((directory / 'repeat-0/normalized.json').read_text())
    return {entry['statement_id']: {'line': int(number), 'expected': entry['count'],
            'allow_elided': entry.get('allow_elided', False),
            **{tool: normalized['tools'][tool]['lines'].get(number, MISSING)
               for tool in ('gcov', 'llvm-cov')}} for number, entry in manifest['lines'].items()}


def compare_statements(base, variant):
    if set(base) != set(variant):
        raise ValueError('Layout pair has different statement IDs')
    rows = []
    for identifier in base:
        left, right = base[identifier], variant[identifier]
        if left['expected'] != right['expected']:
            raise ValueError('Layout pair has different statement oracles')
        same = all((left[tool]['state'], left[tool]['count']) ==
                   (right[tool]['state'], right[tool]['count']) for tool in ('gcov', 'llvm-cov'))
        valid = all(observation[tool]['count'] == observation['expected']
                    if observation[tool]['state'] == 'reported' else
                    observation['expected'] == 0 and observation['allow_elided']
                    for observation in (left, right) for tool in ('gcov', 'llvm-cov'))
        rows.append({'statement_id': identifier, 'base': left, 'variant': right,
                     'observations_equal': same, 'oracle_counts_correct': valid})
    return rows


def run_layout_controls(dataset: Path, output: Path) -> dict:
    pairs = generate_layout_controls(dataset, output)
    analysis = run_analysis(output / 'cases', output / 'analysis', control_fraction=1)
    results = {r['case_id']: r for r in analysis['results']}
    comparisons = []
    for pair in pairs['pairs']:
        base, variant = (results[pair[key]] for key in ('base_case_id', 'variant_case_id'))
        valid = all(r['runs'] == 3 and r['stable'] is True and not any(r['errors'])
                    and r['oracle_validation']['passed'] for r in (base, variant))
        rows = compare_statements(statement_observations(output / 'analysis/cases' / base['case_id']),
                                  statement_observations(output / 'analysis/cases' / variant['case_id'])) if valid else []
        parent_path = dataset.parent / 'analysis/cases' / base['case_id'] / 'analysis.json'
        parent_signature = json.loads(parent_path.read_text())['signatures'][0] if parent_path.exists() else None
        statement_invariance = bool(rows) and all(r['observations_equal'] and r['oracle_counts_correct'] for r in rows)
        comparisons.append({**pair, 'passed': valid and statement_invariance,
            'statement_observations_equal': statement_invariance,
            'parent_main_baseline_signature': parent_signature,
            'base_reproduces_main_signature': base['signatures'][0] == parent_signature if parent_signature else None,
            'classifications': {'base': base['classification'], 'variant': variant['classification']},
            'mapping_differences': {'base': base['mapping_differences'], 'variant': variant['mapping_differences']},
            'raw_count_disagreements': {'base': base['raw_count_disagreements'], 'variant': variant['raw_count_disagreements']},
            'statements': rows})
    summary = {'schema_version': 1, 'purpose': 'paired_layout_controls',
               'parent_dataset_sha256': pairs['parent_dataset_sha256'],
               'dataset_sha256': pairs['dataset_sha256'], 'pairs': len(comparisons),
               'pairs_passed': sum(pair['passed'] for pair in comparisons), 'programs': analysis['cases'],
               'valid_programs': analysis['valid_first_pass_cases'], 'coverage_collections': analysis['coverage_collections'],
               'classification_counts': analysis['classification_counts'], 'oracle_mismatches': analysis['oracle_mismatches'],
               'pairs_with_mapping_total_change': sum(p['mapping_differences']['base'] != p['mapping_differences']['variant'] for p in comparisons),
               'pairs_with_classification_change': sum(p['classifications']['base'] != p['classifications']['variant'] for p in comparisons),
               'compared_statement_pairs': sum(len(pair['statements']) for pair in comparisons),
               'results': comparisons}
    write_json(output / 'layout-results.json', summary)
    return summary
