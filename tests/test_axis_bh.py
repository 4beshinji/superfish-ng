# SPDX-License-Identifier: Apache-2.0
import json,unittest
from dataclasses import replace
import numpy as np
from scripts.axis_bh_reference import uniform_field,current_cylinder,radial_layers,field_l2_errors
from superfish_ng.axis_bh import AxisBHCase,solve_axis_bh,axis_bh_quantities
from superfish_ng.nonlinear_magnetic import MagneticNewtonControls,MagneticNonlinearFailure
from superfish_ng.axis_magnetic_materials import AxisMagneticPartition
from superfish_ng.magnetic_materials import LinearMagneticMaterial
from superfish_ng.axis_magnetostatic import AxisMagnetostaticCase,solve_axis_magnetostatic,axis_magnetostatic_quantities
from superfish_ng.constants import MU0


class AxisBHSolveTests(unittest.TestCase):
    def test_uniform_nonlinear_axis_and_axial_material_layers_with_both_boundaries(self):
        rejected=0
        for boundary in ('fixed','tangential'):
            for holes,layers in ((0,False),(1,True)):
                c,ref=uniform_field(n=2,holes=holes,axial_layers=layers,boundary=boundary,scale=2.,h_scale=7.,amplitude=-1.,shift=-.25)
                s=solve_axis_bh(c);q=axis_bh_quantities(s);self.assertLess(max(field_l2_errors(s,ref)),1e-10)
                for name,value in ref['potentials'].items():self.assertAlmostEqual(q[name]/value,1.,places=10)
                self.assertGreater(abs(q['energy_j']-q['coenergy_j']),0.);self.assertEqual(len(s.free_dofs),len(s.aphi_over_r_t) if boundary=='tangential' else len(s.aphi_over_r_t)-len(s.fixed_boundary_dofs['outer']))
                self.assertGreater(len(s.space.axis_dofs),0);probe=s.probe_at(c.partition.mesh.points_rz_m[c.partition.mesh.axis_nodes]);np.testing.assert_array_equal(probe['fields']['Br_T'],0.);np.testing.assert_array_equal(probe['fields']['Hr_A_per_m'],0.);np.testing.assert_array_equal(probe['fields']['Aphi_Wb_per_m'],0.)
                self.assertNotIn('reference_aphi_over_r_t',probe);self.assertEqual(len(probe['fields']),6)
                rejected+=sum(v['event']=='trial' and not v['accepted'] for v in s.iteration_report['history'])
        self.assertGreater(rejected,0)

    def test_exact_current_in_nonzero_curve_segment_keeps_original_H_and_true_tangent(self):
        for boundary in ('fixed','tangential'):
            c,ref=current_cylinder(n=2,single_interval=True,boundary=boundary);s=solve_axis_bh(c);q=axis_bh_quantities(s);self.assertLess(max(field_l2_errors(s,ref)),1e-10)
            for name,value in ref['potentials'].items():self.assertAlmostEqual(q[name]/value,1.,places=10)
            self.assertGreater(np.linalg.norm(s.tangent@s.aphi_over_r_t-s.internal_load_a_m2)/np.linalg.norm(s.internal_load_a_m2),.1)
            self.assertLess(q['discrete_work_relative_error'],1e-9);self.assertLess(q['discrete_current_work_relative_error'],1e-9)
            self.assertEqual(s.iteration_report['coefficient_unit'],'T');self.assertEqual(s.iteration_report['residual_unit'],'A m^2')

    def test_mesh_error_and_knot_quadrature_residual_are_distinct_from_Newton_convergence(self):
        for factory in (current_cylinder,radial_layers):
            previous=None
            for n in (4,8,16):
                c,ref=factory(n=n,quadrature_order=8);s=solve_axis_bh(c);q=axis_bh_quantities(s);errors=field_l2_errors(s,ref)
                self.assertLess(s.relative_residual,1e-10);self.assertGreater(errors[3],1e-5)
                if previous is not None:self.assertTrue(all(a<b for a,b in zip(errors,previous)),(errors,previous))
                previous=errors
            self.assertLess(max(errors[:2]),1e-3);self.assertLess(max(errors[2:]),.03)
        c,ref=current_cylinder(n=4,quadrature_order=4);s=solve_axis_bh(c);q=axis_bh_quantities(s);comparison=q['quadrature_comparison']
        self.assertEqual(comparison['orders'],[4,8]);self.assertGreater(comparison['free_dof_relative_residual_at_comparison_order'],100*s.relative_residual);self.assertGreater(comparison['tangent_relative_difference'],1e-6)

    def test_linear_limit_matches_original_axis_FEM_with_all_axis_DOFs(self):
        for boundary in ('fixed','tangential'):
            c,ref=current_cylinder(n=4,linear=True,boundary=boundary);p=c.partition;op=AxisMagneticPartition(p.mesh,[LinearMagneticMaterial(m.id,1/(MU0*m.h_a_per_m[1]/m.b_t[1])) for m in p.materials],p.regions)
            oc=AxisMagnetostaticCase(op,dict(c.current_density_phi_a_per_m2),c.boundaries,1);old=solve_axis_magnetostatic(oc);s=solve_axis_bh(c)
            np.testing.assert_allclose(s.aphi_over_r_t,old.aphi_over_r_t,rtol=1e-10,atol=1e-12);self.assertEqual(len(s.space.axis_dofs),len(old.space.axis_dofs));self.assertEqual(s.iteration_report['iterations'],1)
            q=axis_bh_quantities(s);oq=axis_magnetostatic_quantities(old);self.assertAlmostEqual(q['energy_j']/oq['energy_j'],1.,places=10);self.assertAlmostEqual(q['coenergy_j']/q['energy_j'],1.,places=10)

    def test_iteration_range_and_invalid_initial_failures_retain_context_and_last_state(self):
        c,_=uniform_field(n=2)
        with self.assertRaises(MagneticNonlinearFailure) as caught:solve_axis_bh(replace(c,controls=MagneticNewtonControls(max_iterations=1)))
        report=caught.exception.report;self.assertEqual(report['schema_version'],2);self.assertEqual(report['coefficient_field'],'aphi_over_r_t');self.assertNotIn('last_valid_relative_coefficients',report);self.assertEqual(report['reason'],'iteration_limit');self.assertIsNotNone(report['last_valid_coefficients']);self.assertEqual(report['context']['energy_unit'],'J');self.assertEqual(json.loads(json.dumps(report,allow_nan=False)),report)
        with self.assertRaises(MagneticNonlinearFailure) as caught:solve_axis_bh(replace(c,initial_aphi_over_r_t=[100.]*len(c.partition.mesh.points_rz_m)))
        self.assertEqual(caught.exception.report['reason'],'invalid_initial_field');self.assertIsNone(caught.exception.report['last_valid_coefficients'])
        raw=c.to_dict();next(b for b in raw['boundaries'] if b.get('tangential_h_a_per_m',0.)!=0.)['tangential_h_a_per_m']=1e9;raw['controls']['max_backtracks']=3
        with self.assertRaises(MagneticNonlinearFailure) as caught:solve_axis_bh(AxisBHCase.from_dict(raw))
        self.assertEqual(caught.exception.report['reason'],'line_search_limit');self.assertTrue(any(v.get('reason')=='invalid_material_trial' for v in caught.exception.report['history']));np.testing.assert_array_equal(caught.exception.report['last_valid_coefficients'],0.)

    def test_zero_field_and_strict_dedicated_case_initial_boundary_and_probe(self):
        for boundary in ('fixed','tangential'):
            c,ref=uniform_field(n=2,amplitude=0.,boundary=boundary);s=solve_axis_bh(c);q=axis_bh_quantities(s);np.testing.assert_array_equal(s.aphi_over_r_t,0.);self.assertEqual(q['energy_j'],0.);self.assertEqual(q['coenergy_j'],0.);self.assertEqual(s.iteration_report['iterations'],0)
            self.assertEqual(AxisBHCase.from_dict(json.loads(json.dumps(c.to_dict()))).to_dict(),c.to_dict())
            for name,value in [('element_order',2),('schema_version',True),('physics','linear_magnetostatic'),('quadrature_order',True),('reference_aphi_over_r_t',1.),('initial_aphi_over_r_t',[0.])]:
                data=c.to_dict();data[name]=value
                with self.assertRaises(ValueError):AxisBHCase.from_dict(data)
            for points in ([[False,0.]],[[1+0j,0.]],[[100.,100.]], [[-.01,0.]]):
                with self.assertRaises(ValueError):s.probe_at(points)
            if boundary=='fixed':
                with self.assertRaises(ValueError):replace(c,initial_aphi_over_r_t=[1.]*len(s.aphi_over_r_t))
