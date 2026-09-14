# SPDX-License-Identifier: Apache-2.0
"""Independent identities and dimensional failures for declared scalar laws."""
import math
import unittest


def constant(value, unit='1'):
    return dict(constant=value, unit=unit)


def operation(name, *args):
    return dict(op=name, args=list(args))


X = dict(variable='x')


class ScalarExpressionTests(unittest.TestCase):
    def evaluate(self, expression, x, variable_unit='1', expected_unit='1'):
        from superfish_ng.scalar_expressions import evaluate_scalar_expression
        return evaluate_scalar_expression(expression, {'x': x}, {'x': variable_unit}, expected_unit=expected_unit)

    def test_exponential_geometry_law_and_independent_inverse(self):
        law = operation('mul', constant(.1, 'm'), operation('exp', X))
        for radius in (.07, .1, .13):
            self.assertAlmostEqual(self.evaluate(law, math.log(radius/.1), expected_unit='m'), radius, places=15)
        inverse = operation('exp', operation('log', X))
        for x in (.01, 1., 12.):
            self.assertAlmostEqual(self.evaluate(inverse, x), x, places=13)

    def test_length_units_and_geometric_pythagorean_identity(self):
        law = operation('sqrt', operation('add', operation('pow', X, constant(2)),
                                         operation('pow', constant(4, 'm'), constant(2))))
        self.assertEqual(self.evaluate(law, 3., 'm', 'm'), 5.)
        for expression in [operation('exp', X), operation('add', X, constant(1)), X]:
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                self.evaluate(expression, 2., 'm', '1')

    def test_trigonometric_identity_and_dimensionless_angle(self):
        law = operation('add', operation('pow', operation('sin', X), constant(2)),
                        operation('pow', operation('cos', X), constant(2)))
        for x in (-2., .1, 3.):
            self.assertAlmostEqual(self.evaluate(law, x), 1., places=14)
        angle = operation('atan2', X, constant(1, 'm'))
        self.assertAlmostEqual(self.evaluate(angle, 1., 'm'), math.pi/4, places=15)

    def test_conditional_is_lazy_but_both_branches_are_dimension_checked(self):
        law = operation('if', operation('gt', X, constant(0)), operation('log', X), constant(0))
        self.assertEqual(self.evaluate(law, -1), 0)
        self.assertEqual(self.evaluate(law, math.e), 1)
        law['args'][2] = constant(0, 'm')
        with self.assertRaises(ValueError):
            self.evaluate(law, math.e)

    def test_domains_overflow_and_unknown_inputs_fail(self):
        for expression, x in [(operation('log', X), 0), (operation('sqrt', X), -1),
                              (operation('exp', X), 1000), (operation('div', constant(1), X), 0),
                              (operation('pow', X, constant(.5)), -1)]:
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                self.evaluate(expression, x)
        for expression in [dict(op='__import__', args=[]), dict(variable='missing'),
                           dict(constant=True, unit='1'), dict(constant=1, unit='cm'),
                           dict(variable='x', extra=1), operation('sin', X, X)]:
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                self.evaluate(expression, 1)

    def test_depth_budget_and_variable_values_are_strict(self):
        law = X
        for _ in range(40):
            law = operation('neg', law)
        with self.assertRaises(ValueError):
            self.evaluate(law, 1)
        for value in (True, float('nan'), float('inf'), '1'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.evaluate(X, value)

    def test_node_budget_and_fractional_dimensions(self):
        wide = operation('min', *[operation('min', *[constant(1) for _ in range(16)]) for _ in range(16)])
        with self.assertRaisesRegex(ValueError, 'budget'):
            self.evaluate(wide, 1)
        law = operation('pow', operation('sqrt', X), constant(2))
        self.assertAlmostEqual(self.evaluate(law, .3, 'm', 'm'), .3, places=15)
        with self.assertRaisesRegex(ValueError, 'literal constant exponent'):
            self.evaluate(operation('pow', constant(1, 'm'), X), 2, expected_unit='m')

    def test_multiple_variables_and_length_scaling(self):
        from superfish_ng.scalar_expressions import evaluate_scalar_expression, validate_scalar_expression
        radius, length = dict(variable='radius'), dict(variable='length')
        law = operation('mul', radius, operation('exp', operation('div', X, length)))
        units = dict(radius='m', length='m', x='m')
        metadata = validate_scalar_expression(law, units, expected_unit='m')
        self.assertEqual(metadata['variables'], ['length', 'radius', 'x'])
        values = dict(radius=.1, length=.2, x=.03)
        a = evaluate_scalar_expression(law, values, units, expected_unit='m')
        b = evaluate_scalar_expression(law, {k: 2*v for k, v in values.items()}, units, expected_unit='m')
        self.assertEqual(b, 2*a)
        with self.assertRaisesRegex(ValueError, 'exactly'):
            evaluate_scalar_expression(law, dict(radius=.1, x=.03), units, expected_unit='m')
