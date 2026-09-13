# SPDX-License-Identifier: Apache-2.0
import json,unittest
from dataclasses import replace
import numpy as np
from scripts.off_axis_bh_reference import radial_field,current_annulus,radial_layers,field_l2_errors
from scripts.validate_off_axis_bh_solve import errors
from superfish_ng.off_axis_bh import OffAxisBHCase,solve_off_axis_bh,off_axis_bh_quantities
from superfish_ng.nonlinear_magnetic import MagneticNewtonControls,MagneticNonlinearFailure
from superfish_ng.off_axis_magnetic_materials import OffAxisMagneticPartition
from superfish_ng.magnetic_materials import LinearMagneticMaterial
from superfish_ng.off_axis_magnetostatic import OffAxisMagnetostaticCase,solve_off_axis_magnetostatic,off_axis_magnetostatic_quantities
from superfish_ng.constants import MU0


class OffAxisBHSolveTests(unittest.TestCase):
    def test_exact_radial_field_logarithmic_potentials_material_interfaces_and_psi_reference(self):
        for holes,layers in ((0,False),(1,True),(2,True)):
            c,ref=radial_field(n=2,holes=holes,radial_materials=layers,scale=2.,h_scale=7.,amplitude=-1.,shift=-.25,offset=.125)
            s=solve_off_axis_bh(c);values,flux,q=errors(s,ref);self.assertLess(max(*values,flux),1e-10);self.assertNotEqual(q['energy_j'],q['coenergy_j'])
            self.assertGreater(len(s.free_dofs),0);self.assertEqual(s.reference_psi_wb,.125)
            probe=s.probe_at(c.partition.mesh.points_rz_m);self.assertEqual(len(probe['fields']),6);self.assertTrue(probe['material_provenance'])
            for value in (s.psi_wb,s.psi_relative_to_reference_wb,s.internal_load_a,s.current_load_a,s.boundary_load_a,s.free_dofs):self.assertFalse(value.flags.writeable)
            self.assertEqual(OffAxisBHCase.from_dict(json.loads(json.dumps(c.to_dict()))).to_dict(),c.to_dict())

    def test_nonlinear_current_true_tangent_and_both_boundaries_keep_actual_internal_load(self):
        for boundary in ('fixed','tangential'):
            c,ref=current_annulus(n=4,boundary=boundary);s=solve_off_axis_bh(c);q=off_axis_bh_quantities(s)
            self.assertGreater(np.linalg.norm(s.tangent@s.psi_relative_to_reference_wb-s.internal_load_a)/np.linalg.norm(s.internal_load_a),.01)
            self.assertLess(q['discrete_work_relative_error'],1e-9);self.assertLess(q['discrete_current_relative_error'],1e-9)
            self.assertEqual(s.iteration_report['coefficient_unit'],'Wb');self.assertEqual(s.iteration_report['residual_unit'],'A');self.assertGreater(s.iteration_report['iterations'],1)
            shifted,_=current_annulus(n=4,boundary=boundary,offset=.125);ss=solve_off_axis_bh(shifted)
            np.testing.assert_allclose(ss.psi_relative_to_reference_wb,s.psi_relative_to_reference_wb,rtol=1e-10,atol=1e-14)
            self.assertAlmostEqual(off_axis_bh_quantities(ss)['energy_j']/q['energy_j'],1.,places=10)

    def test_mesh_error_and_knot_quadrature_residual_are_distinct_from_Newton_convergence(self):
        for factory in (current_annulus,radial_layers):
            previous=None
            for n in (4,8,16):
                c,ref=factory(n=n,quadrature_order=8);s=solve_off_axis_bh(c);q=off_axis_bh_quantities(s);values=field_l2_errors(s,ref)
                self.assertLess(s.relative_residual,1e-10);self.assertGreater(values[3],1e-5)
                if previous is not None:self.assertTrue(all(a<b for a,b in zip(values,previous)),(values,previous))
                previous=values
            self.assertLess(max(values[:2]),1e-3);self.assertLess(max(values[2:]),.03)
        c,ref=current_annulus(n=4,quadrature_order=4);s=solve_off_axis_bh(c);comparison=off_axis_bh_quantities(s)['quadrature_comparison']
        self.assertEqual(comparison['orders'],[4,8]);self.assertGreater(comparison['free_dof_relative_residual_at_comparison_order'],100*s.relative_residual);self.assertGreater(comparison['tangent_relative_difference'],1e-6)

    def test_linear_limit_matches_original_off_axis_FEM_with_the_same_psi_reference(self):
        for boundary in ('fixed','tangential'):
            c,ref=current_annulus(n=4,linear=True,boundary=boundary,offset=.125,quadrature_order=16);p=c.partition;op=OffAxisMagneticPartition(p.mesh,[LinearMagneticMaterial(m.id,1/(MU0*m.h_a_per_m[1]/m.b_t[1])) for m in p.materials],p.regions)
            old=solve_off_axis_magnetostatic(OffAxisMagnetostaticCase(op,dict(c.current_density_phi_a_per_m2),c.boundaries,1,16));s=solve_off_axis_bh(c)
            np.testing.assert_allclose(s.psi_relative_to_reference_wb,old.psi_relative_to_reference_wb,rtol=1e-10,atol=1e-14);self.assertEqual(s.iteration_report['iterations'],1)
            q=off_axis_bh_quantities(s);oq=off_axis_magnetostatic_quantities(old);self.assertAlmostEqual(q['energy_j']/oq['energy_j'],1.,places=10);self.assertAlmostEqual(q['coenergy_j']/q['energy_j'],1.,places=10)

    def test_iteration_range_and_invalid_initial_failures_retain_explicit_relative_psi(self):
        c,_=current_annulus(n=2)
        with self.assertRaises(MagneticNonlinearFailure) as caught:solve_off_axis_bh(replace(c,controls=MagneticNewtonControls(max_iterations=1)))
        report=caught.exception.report;self.assertEqual(report['schema_version'],2);self.assertEqual(report['coefficient_field'],'psi_relative_to_reference_wb');self.assertNotIn('last_valid_relative_coefficients',report);self.assertEqual(report['reason'],'iteration_limit');self.assertIsNotNone(report['last_valid_coefficients']);self.assertEqual(report['context']['energy_unit'],'J');self.assertEqual(json.loads(json.dumps(report,allow_nan=False)),report)
        initial=np.zeros(len(c.partition.mesh.points_rz_m));initial[1]=100.
        with self.assertRaises(MagneticNonlinearFailure) as caught:solve_off_axis_bh(replace(c,initial_psi_relative_to_reference_wb=initial.tolist()))
        self.assertEqual(caught.exception.report['reason'],'invalid_initial_field');self.assertIsNone(caught.exception.report['last_valid_coefficients'])
        raw=c.to_dict();next(b for b in raw['boundaries'] if b.get('tangential_h_a_per_m',0.)!=0.)['tangential_h_a_per_m']=1e9;raw['controls']['max_backtracks']=3
        with self.assertRaises(MagneticNonlinearFailure) as caught:solve_off_axis_bh(OffAxisBHCase.from_dict(raw))
        self.assertEqual(caught.exception.report['reason'],'line_search_limit');self.assertTrue(any(v.get('reason')=='invalid_material_trial' for v in caught.exception.report['history']));np.testing.assert_array_equal(caught.exception.report['last_valid_coefficients'],0.)

    def test_zero_field_nonzero_aphi_and_strict_dedicated_case_initial_boundary_and_probe(self):
        for offset in (0.,.125):
            c,ref=radial_field(n=2,amplitude=0.,offset=offset);s=solve_off_axis_bh(c);q=off_axis_bh_quantities(s);np.testing.assert_array_equal(s.psi_relative_to_reference_wb,0.);np.testing.assert_array_equal(s.psi_wb,offset);self.assertEqual(q['energy_j'],0.);self.assertEqual(q['coenergy_j'],0.);self.assertEqual(s.iteration_report['iterations'],0)
            points=c.partition.mesh.points_rz_m;probe=s.probe_at(points);np.testing.assert_allclose(probe['fields']['Aphi_Wb_per_m'],offset/points[:,0],rtol=1e-14,atol=0.)
            for field in ('Br_T','Bz_T','Hr_A_per_m','Hz_A_per_m'):np.testing.assert_array_equal(probe['fields'][field],0.)
            for name,value in [('element_order',2),('schema_version',True),('physics','linear_magnetostatic'),('quadrature_order',True),('reference_psi_wb',1.),('initial_psi_relative_to_reference_wb',[0.])]:
                data=c.to_dict();data[name]=value
                with self.assertRaises(ValueError):OffAxisBHCase.from_dict(data)
            for points in ([[False,0.]],[[1+0j,0.]],[[100.,100.]],[[0.,0.]]):
                with self.assertRaises(ValueError):s.probe_at(points)
            with self.assertRaises(ValueError):replace(c,initial_psi_relative_to_reference_wb=[1.]*len(s.psi_wb))
            raw=c.to_dict()
            for b in raw['boundaries']:
                if b['kind']=='fixed_psi':b.pop('psi_wb');b.update(kind='tangential_h',tangential_h_a_per_m=0.)
            with self.assertRaisesRegex(ValueError,'fixed-psi'):OffAxisBHCase.from_dict(raw)
