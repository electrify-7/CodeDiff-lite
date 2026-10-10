"""Deterministic, balanced generation with semantic oracles and source hashes."""

import hashlib
import json
from pathlib import Path

from .io import write_json
from .oracle import interpret
from .render import Renderer
from .templates import FAMILIES, TEMPLATE_VERSION, build_program, parameters_for


GENERATOR_VERSION = '1'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def make_case(family: str, parameters: dict, seed: int) -> tuple[str, dict]:
    if type(seed) is not int or not 0 <= seed < 2**64:
        raise ValueError('Seed must be an unsigned 64-bit integer')
    program = build_program(family, parameters)
    expected = interpret(program)
    renderer = Renderer(family, parameters)
    source = renderer.render(program)
    identity = hashlib.sha256(canonical({'family': family, 'parameters': parameters,
                                        'template_version': TEMPLATE_VERSION}).encode()).hexdigest()[:16]
    case_id = f'{family}_v{TEMPLATE_VERSION}_{identity}'
    lines = {}
    for identifier, location in renderer.statements.items():
        entry = {**location, 'statement_id': identifier, 'count': expected['statements'][identifier],
                 'comparison': 'exact', 'oracle_trust': 'template_semantics'}
        if entry['allow_elided']:
            entry['elision_reason'] = 'literal_constant_unreachable_body'
        lines[str(entry.pop('line'))] = entry
    branches = [
        {'decision_id': identifier, 'expected': outcomes, 'source_span': renderer.decisions[identifier],
         'mapping_status': 'semantic_only'}
        for identifier, outcomes in expected['decisions'].items()
    ]
    branches.extend({'decision_id': identifier, 'expected': outcomes,
                     'source_span': renderer.decisions[identifier], 'mapping_status': 'semantic_only'}
                    for identifier, outcomes in expected['switches'].items())
    manifest = {
        'schema_version': 1, 'case_id': case_id, 'family': family, 'source': case_id + '.c',
        'source_sha256': hashlib.sha256(source.encode()).hexdigest(), 'origin': 'generated',
        'generator_version': GENERATOR_VERSION, 'template_version': TEMPLATE_VERSION, 'seed': seed,
        'parameters': parameters, 'expected_output': expected['expected_output'],
        'lines': lines, 'line_roles': renderer.roles, 'branches': branches,
        'branch_mapping': 'semantic_only', 'oracle': {'method': 'bounded_model_interpreter',
        'trace_events': expected['trace_events'], 'statement_counts': expected['statements'],
        'final_state': expected['final_state']},
    }
    return source, manifest


def selected_parameters(family: str, per_family: int, seed: int) -> list[dict]:
    """Keep two contrasting controls, then order the remaining grid by SHA-256.

    SHA ordering avoids depending on Python's RNG, hash seed, or directory order.
    """
    domain = parameters_for(family)
    if type(per_family) is not int or not 1 <= per_family <= len(domain):
        raise ValueError(f'{family} supports 1..{len(domain)} unique parameter combinations')
    # The endpoints deliberately contrast condition/input values. Loops also
    # receive a zero-iteration while control and a positive-iteration do control.
    controls = [domain[0], domain[-1]]
    remaining = [p for p in domain if p not in controls]
    remaining.sort(key=lambda p: hashlib.sha256(canonical([GENERATOR_VERSION, seed, family, p]).encode()).digest())
    return (controls + remaining)[:per_family]


def validate_generated_manifest(manifest: dict, source: str) -> None:
    if manifest.get('generator_version') != GENERATOR_VERSION or manifest.get('template_version') != TEMPLATE_VERSION:
        raise ValueError('Unsupported generator/template version')
    rebuilt_source, rebuilt_manifest = make_case(manifest['family'], manifest['parameters'], manifest['seed'])
    # Saved run evidence may rename the source to case.c without changing it.
    rebuilt_manifest['source'] = manifest['source']
    if source != rebuilt_source or manifest != rebuilt_manifest:
        raise ValueError('Generated source or oracle differs from reviewed template semantics')


def generate_dataset(output: Path, per_family=40, seed=20261010) -> dict:
    if type(seed) is not int or not 0 <= seed < 2**64:
        raise ValueError('Seed must be an unsigned 64-bit integer')
    cases = [make_case(family, p, seed) for family in FAMILIES
             for p in selected_parameters(family, per_family, seed)]
    hashes = [manifest['source_sha256'] for _, manifest in cases]
    if len(hashes) != len(set(hashes)):
        raise ValueError('Duplicate source programs in dataset')
    output.mkdir(parents=True, exist_ok=False)
    directory = output / 'cases'
    directory.mkdir()
    for source, manifest in cases:
        (directory / manifest['source']).write_text(source)
        write_json(directory / (manifest['case_id'] + '.json'), manifest)
    summary = {
        'schema_version': 1, 'generator_version': GENERATOR_VERSION,
        'template_version': TEMPLATE_VERSION, 'seed': seed, 'per_family': per_family,
        'programs': len(cases), 'families': {family: per_family for family in FAMILIES},
        'case_ids': [manifest['case_id'] for _, manifest in cases],
        'dataset_sha256': hashlib.sha256(canonical([manifest for _, manifest in cases]).encode()).hexdigest(),
        'source_hashes': hashes, 'oracle_validation': 'not_yet_run',
    }
    write_json(output / 'dataset.json', summary)
    return summary
