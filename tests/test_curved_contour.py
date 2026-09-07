# SPDX-License-Identifier: Apache-2.0
import math
import unittest
from superfish_ng.conics import LineSegment,EllipseArc
from superfish_ng.curved_contour import CurvedContour


class CurvedContourTests(unittest.TestCase):
    def test_two_primitive_half_ellipse_area_and_scaling(self):
        for scale in (1e-6,1.,1e6):
            a,b = 3*scale,2*scale
            curves = (LineSegment((0,0),(2*a,0)),EllipseArc((a,0),(a,b),0,math.pi))
            contour = CurvedContour(curves,('axis','pec'),1e-12*scale)
            self.assertAlmostEqual(contour.area_m2/(math.pi*a*b/2),1)
            self.assertEqual(contour.curves,curves)

    def test_split_axis_local_tags_and_rectangle_area(self):
        vertices = ((0,0),(1,0),(2,0),(2,1),(0,1),(0,.5))
        curves = tuple(LineSegment(a,b) for a,b in zip(vertices,vertices[1:]+vertices[:1]))
        tags = ('axis','axis','electric_symmetry','pec','pec','magnetic_symmetry')
        contour = CurvedContour(curves,tags,0.)
        self.assertEqual(contour.area_m2,2.)
        self.assertEqual(contour.edge_tags,tags)

    def test_invalid_topology_gaps_tags_and_orientation(self):
        vertices = ((0,0),(3,0),(1,2),(3,2),(0,1))
        crossed = tuple(LineSegment(a,b) for a,b in zip(vertices,vertices[1:]+vertices[:1]))
        with self.assertRaises(ValueError):CurvedContour(crossed,('axis',)+('pec',)*4,1e-12)
        axis = LineSegment((0,0),(2,0))
        arc = EllipseArc((1,0),(1,1),0,math.pi)
        for tags in (('pec','pec'),('axis','axis'),('axis','electric_symmetry')):
            with self.assertRaises(ValueError):CurvedContour((axis,arc),tags,1e-12)
        with self.assertRaisesRegex(ValueError,'gap'):
            CurvedContour((axis,EllipseArc((1.01,0),(1,1),0,math.pi)),('axis','pec'),1e-12)
        with self.assertRaisesRegex(ValueError,'tolerance'):
            CurvedContour((axis,arc),('axis','pec'),.01)
        with self.assertRaises(ValueError):
            CurvedContour((LineSegment((2,0),(0,0)),EllipseArc((1,0),(1,1),math.pi,-math.pi)),('axis','pec'),1e-12)
        with self.assertRaises(ValueError):
            CurvedContour((axis,EllipseArc((1,0),(1,1),0,-math.pi)),('axis','pec'),1e-12)
