"""Render ordinary C and optional trace twins, preserving model IDs."""


class Renderer:
    def __init__(self, family: str, parameters: dict, trace=False):
        self.family = family
        self.parameters = parameters
        self.trace = trace
        self.text = []
        self.statements = {}
        self.decisions = {}
        self.roles = {}

    def locate_decisions(self, node, line, end_line, column):
        if node['kind'] == 'decision':
            self.decisions[node['id']] = {'line': line, 'end_line': end_line, 'column': column,
                                          'precision': 'enclosing_construct'}
        for value in node.values():
            if isinstance(value, dict):
                self.locate_decisions(value, line, end_line, column)

    def line(self, text, role='structure', identifier=None):
        self.text.append(text)
        number = len(self.text)
        self.roles[str(number)] = {'role': role, 'semantic_id': identifier}
        return number

    def expression(self, node):
        kind = node['kind']
        if kind == 'literal':
            return node.get('spelling', str(node['value']))
        if kind == 'variable':
            return node['name']
        if kind == 'binary':
            return f"({self.expression(node['left'])} {node['op']} {self.expression(node['right'])})"
        if kind == 'select':
            return f"({self.expression(node['condition'])} ? {self.expression(node['yes'])} : {self.expression(node['no'])})"
        if kind == 'decision':
            value = self.expression(node['value'])
            return f'trace_dec("{node["id"]}", {value})' if self.trace else value
        raise ValueError(f'Unsupported expression {kind}')

    def block(self, statements, depth=1, elided=False):
        indent = '    ' * depth
        for node in statements:
            kind = node['kind']
            if kind in ('declare', 'assign', 'add', 'macro', 'output', 'return'):
                identifier = node['id']
                if self.trace:
                    self.line(indent + f'fprintf(stderr, "S {identifier}\\n");', 'trace')
                if kind == 'declare':
                    text = f"int {node['name']} = {self.expression(node['value'])};"
                elif kind in ('assign', 'add'):
                    op = '=' if kind == 'assign' else '+='
                    text = f"{node['name']} {op} {self.expression(node['value'])};"
                elif kind == 'macro':
                    text = f"ADD_TO({node['name']}, {self.expression(node['value'])});"
                elif kind == 'output':
                    text = 'printf("%d\\n", result);'
                else:
                    text = 'return 0;'
                number = self.line(indent + text + f' // @id {identifier}', 'statement', identifier)
                column = len(indent) + 1
                self.statements[identifier] = {'line': number, 'column': column, 'end_column': len(indent + text) + 1,
                                               'allow_elided': elided, 'role': 'statement'}
                if kind == 'assign' and node['value']['kind'] == 'select':
                    self.locate_decisions(node['value'], number, number, column)
            elif kind == 'if':
                first_line = len(self.text) + 1
                condition = self.expression(node['condition'])
                if node['multiline']:
                    self.line(indent + 'if (', 'condition')
                    separator = ' && ' if ' && ' in condition else ' || '
                    left, right = condition.split(separator, 1)
                    self.line(indent + '    ' + left, 'condition_continuation')
                    self.line(indent + '    ' + separator.strip() + ' ' + right, 'condition_continuation')
                    self.line(indent + ') {', 'condition_continuation')
                else:
                    self.line(indent + f'if ({condition}) {{', 'condition')
                self.locate_decisions(node['condition'], first_line, len(self.text), len(indent) + 1)
                value = node['condition']['value']
                constant = value['value'] != 0 if value['kind'] == 'literal' else None
                self.block(node['yes'], depth + 1, elided or constant is False)
                self.line(indent + '} else {')
                self.block(node['no'], depth + 1, elided or constant is True)
                self.line(indent + '}')
            elif kind == 'loop':
                condition = self.expression(node['condition'])
                style = node['style']
                number = self.line(indent + ('do {' if style == 'do' else
                                   f'for (; {condition}; ) {{' if style == 'for' else f'while ({condition}) {{'), 'condition')
                self.block(node['body'], depth + 1, elided)
                end = self.line(indent + (f'}} while ({condition});' if style == 'do' else '}'),
                                'condition' if style == 'do' else 'structure')
                condition_line = end if style == 'do' else number
                self.locate_decisions(node['condition'], condition_line, condition_line, len(indent) + 1)
            elif kind == 'switch':
                value = self.expression(node['value'])
                if self.trace:
                    value = f'trace_switch("{node["id"]}", {value})'
                number = self.line(indent + f'switch ({value}) {{', 'switch', node['id'])
                self.decisions[node['id']] = {'line': number, 'column': len(indent) + 1}
                for label, block in [('case 0:', 'zero'), ('case 1:', 'one'), ('default:', 'default')]:
                    self.line(indent + label, 'case_label')
                    self.block(node[block], depth + 1, elided)
                    if block != 'zero' or not node['fallthrough']:
                        self.line(indent + '    break;', 'jump')
                self.line(indent + '}')
            else:
                raise ValueError(f'Unsupported statement {kind}')

    def render(self, program):
        self.line('#include <stdio.h>', 'preprocessor')
        if self.family == 'macros':
            self.line('#define ADD_TO(dst, amount) do { (dst) += (amount); } while (0)', 'macro_definition')
        if self.family == 'constants' and self.parameters['form'] == 'macro':
            self.line(f"#define FLAG {self.parameters['enabled']}", 'macro_definition')
        if self.trace:
            self.line('static int trace_dec(const char *id, int value) {', 'trace')
            self.line('    fprintf(stderr, "D %s %d\\n", id, value != 0); return value != 0;', 'trace')
            self.line('}', 'trace')
            self.line('static int trace_switch(const char *id, int value) {', 'trace')
            self.line('    fprintf(stderr, "W %s %d\\n", id, value); return value;', 'trace')
            self.line('}', 'trace')
        self.line('', 'blank')
        self.line('int main(void) {')
        self.block(program)
        self.line('}')
        return '\n'.join(self.text) + '\n'
