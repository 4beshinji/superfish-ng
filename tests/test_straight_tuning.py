# SPDX-License-Identifier: Apache-2.0
"""Independent TM physics and real straight-geometry tuning/replay failures."""
from copy import deepcopy
from dataclasses import replace
import hashlib,json,math,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from scipy.special import jn_zeros,jv
from superfish_ng import Case,solve
from superfish_ng.constants import C0,EPS0,MU0,TAU
from superfish_ng.model import Model
from superfish_ng.project import Project
from superfish_ng.contour import Contour
from superfish_ng.contour_mesh import triangulate_contour
from superfish_ng.mesh_input import mesh_to_dict
from superfish_ng.sampling import FieldSampler
from superfish_ng.rf import quantities
from superfish_ng.affine_saved import read_verified_affine_solution
from superfish_ng.tuning import execute_tune,read_tune,replay_tune,_project
from test_straight_tuning_geometry import request,boundary


def cylinder_request(modes=1):
    r=request('profile');case=Case(((0.,.08),(.08,.08)),nr=20,nz=24,modes=modes,element_order=2,model=Model())
    polygon=Contour.from_profile(case);mesh=mesh_to_dict(triangulate_contour(Case((),contour=polygon,element_order=2,model=Model())))
    r['project']=Project(case).to_dict();r['initial_ids']=['mode-'+str(i+1) for i in range(modes)]
    r['shape_law']['reference_comparison_mesh']=mesh
    r['shape_law']['case_boundary_vertices']=[dict(case_vertex=i,reference_vertex=mesh['points'].index([h,z])) for i,(z,h) in enumerate(case.profile)]
    r['shape_law']['bindings']=[dict(vertex=i,coordinate=c,expression=dict(op='mul',args=[dict(constant=v,unit='m'),dict(variable='scale')])) for i,p in enumerate(mesh['points']) for c,v in zip(('r','z'),p)]
    r['target_hz']=float(C0*jn_zeros(0,1)[0]/(TAU*.08))
    return r


def read_solution(directory):
    """Reassemble the saved original basis; no new eigensolve or field fitting."""
    solution=read_verified_affine_solution(directory)
    if solution.element_order==2:
        from superfish_ng.high_order import assemble_p2
        solution.stiffness,solution.mass=assemble_p2(solution.space)
    else:
        from superfish_ng.fem import assemble
        solution.stiffness,solution.mass=assemble(solution.mesh)
    ku=solution.stiffness@solution.u;mu=solution.mass@solution.u;values=(TAU*solution.frequencies_hz/C0)**2
    solution.residuals=np.linalg.norm(ku-mu*values,axis=0)/(np.linalg.norm(ku,axis=0)+values*np.linalg.norm(mu,axis=0))
    if np.any(solution.residuals>1e-8):raise ValueError('saved original eigenfields fail matrix reconstruction')
    return solution


def snapshots(runs):
    return [{p.relative_to(Path(run)).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(run).rglob('*') if p.is_file()} for run in runs]


