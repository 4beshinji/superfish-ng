# SPDX-License-Identifier: Apache-2.0
import math
import unittest
from superfish_ng.conics import LineSegment,EllipseArc
from superfish_ng.curved_contour import CurvedContour


class CurvedContourTests(unittest.TestCase):
    def test_chords_preserve_tags_and_converge_to_spheroid_geometry(self):
        a,b = 3.,2.
        curves = (LineSegment((0,0),(2*a,0)),EllipseArc((a,0),(a,b),0,math.pi))
        contour = CurvedContour(curves,('axis','pec'),1e-12)
        errors = []
        for tolerance in (.02,.005,.00125):
            result = contour.linearize(tolerance)
            self.assertEqual(result.contour.edge_tags.count('axis'),1)
            self.assertEqual(len(result.segment_curve_indices),len(result.contour.edge_tags))
            self.assertEqual(result.segment_curve_indices[0],0)
            self.assertTrue(all(i==1 for i in result.segment_curve_indices[1:]))
            self.assertLessEqual(result.primitive_chord_tolerance_m+max(result.endpoint_adjustments_m),tolerance)
            self.assertLess(result.area_difference_m2,0)
            # Rotating the half ellipse makes a full spheroid, an independent
            # exact volume not derived from the curve discretization.
            errors.append(abs(result.contour.volume_m3/(4*math.pi*a*b*b/3)-1))
        self.assertGreater(errors[0],errors[1])
        self.assertGreater(errors[1],errors[2])
        self.assertLess(errors[-1],.001)
        self.assertEqual(contour.curves,curves)
        with self.assertRaisesRegex(ValueError,'max_segments'):
            contour.linearize(1e-6,max_segments=5)
        with self.assertRaisesRegex(ValueError,'budget'):
            contour.linearize(1e-20)

    def test_linear_polygon_zero_adjustment_and_mixed_tags(self):
        vertices = ((0,0),(2,0),(2,1),(0,1),(0,.5))
        curves = tuple(LineSegment(a,b) for a,b in zip(vertices,vertices[1:]+vertices[:1]))
        tags = ('axis','electric_symmetry','pec','pec','magnetic_symmetry')
        result = CurvedContour(curves,tags,0).linearize(.01)
        self.assertEqual(result.contour.vertices_zr_m,vertices)
        self.assertEqual(result.contour.edge_tags,tags)
        self.assertEqual(result.area_difference_m2,0)
        self.assertEqual(max(result.endpoint_adjustments_m),0)

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
