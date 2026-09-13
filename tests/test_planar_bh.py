# SPDX-License-Identifier: Apache-2.0
import copy,json,unittest
from dataclasses import replace
import numpy as np
from scripts.planar_bh_reference import uniform_field,layered_field,current_slab,field_l2_errors
from superfish_ng.planar_bh import PlanarBHCase,solve_planar_bh,planar_bh_quantities
from superfish_ng.nonlinear_magnetic import MagneticNewtonControls,MagneticNonlinearFailure
from superfish_ng.magnetic_materials import PlanarMagneticPartition,LinearMagneticMaterial
from superfish_ng.planar_magnetostatic import PlanarMagnetostaticCase,solve_planar_magnetostatic,planar_magnetostatic_quantities
from superfish_ng.constants import MU0


class PlanarBHSolveTests(unittest.TestCase):
    def test_exact_uniform_nonlinear_field_boundary_gauge_rotation_and_saturation(self):
        rejected=0
        for boundary in ('fixed','tangential'):
            for b in (.375,1.5,-.75):
                for offset in (0.,.125):
                    case,reference=uniform_field(n=2,b_t=b,boundary=boundary,offset=offset,angle=.713 if offset else 0.,shift=(-.25,.125) if offset else (0.,0.))
                    s=solve_planar_bh(case);q=planar_bh_quantities(s);self.assertLess(max(field_l2_errors(s,reference)),1e-10)
                    for name,value in reference['potentials'].items():self.assertAlmostEqual(q[name]/value,1.,places=10)
                    for name,value in reference['fixed_reaction_a'].items():self.assertAlmostEqual(q['fixed_boundary_original_reaction_current_a'][name]/value,1.,places=10)
                    self.assertGreater(abs(q['energy_j_per_m']-q['coenergy_j_per_m'])/(q['energy_j_per_m']+q['coenergy_j_per_m']),1e-3)
                    self.assertLess(q['discrete_work_relative_error'],1e-9);self.assertEqual(s.iteration_report['status'],'converged')
                    rejected+=sum(v['event']=='trial' and not v['accepted'] for v in s.iteration_report['history'])
        self.assertGreater(rejected,0)

    def test_exact_layered_common_H_interface_probe_and_material_scaling(self):
        baseline=None
        for boundary in ('fixed','tangential'):
            for scale,hscale,amplitude in ((.5,1.,1.),(2.,7.,-1.)):
                case,reference=layered_field(n=2,scale=scale,h_scale=hscale,amplitude=amplitude,boundary=boundary,offset=.125,angle=.713,shift=(-.25,.125))
                s=solve_planar_bh(case);q=planar_bh_quantities(s);self.assertLess(max(field_l2_errors(s,reference)),1e-10)
                for name,value in reference['potentials'].items():self.assertAlmostEqual(q[name]/value,1.,places=10)
                normalized=s.az_relative_to_reference_wb_per_m/(scale*amplitude)
                if baseline is None:baseline=normalized.copy()
                else:np.testing.assert_allclose(normalized,baseline,rtol=1e-10,atol=1e-12)
                p=case.partition;vertex=p.interface_edges[0,0];owners=np.flatnonzero(np.any(p.mesh.triangles==vertex,axis=1));probe=s.probe_at([p.mesh.points_xy_m[vertex]])
                self.assertEqual(probe['cell_indices'],[int(owners.min())]);self.assertEqual(len(probe['fields']),5);self.assertIn('Synthetic',probe['material_provenance'][0]);self.assertNotIn('mu_r',probe)

    def test_linear_limit_matches_existing_real_P1_solve_and_energy(self):
        for boundary in ('fixed','tangential'):
            case,reference=current_slab(n=4,linear=True,boundary=boundary,offset=.125,angle=.3)
            p=case.partition;oldp=PlanarMagneticPartition(p.mesh,[LinearMagneticMaterial(m.id,1/(MU0*(m.h_a_per_m[1]/m.b_t[1]))) for m in p.materials],p.regions)
            oldcase=PlanarMagnetostaticCase(oldp,dict(case.current_density_z_a_per_m2),case.boundaries,1);old=solve_planar_magnetostatic(oldcase);s=solve_planar_bh(case)
            np.testing.assert_allclose(s.az_relative_to_reference_wb_per_m,old.az_relative_to_reference_wb_per_m,rtol=1e-11,atol=1e-13)
            q=planar_bh_quantities(s);oq=planar_magnetostatic_quantities(old);self.assertAlmostEqual(q['energy_j_per_m']/oq['energy_j_per_m'],1.,places=11);self.assertAlmostEqual(q['coenergy_j_per_m']/q['energy_j_per_m'],1.,places=11)
            self.assertEqual(s.iteration_report['iterations'],1)

    def test_current_refinement_keeps_field_errors_separate_from_Newton_residual(self):
        previous=None
        for n in (4,8,16):
            case,reference=current_slab(n=n);s=solve_planar_bh(case);q=planar_bh_quantities(s);errors=field_l2_errors(s,reference)
            self.assertLess(s.relative_residual,1e-10);self.assertGreater(errors[2],1e-5)
            if previous is not None:self.assertTrue(all(a<b for a,b in zip(errors,previous)),(errors,previous))
            previous=errors
        self.assertLess(errors[0],1e-3);self.assertLess(max(errors[1:]),.04)
        for name,value in reference['potentials'].items():self.assertLess(abs(q[name]/value-1.),1e-3)

    def test_iteration_material_range_and_initial_field_failures_retain_valid_history(self):
        case,_=uniform_field(n=2);limited=replace(case,controls=MagneticNewtonControls(max_iterations=1))
        with self.assertRaises(MagneticNonlinearFailure) as caught:solve_planar_bh(limited)
        report=caught.exception.report;self.assertEqual(report['reason'],'iteration_limit');self.assertIsNotNone(report['last_valid_relative_coefficients']);self.assertEqual(json.loads(json.dumps(report,allow_nan=False)),report)
        initial=np.zeros(len(case.partition.mesh.points_xy_m));bottom=next(b for b in case.boundaries if b.id=='bottom');fixed=set(case.partition.mesh.boundary_edges[list(bottom.edge_indices)].ravel());node=next(i for i in range(len(initial)) if i not in fixed);initial[node]=100.
        with self.assertRaises(MagneticNonlinearFailure) as caught:solve_planar_bh(replace(case,initial_az_relative_to_reference_wb_per_m=initial.tolist()))
        self.assertEqual(caught.exception.report['reason'],'invalid_initial_field');self.assertIsNone(caught.exception.report['last_valid_relative_coefficients'])
        raw=case.to_dict();next(v for v in raw['boundaries'] if v['id']=='top')['tangential_h_a_per_m']=-1e9
        raw['controls']['max_backtracks']=3
        with self.assertRaises(MagneticNonlinearFailure) as caught:solve_planar_bh(PlanarBHCase.from_dict(raw))
        report=caught.exception.report;self.assertEqual(report['reason'],'line_search_limit');self.assertTrue(any(v.get('reason')=='invalid_material_trial' for v in report['history']));np.testing.assert_array_equal(report['last_valid_relative_coefficients'],0.)

    def test_zero_field_strict_case_controls_initial_boundary_and_probe_contract(self):
        case,_=uniform_field(n=2,b_t=0.,offset=.125);s=solve_planar_bh(case);np.testing.assert_array_equal(s.az_relative_to_reference_wb_per_m,0.);np.testing.assert_array_equal(s.az_wb_per_m,.125);self.assertEqual(s.iteration_report['iterations'],0)
        self.assertEqual(PlanarBHCase.from_dict(json.loads(json.dumps(case.to_dict()))).to_dict(),case.to_dict())
        for name,value in [('max_iterations',0),('max_iterations',True),('max_backtracks',0),('relative_residual_tolerance',1e-3),('relative_residual_tolerance',True),('backtrack_factor',1.),('armijo_factor',.5)]:
            data=case.controls.to_dict();data[name]=value
            with self.assertRaises(ValueError):MagneticNewtonControls.from_dict(data)
        for name,value in [('element_order',2),('schema_version',True),('physics','linear_magnetostatic'),('quadrature_order',4),('current_density_z_a_per_m2',dict(r0=True)),('initial_az_relative_to_reference_wb_per_m',[0.])]:
            data=case.to_dict();data[name]=value
            with self.assertRaises(ValueError):PlanarBHCase.from_dict(data)
        with self.assertRaises(ValueError):replace(case,initial_az_relative_to_reference_wb_per_m=[1.]*len(s.az_wb_per_m))
        for points in ([[False,0.]],[[1+0j,0.]],[[100.,100.]]):
            with self.assertRaises(ValueError):s.probe_at(points)
