# SPDX-License-Identifier: Apache-2.0
import json,unittest
import numpy as np
from scripts.planar_magnetic_force_material_reference import material_body
from superfish_ng.constants import MU0
from superfish_ng.planar_bh import PlanarBHCase,solve_planar_bh
from superfish_ng.planar_recoil import PlanarRecoilCase,solve_planar_recoil
from superfish_ng.planar_magnetic_force import planar_magnetic_force as force,planar_magnetic_virtual_work as work


def solve(case):return (solve_planar_bh if type(case) is PlanarBHCase else solve_planar_recoil)(case)


class PlanarMagneticForceMaterialsTests(unittest.TestCase):
    def test_linear_material_limits_preserve_lorentz_force_and_nodal_couple(self):
        for kind,order in (('bh',1),('recoil',1),('recoil',2)):
            for pair in (False,True):
                case,body,w,c,ref=material_body(kind,order=order,pair=pair,rotation_rad=.3,current_a=-10.)
                result=force(solve(case),body,w,c)
                self.assertLess(np.linalg.norm(np.asarray(result['force_xy_n_per_m'])-ref['force_xy_n_per_m'])/ref['force_scale'],1e-9)
                self.assertLess(abs(result['nodal_rotation_stress_torque_z_nm_per_m']-ref['torque_z_nm_per_m'])/ref['torque_scale'],1e-9)
                self.assertEqual(result['schema_version'],2);self.assertEqual(result['source_physics'],case.to_dict()['physics']);self.assertEqual(json.loads(json.dumps(result,allow_nan=False)),result)
                if order==2 or not pair:self.assertLess(abs(result['torque_z_nm_per_m']-ref['torque_z_nm_per_m'])/ref['torque_scale'],1e-9)

    def test_permanent_moment_torque_refines_without_replacing_original_field(self):
        for order in (1,2):
            previous=None
            for n in (8,16,32):
                case,body,w,c,ref=material_body('recoil',permanent=True,order=order,n=n);result=force(solve(case),body,w,c)
                error=abs(result['torque_z_nm_per_m']-ref['torque_z_nm_per_m'])/ref['torque_scale']
                if previous is not None and order==1:self.assertLess(error,previous)
                previous=error
                if order==2:self.assertLess(error,1e-9)
                self.assertLess(np.linalg.norm(result['force_xy_n_per_m'])/ref['force_scale'],1e-9)
                self.assertLess(abs(result['nodal_rotation_stress_torque_z_nm_per_m']-ref['torque_z_nm_per_m'])/ref['torque_scale'],1e-9)
                self.assertLess(max(result['quadrature_relative_differences']),1e-12)
            self.assertLess(error,.02)

    def test_origin_rotation_scale_and_remanence_reversal(self):
        for angle,scale,remanence in ((0.,1.,.1),(.3,.5,-.1),(-.7,2.,.1)):
            case,body,w,c,ref=material_body('recoil',permanent=True,order=2,rotation_rad=angle,scale=scale,remanence_t=remanence)
            solution=solve(case);result=force(solution,body,w,c);delta=np.array([.13,-.17])*ref['length_m'];shifted=force(solution,body,w,c+delta);f=result['force_xy_n_per_m'];correction=delta[0]*f[1]-delta[1]*f[0]
            self.assertLess(abs(result['nodal_rotation_stress_torque_z_nm_per_m']-ref['torque_z_nm_per_m'])/ref['torque_scale'],1e-9)
            for key in ('torque_z_nm_per_m','nodal_rotation_stress_torque_z_nm_per_m'):self.assertLess(abs(shifted[key]-result[key]+correction)/ref['torque_scale'],1e-9)

    def test_nonlinear_and_anisotropic_body_symmetry_without_false_torque_reference(self):
        for kind in ('bh','recoil'):
            case,body,w,c,ref=material_body(kind,nonlinear=True,principal=(2.,5.),permanent=kind=='recoil',current_a=0.,order=1);result=force(solve(case),body,w,c);scale=.25**2*ref['length_m']/MU0
            self.assertLess(np.linalg.norm(result['force_xy_n_per_m'])/scale,1e-9)
            if kind=='bh':self.assertLess(abs(result['torque_z_nm_per_m'])/(scale*ref['length_m']),1e-9)
            self.assertEqual(result['schema_version'],2)

    def test_declared_vacuum_requires_entire_table_exact_principal_values_and_zero_remanence(self):
        for kind in ('bh','recoil'):
            case,body,w,c,ref=material_body(kind,order=1);data=case.to_dict()
            variants=[]
            if kind=='bh':
                data['partition']['materials'][0]['h_a_per_m'][-1]*=.9;variants.append(data)
            else:
                for key,value in (('mu_r_principal',[1.,1.+1e-12]),('remanent_b_local_t',[1e-15,0.])):
                    changed=case.to_dict();changed['partition']['materials'][0][key]=value;variants.append(changed)
            changed=case.to_dict();changed['current_density_z_a_per_m2']['air']=1.;variants.append(changed)
            for changed in variants:
                with self.assertRaisesRegex(ValueError,'vacuum'):force(solve(type(case).from_dict(changed)),body,w,c)
            changed=case.to_dict();region=changed['partition']['regions'][1];cell=region['cell_indices'].pop();other=dict(region,id='other',cell_indices=[cell]);changed['partition']['regions'].append(other);changed['current_density_z_a_per_m2']['other']=1.
            with self.assertRaisesRegex(ValueError,'weight zero'):force(solve(type(case).from_dict(changed)),body,w,c)

    def test_edited_coefficients_bad_weights_and_material_virtual_work_reject(self):
        for kind in ('bh','recoil'):
            case,body,w,c,ref=material_body(kind,order=1);solution=solve(case)
            for invalid in (np.ones(len(w)),np.zeros(len(w)),w*1.01):
                with self.assertRaises(ValueError):force(solution,body,invalid,c)
            solution.az_relative_to_reference_wb_per_m=solution.az_relative_to_reference_wb_per_m*1.01
            with self.assertRaisesRegex(ValueError,'FEM replay'):force(solution,body,w,c)
            with self.assertRaisesRegex(ValueError,'material rotation'):work(case,body,w,c,[1e-5,5e-6],[1e-3,5e-4])


if __name__=='__main__':unittest.main()
