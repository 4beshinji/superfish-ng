# SPDX-License-Identifier: Apache-2.0
"""Independent TE fields and actual version9 shape tuning with original data."""
from copy import deepcopy
from pathlib import Path
import json,math,tempfile,unittest
from unittest.mock import patch
import numpy as np
from scipy.special import jn_zeros,jv
from superfish_ng import solve
from superfish_ng.constants import C0,EPS0,MU0,TAU
from superfish_ng.te import TEFieldSampler,te_quantities
from superfish_ng.te_saved import read_te_run
from superfish_ng.tuning import execute_tune,replay_tune,_project,read_tune
from test_straight_tuning import cylinder_request,snapshots
from test_straight_te_tuning_geometry import request,sector_request


def te_cylinder_request(tag='pec',side='z_max'):
    r=cylinder_request();r['project']['case']['model']['polarization']='te'
    if tag!='pec':
        r['project']['case']['boundaries']={'z_min':'pec','z_max':'pec'};r['project']['case']['boundaries'][side]=tag
        source=_project(dict(r,project=dict(r['project'],case=dict(r['project']['case'],boundaries={'z_min':'pec','z_max':'pec'}))),1.,'search').case
        plane=0. if side=='z_min' else source.length
        data=r['shape_law']['reference_comparison_mesh']
        for i,edge in enumerate(data['boundary_edges']):
            points=np.array(data['points'])[edge]
            if np.all(points[:,1]==plane) and not np.all(points[:,0]==0):data['boundary_tags'][i]=tag
    source=_project(r,1.,'search').case
    kz=(.5 if tag=='magnetic_symmetry' else 1.)*math.pi/source.length
    r['target_hz']=float(C0/TAU*math.hypot(jn_zeros(1,1)[0]/source.profile[0][1],kz))
    return r


