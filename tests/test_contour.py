# SPDX-License-Identifier: Apache-2.0
import math
import unittest
from superfish_ng.contour import Contour


class ContourTests(unittest.TestCase):
    def test_reentrant_area_volume_orientation_and_scaling(self):
        points=((0.,0.),(3.,0.),(3.,2.),(1.,2.),(1.,1.),(2.,1.),(2.,.5),(0.,.5))
        tags=('axis',)+('pec',)*7
        original=Contour(points,tags)
        self.assertEqual(original.area_m2,4.)
        self.assertAlmostEqual(original.volume_m3,7.5*math.pi)
        for offset in range(len(points)):
            rotated=points[offset:]+points[:offset]
            rotated_tags=tags[offset:]+tags[:offset]
            self.assertEqual(Contour(rotated,rotated_tags),original)
            reversed_tags=tuple(rotated_tags[(i-1)%len(tags)] for i in range(len(tags)-1,-1,-1))
            self.assertEqual(Contour(rotated[::-1],reversed_tags),original)
        scaled=Contour(tuple((z*3,r*3) for z,r in points),tags)
        self.assertAlmostEqual(scaled.area_m2/original.area_m2,9)
        self.assertAlmostEqual(scaled.volume_m3/original.volume_m3,27)

    def test_triangle_cone_is_a_valid_single_boundary(self):
        cone=Contour(((0,0),(3,0),(0,2)),('axis','pec','pec'))
        self.assertAlmostEqual(cone.area_m2,3)
        self.assertAlmostEqual(cone.volume_m3,4*math.pi)

    def test_invalid_crossings_contacts_axis_and_tags(self):
        bad=[((0,0),(3,0),(1,2),(3,2),(0,1)),
             ((0,0),(3,0),(3,2),(1,0),(0,2)),
             ((0,0),(3,0),(3,2),(3,1),(0,1)),
             ((0,0),(3,0),(3,2),(0,2),(0,0)),
             ((0,0),(3,0),(3,-1),(0,1))]
        for points in bad:
            with self.subTest(points=points),self.assertRaises(ValueError):
                Contour(points,('axis',)+('pec',)*(len(points)-1))
        rectangle=((0,0),(3,0),(3,2),(0,2))
        for tags in [('pec',)*4,('axis','pec','magnetic_symmetry','pec')]:
            with self.assertRaises(ValueError):Contour(rectangle,tags)
        self.assertEqual(Contour(rectangle,('axis','electric_symmetry','pec','pec')).area_m2,6)
