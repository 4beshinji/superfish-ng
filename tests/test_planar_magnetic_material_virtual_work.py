# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import json,unittest
import numpy as np
from scripts.planar_magnetic_force_material_reference import material_body
from superfish_ng.constants import MU0
from superfish_ng.planar_bh import PlanarBHCase,solve_planar_bh
from superfish_ng.planar_recoil import PlanarRecoilCase,solve_planar_recoil
from superfish_ng.nonlinear_magnetic import MagneticNewtonControls,MagneticNonlinearFailure
from superfish_ng.planar_magnetic_force import planar_magnetic_force as force
from superfish_ng.planar_magnetic_material_virtual_work import material_planar_magnetic_virtual_work as work,PlanarMagneticVirtualWorkFailure


def solve(case):return (solve_planar_bh if type(case) is PlanarBHCase else solve_planar_recoil)(case)


class PlanarMagneticMaterialVirtualWorkTests(unittest.TestCase):
    def test_lorentz_and_permanent_moment_with_actual_material_fem_displacements(self):
        for kind,permanent,order,pair in (('bh',False,1,False),('bh',False,1,True),('recoil',True,1,False),('recoil',True,2,False)):
            case,body,w,c,ref=material_body(kind,permanent=permanent,order=order,pair=pair);result=work(case,body,w,c,[1e-5,5e-6],[1e-3,5e-4]);self.assertEqual(result['status'],'complete');self.assertEqual(result['schema_version'],2);self.assertIsNone(result['failure']);self.assertEqual(json.loads(json.dumps(result,allow_nan=False)),result)
            targets={'x':ref['force_xy_n_per_m'][0],'y':ref['force_xy_n_per_m'][1],'rotation':ref['torque_z_nm_per_m']}
            for row in result['records']:
                scale=ref['torque_scale'] if row['kind']=='rotation' else ref['force_scale'];self.assertLess(abs(row['negative_potential_derivative']-targets[row['kind']])/scale,1e-5)

    def test_nonlinear_anisotropic_remanent_material_work_matches_nodal_stress(self):
        for kind,order in (('bh',1),('recoil',1),('recoil',2)):
            case,body,w,c,ref=material_body(kind,nonlinear=True,principal=(2.,5.),permanent=kind=='recoil',current_a=1000.,order=order,rotation_rad=.3);stress=force(solve(case),body,w,c);result=work(case,body,w,c,[1e-5,5e-6],[1e-3,5e-4]);targets={'x':stress['force_xy_n_per_m'][0],'y':stress['force_xy_n_per_m'][1],'rotation':stress['nodal_rotation_stress_torque_z_nm_per_m']}
            for row in result['records']:
                scale=ref['torque_scale'] if row['kind']=='rotation' else ref['force_scale'];self.assertLess(abs(row['negative_potential_derivative']-targets[row['kind']])/scale,1e-5)

    def test_body_material_axes_currents_boundary_and_reference_constants_are_preserved(self):
        case,body,w,c,ref=material_body('recoil',permanent=True,principal=(2.,5.),order=2,rotation_rad=.3);original=case.to_dict();result=work(case,body,w,c,[1e-5,5e-6],[1e-3,5e-4]);self.assertEqual(case.to_dict(),original)
        for row in result['records']:
            for trial in row['trials']:
                changed=PlanarRecoilCase.from_dict(trial['case']);self.assertEqual(changed.boundaries,case.boundaries)
                for i,(old,new) in enumerate(zip(case.partition.regions,changed.partition.regions)):
                    angle=trial['sign']*row['step'] if row['kind']=='rotation' and old.id in body else 0.;self.assertEqual(new.orientation_rad,old.orientation_rad+angle)
                    self.assertLess(abs(changed.partition.region_area_m2[i]/case.partition.region_area_m2[i]-1.),1e-12)
                    self.assertAlmostEqual(changed.current_density_z_a_per_m2[old.id]*changed.partition.region_area_m2[i],case.current_density_z_a_per_m2[old.id]*case.partition.region_area_m2[i])
                constant=trial['remanent_reference_constant_j_per_m'];self.assertLess(abs(constant/result['baseline']['remanent_reference_constant_j_per_m']-1.),1e-12)
                self.assertLess(abs(trial['constitutive_potential_h0_j_per_m']-trial['constitutive_potential_j_per_m']-constant)/max(abs(constant),1.),1e-12)
            alternative=-((row['trials'][1]['constitutive_potential_h0_j_per_m']-row['trials'][1]['source_and_boundary_work_j_per_m'])-(row['trials'][0]['constitutive_potential_h0_j_per_m']-row['trials'][0]['source_and_boundary_work_j_per_m']))/(2*row['step']);scale=ref['torque_scale'] if row['kind']=='rotation' else ref['force_scale'];self.assertLess(abs(alternative-row['negative_potential_derivative'])/scale,1e-5)

    def test_failed_baseline_and_displacement_retain_actual_nonlinear_history(self):
        case,body,w,c,ref=material_body('bh',nonlinear=True,order=1);limited=replace(case,controls=MagneticNewtonControls(max_iterations=1))
        with self.assertRaises(PlanarMagneticVirtualWorkFailure) as caught:work(limited,body,w,c,[1e-4,5e-5],[1e-3,5e-4])
        report=caught.exception.report;self.assertEqual(report['failure']['kind'],'baseline');self.assertEqual(report['records'],[]);self.assertIsNone(report['baseline']);self.assertEqual(report['failure']['nonlinear_failure']['reason'],'iteration_limit')
        solution=solve(case);limited=replace(limited,initial_az_relative_to_reference_wb_per_m=solution.az_relative_to_reference_wb_per_m.tolist())
        with self.assertRaises(PlanarMagneticVirtualWorkFailure) as caught:work(limited,body,w,c,[1e-4,5e-5],[1e-3,5e-4])
        report=caught.exception.report;self.assertEqual(report['status'],'failed');self.assertEqual(report['failure']['kind'],'x');self.assertIsNotNone(report['baseline']);self.assertIsNone(report['records'][-1]['negative_potential_derivative']);self.assertIsNotNone(report['failure']['nonlinear_failure']['last_valid_relative_coefficients']);self.assertEqual(json.loads(json.dumps(report,allow_nan=False)),report)
        failed=PlanarBHCase.from_dict(report['failure']['case'])
        with self.assertRaises(MagneticNonlinearFailure) as repeated:solve_planar_bh(failed)
        self.assertEqual(repeated.exception.report,report['failure']['nonlinear_failure'])

    def test_completed_pairs_survive_a_later_failure_without_fabricated_derivative(self):
        case,body,w,c,ref=material_body('bh',nonlinear=True,order=1,current_a=0.);solution=solve(case);limited=replace(case,controls=MagneticNewtonControls(max_iterations=1),initial_az_relative_to_reference_wb_per_m=solution.az_relative_to_reference_wb_per_m.tolist())
        with self.assertRaises(PlanarMagneticVirtualWorkFailure) as caught:work(limited,body,w,c,[1e-6,5e-7],[.01,.005])
        report=caught.exception.report;self.assertEqual(report['failure']['kind'],'rotation');self.assertEqual(len(report['records']),5)
        for row in report['records'][:-1]:self.assertIsNotNone(row['negative_potential_derivative']);self.assertEqual(len(row['trials']),2)
        self.assertIsNone(report['records'][-1]['negative_potential_derivative']);self.assertEqual(report['failure']['step'],.01)

    def test_invalid_steps_geometry_source_and_unresolved_material_orientation_reject(self):
        case,body,w,c,ref=material_body('recoil',permanent=True,order=1)
        for steps in ([True,False],[1e-5],[0.,1e-5],[1e-5,2e-5],[1e-320,5e-321],[1.,.5]):
            with self.assertRaises(ValueError):work(case,body,w,c,steps,[.001,.0005])
        with self.assertRaises(ValueError):work(case,body,np.ones(len(w)),c,[1e-5,5e-6],[.001,.0005])
        with self.assertRaises(ValueError):work(object(),body,w,c,[1e-5,5e-6],[.001,.0005])
        data=case.to_dict();data['partition']['regions'][1]['orientation_rad']=1e20;changed=PlanarRecoilCase.from_dict(data)
        with self.assertRaisesRegex(ValueError,'material rotation'):work(changed,body,w,c,[1e-5,5e-6],[.001,.0005])


if __name__=='__main__':unittest.main()
