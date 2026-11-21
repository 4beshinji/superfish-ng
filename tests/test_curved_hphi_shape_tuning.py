# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import unittest
import numpy as np
from test_curved_hphi_field_overlap import case
from superfish_ng.hphi_project import HphiProject
from superfish_ng.curved_hphi import solve_curved_hphi
from superfish_ng.axis_hphi import AxisAccelerationPath


class CurvedHphiShapeTests(unittest.TestCase):
    def test_original_full_p2_uniform_scale_and_fem_frequency(self):
        for axis in (False,True):
            p=HphiProject(case(axis,holes=2));g=p.case.geometry;before=p.to_dict()
            s=solve_curved_hphi(p.case)
            from superfish_ng.curved_hphi_shape_tuning import CurvedHphiShapeLaw
            law=CurvedHphiShapeLaw(1.,g.points_rz_m.tolist(),'transport_on_axis')
            result=law.apply(p,2.);b=result.project.case.geometry
            np.testing.assert_array_equal(b.points_rz_m,2*g.points_rz_m)
            self.assertAlmostEqual(b.area_m2/g.area_m2,4.,places=12)
            self.assertAlmostEqual(b.volume_m3/g.volume_m3,8.,places=12)
            other=solve_curved_hphi(result.project.case)
            np.testing.assert_allclose(other.frequencies_hz,s.frequencies_hz/2,rtol=1e-9)
            self.assertEqual(p.to_dict(),before)
            self.assertEqual(law.apply(p,2.).project,result.project)
            self.assertEqual(result.domain.previous.points_rz_m.tolist(),g.points_rz_m.tolist())
            self.assertEqual(len(b.base_mesh.holes_rz_m),2)

    def test_quadratic_shear_independent_volume_and_acceleration(self):
        from superfish_ng.curved_hphi_shape_tuning import CurvedHphiShapeLaw
        p=HphiProject(case(True,holes=2));g=p.case.geometry
        path=AxisAccelerationPath(.03125,.15625,.8,.0625)
        p=replace(p,case=replace(p.case,acceleration=path))
        displacement=np.column_stack((np.zeros(len(g.points_rz_m)),g.points_rz_m[:,0]**2))
        result=CurvedHphiShapeLaw(1.,displacement.tolist(),'transport_on_axis').apply(p,1.5)
        self.assertAlmostEqual(result.project.case.geometry.area_m2/g.area_m2,1.,places=12)
        self.assertAlmostEqual(result.project.case.geometry.volume_m3/g.volume_m3,1.,places=12)
        self.assertEqual(result.project.case.acceleration,path)
        result=CurvedHphiShapeLaw(1.,g.points_rz_m.tolist(),'transport_on_axis').apply(p,1.7)
        actual=result.project.case.acceleration
        np.testing.assert_allclose([actual.z_start_m,actual.z_end_m,actual.phase_origin_m],
            1.7*np.array([path.z_start_m,path.z_end_m,path.phase_origin_m]),rtol=1e-14)
        self.assertEqual(actual.beta,path.beta)
        self.assertTrue(np.isfinite(result.diagnostic['axis_midpoint_roundoff_upper_m']))

    def test_strict_law_and_invalid_geometry(self):
        from superfish_ng.curved_hphi_shape_tuning import CurvedHphiShapeLaw
        p=HphiProject(case(True));g=p.case.geometry
        law=CurvedHphiShapeLaw(1.,g.points_rz_m.tolist(),'transport_on_axis')
        self.assertEqual(CurvedHphiShapeLaw.from_dict(law.to_dict()).to_dict(),law.to_dict())
        for name,value in (('schema_version',True),('reference_value',True),('acceleration_policy','fixed'),('extra',0)):
            raw=law.to_dict();raw[name]=value
            with self.assertRaises(ValueError):CurvedHphiShapeLaw.from_dict(raw)
        for value in (True,float('nan'),0.):
            with self.assertRaises(ValueError):law.apply(p,value)
        for displacement in (g.points_rz_m[:-1],np.ones_like(g.points_rz_m),-2*g.points_rz_m):
            with self.assertRaises(ValueError):CurvedHphiShapeLaw(1.,displacement.tolist(),'transport_on_axis').apply(p,2.)
        bad=g.points_rz_m.copy();node=g.boundary_nodes[g.boundary_tags=='axis'][0,2];bad[node,1]+=.001
        with self.assertRaises(ValueError):CurvedHphiShapeLaw(1.,bad.tolist(),'transport_on_axis').apply(p,1.1)

    def test_axis_extrapolation_and_unresolved_offset_roundoff_rejected(self):
        from superfish_ng.curved_hphi_shape_tuning import CurvedHphiShapeLaw
        from superfish_ng.curved_hphi import CurvedHphiCase
        from superfish_ng.curved_meridional_geometry import CurvedMeridionalGeometry
        from scripts.curved_meridional_reference import fixture
        p=HphiProject(case(True));g=p.case.geometry
        p=replace(p,case=replace(p.case,acceleration=AxisAccelerationPath(.03125,.15625,.8,-1.)))
        with self.assertRaisesRegex(ValueError,'extrapolation'):
            CurvedHphiShapeLaw(1.,g.points_rz_m.tolist(),'transport_on_axis').apply(p,1.5)
        data,_=fixture(True,1,z_offset=1e12)
        g=CurvedMeridionalGeometry(**data);p=HphiProject(CurvedHphiCase(g))
        with self.assertRaisesRegex(ValueError,'roundoff.*edge size'):
            CurvedHphiShapeLaw(1.,g.points_rz_m.tolist(),'transport_on_axis').apply(p,1.7)
