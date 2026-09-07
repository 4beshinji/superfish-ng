# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from superfish_ng.curved_queries import quadratic_radial_extent


class CurvedQueryTests(unittest.TestCase):
    def extent(self, points, z):
        return quadratic_radial_extent(np.array(points, dtype=float), np.array([[0, 1, 2]]), z)

    def test_bulge_beyond_endpoint_chord_and_scale(self):
        # r=1+4t(1-t), z=t: the endpoint chord misses the bulge.
        for scale in (1e-5, 1., 1e5):
            points = scale*np.array([[1, 0], [1, 1], [2, .5]])
            for t in (0., .1, .5, .9, 1.):
                self.assertAlmostEqual(self.extent(points, scale*t)/scale, 1+4*t*(1-t), places=13)

    def test_fold_tangent_and_constant_plane(self):
        # r=1+t, z=4t(1-t): two intersections; use the outer one.
        points = [[1, 0], [2, 0], [1.5, 1]]
        self.assertAlmostEqual(self.extent(points, .75), 1.75)
        self.assertAlmostEqual(self.extent(points, 1.), 1.5)
        with self.assertRaisesRegex(ValueError, 'intersect'):
            self.extent(points, 1.001)
        self.assertEqual(self.extent([[1, 2], [1, 2], [2, 2]], 2.), 2.)
        with self.assertRaisesRegex(ValueError, 'finite'):
            self.extent(points, True)
