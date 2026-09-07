# SPDX-License-Identifier: Apache-2.0
import math
import unittest
import numpy as np
from superfish_ng import Case
from superfish_ng.contour import Contour
from superfish_ng.contour_mesh import triangulate_contour


class InitialContourMeshTests(unittest.TestCase):
    def check_moments(self, contour, area, volume):
        mesh = triangulate_contour(Case((), contour=contour))
        p = mesh.points[mesh.triangles]
        u, v = p[:, 1]-p[:, 0], p[:, 2]-p[:, 0]
        areas = (u[:, 0]*v[:, 1]-u[:, 1]*v[:, 0])/2
        self.assertTrue(np.all(areas > 0))
        self.assertAlmostEqual(areas.sum()/area, 1, places=13)
        self.assertAlmostEqual(np.sum(2*math.pi*areas*p[:, :, 0].mean(axis=1))/volume,
                               1, places=13)
        self.assertEqual(len(mesh.triangles), len(contour.vertices_zr_m)-2)
        np.testing.assert_array_equal(mesh.points[:, ::-1], contour.vertices_zr_m)
        self.assertEqual(tuple(mesh.boundary_tags), contour.edge_tags)
        return mesh

    def test_reentrant_partition_independent_rectangles_and_scale(self):
        vertices = ((0,0),(3,0),(3,2),(1,2),(1,1),(2,1),(2,.5),(0,.5))
        for scale in (1e-6, 1., 1e6):
            contour = Contour(tuple((z*scale,r*scale) for z,r in vertices),
                              ('axis',)+('pec',)*7)
            mesh = self.check_moments(contour, 4*scale**2, 7.5*math.pi*scale**3)
            again = triangulate_contour(Case((), contour=contour))
            np.testing.assert_array_equal(mesh.triangles, again.triangles)
            # Interior of the explicit radial gap cannot be covered.
            for triangle in mesh.points[mesh.triangles]/scale:
                for weights in ((.2,.3,.5),(.6,.2,.2), (1/3,)*3):
                    r,z = np.asarray(weights) @ triangle
                    self.assertFalse(1 < z < 2 and .5 < r < 1)

    def test_collinear_axis_and_mixed_end_tags_survive(self):
        contour = Contour(((0,0),(1,0),(2,0),(2,1),(1,1),(0,1),(0,.5)),
                          ('axis','axis','pec','pec','pec','pec','magnetic_symmetry'))
        mesh = self.check_moments(contour, 2., 2*math.pi)
        np.testing.assert_array_equal(mesh.points[mesh.axis_nodes, 1], [0,1,2])

    def test_cone_and_narrow_reentrant_channel(self):
        self.check_moments(Contour(((0,0),(3,0),(0,2)), ('axis','pec','pec')),
                           3., 4*math.pi)
        width = 1e-5
        contour = Contour(((0,0),(3,0),(3,2),(1,2),(1,1),(2,1),
                           (2,width),(0,width)), ('axis',)+('pec',)*7)
        # Separate rectangles: lower channel, right riser, upper left arm.
        self.check_moments(contour, 3+2*width, math.pi*(7+2*width**2))

    def test_profile_requires_explicit_conversion(self):
        with self.assertRaisesRegex(ValueError, 'contour Case'):
            triangulate_contour(Case(((0,.1),(.2,.1))))
