# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import math,tempfile,unittest
import numpy as np
from superfish_ng import solve
from superfish_ng.conics import EllipseArc,curve_to_dict,curve_from_dict
from superfish_ng.project import Project
from superfish_ng.curved_project_transform import transform_curved_project
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution
from test_curved_reflection import half_case


class CardinalEllipseEvaluationTests(unittest.TestCase):
    def test_explicit_exact_quarter_and_old_serialization_contract(self):
        old=EllipseArc((.12,0.),(.12,.096),math.pi/2,math.pi/2)
        self.assertNotEqual(old.evaluate(0.)['points_zr_m'][0],.12)
        self.assertNotIn('parameter_evaluation',curve_to_dict(old))
        self.assertEqual(curve_from_dict(curve_to_dict(old)),old)
        exact=EllipseArc((.12,0.),(.12,.096),math.pi/2,math.pi/2,parameter_evaluation='exact_cardinal')
        np.testing.assert_array_equal(exact.evaluate(0.)['points_zr_m'],[.12,.096])
        np.testing.assert_array_equal(exact.evaluate([0.,1.])['tangent_zr'],[[-1.,0.],[0.,-1.]])
        self.assertEqual(curve_to_dict(exact)['parameter_evaluation'],'exact_cardinal')
        self.assertEqual(curve_from_dict(curve_to_dict(exact)),exact)

    def test_no_tolerance_snapping_and_strict_evaluation_name(self):
        for angle in (np.nextafter(math.pi/2,0.),np.nextafter(math.pi/2,math.pi)):
            curve=EllipseArc((0.,0.),(.12,.096),float(angle),.1,parameter_evaluation='exact_cardinal')
            self.assertEqual(curve.evaluate(0.)['points_zr_m'][0],.12*np.cos(angle))
            self.assertNotEqual(curve.evaluate(0.)['points_zr_m'][0],0.)
        for flag in (None,True,[],{},'snap'):
            with self.subTest(flag=flag),self.assertRaises(ValueError):
                EllipseArc((0.,0.),(.12,.096),0.,1.,parameter_evaluation=flag)

    def test_scaled_symmetry_join_and_saved_quadratic_maps(self):
        for side in ('z_min','z_max'):
            for tag in ('electric_symmetry','magnetic_symmetry'):
                case=half_case(side,tag);old=solve(case);p=Project(case,reflect_full=True,mesh_data=old.source_mesh_data)
                target=transform_curved_project(p,dict(radial_scale=1.2,axial_scale=1.2,axial_shear=0.),rf_coordinates='axial')
                new=solve(target.case,mesh_data=target.mesh_data)
                np.testing.assert_allclose(new.space.geometry.points_rz_m,old.space.geometry.points_rz_m*1.2,rtol=0,atol=1e-15)
                with tempfile.TemporaryDirectory() as tmp:
                    run=Path(tmp)/'run';save_run(target.case,new,run);saved=read_solution(run)
                    np.testing.assert_array_equal(saved.space.geometry.points_rz_m,new.space.geometry.points_rz_m)
