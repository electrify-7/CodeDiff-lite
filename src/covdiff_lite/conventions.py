"""Version-scoped rules for locations without contradictory statement oracles.

Rules never excuse an observed contradiction on a scored statement. References:
https://gcc.gnu.org/onlinedocs/gcc-11.5.0/gcc/Invoking-Gcov.html
https://releases.llvm.org/14.0.0/tools/clang/docs/SourceBasedCodeCoverage.html
"""


RULE_VERSION = 1


def explain(manifest, line, text, expected, observations, versions):
    if versions.get('gcov') != '11.4.0' or versions.get('llvm-cov') != '14.0.0':
        return None
    gcc, llvm = observations['gcov'], observations['llvm-cov']
    if expected is not None:
        if (manifest.get('family') == 'constants' and expected.get('allow_elided') is True
                and expected['count'] == 0 and gcc['state'] == 'not_reported'
                and llvm['state'] == 'reported' and llvm['count'] == 0):
            return {'rule_id': 'constant_dead_body_elision_v1',
                    'reason': 'An explicitly unreachable constant body has no GCC counter; LLVM records zero.'}
        return None
    stripped = text.strip()
    if stripped in ('}', '{', '} else {'):
        return {'rule_id': 'brace_line_attribution_v1',
                'reason': 'An unscored brace line inherits tool-specific block or region attribution.'}
    if (stripped.startswith('#define ADD') and gcc['state'] == 'not_reported'
            and llvm['state'] == 'reported'):
        return {'rule_id': 'macro_definition_file_view_v1',
                'reason': 'LLVM displays expansion coverage on the macro definition; GCC has no line record there.'}
    role = manifest.get('line_roles', {}).get(str(line), {}).get('role')
    if (role == 'case_label' and gcc['state'] == 'not_reported' and llvm['state'] == 'reported'):
        return {'rule_id': 'unscored_switch_label_mapping_v1',
                'reason': 'The unscored case label has a source region in LLVM and no separate GCC line record.'}
    if (role == 'condition_continuation' and manifest.get('origin') == 'generated'
            and manifest.get('template_version') == 1 and manifest['family'] == 'multiline'):
        return {'rule_id': 'multiline_condition_attribution_v1',
                'reason': 'This condition continuation has no universal statement count; retain each tool attribution.'}
    return None