class StraightTETuningTests(unittest.TestCase):
    def test_independent_bessel_cylinder_frequency_ephi_hr_hz_wall_and_na(self):
        for tag,side in [('pec','z_max'),('electric_symmetry','z_max'),('magnetic_symmetry','z_max'),('magnetic_symmetry','z_min')]:
            r=te_cylinder_request(tag,side)
            with self.subTest(tag=tag,side=side),tempfile.TemporaryDirectory() as tmp:
                result=execute_tune(r,Path(tmp)/'run');self.assertEqual(result['status'],'TUNED',result['decision'])
                before=snapshots(result['trial_runs']);self.assertEqual(result,replay_tune(result));errors=[]
                for trial,path in zip(result['trials'],result['trial_runs']):
                    s=read_te_run(Path(path)/'solution');case=s.case;R=case.profile[0][1];L=case.length;chi=jn_zeros(1,1)[0]
                    kz=(.5 if tag=='magnetic_symmetry' else 1.)*math.pi/L;kr=chi/R;f=C0/TAU*math.hypot(kr,kz);omega=TAU*f
                    A=math.sqrt(4*case.normalization_j/(EPS0*math.pi*R*R*L*jv(2,chi)**2))
                    points=s.mesh.points[s.mesh.triangles].mean(axis=1);radius=points[:,0];z=points[:,1]
                    axial=np.cos(kz*z) if tag=='magnetic_symmetry' and side=='z_min' else np.sin(kz*z)
                    derivative=-kz*np.sin(kz*z) if tag=='magnetic_symmetry' and side=='z_min' else kz*np.cos(kz*z)
                    expected=dict(Ephi_V_per_m=A*jv(1,kr*radius)*axial,
                        Hr_quadrature_A_per_m=-A*jv(1,kr*radius)*derivative/(omega*MU0),
                        Hz_quadrature_A_per_m=A*kr*jv(0,kr*radius)*axial/(omega*MU0))
                    fields=TEFieldSampler(s).evaluate(points);sign=np.sign(expected['Ephi_V_per_m']@fields['Ephi_V_per_m'])
                    field_errors=[float(np.linalg.norm(sign*fields[key]-value)/np.linalg.norm(value)) for key,value in expected.items()]
                    self.assertLess(field_errors[0],.001);self.assertLess(field_errors[1],.01);self.assertLess(field_errors[2],.01)
                    rf=te_quantities(s)
                    ends=2 if tag=='pec' else 1
                    surface=math.pi*R*L*A*A*kr*kr*jv(0,chi)**2/(omega*MU0)**2+ends*math.pi*R*R*A*A*kz*kz*jv(2,chi)**2/(omega*MU0)**2
                    rs=math.sqrt(math.pi*f*MU0/case.conductivity_s_per_m);loss=rs*surface/2
                    error=[abs(rf['frequency_hz']/f-1),*field_errors,abs(rf['wall_loss_w']/loss-1)]
                    self.assertLess(error[0],1e-5);self.assertLess(error[-1],.005)
                    self.assertAlmostEqual(rf['stored_energy_j'],1.,places=10)
                    self.assertAlmostEqual(rf['electric_energy_j'],.5,places=10);self.assertAlmostEqual(rf['magnetic_energy_j'],.5,places=10)
                    for key in ('vacc_v','eacc_v_per_m','r_over_q_accelerator_ohm','r_over_q_circuit_ohm'):self.assertIsNone(rf[key])
                    errors.append(error)
                    if trial['tracking']:self.assertTrue(trial['tracking']['tracking']['individual_ids_complete'])
                self.assertTrue(np.all(np.array(errors[-1])<np.array(errors[-2])),errors)
                self.assertEqual(before,snapshots(result['trial_runs']))
                print('independent version9 TE cylinder errors',tag,side,json.dumps(errors),flush=True)

    def test_actual_step_sectors_independent_refinement_resume_original_fields_and_na(self):
        for tag,reflected in [('pec',False),('magnetic_symmetry',False),('electric_symmetry',True),('magnetic_symmetry',True)]:
            r=request() if tag=='pec' else sector_request(tag=tag,reflected=reflected)
            r['project']['case']['mesh'].update(nr=32,nz=48,corner_radius_m=.0078125,corner_max_edge_m=.00048828125)
            r['project']['case']['solver']['modes']=1;r['initial_ids']=['mode-1']
            pilot=solve(_project(r,1.,'search').case);r['target_hz']=float(pilot.frequencies_hz[0])
            with self.subTest(tag=tag,reflected=reflected),tempfile.TemporaryDirectory() as tmp:
                first=execute_tune(r,Path(tmp)/'first',max_new_trials=2);self.assertEqual(first['status'],'PAUSED')
                original=snapshots(first['trial_runs']);final=execute_tune(r,Path(tmp)/'rest',checkpoint=first)
                self.assertIn(final['status'],('TUNED','REFINEMENT_FAILED'))
                self.assertEqual(final,replay_tune(final));self.assertEqual(original,snapshots(first['trial_runs']))
                self.assertEqual(final['trials'][-1]['phase'],'refinement')
                self.assertEqual(final['decision']['mesh_difference_met'],final['decision']['mesh_frequency_difference_hz']<=r['mesh_frequency_tolerance_hz'])
                self.assertEqual(final['status']=='TUNED',final['decision']['mesh_difference_met'] and final['decision']['refined_target_met'])
                for trial,path in zip(final['trials'],final['trial_runs']):
                    s=read_te_run(Path(path)/'solution');source=s.reflection_source_case or s.case
                    self.assertEqual(source,_project(r,trial['value'],trial['phase']).case)
                    rf=te_quantities(s);self.assertAlmostEqual(rf['stored_energy_j'],2. if reflected else 1.,places=10)
                    self.assertIsNone(rf['r_over_q_accelerator_ohm']);self.assertIsNone(rf['r_over_q_circuit_ohm'])
                    if trial['tracking']:
                        mapping=trial['tracking']['tracking']['physical_mapping']
                        self.assertEqual(mapping['field'],'Ephi_V_per_m');self.assertTrue(trial['tracking']['tracking']['individual_ids_complete'])
                        if tag!='pec':self.assertEqual(mapping['symmetry_sector']['reflected'],reflected)
                print('version9 actual step',tag,reflected,final['status'],final['decision']['mesh_frequency_difference_hz'],flush=True)

    def test_actual_unresolved_ids_stop_before_frequency_and_final_refinement(self):
        r=te_cylinder_request();r['project']['case']['solver']['modes']=2;r['initial_ids']=['mode-1','mode-2']
        r['controls']['relative_cluster_gap']=.99
        with tempfile.TemporaryDirectory() as tmp:
            result=execute_tune(r,Path(tmp)/'run');self.assertEqual(result['status'],'UNVERIFIED')
            self.assertIsNone(result['trials'][-1]['frequency_hz']);self.assertFalse(result['can_resume'])
            self.assertEqual(len(result['trials']),2);self.assertEqual(result,replay_tune(result))

    def test_invalid_mid_trial_does_not_enter_solver_and_retains_te_checkpoints(self):
        r=te_cylinder_request()
        binding=next(b for b in r['shape_law']['bindings'] if b['vertex']==0 and b['coordinate']=='r')
        binding['expression']={'op':'if','args':[{'op':'lt','args':[{'op':'abs','args':[{'op':'sub','args':[{'variable':'scale'},{'constant':1.,'unit':'1'}]}]},{'constant':.01,'unit':'1'}]},{'constant':-.001,'unit':'m'},{'constant':0.,'unit':'m'}]}
        with tempfile.TemporaryDirectory() as tmp:
            first=execute_tune(r,Path(tmp)/'first',max_new_trials=2);before=snapshots(first['trial_runs'])
            with patch('superfish_ng.tuning.execute_project',side_effect=AssertionError('invalid TE geometry entered FEM')):
                with self.assertRaises(ValueError):execute_tune(r,Path(tmp)/'failed',checkpoint=first)
            self.assertEqual(first,read_tune(Path(tmp)/'first/checkpoint-002.json'));self.assertEqual(before,snapshots(first['trial_runs']))
            self.assertEqual(json.loads((Path(tmp)/'failed/failure-003.json').read_text())['status'],'FAILED')

    def test_folded_contour_actual_te_tune_retains_original_geometry_and_na(self):
        r=request('contour');r['project']['case']['mesh']['contour_mesh']=dict(max_edge_m=.015625,min_angle_deg=5.,max_triangles=30000,max_rounds=12)
        r['project']['case']['solver']['modes']=1;r['initial_ids']=['mode-1']
        pilot=solve(_project(r,1.,'search').case);r['target_hz']=float(pilot.frequencies_hz[0])
        with tempfile.TemporaryDirectory() as tmp:
            result=execute_tune(r,Path(tmp)/'run');self.assertIn(result['status'],('TUNED','REFINEMENT_FAILED'))
            self.assertEqual(result,replay_tune(result))
            for trial,path in zip(result['trials'],result['trial_runs']):
                s=read_te_run(Path(path)/'solution');self.assertEqual(s.case,_project(r,trial['value'],trial['phase']).case)
                rf=te_quantities(s);self.assertIsNone(rf['r_over_q_accelerator_ohm']);self.assertIsNone(rf['r_over_q_circuit_ohm'])
                if trial['tracking']:self.assertTrue(trial['tracking']['tracking']['individual_ids_complete'])
            print('version9 folded TE contour',result['status'],result['decision']['mesh_frequency_difference_hz'],flush=True)
