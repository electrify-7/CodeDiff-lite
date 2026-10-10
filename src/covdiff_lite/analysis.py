"""Oracle-guided analysis with fresh confirmation builds and retained evidence."""

import csv
import hashlib
import json
import math
import shlex
import shutil
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path

from .calibration import execute_case, load_fixture
from .compare import compare_observations
from .conventions import RULE_VERSION
from .environment import inspect_environment
from .io import write_json
from .repeat import classify, semantic_signature
from .validation import validate_oracles


def run_analysis(fixtures: Path | None, output: Path, case: Path | None = None,
                 control_fraction=0.1) -> dict:
    if not 0 <= control_fraction <= 1:
        raise ValueError('Control fraction must lie between zero and one')
    environment = inspect_environment()
    if not environment['ready']:
        raise ValueError('Environment is not ready: ' + '; '.join(environment['errors']))
    paths = [case] if case is not None else sorted(fixtures.glob('*.json'))
    loaded = [load_fixture(path) for path in paths]
    if not loaded or len({m['case_id'] for m, _ in loaded}) != len(loaded):
        raise ValueError('Expected at least one case with unique IDs')
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    write_json(output / 'environment.json', environment)
    write_json(output / 'config.json', {'schema_version': 1, 'confirmation_runs': 3,
        'control_fraction': control_fraction, 'convention_rule_version': RULE_VERSION,
        'case_ids': [m['case_id'] for m, _ in loaded], 'branch_mapping': 'not_implemented'})
    versions = {'gcov': environment['tools']['gcov']['version'],
                'llvm-cov': environment['tools']['llvm_cov']['version']}
    cases = []
    generated_inputs = output / 'oracle-inputs'
    generated = [m for m, _ in loaded if m.get('origin') == 'generated']
    if generated:
        generated_inputs.mkdir()
    for manifest, original in loaded:
        directory = output / 'cases' / manifest['case_id']
        directory.mkdir(parents=True)
        source = directory / 'case.c'
        shutil.copyfile(original, source)
        write_json(directory / 'manifest.json', {**manifest, 'source': 'case.c'})
        if manifest.get('origin') == 'generated':
            name = manifest['case_id'] + '.c'
            shutil.copyfile(source, generated_inputs / name)
            write_json(generated_inputs / (manifest['case_id'] + '.json'), {**manifest, 'source': name})
        cases.append({'manifest': manifest, 'source': source, 'directory': directory,
                      'executions': [], 'assessments': [], 'signatures': [], 'durations': []})
    oracle_results = {}
    if generated:
        trace = validate_oracles(generated_inputs, output / 'oracle-validation')
        oracle_results = {r['case_id']: r for r in trace['results']}

    def execute(current):
        pass_started = time.monotonic()
        manifest = current['manifest']
        index = len(current['executions'])
        directory = current['directory'] / f'repeat-{index}'
        execution = execute_case(manifest, current['source'], directory, environment['tools'])
        trusted = manifest.get('origin') in ('generated', 'handwritten_calibration', 'documented_issue')
        if manifest.get('origin') == 'generated' and not oracle_results[manifest['case_id']]['passed']:
            trusted = False
            execution['errors'].append({'tool': 'oracle', 'stage': 'oracle_validation',
                                        'message': 'Model oracle failed independent C trace validation'})
        assessment = compare_observations(manifest, current['source'].read_text(), execution['reports'], versions, trusted)
        signature = semantic_signature(execution)
        current['executions'].append(execution)
        current['assessments'].append(assessment)
        current['signatures'].append(signature)
        current['durations'].append(time.monotonic() - pass_started)
        write_json(directory / 'analysis.json', {'assessment': assessment, 'signature': signature,
                                               'errors': execution['errors'], 'oracle_trusted': trusted})

    for current in cases:
        execute(current)
    agreeing = [current for current in cases
                if not current['assessments'][0]['findings'] and not current['executions'][0]['errors']]
    agreeing.sort(key=lambda c: hashlib.sha256(c['manifest']['case_id'].encode()).digest())
    controls = {c['manifest']['case_id'] for c in agreeing[:math.ceil(len(agreeing) * control_fraction)]}
    results = []
    for current in cases:
        manifest, directory = current['manifest'], current['directory']
        is_control = manifest['case_id'] in controls
        if current['assessments'][0]['findings'] or current['executions'][0]['errors'] or is_control:
            execute(current)
            execute(current)
        classification = classify(current['assessments'], current['signatures'],
                                  [e['errors'] for e in current['executions']])
        first = current['assessments'][0]
        result = {
            'case_id': manifest['case_id'], 'family': manifest['family'], 'classification': classification,
            'runs': len(current['executions']), 'control': is_control,
            'stable': len(set(current['signatures'])) == 1 if len(current['signatures']) > 1 else None,
            'signatures': current['signatures'], 'errors': [e['errors'] for e in current['executions']],
            'comparable_lines': first['comparable_lines'], 'raw_count_disagreements': first['raw_count_disagreements'],
            'raw_binary_disagreements': first['raw_binary_disagreements'],
            'mapping_differences': first['mapping_differences'], 'oracle_mismatches': first['oracle_mismatches'],
            'findings': first['findings'], 'branches': first['branches'],
            'secondary_labels': sorted({f['assessment'] for a in current['assessments'] for f in a['findings']}),
            'oracle_validation': oracle_results.get(manifest['case_id']),
            'first_pass_seconds': current['durations'][0], 'repeat_seconds': sum(current['durations'][1:]),
            'manual_review': 'pending' if classification in ('probable_incorrect_coverage_report', 'unresolved_disagreement') else 'not_required',
        }
        manifest_path = directory / 'manifest.json'
        argument = str(manifest_path.relative_to(Path.cwd())) if manifest_path.is_relative_to(Path.cwd()) else str(manifest_path)
        command = ['bash', 'scripts/env.sh', 'analyze', '--case', argument, '--output']
        result['reproduction_command'] = command + ['<new-output-directory>']
        script = '#!/bin/sh\nset -eu\n: "${1:?Pass a new output directory; run from the repository root}"\nexec ' + shlex.join(command) + ' "$1"\n'
        (directory / 'reproduce.sh').write_text(script)
        (directory / 'reproduce.sh').chmod(0o755)
        write_json(directory / 'analysis.json', result)
        results.append(result)
        print(f"{result['case_id']}: {classification} ({result['runs']} run(s))", flush=True)
    usable = [r for r in results if not r['errors'][0]]
    counts = Counter(r['classification'] for r in results)
    families = defaultdict(Counter)
    for result in results:
        families[result['family']][result['classification']] += 1
    times = [r['first_pass_seconds'] for r in results]
    summary = {
        'schema_version': 1, 'cases': len(results), 'valid_first_pass_cases': len(usable),
        'classification_counts': dict(counts), 'families': {f: dict(c) for f, c in families.items()},
        'coverage_collections': sum(r['runs'] for r in results), 'control_cases': len(controls),
        'comparable_lines': sum(r['comparable_lines'] for r in usable),
        'raw_count_disagreements': sum(r['raw_count_disagreements'] for r in usable),
        'raw_binary_disagreements': sum(r['raw_binary_disagreements'] for r in usable),
        'mapping_differences': sum(r['mapping_differences'] for r in usable),
        'oracle_mismatches': {tool: sum(r['oracle_mismatches'][tool] for r in usable) for tool in ('gcov', 'llvm-cov')},
        'known_convention_observations': sum(f['assessment'] == 'known_convention_difference' for r in usable for f in r['findings']),
        'mean_first_pass_seconds': statistics.mean(times), 'median_first_pass_seconds': statistics.median(times),
        'p95_first_pass_seconds': sorted(times)[math.ceil(len(times) * .95) - 1],
        'repeat_seconds': sum(r['repeat_seconds'] for r in results),
        'elapsed_seconds': time.monotonic() - started, 'convention_rule_version': RULE_VERSION,
        'branches': {'mapping_status': 'not_implemented', 'comparable_outcomes': 0},
        'results': results,
    }
    write_json(output / 'summary.json', summary)
    (output / 'results.jsonl').write_text(''.join(json.dumps(r, sort_keys=True) + '\n' for r in results))
    fields = ['case_id', 'family', 'classification', 'runs', 'stable', 'control', 'comparable_lines',
              'raw_count_disagreements', 'mapping_differences', 'first_pass_seconds', 'repeat_seconds']
    with (output / 'cases.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(results)
    with (output / 'observations.csv').open('w', newline='') as stream:
        fields = ['case_id', 'line', 'role', 'comparable', 'expected', 'gcov', 'llvm-cov', 'finding_kinds', 'rule_ids']
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for current in cases:
            for row in current['assessments'][0]['lines']:
                writer.writerow({'case_id': current['manifest']['case_id'], 'line': row['line'], 'role': row['role'],
                    'comparable': row['comparable'], 'expected': row['expected']['count'] if row['expected'] else None,
                    'gcov': row['gcov']['count'], 'llvm-cov': row['llvm-cov']['count'],
                    'finding_kinds': ';'.join(f['kind'] for f in row['findings']),
                    'rule_ids': ';'.join(f.get('rule_id', '') for f in row['findings'])})
    return summary
