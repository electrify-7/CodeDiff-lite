"""Bounded interpreter for the generator's deliberately small C subset.

This module never reads a coverage report and never executes rendered C.
Statement counts and decision outcomes follow the model's execution semantics.
"""

from collections import Counter


def walk(program: list[dict]):
    """Visit every node, including nodes on paths that are never executed."""
    def visit(node):
        yield node
        for value in node.values():
            if isinstance(value, dict):
                yield from visit(value)
            elif isinstance(value, list):
                for child in value:
                    if isinstance(child, dict):
                        yield from visit(child)
    for statement in program:
        yield from visit(statement)


def interpret(program: list[dict]) -> dict:
    state = {}
    statements = Counter({node['id']: 0 for node in walk(program)
                          if node['kind'] in ('declare', 'assign', 'add', 'macro', 'output', 'return')})
    decisions = {node['id']: {'true': 0, 'false': 0, 'not_evaluated': 0}
                 for node in walk(program) if node['kind'] == 'decision'}
    switches = {node['id']: {'case:0': 0, 'case:1': 0, 'default': 0}
                for node in walk(program) if node['kind'] == 'switch'}
    events = []
    budget = 10000
    stdout = ''

    def skip(node):
        if node['kind'] == 'decision':
            decisions[node['id']]['not_evaluated'] += 1
        for value in node.values():
            if isinstance(value, dict):
                skip(value)

    def expression(node):
        kind = node['kind']
        if kind == 'literal':
            return node['value']
        if kind == 'variable':
            return state[node['name']]
        if kind == 'decision':
            value = int(expression(node['value']) != 0)
            decisions[node['id']]['true' if value else 'false'] += 1
            events.append(f"D {node['id']} {value}")
            return value
        if kind == 'select':
            selected = expression(node['condition']) != 0
            skip(node['no'] if selected else node['yes'])
            return expression(node['yes'] if selected else node['no'])
        if kind != 'binary':
            raise ValueError(f'Unsupported expression: {kind}')
        left = expression(node['left'])
        op = node['op']
        if op == '&&' and not left:
            skip(node['right'])
            return 0
        if op == '||' and left:
            skip(node['right'])
            return 1
        right = expression(node['right'])
        if op == '+':
            value = left + right
        elif op == '<':
            value = int(left < right)
        elif op == '>':
            value = int(left > right)
        elif op == '==':
            value = int(left == right)
        elif op in ('&&', '||'):
            value = int(bool(right))
        else:
            raise ValueError(f'Unsupported operator: {op}')
        if not -100000 <= value <= 100000:
            raise ValueError('Oracle arithmetic bound exceeded')
        return value

    def execute(block):
        nonlocal budget, stdout
        for node in block:
            budget -= 1
            if budget < 0:
                raise ValueError('Oracle execution bound exceeded')
            kind = node['kind']
            if kind in ('declare', 'assign', 'add', 'macro', 'output', 'return'):
                statements[node['id']] += 1
                events.append(f"S {node['id']}")
            if kind in ('declare', 'assign'):
                state[node['name']] = expression(node['value'])
            elif kind in ('add', 'macro'):
                state[node['name']] += expression(node['value'])
            elif kind == 'if':
                execute(node['yes'] if expression(node['condition']) else node['no'])
            elif kind == 'loop':
                first = True
                iterations = 0
                while (first and node['style'] == 'do') or expression(node['condition']):
                    first = False
                    iterations += 1
                    if iterations > 20:
                        raise ValueError('Loop iteration bound exceeded')
                    execute(node['body'])
            elif kind == 'switch':
                selector = expression(node['value'])
                chosen = f'case:{selector}' if selector in (0, 1) else 'default'
                switches[node['id']][chosen] += 1
                events.append(f"W {node['id']} {selector}")
                if selector == 0:
                    execute(node['zero'])
                    if node['fallthrough']:
                        execute(node['one'])
                elif selector == 1:
                    execute(node['one'])
                else:
                    execute(node['default'])
            elif kind == 'output':
                stdout += f"{state['result']}\n"
            elif kind == 'return':
                if expression(node['value']) != 0:
                    raise ValueError('Generated programs must exit normally')
                return
            elif kind not in ('declare', 'assign', 'add', 'macro'):
                raise ValueError(f'Unsupported statement: {kind}')
    execute(program)
    return {'statements': dict(statements), 'decisions': decisions, 'switches': switches,
            'expected_output': {'stdout': stdout, 'exit_code': 0}, 'trace_events': events,
            'final_state': state}
