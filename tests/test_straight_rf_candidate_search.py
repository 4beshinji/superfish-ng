# SPDX-License-Identifier: Apache-2.0
"""Actual original-domain multivariable polls, native IDs and exclusive resume."""
from copy import deepcopy
import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from test_straight_rf_candidates import request as candidate_request
from test_straight_tuning_geometry import boundary
from superfish_ng.project import Project


def request(kind='stepped_profile',modes=1):
    candidate=candidate_request(kind);candidate['max_candidates']=4
    candidate['project']['case']['mesh'].update(nr=6,nz=8)
    candidate['project']['case']['solver']['modes']=modes
    return dict(schema_version=1,document_type='straight_rf_candidate_search_request',
        candidate_request=candidate,
        poll_variables=[dict(name=v['name'],initial=1.,step=.01,tolerance=.01) for v in candidate['variables']],
        max_trials=4,initial_ids=['mode-'+str(i+1) for i in range(modes)],refinement_scale=2)


def hashes(runs):
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for group in runs for run in group
        for p in Path(run).rglob('*') if p.is_file()}


class StraightRFCandidateSearchTests(unittest.TestCase):
    def test_independent_original_shape_poll_and_three_level_domains(self):
        from superfish_ng.straight_rf_candidate_search import candidate_projects,candidate_decision,validate_request
        r=request();original=deepcopy(r);validate_request(r)
        source=boundary(Project.from_dict(r['candidate_request']['project']).case)
        trials=[];seen=[]
        for _ in range(4):
            trial=candidate_decision(r,trials)['next_trial'];projects=candidate_projects(r,trial)
            sr,sz=trial['values'];seen.append(trial['values'])
            for project in projects:
                polygon=boundary(project.case)
                self.assertAlmostEqual(polygon.area_m2/source.area_m2,sr*sz)
                self.assertAlmostEqual(polygon.volume_m3/source.volume_m3,sr**2*sz)
            expected=[2**i for i in range(1 if trial['phase']=='final' else 0,4 if trial['phase']=='final' else 3)]
            self.assertEqual([p.case.nr for p in projects],[6*s for s in expected])
            trials.append(dict(**trial,status='IDENTITY_VERIFIED',assessment=None))
        self.assertEqual(seen,[[1.,1.],[1.01,1.],[.99,1.],[1.,1.]])
        self.assertEqual(candidate_decision(r,trials)['status'],'FINAL_UNVERIFIED')
        self.assertEqual(r,original)

    def test_actual_all_geometries_both_variables_pause_resume_and_native_replay(self):
        from superfish_ng.straight_rf_candidate_search import execute_straight_rf_candidate_search as execute,replay_straight_rf_candidate_search as replay,candidate_projects
        from test_straight_tuning import read_solution
        from superfish_ng.rf import quantities
        for kind in ('profile','stepped_profile','contour'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as tmp:
                r=request(kind);r['max_trials']=6;r['candidate_request']['max_candidates']=6
                if kind=='contour':r['candidate_request']['project']['case']['mesh']['contour_mesh']=dict(max_edge_m=.03,min_angle_deg=5.,max_triangles=30000,max_rounds=12)
                root=Path(tmp);first=execute(r,root/'first',max_new_trials=2)
                self.assertEqual(first['status'],'PAUSED');original=hashes(first['candidate_runs'])
                result=execute(r,root/'rest',checkpoint=first)
                self.assertEqual(result['status'],'FINAL_UNVERIFIED');self.assertFalse(result['can_resume'])
                self.assertEqual(result['completed_fem_solves'],18);self.assertEqual(result['max_fem_solves'],18)
                self.assertEqual(result,replay(result));self.assertEqual(original,hashes(first['candidate_runs']))
                self.assertEqual([t['values'] for t in result['trials']],[[1.,1.],[1.01,1.],[.99,1.],[1.,1.01],[1.,.99],[1.,1.]])
                for trial,group in zip(result['trials'],result['candidate_runs']):
                    self.assertEqual(trial['status'],'IDENTITY_VERIFIED');self.assertIsNone(trial['assessment'])
                    self.assertTrue(all(s['tracking']['individual_ids_complete'] for s in trial['refinement_history']['steps']))
                    if trial['tracking']:self.assertEqual(trial['tracking']['tracking']['current_mode_ids'],r['initial_ids'])
                    for run,project in zip(group,candidate_projects(r,trial)):
                        solution=read_solution(Path(run)/'solution');self.assertEqual(solution.case,project.case)
                        rf=quantities(solution.case,solution);self.assertAlmostEqual(rf['stored_energy_j'],1.,places=10)
                        self.assertAlmostEqual(rf['r_over_q_accelerator_ohm'],2*rf['r_over_q_circuit_ohm'],places=8)
                for change in ('values','score','parent','comparison','source'):
                    bad=deepcopy(result)
                    if change=='values':bad['trials'][1]['values'][0]=1.001
                    elif change=='score':bad['trials'][0]['assessment']={'objective':{'eligible_value':1e99}}
                    elif change=='parent':bad['trials'][1]['parent_index']=1
                    elif change=='comparison':bad['trials'][1]['tracking']['request']['controls']['comparison_meshes'][0]['points'][0][0]+=.001
                    else:bad['candidate_sources_sha256'][0][0]={}
                    with self.subTest(change=change),self.assertRaises(ValueError):replay(bad)
                with self.assertRaisesRegex(ValueError,'PAUSED'):execute(r,root/'terminal',checkpoint=result)
                self.assertFalse((root/'terminal').exists())
                print('actual straight candidate search:',kind,len(result['trials']),result['completed_fem_solves'],result['status'],flush=True)

    def test_independent_bessel_cylinder_in_original_candidate_native_fields_and_rf(self):
        from test_straight_tuning import cylinder_request,read_solution
        from superfish_ng.straight_rf_candidate_search import execute_straight_rf_candidate_search as execute
        from superfish_ng.constants import C0,MU0,EPS0,TAU
        from scipy.special import jn_zeros,jv
        from superfish_ng.sampling import FieldSampler
        from superfish_ng.rf import quantities
        r=request('profile');tune=cylinder_request();r['candidate_request']['project']=tune['project']
        r['candidate_request']['shape_law']=deepcopy(tune['shape_law'])
        for binding in r['candidate_request']['shape_law']['bindings']:
            binding['expression']['args'][1]['variable']='radial' if binding['coordinate']=='r' else 'axial'
        r['max_trials']=2;r['candidate_request']['max_candidates']=2
        with tempfile.TemporaryDirectory() as tmp:
            result=execute(r,Path(tmp)/'run');errors=[]
            for group in result['candidate_runs']:
                for run in group:
                    s=read_solution(Path(run)/'solution');case=s.case;R=case.profile[0][1];L=case.length;chi=jn_zeros(0,1)[0]
                    f=C0*chi/(TAU*R);omega=TAU*f;A=np.sqrt(2/(MU0*np.pi*R**2*L*jv(1,chi)**2))
                    points=s.mesh.points[s.mesh.triangles].mean(axis=1);h=A*jv(1,chi*points[:,0]/R);e=A/(C0*EPS0)*jv(0,chi*points[:,0]/R)
                    fields=FieldSampler.from_solution(s).evaluate(points);sign=np.sign(h@fields['Hphi_A_per_m'])
                    wall=TAU*A*A*jv(1,chi)**2*R*(L+R);rs=np.sqrt(np.pi*f*MU0/case.conductivity_s_per_m);loss=rs*wall/2
                    voltage=A/(C0*EPS0)*L*np.sinc(omega*L/(TAU*C0));rq=voltage**2/omega;rf=quantities(case,s)
                    error=np.array([abs(rf['frequency_hz']/f-1),np.linalg.norm(sign*fields['Hphi_A_per_m']-h)/np.linalg.norm(h),np.linalg.norm(sign*fields['Ez_quadrature_V_per_m']-e)/np.linalg.norm(e),abs(rf['wall_loss_w']/loss-1),abs(rf['r_over_q_accelerator_ohm']/rq-1)])
                    np.testing.assert_array_less(error,[1e-4,.001,.01,.005,.005]);errors.append(error.tolist())
            self.assertTrue(np.all(np.asarray(errors[1])<np.asarray(errors[0])));self.assertTrue(np.all(np.asarray(errors[2])<np.asarray(errors[1])))
            self.assertEqual(result['status'],'FINAL_UNVERIFIED');self.assertEqual(result['rf_assessments'],0)
            print('candidate cylinder independent f/H/E/loss/RQ:',json.dumps(errors),flush=True)

    def test_actual_ambiguous_ids_stop_before_third_level_or_next_poll(self):
        import superfish_ng.straight_rf_candidate_search as engine
        r=request(modes=2);r['candidate_request']['controls']['relative_cluster_gap']=.99
        with tempfile.TemporaryDirectory() as tmp,patch.object(engine,'execute_project',wraps=engine.execute_project) as solve:
            result=engine.execute_straight_rf_candidate_search(r,Path(tmp)/'run')
            self.assertEqual(solve.call_count,2);self.assertEqual(result['completed_fem_solves'],2)
            self.assertEqual(result['status'],'UNVERIFIED');self.assertFalse(result['can_resume'])
            self.assertIsNone(result['trials'][0]['assessment']);self.assertEqual(result,engine.replay_straight_rf_candidate_search(result))
            self.assertFalse(result['trials'][0]['refinement_history']['steps'][0]['tracking']['individual_ids_complete'])

    def test_invalid_later_candidate_no_new_fem_failure_budget_and_immutable_prefix(self):
        import superfish_ng.straight_rf_candidate_search as engine
        r=request('contour');binding=r['candidate_request']['shape_law']['bindings'][0];old=binding['expression']
        r['candidate_request']['project']['case']['mesh']['contour_mesh']=dict(max_edge_m=.03,min_angle_deg=5.,max_triangles=30000,max_rounds=12)
        binding['expression']=dict(op='if',args=[dict(op='gt',args=[dict(variable='radial'),dict(constant=1.005,unit='1')]),dict(constant=-.001,unit='m'),old])
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);first=engine.execute_straight_rf_candidate_search(r,root/'first',max_new_trials=1)
            original=hashes(first['candidate_runs']);saved=(root/'first/checkpoint-001.json').read_bytes()
            with patch.object(engine,'execute_project',side_effect=AssertionError('invalid geometry must not enter FEM')) as solve:
                with self.assertRaises(ValueError):engine.execute_straight_rf_candidate_search(r,root/'fail',checkpoint=first)
                solve.assert_not_called()
            failure=json.loads((root/'fail/failure-002.json').read_text());self.assertEqual(failure['candidates_attempted'],2)
            self.assertEqual(failure['fem_calls_attempted'],3);self.assertIsNone(failure['assessment'])
            self.assertEqual(original,hashes(first['candidate_runs']));self.assertEqual(saved,(root/'first/checkpoint-001.json').read_bytes())
            self.assertEqual(first,engine.replay_straight_rf_candidate_search(first))

    def test_actual_cylinder_rank_crossing_tracks_original_individual_fields(self):
        from test_straight_tuning import cylinder_request
        from scipy.special import jn_zeros
        from superfish_ng.straight_rf_candidate_search import execute_straight_rf_candidate_search as execute,replay_straight_rf_candidate_search as replay
        tune=cylinder_request(modes=3);R=.08;roots=jn_zeros(0,2);L=np.pi*R/np.sqrt(roots[1]**2-roots[0]**2)*1.002
        r=request('profile',modes=3);r['candidate_request']['project']=tune['project'];r['candidate_request']['shape_law']=deepcopy(tune['shape_law'])
        factor=float(L/.08)
        for point in r['candidate_request']['shape_law']['reference_comparison_mesh']['points']:point[1]*=factor
        # Both physical owners use the same represented endpoint, rather than
        # mixing L with the separately rounded product .08*(L/.08).
        r['candidate_request']['project']['case']['geometry']['points_zr_m'][1][0]=.08*factor
        for binding in r['candidate_request']['shape_law']['bindings']:
            binding['expression']['args'][1]['variable']='radial' if binding['coordinate']=='r' else 'axial'
            if binding['coordinate']=='z':binding['expression']['args'][0]['constant']*=factor
        r['max_trials']=3;r['candidate_request']['max_candidates']=3;r['poll_variables'][0]['step']=.01
        with tempfile.TemporaryDirectory() as tmp:
            result=execute(r,Path(tmp)/'run');self.assertEqual(result['status'],'FINAL_UNVERIFIED')
            pair=result['trials'][1]['tracking'];self.assertEqual(pair['status'],'PASS');self.assertTrue(pair['tracking']['individual_ids_complete'])
            self.assertEqual(pair['tracking']['current_mode_ids'],['mode-1','mode-3','mode-2'])
            self.assertEqual(result['trials'][-1]['current_mode_ids'],r['initial_ids']);self.assertEqual(result,replay(result))
            print('actual native cylinder rank crossing:',pair['tracking']['current_mode_ids'],flush=True)

    def test_strict_poll_request_project_binding_and_no_criteria_capability(self):
        from superfish_ng.straight_rf_candidate_search import validate_request,candidate_projects,candidate_pair_controls,candidate_decision
        r=request();bad=[]
        for mutate in (
            lambda x:x.update(criteria={}),lambda x:x.update(schema_version=True),lambda x:x.update(max_trials=5),
            lambda x:x['poll_variables'][0].update(initial=2.),lambda x:x['poll_variables'][0].update(step=0.),
            lambda x:x['poll_variables'][0].update(tolerance=float('nan')),lambda x:x['poll_variables'].reverse(),
            lambda x:x.update(initial_ids=[[]]),lambda x:x.update(refinement_scale=True),
        ):
            data=deepcopy(r);mutate(data);bad.append(data)
        for data in bad:
            with self.subTest(data=data),self.assertRaises(ValueError):validate_request(data)
        trial=candidate_decision(r,[])['next_trial'];projects=candidate_projects(r,trial)
        self.assertEqual(candidate_pair_controls(r,trial,trial,*projects[:2])['comparison_meshes'][0],candidate_pair_controls(r,trial,trial,*projects[:2])['comparison_meshes'][1])
        raw=projects[1].to_dict();raw['case']['rf']['normalization_j']=2.
        with self.assertRaisesRegex(ValueError,'Project differs'):candidate_pair_controls(r,trial,trial,projects[0],Project.from_dict(raw))
        with self.assertRaisesRegex(ValueError,'no RF assessment'):candidate_decision(r,[dict(**trial,status='IDENTITY_VERIFIED',assessment={'objective':1.})])

    def test_solver_failure_and_symlink_or_late_ancestor_mutation_rejected(self):
        import superfish_ng.straight_rf_candidate_search as engine
        r=request()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch.object(engine,'execute_project',side_effect=RuntimeError('native failure')):
                with self.assertRaisesRegex(RuntimeError,'native failure'):engine.execute_straight_rf_candidate_search(r,root/'failure')
            failure=json.loads((root/'failure/failure-001.json').read_text());self.assertEqual(failure['fem_calls_attempted'],1);self.assertIsNone(failure['assessment'])
            first=engine.execute_straight_rf_candidate_search(r,root/'first',max_new_trials=1);original=hashes(first['candidate_runs'])
            path=Path(first['candidate_runs'][0][0]);link=path/'linked-source';link.symlink_to(path/'project.json')
            with self.assertRaisesRegex(ValueError,'symbolic links'):engine.replay_straight_rf_candidate_search(first)
            link.unlink();native=path/'project.json';data=native.read_bytes();execute=engine.execute_project
            def mutate(project,run):
                value=execute(project,run);native.write_bytes(data+b' ');return value
            try:
                with patch.object(engine,'execute_project',side_effect=mutate):
                    with self.assertRaises(ValueError):engine.execute_straight_rf_candidate_search(r,root/'late',checkpoint=first)
            finally:native.write_bytes(data)
            self.assertEqual(original,hashes(first['candidate_runs']));self.assertEqual(first,engine.replay_straight_rf_candidate_search(first))
