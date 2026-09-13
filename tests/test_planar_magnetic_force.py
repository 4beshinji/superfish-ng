# SPDX-License-Identifier: Apache-2.0
import copy,unittest
import numpy as np
from scripts.planar_magnetic_force_reference import current_body
from superfish_ng.constants import MU0
from superfish_ng.planar_magnetostatic import PlanarMagnetostaticCase,solve_planar_magnetostatic
from superfish_ng.planar_magnetic_force import planar_magnetic_force as force,planar_magnetic_virtual_work as work


class PlanarMagneticForceTests(unittest.TestCase):
    def test_actual_current_force_and_p2_couple_match_analytic_lorentz_values(self):
        for pair,order in ((False,1),(False,2),(True,2)):
            case,body,w,origin,ref=current_body(pair=pair,order=order);result=force(solve_planar_magnetostatic(case),body,w,origin)
            self.assertLess(np.linalg.norm(np.asarray(result['force_xy_n_per_m'])-ref['force_xy_n_per_m'])/ref['force_scale'],1e-9)
            self.assertLess(abs(result['torque_z_nm_per_m']-ref['torque_z_nm_per_m'])/ref['torque_scale'],1e-9);self.assertLess(max(result['quadrature_relative_differences']),1e-12)
            self.assertIn('N m/m',result['conventions']);self.assertEqual(len(result['body_cell_indices']),sum(len(r.cell_indices) for r in case.partition.regions if r.id in body))
        case,body,w,origin,ref=current_body(current_a=0.);result=force(solve_planar_magnetostatic(case),body,w,origin);scale=.25**2*.125/MU0
        self.assertLess(np.linalg.norm(result['force_xy_n_per_m'])/scale,1e-10)

    def test_origin_shift_rotation_scaling_and_current_reversal(self):
        for angle,scale,current in ((0.,1.,10.),(.3,.5,-10.),(-.7,2.,1000.)):
            case,body,w,origin,ref=current_body(rotation_rad=angle,scale=scale,current_a=current);solution=solve_planar_magnetostatic(case);result=force(solution,body,w,origin)
            self.assertLess(np.linalg.norm(np.asarray(result['force_xy_n_per_m'])-ref['force_xy_n_per_m'])/ref['force_scale'],1e-9)
            displacement=np.array([.01,-.02])*scale;shifted=force(solution,body,w,origin+displacement);f=np.asarray(result['force_xy_n_per_m']);correction=displacement[0]*f[1]-displacement[1]*f[0]
            for key in ('torque_z_nm_per_m','nodal_rotation_stress_torque_z_nm_per_m'):self.assertLess(abs(shifted[key]-result[key]+correction)/ref['torque_scale'],1e-9)

    def test_p1_weighted_torque_mesh_error_and_weight_choice_remain_visible(self):
        previous=None
        for n in (8,16,32):
            case,body,w,origin,ref=current_body(n=n,order=1,pair=True);result=force(solve_planar_magnetostatic(case),body,w,origin);error=abs(result['torque_z_nm_per_m']-ref['torque_z_nm_per_m'])/ref['torque_scale']
            if previous is not None:self.assertLess(error,previous)
            previous=error
        self.assertLess(error,.02);self.assertGreater(abs(result['nodal_minus_weighted_torque_nm_per_m']),1e-8)
        results=[]
        for outer in (.875,.95,1.):
            case,body,w,origin,ref=current_body(order=2,pair=True,weight_outer=outer);result=force(solve_planar_magnetostatic(case),body,w,origin);results.append(result)
            self.assertLess(abs(result['torque_z_nm_per_m']-ref['torque_z_nm_per_m'])/ref['torque_scale'],1e-9)
        self.assertNotEqual(results[0]['weights'],results[2]['weights'])

    def test_same_nodal_motion_stress_matches_independent_fem_potential_differences(self):
        for order,pair in ((1,False),(2,False),(1,True),(2,True)):
            case,body,w,origin,ref=current_body(order=order,pair=pair);before=case.to_dict();old=w.copy();result=force(solve_planar_magnetostatic(case),body,w,origin);trial=work(case,body,w,origin,[1e-5,5e-6],[1e-3,5e-4]);self.assertEqual(case.to_dict(),before);np.testing.assert_array_equal(w,old)
            targets={'x':result['force_xy_n_per_m'][0],'y':result['force_xy_n_per_m'][1],'rotation':result['nodal_rotation_stress_torque_z_nm_per_m']}
            for row in trial['records']:
                scale=ref['torque_scale'] if row['kind']=='rotation' else ref['force_scale'];self.assertLess(abs(row['negative_potential_derivative']-targets[row['kind']])/scale,1e-5)
                for moved in row['trials']:
                    restored=PlanarMagnetostaticCase.from_dict(moved['case']);self.assertEqual(restored.boundaries,case.boundaries)
                    for i,region in enumerate(case.partition.regions):self.assertAlmostEqual(restored.current_density_z_a_per_m2[region.id]*restored.partition.region_area_m2[i],case.current_density_z_a_per_m2[region.id]*case.partition.region_area_m2[i],places=11)
            if pair and order==1:self.assertGreater(abs(result['torque_z_nm_per_m']-targets['rotation'])/ref['torque_scale'],1e-5)

    def test_invalid_weights_materials_body_and_modified_source_are_rejected(self):
        case,body,w,origin,ref=current_body();solution=solve_planar_magnetostatic(case)
        for invalid in (w.tolist()+[0.],np.ones(len(w)),w*1.01,np.zeros(len(w)),[False]*len(w)):
            with self.assertRaises(ValueError):force(solution,body,invalid,origin)
        for invalid in ([],[body[0],body[0]],['unknown']):
            with self.assertRaises(ValueError):force(solution,invalid,w,origin)
        with self.assertRaises(ValueError):force(solution,body,w,[False,0.])
        for kind in ('current','material'):
            data=case.to_dict()
            if kind=='current':data['current_density_z_a_per_m2']['air']=1.
            else:data['partition']['materials'][0]['mu_r']=2.
            changed=PlanarMagnetostaticCase.from_dict(data)
            with self.assertRaisesRegex(ValueError,'vacuum'):force(solve_planar_magnetostatic(changed),body,w,origin)
        solution.az_relative_to_reference_wb_per_m=solution.az_relative_to_reference_wb_per_m*1.01
        with self.assertRaisesRegex(ValueError,'FEM replay'):force(solution,body,w,origin)

    def test_virtual_steps_and_unresolved_or_inverted_geometry_reject(self):
        case,body,w,origin,ref=current_body()
        for values in ([0.,1e-5],[1e-5],[1e-5,2e-5],[True,False],[1e-5,float('nan')]):
            with self.assertRaises(ValueError):work(case,body,w,origin,values,[1e-3,5e-4])
        with self.assertRaises(ValueError):work(case,body,w,origin,[1e-320,5e-321], [1e-3,5e-4])
        with self.assertRaises(ValueError):work(case,body,w,origin,[1.,.5],[1e-3,5e-4])


if __name__=='__main__':unittest.main()
