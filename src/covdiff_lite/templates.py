"""Eight finite, reviewable template families with small integer domains."""

from itertools import product


TEMPLATE_VERSION = 1
DOMAINS = {
    'if_else': {'x': [-2, -1, 0, 1, 2], 'threshold': [-1, 0, 1], 'amount': [1, 2, 3, 4], 'nested': [False, True]},
    'loops': {'limit': [0, 1, 2, 3, 4, 5], 'amount': [1, 2, 3, 4, 5, 6], 'style': ['while', 'for', 'do']},
    'switch': {'selector': [0, 1, 2], 'amount': list(range(1, 13)), 'fallthrough': [False, True]},
    'short_circuit': {'x': [-1, 0, 1], 'y': [-1, 0, 1], 'amount': [1, 2, 3, 4], 'op': ['&&', '||']},
    'multiline': {'x': [-1, 0, 1], 'y': [-1, 0, 1], 'amount': [1, 2, 3, 4], 'op': ['&&', '||']},
    'ternary': {'x': [-2, -1, 0, 1, 2], 'threshold': [-1, 0, 1], 'amount': list(range(1, 9))},
    'macros': {'enabled': [0, 1], 'amount': list(range(1, 9)), 'repetitions': [1, 2, 3, 4]},
    'constants': {'enabled': [0, 1], 'amount': list(range(1, 9)), 'form': ['literal', 'macro', 'comparison', 'negation']},
}
FAMILIES = tuple(DOMAINS)


def literal(value, spelling=None):
    node = {'kind': 'literal', 'value': value}
    if spelling is not None:
        node['spelling'] = spelling
    return node


def variable(name):
    return {'kind': 'variable', 'name': name}


def binary(op, left, right):
    return {'kind': 'binary', 'op': op, 'left': left, 'right': right}


def decision(identifier, value):
    return {'kind': 'decision', 'id': identifier, 'value': value}


def statement(kind, identifier, name=None, value=None):
    node = {'kind': kind, 'id': identifier}
    if name is not None:
        node['name'] = name
    if value is not None:
        node['value'] = value
    return node


def parameters_for(family):
    domain = DOMAINS[family]
    return [dict(zip(domain, values)) for values in product(*domain.values())]


def validate_parameters(family, parameters):
    if family not in DOMAINS or set(parameters) != set(DOMAINS[family]):
        raise ValueError('Unknown template family or parameter keys')
    for key, values in DOMAINS[family].items():
        if not any(type(parameters[key]) is type(value) and parameters[key] == value for value in values):
            raise ValueError(f'Parameter outside reviewed domain: {family}.{key}')


def build_program(family: str, p: dict) -> list[dict]:
    validate_parameters(family, p)
    program = [statement('declare', 'init_result', 'result', literal(0))]
    amount = p['amount']

    def declare(name, value):
        program.append(statement('declare', 'init_' + name, name, literal(value)))

    def add(identifier, value):
        return statement('add', identifier, 'result', literal(value))

    if family == 'if_else':
        declare('x', p['x'])
        yes = [add('then_body', amount)]
        if p['nested']:
            yes = [{'kind': 'if', 'condition': decision('inner', binary('==', variable('x'), literal(1))),
                    'yes': [add('inner_then', amount * 2)], 'no': [add('inner_else', amount * 3)], 'multiline': False}]
        program.append({'kind': 'if', 'condition': decision('outer', binary('>', variable('x'), literal(p['threshold']))),
                        'yes': yes, 'no': [add('else_body', amount + 1)], 'multiline': False})
    elif family == 'loops':
        declare('limit', p['limit'])
        declare('i', 0)
        program.append({'kind': 'loop', 'style': p['style'],
                        'condition': decision('loop_condition', binary('<', variable('i'), variable('limit'))),
                        'body': [add('loop_body', amount), statement('add', 'increment', 'i', literal(1))]})
    elif family == 'switch':
        declare('selector', p['selector'])
        program.append({'kind': 'switch', 'id': 'dispatch', 'value': variable('selector'),
                        'fallthrough': p['fallthrough'], 'zero': [add('case_zero', amount)],
                        'one': [add('case_one', amount * 2)], 'default': [add('default_body', amount * 3)]})
    elif family in ('short_circuit', 'multiline'):
        declare('x', p['x'])
        declare('y', p['y'])
        left = decision('left_operand', binary('>', variable('x'), literal(0)))
        right = decision('right_operand', binary('>', variable('y'), literal(0)))
        program.append({'kind': 'if', 'condition': decision('combined', binary(p['op'], left, right)),
                        'yes': [add('then_body', amount)], 'no': [add('else_body', amount + 1)],
                        'multiline': family == 'multiline'})
    elif family == 'ternary':
        declare('x', p['x'])
        value = {'kind': 'select', 'condition': decision('selection', binary('>', variable('x'), literal(p['threshold']))),
                 'yes': literal(amount), 'no': literal(-amount)}
        program.append(statement('assign', 'ternary_assignment', 'result', value))
    elif family == 'macros':
        declare('enabled', p['enabled'])
        declare('limit', p['repetitions'])
        declare('i', 0)
        program.append({'kind': 'loop', 'style': 'for',
                        'condition': decision('loop_condition', binary('<', variable('i'), variable('limit'))),
                        'body': [{'kind': 'if', 'condition': decision('enabled_condition', variable('enabled')),
                                  'yes': [statement('macro', 'macro_invocation', 'result', literal(amount))],
                                  'no': [add('disabled_body', 1)], 'multiline': False},
                                 statement('add', 'increment', 'i', literal(1))]})
    elif family == 'constants':
        value = p['enabled']
        spelling = {'literal': str(value), 'macro': 'FLAG', 'comparison': '(3 == 3)' if value else '(3 == 4)',
                    'negation': '(!0)' if value else '(!1)'}[p['form']]
        program.append({'kind': 'if', 'condition': decision('constant_condition', literal(value, spelling)),
                        'yes': [add('then_body', amount)], 'no': [add('else_body', amount + 1)], 'multiline': False})
    program.extend([statement('output', 'output'), statement('return', 'return', value=literal(0))])
    return program
