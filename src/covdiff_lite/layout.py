"""Reviewed whitespace-only controls, separate from the frozen main corpus."""

import copy
import hashlib
import json
import re
from pathlib import Path

from .generator import canonical, make_case, selected_parameters
from .io import write_json
from .templates import FAMILIES


LAYOUT_VERSION = 1
TRANSFORMATION = 'braces_on_separate_lines'
TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*.*?\*/|'
                   r'[A-Za-z_]\w*|\d+|>>=|<<=|==|!=|<=|>=|&&|\|\||\+\+|--|\+=|-=|'
                   r'\*=|/=|%=|<<|>>|->|[^\s]', re.S)


def c_tokens(source):
    return [token for token in TOKEN.findall(source)
            if not token.startswith(('//', '/*'))]


def transform_braces(source: str, roles: dict) -> tuple[str, dict, dict]:
    """Move only renderer-owned control/function braces; keep directives intact."""
    lines, new_roles, positions = [], {}, {}
    for old_number, text in enumerate(source.splitlines(), 1):
        role = roles[str(old_number)]
        indent = text[:len(text) - len(text.lstrip())]
        stripped = text.strip()
        fragments = [(text, role)]
        structure = {'role': 'structure', 'semantic_id': None}
        if role['role'] not in ('statement', 'macro_definition', 'preprocessor', 'trace'):
            if stripped == '} else {':
                fragments = [(indent + '}', structure), (indent + 'else', structure),
                             (indent + '{', structure)]
            elif stripped.startswith('} while ('):
                fragments = [(indent + '}', structure), (indent + stripped[2:], role)]
            elif stripped.endswith(' {'):
                fragments = [(text[:-2], role), (indent + '{', structure)]
        first = len(lines) + 1
        for fragment, metadata in fragments:
            lines.append(fragment)
            new_roles[str(len(lines))] = metadata.copy()
        anchor = first + (1 if stripped.startswith('} while (') and len(fragments) == 2 else 0)
        positions[old_number] = {'first': first, 'last': len(lines), 'anchor': anchor}
    transformed = '\n'.join(lines) + '\n'
    directives = lambda text: [line for line in text.splitlines() if line.lstrip().startswith('#')]
    if c_tokens(source) != c_tokens(transformed) or directives(source) != directives(transformed):
        raise ValueError('Layout transformation changed C tokens or preprocessor directives')
    if transformed == source:
        raise ValueError('Layout control did not change the source')
    return transformed, new_roles, positions


def make_layout_case(family, parameters, seed):
    source, base = make_case(family, parameters, seed)
    transformed, roles, positions = transform_braces(source, base['line_roles'])
    manifest = copy.deepcopy(base)
    manifest['case_id'] += '_layout_braces_v1'
    manifest['source'] = manifest['case_id'] + '.c'
    manifest['source_sha256'] = hashlib.sha256(transformed.encode()).hexdigest()
    manifest['line_roles'] = roles
    manifest['lines'] = {str(positions[int(n)]['anchor']): entry for n, entry in manifest['lines'].items()}
    for branch in manifest['branches']:
        span = branch['source_span']
        span['line'] = positions[span['line']]['anchor']
        if 'end_line' in span:
            span['end_line'] = positions[span['end_line']]['last']
    manifest['layout_control'] = {'version': LAYOUT_VERSION, 'transformation': TRANSFORMATION,
        'parent_case_id': base['case_id'], 'parent_source_sha256': base['source_sha256'],
        'statement_mapping': 'same_semantic_ids_relocated_lines'}
    return transformed, manifest


def validate_layout_manifest(manifest, source):
    if manifest.get('layout_control', {}).get('version') != LAYOUT_VERSION:
        raise ValueError('Unsupported layout transformation version')
    expected_source, expected = make_layout_case(manifest['family'], manifest['parameters'], manifest['seed'])
    expected['source'] = manifest['source']
    if source != expected_source or manifest != expected:
        raise ValueError('Layout source or oracle differs from the reviewed transformation')


def generate_layout_controls(dataset: Path, output: Path) -> dict:
    from .calibration import load_fixture
    index = json.loads((dataset / 'dataset.json').read_text())
    loaded = {identifier: load_fixture(dataset / 'cases' / (identifier + '.json'))
              for identifier in index['case_ids']}
    manifests = [loaded[identifier][0] for identifier in index['case_ids']]
    if (len(loaded) != index['programs'] or any(m.get('layout_control') for m in manifests)
            or hashlib.sha256(canonical(manifests).encode()).hexdigest() != index['dataset_sha256']
            or [m['source_sha256'] for m in manifests] != index['source_hashes']):
        raise ValueError('Parent dataset index does not match its validated source/manifests')
    selected = []
    for family in FAMILIES:
        parameters = selected_parameters(family, 2, index['seed'])
        if family == 'constants':
            macros = sorted((m for m in manifests if m['family'] == family
                             and m['parameters']['form'] == 'macro' and m['parameters']['enabled'] == 1),
                            key=lambda m: m['case_id'])
            if not macros:
                raise ValueError('Controls require a true constant-macro case in the parent dataset')
            parameters[1] = macros[0]['parameters']
        for p in parameters:
            source, manifest = make_case(family, p, index['seed'])
            if manifest['case_id'] not in loaded or manifest != loaded[manifest['case_id']][0]:
                raise ValueError('Required contrasting control is absent from the parent dataset')
            selected.append((source, manifest))
    cases, pairs = [], []
    for source, manifest in selected:
        variant_source, variant = make_layout_case(manifest['family'], manifest['parameters'], manifest['seed'])
        if manifest['oracle'] != variant['oracle'] or manifest['expected_output'] != variant['expected_output']:
            raise ValueError('Layout variant changed semantic expectations')
        cases.extend([(source, manifest), (variant_source, variant)])
        pairs.append({'pair_id': manifest['case_id'] + '_brace_pair', 'family': manifest['family'],
                      'base_case_id': manifest['case_id'], 'variant_case_id': variant['case_id'],
                      'parameters': manifest['parameters'], 'transformation': TRANSFORMATION})
    if len({m['source_sha256'] for _, m in cases}) != len(cases):
        raise ValueError('Duplicate sources in layout controls')
    output.mkdir(parents=True, exist_ok=False)
    (output / 'cases').mkdir()
    for source, manifest in cases:
        (output / 'cases' / manifest['source']).write_text(source)
        write_json(output / 'cases' / (manifest['case_id'] + '.json'), manifest)
    summary = {'schema_version': 1, 'purpose': 'paired_layout_controls', 'layout_version': LAYOUT_VERSION,
               'parent_dataset_sha256': index['dataset_sha256'], 'programs': len(cases), 'pair_count': len(pairs),
               'dataset_sha256': hashlib.sha256(canonical([m for _, m in cases]).encode()).hexdigest(),
               'selection': 'Two contrasting cases per family; constants include a true FLAG macro.', 'pairs': pairs}
    write_json(output / 'pairs.json', summary)
    return summary