class StraightTuningTests(unittest.TestCase):
    def test_cylinder_independent_bessel_frequency_original_EH_all_wall_and_rq(self):
        r=cylinder_request()
        with tempfile.TemporaryDirectory() as tmp:
            result=execute_tune(r,Path(tmp)/'run');self.assertEqual(result['status'],'TUNED',result['decision'])
            original=snapshots(result['trial_runs']);self.assertEqual(result,replay_tune(result));errors=[]
            for trial,run in zip(result['trials'],result['trial_runs']):
                s=read_solution(Path(run)/'solution');case=s.case;R=case.profile[0][1];L=case.length;chi=jn_zeros(0,1)[0]
                f=C0*chi/(TAU*R);omega=TAU*f;A=np.sqrt(2/(MU0*np.pi*R**2*L*jv(1,chi)**2))
                points=s.mesh.points[s.mesh.triangles].mean(axis=1);h=A*jv(1,chi*points[:,0]/R);e=A/(C0*EPS0)*jv(0,chi*points[:,0]/R)
                fields=FieldSampler.from_solution(s).evaluate(points);sign=np.sign(h@fields['Hphi_A_per_m'])
                wall=TAU*A*A*jv(1,chi)**2*R*(L+R);rs=np.sqrt(np.pi*f*MU0/case.conductivity_s_per_m);loss=rs*wall/2
                voltage=A/(C0*EPS0)*L*np.sinc(omega*L/(TAU*C0));rq=voltage**2/omega
                rf=quantities(case,s);error=np.array([abs(rf['frequency_hz']/f-1),np.linalg.norm(sign*fields['Hphi_A_per_m']-h)/np.linalg.norm(h),np.linalg.norm(sign*fields['Ez_quadrature_V_per_m']-e)/np.linalg.norm(e),abs(rf['wall_loss_w']/loss-1),abs(rf['r_over_q_accelerator_ohm']/rq-1)])
                self.assertLess(error[0],1e-4);self.assertLess(error[1],.001);self.assertLess(error[2],.01);self.assertLess(error[3],.005);self.assertLess(error[4],.005)
                self.assertLess(np.linalg.norm(fields['Er_quadrature_V_per_m'])/np.linalg.norm(e),.01)
                self.assertAlmostEqual(rf['stored_energy_j'],1.,places=10);self.assertAlmostEqual(rf['electric_energy_j'],.5,places=10);self.assertAlmostEqual(rf['magnetic_energy_j'],.5,places=10)
                self.assertEqual(rf['r_over_q_accelerator_ohm'],2*rf['r_over_q_circuit_ohm']);errors.append(error.tolist())
                if trial['tracking']:self.assertTrue(trial['tracking']['tracking']['individual_ids_complete'])
            self.assertTrue(np.all(np.asarray(errors[-1])<np.asarray(errors[-2])),errors)
            self.assertEqual(original,snapshots(result['trial_runs']));print('independent straight cylinder f/H/E/Pwall/RQ errors:',json.dumps(errors),flush=True)

    def test_actual_step_scale_fields_rf_restart_and_complete_native_replay(self):
        r=request();r['project']['case']['mesh'].update(nr=32,nz=48);r['initial_ids']=['mode-1'];r['project']['case']['solver']['modes']=1
        pilot_case=_project(r,1.,'search').case;pilot=solve(pilot_case);r['target_hz']=float(pilot.frequencies_hz[0])
        with tempfile.TemporaryDirectory() as tmp:
            first=execute_tune(r,Path(tmp)/'first',max_new_trials=2);self.assertEqual(first['status'],'PAUSED')
            original=snapshots(first['trial_runs']);result=execute_tune(r,Path(tmp)/'resume',checkpoint=first)
            self.assertEqual(result['status'],'REFINEMENT_FAILED',result['decision']);self.assertFalse(result['decision']['refined_target_met']);self.assertFalse(result['decision']['mesh_difference_met']);self.assertGreater(result['decision']['mesh_frequency_difference_hz'],1e4);self.assertEqual(result,replay_tune(result));self.assertEqual(original,snapshots(first['trial_runs']))
            reference=None;errors=[]
            for trial,run in zip(result['trials'],result['trial_runs']):
                s=read_solution(Path(run)/'solution');rf=quantities(s.case,s);poly=boundary(s.case);base=boundary(pilot_case);scale=trial['value']
                self.assertAlmostEqual(poly.volume_m3/base.volume_m3,scale**3);self.assertEqual(poly.edge_tags,base.edge_tags)
                expected=_project(r,scale,trial['phase']);self.assertEqual(s.case,expected.case)
                if trial['tracking']:self.assertTrue(trial['tracking']['tracking']['individual_ids_complete'])
                if trial['phase']=='refinement':continue
                points=s.mesh.points[s.mesh.triangles].mean(axis=1);fields=FieldSampler.from_solution(s).evaluate(points)
                pf=FieldSampler.from_solution(pilot).evaluate(points/scale);sign=np.sign(pf['Hphi_A_per_m']@fields['Hphi_A_per_m'])
                H=np.linalg.norm(sign*fields['Hphi_A_per_m']*scale**1.5-pf['Hphi_A_per_m'])/np.linalg.norm(pf['Hphi_A_per_m'])
                E=np.linalg.norm(np.column_stack([sign*fields[k]*scale**1.5-pf[k] for k in ('Er_quadrature_V_per_m','Ez_quadrature_V_per_m')]))/np.linalg.norm(np.column_stack([pf[k] for k in ('Er_quadrature_V_per_m','Ez_quadrature_V_per_m')]))
                self.assertLess(H,1e-8);self.assertLess(E,1e-8);self.assertAlmostEqual(rf['frequency_hz']*scale/r['target_hz'],1.,places=10)
                if reference is None:reference=(scale,rf)
                else:
                    factor=scale/reference[0];old=reference[1]
                    self.assertAlmostEqual(rf['geometry_factor_ohm']/old['geometry_factor_ohm'],1.,places=9)
                    self.assertAlmostEqual(rf['q0']/old['q0'],np.sqrt(factor),places=9)
                    for k in ('r_over_q_accelerator_ohm','r_over_q_circuit_ohm'):self.assertAlmostEqual(rf[k]/old[k],1.,places=8)
                errors.append([H,E])
            bad=deepcopy(result);bad['decision']['value']=0.
            with self.assertRaises(ValueError):replay_tune(bad)
            print('step original H/E similarity errors:',json.dumps(errors),flush=True)

    def test_general_folded_contour_original_walls_and_actual_refinement_failure(self):
        r=request('contour');r['project']['case']['mesh']['contour_mesh']=dict(max_edge_m=.015625,min_angle_deg=5.,max_triangles=20000,max_rounds=12)
        r['project']['case']['solver']['modes']=1;r['initial_ids']=['mode-1'];r['mesh_frequency_tolerance_hz']=1.
        pilot_case=_project(r,1.,'search').case;pilot=solve(pilot_case);r['target_hz']=float(pilot.frequencies_hz[0])
        with tempfile.TemporaryDirectory() as tmp:
            result=execute_tune(r,Path(tmp)/'run');self.assertEqual(result['status'],'REFINEMENT_FAILED');self.assertFalse(result['decision']['mesh_difference_met'])
            self.assertEqual(result,replay_tune(result));self.assertGreater(result['decision']['mesh_frequency_difference_hz'],1.)
            for trial,run in zip(result['trials'],result['trial_runs']):
                s=read_solution(Path(run)/'solution');self.assertEqual(s.case,_project(r,trial['value'],trial['phase']).case)
                poly=s.case.contour;self.assertEqual(poly.edge_tags,pilot_case.contour.edge_tags);self.assertAlmostEqual(poly.volume_m3/pilot_case.contour.volume_m3,trial['value']**3)
                rf=quantities(s.case,s);self.assertGreater(rf['wall_loss_w'],0.);self.assertEqual(rf['r_over_q_accelerator_ohm'],2*rf['r_over_q_circuit_ohm'])
                self.assertTrue(trial['tracking']['tracking']['individual_ids_complete'] if trial['tracking'] else True)

    def test_interior_invalid_trial_records_failure_without_solving_or_changing_old_sources(self):
        r=cylinder_request();binding=next(b for b in r['shape_law']['bindings'] if b['vertex']==0 and b['coordinate']=='r')
        binding['expression']={'op':'if','args':[{'op':'lt','args':[{'op':'abs','args':[{'op':'sub','args':[{'variable':'scale'},{'constant':1.,'unit':'1'}]}]},{'constant':.01,'unit':'1'}]},{'constant':-.001,'unit':'m'},{'constant':0.,'unit':'m'}]}
        with tempfile.TemporaryDirectory() as tmp:
            first=execute_tune(r,Path(tmp)/'first',max_new_trials=2);original=snapshots(first['trial_runs'])
            with patch('superfish_ng.tuning.execute_project',side_effect=AssertionError('invalid geometry entered FEM')):
                with self.assertRaises(ValueError):execute_tune(r,Path(tmp)/'failure',checkpoint=first)
            failure=json.loads((Path(tmp)/'failure/failure-003.json').read_text());self.assertEqual(failure['status'],'FAILED');self.assertEqual(failure['attempt']['value'],1.)
            self.assertEqual(first,read_tune(Path(tmp)/'first/checkpoint-002.json'));self.assertEqual(original,snapshots(first['trial_runs']))

    def test_actual_unresolved_individual_ids_stop_before_frequency_and_refinement(self):
        r=cylinder_request(modes=2);r['controls']['relative_cluster_gap']=.99
        with tempfile.TemporaryDirectory() as tmp:
            result=execute_tune(r,Path(tmp)/'run');self.assertEqual(result['status'],'UNVERIFIED');self.assertEqual(len(result['trials']),2)
            self.assertIsNone(result['trials'][-1]['frequency_hz']);self.assertFalse(result['can_resume']);self.assertEqual(result,replay_tune(result))


    def test_corner_refined_step_actual_tune_retains_original_ten_khz_gates(self):
        r=request();r['project']['case']['mesh'].update(nr=32,nz=48,corner_radius_m=.0078125,corner_max_edge_m=.00048828125)
        r['project']['case']['solver']['modes']=1;r['initial_ids']=['mode-1']
        pilot_case=_project(r,1.,'search').case;pilot=solve(pilot_case);r['target_hz']=float(pilot.frequencies_hz[0])
        self.assertEqual(r['frequency_tolerance_hz'],1e4);self.assertEqual(r['mesh_frequency_tolerance_hz'],1e4)
        with tempfile.TemporaryDirectory() as tmp:
            result=execute_tune(r,Path(tmp)/'run');self.assertEqual(result['status'],'TUNED',result['decision'])
            self.assertTrue(result['decision']['refined_target_met']);self.assertTrue(result['decision']['mesh_difference_met'])
            self.assertEqual(result,replay_tune(result));original=snapshots(result['trial_runs'])
            for trial,run in zip(result['trials'],result['trial_runs']):
                solution=read_solution(Path(run)/'solution');rf=quantities(solution.case,solution)
                self.assertEqual(solution.case,_project(r,trial['value'],trial['phase']).case)
                self.assertEqual(boundary(solution.case).edge_tags,boundary(pilot_case).edge_tags)
                self.assertAlmostEqual(boundary(solution.case).volume_m3/boundary(pilot_case).volume_m3,trial['value']**3)
                self.assertAlmostEqual(rf['stored_energy_j'],1.,places=10);self.assertEqual(rf['r_over_q_accelerator_ohm'],2*rf['r_over_q_circuit_ohm'])
                if trial['tracking']:self.assertTrue(trial['tracking']['tracking']['individual_ids_complete'])
            self.assertEqual(original,snapshots(result['trial_runs']))
            print('actual corner-refined step final difference Hz:',result['decision']['mesh_frequency_difference_hz'],flush=True)
