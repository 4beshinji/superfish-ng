# SPDX-License-Identifier: Apache-2.0
"""Deterministic real expression trees with SI length dimension checking.

Only the operators in this module are executable. There is no Python parsing,
attribute access, imported function dispatch, or external state in a law.
"""
from fractions import Fraction
import math
from .config import keys

MAX_NODES = 256
MAX_DEPTH = 32
_UNARY = {name: getattr(math, name) for name in (
    'exp', 'log', 'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'sinh', 'cosh', 'tanh', 'floor', 'ceil')}
_COMPARE = {'lt': lambda a, b: a < b, 'le': lambda a, b: a <= b,
            'gt': lambda a, b: a > b, 'ge': lambda a, b: a >= b}
_BINARY = {'add': lambda a, b: a+b, 'sub': lambda a, b: a-b,
           'mul': lambda a, b: a*b, 'div': lambda a, b: a/b,
           'pow': math.pow, 'atan2': math.atan2, 'hypot': math.hypot}


def _number(value, label):
    try:
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError(f'{label} must be a finite real number')
        return float(value)
    except OverflowError as exc:
        raise ValueError(f'{label} exceeds finite floating representation') from exc


def _dimension(unit):
    if type(unit) is not str or unit not in ('1', 'm'):
        raise ValueError('scalar expression units must be 1 or m; values use SI without implicit conversion')
    return Fraction(unit == 'm')


def _compile(expression, variable_units, expected_unit):
    if type(variable_units) is not dict or any(type(k) is not str or not k.strip() for k in variable_units):
        raise ValueError('variable_units must map nonempty variable names to units')
    dimensions = {name: _dimension(unit) for name, unit in variable_units.items()}
    expected = _dimension(expected_unit); count = 0; used = set()

    def visit(node, depth):
        nonlocal count
        count += 1
        if count > MAX_NODES or depth > MAX_DEPTH:
            raise ValueError('scalar expression exceeds the 256-node or 32-depth budget')
        if type(node) is not dict:
            raise ValueError('scalar expression nodes must be objects')
        if 'constant' in node:
            keys(node, ('constant', 'unit'), ('constant', 'unit'), 'scalar constant')
            return _dimension(node['unit']), ('constant', _number(node['constant'], 'constant'))
        if 'variable' in node:
            keys(node, ('variable',), ('variable',), 'scalar variable')
            name = node['variable']
            if type(name) is not str or name not in dimensions:
                raise ValueError('scalar expression names an undeclared variable')
            used.add(name)
            return dimensions[name], ('variable', name)
        keys(node, ('op', 'args'), ('op', 'args'), 'scalar operation')
        op, args = node['op'], node['args']
        if type(op) is not str or op not in {*_UNARY, *_BINARY, *_COMPARE, 'neg', 'abs', 'sqrt', 'min', 'max', 'if'}:
            raise ValueError('unsupported scalar expression operator')
        arity = 3 if op == 'if' else 2 if op in _BINARY or op in _COMPARE else 1
        if type(args) is not list or (not 2 <= len(args) <= 16 if op in ('min', 'max') else len(args) != arity):
            raise ValueError(f'scalar operator {op} has invalid argument count')
        children = [visit(x, depth+1) for x in args]
        dims = [x[0] for x in children]
        if op == 'if':
            if dims[0] is not None or dims[1] is None or dims[1] != dims[2]:
                raise ValueError('if requires a comparison and two branches of identical numeric dimensions')
            dimension = dims[1]
        else:
            if any(d is None for d in dims):
                raise ValueError('comparison values may only be used as if conditions')
            if op in ('add', 'sub', 'min', 'max', 'hypot', 'atan2') or op in _COMPARE:
                if any(d != dims[0] for d in dims):
                    raise ValueError(f'scalar operator {op} requires identical argument dimensions')
                dimension = None if op in _COMPARE else Fraction(0) if op == 'atan2' else dims[0]
            elif op == 'mul': dimension = dims[0]+dims[1]
            elif op == 'div': dimension = dims[0]-dims[1]
            elif op == 'sqrt': dimension = dims[0]/2
            elif op == 'pow':
                if dims[1] != 0:
                    raise ValueError('power exponent must be dimensionless')
                if dims[0] != 0:
                    if children[1][1][0] != 'constant':
                        raise ValueError('a dimensioned base requires a literal constant exponent')
                    dimension = dims[0]*Fraction(str(args[1]['constant']))
                else: dimension = Fraction(0)
            elif op in _UNARY:
                if dims[0] != 0:
                    raise ValueError(f'scalar operator {op} requires a dimensionless argument')
                dimension = Fraction(0)
            else: dimension = dims[0]
        return dimension, (op, tuple(x[1] for x in children))

    dimension, compiled = visit(expression, 1)
    if dimension is None or dimension != expected:
        raise ValueError(f'scalar expression result does not have expected unit {expected_unit}')
    return compiled, dict(unit=expected_unit, node_count=count, variables=sorted(used))


def validate_scalar_expression(expression, variable_units, *, expected_unit):
    """Validate the whole tree, including unselected branches, without evaluation."""
    return _compile(expression, variable_units, expected_unit)[1]


def evaluate_scalar_expression(expression, variables, variable_units, *, expected_unit):
    """Evaluate a validated law at finite values; domain errors are explicit.

    If is lazy, while both branch dimensions and syntax are always checked.
    Finite output at one point does not establish continuity or validity over
    a tuning interval, and this evaluator performs no FEM or frequency solve.
    """
    compiled, _ = _compile(expression, variable_units, expected_unit)
    if type(variables) is not dict or variables.keys() != variable_units.keys():
        raise ValueError('scalar variable values must match the declared variable names exactly')
    values = {name: _number(value, f'variable {name}') for name, value in variables.items()}

    def evaluate(node):
        op, data = node
        if op == 'constant': return data
        if op == 'variable': return values[data]
        if op == 'if': return evaluate(data[1] if evaluate(data[0]) else data[2])
        args = [evaluate(child) for child in data]
        try:
            if op in _COMPARE: return _COMPARE[op](*args)
            if op in _UNARY: value = _UNARY[op](*args)
            elif op in _BINARY: value = _BINARY[op](*args)
            elif op == 'sqrt': value = math.sqrt(args[0])
            elif op == 'neg': value = -args[0]
            elif op == 'abs': value = abs(args[0])
            elif op == 'min': value = min(args)
            else: value = max(args)
        except (ValueError, OverflowError, ZeroDivisionError) as exc:
            raise ValueError(f'scalar operator {op} is outside its finite real domain') from exc
        return _number(value, f'scalar operator {op} result')

    return evaluate(compiled)
