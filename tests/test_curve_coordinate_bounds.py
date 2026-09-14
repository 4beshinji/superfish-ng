# SPDX-License-Identifier: Apache-2.0
"""Independent coordinate translation, analytic cap and cancellation bounds."""
from dataclasses import replace
from decimal import Decimal,localcontext
import math,unittest
import numpy as np
from superfish_ng.conics import LineSegment,EllipseArc,HyperbolaArc,rotation_cos_sin
from superfish_ng.curve_bounds import curve_bounds
from superfish_ng.curved_contour import CurvedContour

class CurveCoordinateBoundsTests(unittest.TestCase):
 def test_translating_one_coordinate_preserves_other_coordinate_bounds(self):
  curves=(LineSegment((.125,0.),(.1875,.0625)),EllipseArc((.125,0.),(.0625,.03125),0.,math.pi/2,.3),HyperbolaArc((.125,0.),(.0625,.03125),-.5,.7,1,.3))
  for c in curves:
   for coordinate in (0,1):
    def shift(p):
     q=list(p);q[coordinate]+=1024.;return tuple(q)
    moved=(replace(c,start_zr_m=shift(c.start_zr_m),end_zr_m=shift(c.end_zr_m)) if isinstance(c,LineSegment) else replace(c,center_zr_m=shift(c.center_zr_m)))
    for interval in ((0.,1.),(.25,.75)):
     a,b=curve_bounds(c,*interval),curve_bounds(moved,*interval)
     np.testing.assert_array_equal(np.array(a)[:,1-coordinate],np.array(b)[:,1-coordinate])

 def test_reflected_circular_cap_preserves_analytic_extents(self):
  for tag in ('electric_symmetry','magnetic_symmetry'):
   for straight in (.125,.140625,.15625):
    radius=.0625;length=straight+radius
    curves=(LineSegment((0.,0.),(length,0.)),EllipseArc((straight,0.),(radius,radius),0.,math.pi/2),LineSegment((straight,radius),(0.,radius)),LineSegment((0.,radius),(0.,0.)))
    full=CurvedContour(curves,('axis','pec','pec',tag),1e-14).reflected()
    self.assertNotIn(tag,full.edge_tags)
    for curve in full.curves:
     low,high=curve_bounds(curve)
     self.assertGreaterEqual(low[1],-1e-14)
     self.assertLessEqual(high[1],radius+1e-14)
    self.assertEqual(max(max(c.start_zr_m[0],c.end_zr_m[0]) for c,t in zip(full.curves,full.edge_tags) if t=='axis'),2*length)

 def test_cancellation_encloses_independent_decimal_values(self):
  with localcontext() as context:
   context.prec=70;D=Decimal.from_float
   line=LineSegment((-1e12,.1),(1e12,.2))
   interval=(.5-1e-14,.5+1e-14);low,high=curve_bounds(line,*interval)
   for t in np.linspace(*interval,31):
    for j in (0,1):
     exact=(Decimal(1)-D(float(t)))*D(line.start_zr_m[j])+D(float(t))*D(line.end_zr_m[j])
     self.assertLessEqual(D(float(low[j])),exact);self.assertGreaterEqual(D(float(high[j])),exact)
   curve=HyperbolaArc((.125,-.25),(3.,2.),11.,12.,1,.7)
   low,high=curve_bounds(curve)
   c,s=map(D,rotation_cos_sin(curve.rotation_rad))
   for u in (11.,11.25,11.5,11.75,12.):
    e=D(u).exp();co=(e+1/e)/2;si=(e-1/e)/2
    values=(D(.125)+3*co*c-2*si*s,D(-.25)+3*co*s+2*si*c)
    for j,v in enumerate(values):
     self.assertLessEqual(D(float(low[j])),v);self.assertGreaterEqual(D(float(high[j])),v)
