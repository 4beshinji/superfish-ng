# SPDX-License-Identifier: Apache-2.0
from fractions import Fraction as F
import math
import unittest
from superfish_ng.rational_bounds import bound_rational_norm


class RationalBoundsTests(unittest.TestCase):
    def assert_bracket(self, result, square):
        self.assertLessEqual(F(result['lower_bound'])**2, square)
        self.assertGreaterEqual(F(result['upper_bound'])**2, square)
        self.assertLessEqual(result['upper_bound']/result['lower_bound']-1, 1.000001e-6)

    def test_endpoint_vector_interior_and_zero(self):
        self.assert_bracket(bound_rational_norm([[0, 3], [0, 4]], [1]), F(25))
        self.assert_bracket(bound_rational_norm([[0, 1, -1]], [1]), F(1, 16))
        self.assert_bracket(bound_rational_norm([[1], [1]], [1]), F(2))
        zero = bound_rational_norm([[0]], [1])
        self.assertEqual((zero['lower_bound'], zero['upper_bound']), (0., 0.))

    def test_narrow_peak_between_uniform_samples(self):
        centre, width = F(123, 997), F(1, 100000)
        denominator = [centre*centre+width*width, -2*centre, 1]
        sampled = max(width**2/((F(i, 32)-centre)**2+width**2) for i in range(33))
        self.assertLess(sampled, F(1, 1000))
        result = bound_rational_norm([[width*width]], denominator)
        self.assert_bracket(result, F(1))
        self.assertLess(abs(result['parameter']-float(centre)), float(width)/100)
        with self.assertRaisesRegex(ValueError, 'UNVERIFIED.*budget'):
            bound_rational_norm([[width*width]], denominator, max_boxes=1)

    def test_denominator_must_be_positive_everywhere(self):
        for denominator in ([0], [-1], [1, -4, 4]):
            with self.assertRaisesRegex(ValueError, 'strictly positive'):
                bound_rational_norm([[1]], denominator)
        # Zero at a non-dyadic point must not produce a success even for N=0.
        with self.assertRaisesRegex(ValueError, 'UNVERIFIED.*budget'):
            bound_rational_norm([[0]], [F(1, 9), F(-2, 3), 1], max_boxes=51)

    def test_extreme_scales_and_output_precision(self):
        for scale in (1e-300, 1e300):
            result = bound_rational_norm([[scale]], [1])
            self.assert_bracket(result, F(scale)**2)
        with self.assertRaisesRegex(ValueError, 'output precision'):
            bound_rational_norm([[1], [1]], [1], relative_tolerance=1e-20)
        for kwargs in ({'max_boxes': True}, {'relative_tolerance': True}, {'relative_tolerance': 0}):
            with self.assertRaises(ValueError):
                bound_rational_norm([[1]], [1], **kwargs)
        for coefficients in ([True], [math.inf], [], [complex(1)]):
            with self.assertRaises(ValueError):
                bound_rational_norm([coefficients], [1])
