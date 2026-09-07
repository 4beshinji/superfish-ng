# SPDX-License-Identifier: Apache-2.0
import math
import unittest
import numpy as np
from superfish_ng.conics import LineSegment,EllipseArc,HyperbolaArc
from superfish_ng.curved_contour import CurvedContour
from superfish_ng.curve_moments import revolution_volume_contribution


class CurveMomentTests(unittest.TestCase):
    def test_frustum_and_spheroid_independent_volumes(self):
        for a,b in ((2.,2.),(2.,3.)):
            points = ((0,0),(4,0),(4,b),(0,a))
            curves = tuple(LineSegment(p,q) for p,q in zip(points,points[1:]+points[:1]))
            contour = CurvedContour(curves,('axis','pec','pec','pec'),0.)
            self.assertAlmostEqual(contour.volume_m3,math.pi*4*(a*a+a*b+b*b)/3)
        for scale in (1e-6,1.,1e6):
            a,b = 3*scale,2*scale
            contour = CurvedContour((LineSegment((0,0),(2*a,0)),EllipseArc((a,0),(a,b),0,math.pi)),
                                    ('axis','pec'),1e-12*scale)
            self.assertAlmostEqual(contour.volume_m3/(4*math.pi*a*b*b/3),1)

    def test_hyperbolic_wall_independent_integral(self):
        # z=sinh(u), r=cosh(u): r²=1+z². Integrate in z directly.
        u0,u1 = -.4,.8
        arc = HyperbolaArc((0,0),(1,1),u0,u1,branch=-1,rotation_rad=math.pi/2)
        # This rotation gives z=-sinh(u), r=-cosh(u), with reversed z.
        expected = math.pi*((math.sinh(u1)+math.sinh(u1)**3/3)
                            -(math.sinh(u0)+math.sinh(u0)**3/3))
        self.assertAlmostEqual(revolution_volume_contribution(arc),expected)

    def test_rotated_open_conics_match_independent_numerical_boundary_integral(self):
        for curve in (EllipseArc((1,2),(3,2),.2,2.1,.6),HyperbolaArc((1,2),(3,2),-.7,1.1,-1,.4)):
            # Numerical differentiation and trapezoidal line integration use
            # point coordinates alone, independent of the Laurent coefficients.
            p = curve.evaluate(np.linspace(0,1,20001))['points_zr_m']
            z,r = p.T
            estimate = -math.pi*np.sum(np.diff(z)*(r[:-1]**2+r[:-1]*r[1:]+r[1:]**2)/3)
            actual = revolution_volume_contribution(curve)
            self.assertLess(abs(actual-estimate)/abs(actual),1e-7)
