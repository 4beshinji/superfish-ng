# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from scripts.off_axis_magnetic_force_reference import axial_current_body
from scripts.planar_magnetic_force_reference import current_body
from superfish_ng.off_axis_magnetostatic import OffAxisMagnetostaticCase,solve_off_axis_magnetostatic
from superfish_ng.planar_magnetostatic import solve_planar_magnetostatic
from superfish_ng.off_axis_magnetic_force import off_axis_magnetic_force as force,off_axis_magnetic_virtual_work as work


class OffAxisMagneticForceTests(unittest.TestCase):
    def test_full_ring_force_matches_finite_current_lorentz_law_for_both_orders(self):
        for order in (1,2):
            for scale,current,constant in ((1.,10.,.0625),(.5,-10.,.03125),(2.,10.,-.125)):
                case,body,w,ref=axial_current_body(order=order,scale=scale,current_a=current,external_radial_constant_t_m=constant,shift_z_m=.25*scale);result=force(solve_off_axis_magnetostatic(case),body,w)
                self.assertLess(abs(result['force_z_n']-ref['force_z_n'])/ref['force_scale_n'],1e-9);self.assertLess(result['quadrature_relative_difference'],1e-10);self.assertIn('[N]',result['conventions']);self.assertIn('not force per unit length',result['conventions']);self.assertNotIn('force_r_n',result)
                self.assertAlmostEqual(sum(result['cell_force_z_n']),result['force_z_n'],places=10)

    def test_weight_mesh_and_quadrature_choices_keep_the_analytic_force(self):
        for n,outer,q in ((8,.875,16),(8,.95,20),(16,1.,16)):
            case,body,w,ref=axial_current_body(n=n,weight_outer=outer,quadrature_order=q,order=1);result=force(solve_off_axis_magnetostatic(case),body,w);self.assertLess(abs(result['force_z_n']-ref['force_z_n'])/ref['force_scale_n'],1e-9);self.assertEqual(result['quadrature_orders'],[q,q+4]);self.assertLess(result['quadrature_relative_difference'],1e-10)
        coarse,body,w,ref=axial_current_body(order=2,n=8,quadrature_order=4)
        with self.assertRaisesRegex(ValueError,'1/r integration'):solve_off_axis_magnetostatic(coarse)
        refined,body,w,ref=axial_current_body(order=2,n=16,quadrature_order=4);result=force(solve_off_axis_magnetostatic(refined),body,w);self.assertLess(abs(result['force_z_n']-ref['force_z_n'])/ref['force_scale_n'],1e-9)
        case,body,w,ref=axial_current_body(current_a=0.);result=force(solve_off_axis_magnetostatic(case),body,w);self.assertLess(abs(result['force_z_n'])/ref['force_scale_n'],1e-10)

    def test_actual_axial_virtual_work_matches_stress_with_linear_magnetic_body(self):
        for order in (1,2):
            for mu in (1.,3.,7.):
                case,body,w,ref=axial_current_body(order=order,body_mu_r=mu,current_a=1000.);before=case.to_dict();result=force(solve_off_axis_magnetostatic(case),body,w);displaced=work(case,body,w,[1e-5,5e-6]);self.assertEqual(case.to_dict(),before)
                for row in displaced['records']:self.assertLess(abs(row['negative_potential_derivative_n']-result['force_z_n'])/ref['force_scale_n'],1e-5)

    def test_radial_positions_currents_volume_boundaries_and_psi_reference_are_preserved(self):
        results=[]
        for offset in (0.,.125,-.25):
            case,body,w,ref=axial_current_body(order=1,reference_psi_wb=offset);result=work(case,body,w,[1e-5,5e-6]);results.append(result)
            for row in result['records']:
                self.assertLess(abs(row['negative_potential_derivative_n']-ref['force_z_n'])/ref['force_scale_n'],1e-5)
                for trial in row['trials']:
                    changed=OffAxisMagnetostaticCase.from_dict(trial['case']);self.assertEqual(changed.boundaries,case.boundaries);np.testing.assert_array_equal(changed.partition.mesh.points_rz_m[:,0],case.partition.mesh.points_rz_m[:,0]);boundary=np.unique(case.partition.mesh.boundary_edges);np.testing.assert_array_equal(changed.partition.mesh.points_rz_m[boundary],case.partition.mesh.points_rz_m[boundary])
                    for i,region in enumerate(case.partition.regions):
                        old=case.current_density_phi_a_per_m2[region.id]*case.partition.region_area_m2[i];new=changed.current_density_phi_a_per_m2[region.id]*changed.partition.region_area_m2[i];self.assertLess(abs(new-old)/max(1.,abs(old)),1e-12);self.assertLess(abs(changed.partition.region_volume_m3[i]/case.partition.region_volume_m3[i]-1.),1e-12)
        self.assertNotEqual(results[0]['baseline']['source_and_boundary_work_j'],results[1]['baseline']['source_and_boundary_work_j'])

    def test_nonvacuum_or_current_transition_bad_body_weights_and_edited_field_reject(self):
        case,body,w,ref=axial_current_body(order=1);solution=solve_off_axis_magnetostatic(case)
        for values in (np.ones(len(w)),np.zeros(len(w)),w*1.01,[False]*len(w),w.tolist()+[0.]):
            with self.assertRaises(ValueError):force(solution,body,values)
        for names in ([],[body[0],body[0]],['unknown']):
            with self.assertRaises(ValueError):force(solution,names,w)
        for kind in ('material','current'):
            data=case.to_dict()
            if kind=='material':data['partition']['materials'][0]['mu_r']=2.
            else:data['current_density_phi_a_per_m2']['air']=1.
            changed=OffAxisMagnetostaticCase.from_dict(data)
            with self.assertRaisesRegex(ValueError,'vacuum'):force(solve_off_axis_magnetostatic(changed),body,w)
        solution.psi_relative_to_reference_wb=solution.psi_relative_to_reference_wb*1.01
        with self.assertRaisesRegex(ValueError,'FEM replay'):force(solution,body,w)

    def test_wrong_physics_and_invalid_unresolved_or_inverted_axial_steps_reject(self):
        planar,body,w,c,ref=current_body(order=1)
        with self.assertRaises(ValueError):force(solve_planar_magnetostatic(planar),body,w)
        with self.assertRaises(ValueError):work(planar,body,w,[1e-5,5e-6])
        case,body,w,ref=axial_current_body(order=1)
        for steps in ([0.,1e-5],[1e-5],[1e-5,2e-5],[True,False],[1e-320,5e-321],[1.,.5]):
            with self.assertRaises(ValueError):work(case,body,w,steps)
        data=case.to_dict();minimum=min(p[0] for p in data['partition']['geometry']['points_rz_m'])
        for name in ('points_rz_m','outer_rz_m'):
            for point in data['partition']['geometry'][name]:point[0]-=minimum
        with self.assertRaises(ValueError):OffAxisMagnetostaticCase.from_dict(data)


if __name__=='__main__':unittest.main()
