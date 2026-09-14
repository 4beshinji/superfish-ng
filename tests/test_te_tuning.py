# SPDX-License-Identifier: Apache-2.0
"""TE tuning uses Ephi identities, native TE replay and Bessel dispersion."""
from copy import deepcopy
from dataclasses import replace
import json,math,tempfile,unittest
from pathlib import Path
from scipy.special import jn_zeros
from superfish_ng.constants import C0
from superfish_ng.project import Project
from superfish_ng.tuning import _request,_project,execute_tune,replay_tune
from superfish_ng.te_saved import read_te_run
from superfish_ng.te import te_quantities
from test_te import cavity


def te_request(end='pec',reflected=False):
    case=replace(cavity(n=16,modes=1),z_max=end)
    r=json.loads(Path('examples/tuning/pillbox_length.json').read_text())
    factor=.5 if end=='magnetic_symmetry' else 1.
    r.update(project=Project(case,reflect_full=reflected).to_dict(),bounds=[.16,.2],initial_ids=['TE011'],mode_id='TE011',
        target_hz=float(C0/(2*math.pi)*math.hypot(jn_zeros(1,1)[0]/.1,factor*math.pi/.18)),
        frequency_tolerance_hz=1e5,mesh_frequency_tolerance_hz=1e5)
    return r


class TETuningTests(unittest.TestCase):
    def test_closed_cylinder_bessel_target_native_replay_and_acceleration_na(self):
        r=te_request();_request(r)
        with tempfile.TemporaryDirectory() as tmp:
            result=execute_tune(r,Path(tmp)/'run')
            self.assertEqual(result['status'],'TUNED');self.assertLess(abs(result['decision']['value']/.18-1),2e-4)
            self.assertEqual(replay_tune(result),result)
            self.assertIn('TE Ephi',result['scope'])
            for t,run in zip(result['trials'],result['trial_runs']):
                solution=read_te_run(Path(run)/'solution')
                expected=C0/(2*math.pi)*math.hypot(jn_zeros(1,1)[0]/.1,math.pi/t['value'])
                self.assertLess(abs(t['frequency_hz']/expected-1),1e-4)
                self.assertIsNone(te_quantities(solution)['r_over_q_accelerator_ohm'])
                if t['tracking']:self.assertEqual(t['tracking']['tracking']['physical_mapping']['field'],'Ephi_V_per_m')
            path=Path(result['trial_runs'][0])/'solution/axis_001.csv';path.write_text(path.read_text()+'\n')
            with self.assertRaises(ValueError):replay_tune(result)

    def test_matching_half_and_reflected_sectors_keep_source_frequency_order(self):
        for end,reflected in [('magnetic_symmetry',False),('electric_symmetry',True)]:
            r=te_request(end,reflected);_request(r)
            with self.subTest(end=end,reflected=reflected),tempfile.TemporaryDirectory() as tmp:
                first=execute_tune(r,Path(tmp)/'first',max_new_trials=2)
                final=execute_tune(r,Path(tmp)/'rest',checkpoint=first)
                self.assertEqual(final['status'],'TUNED');self.assertEqual(replay_tune(final),final)
                self.assertEqual(final['trial_sources_sha256'][:2],first['trial_sources_sha256'])
                self.assertIn('source symmetry-sector',final['scope'])
                for trial in final['trials'][1:]:
                    mapping=trial['tracking']['tracking']['physical_mapping']
                    self.assertEqual(mapping['reflected_partial_spectrum'],reflected)
                    self.assertEqual(mapping['boundary_conditions'],['pec',end])

    def test_crossing_changes_rank_while_retaining_the_electric_field_id(self):
        r=te_request();r['project']=Project(cavity(n=24,modes=4)).to_dict();r['bounds']=[.145,.16]
        roots=jn_zeros(1,3)
        def labels(length):return [label for f,label in sorted((math.hypot(root/.1,p*math.pi/length),f'r{n}p{p}') for n,root in enumerate(roots,1) for p in range(1,7))[:4]]
        r.update(initial_ids=labels(.145),mode_id='r1p3',target_hz=float(C0/(2*math.pi)*math.hypot(roots[0]/.1,3*math.pi/.1525)),frequency_tolerance_hz=5e5,mesh_frequency_tolerance_hz=5e5)
        with tempfile.TemporaryDirectory() as tmp:
            result=execute_tune(r,Path(tmp)/'run');self.assertEqual(result['status'],'TUNED')
            self.assertNotEqual(result['trials'][0]['current_mode_ids'].index('r1p3'),result['trials'][1]['current_mode_ids'].index('r1p3'))
            for t in result['trials']:
                self.assertEqual(t['current_mode_ids'],labels(t['value']))
                expected=C0/(2*math.pi)*math.hypot(roots[0]/.1,3*math.pi/t['value'])
                self.assertLess(abs(t['frequency_hz']/expected-1),1e-4)

    def test_unsupported_mapping_geometry_and_tm_reader_remain_strict(self):
        from superfish_ng.saved import read_solution
        r=te_request()
        changed=deepcopy(r);changed['project']['case']['geometry']['points_zr_m'][1][1]=.11
        bad=[changed,dict(r,controls=dict(r['controls'],mapping='normalized_profile'))]
        for value in bad:
            with self.assertRaisesRegex(ValueError,'TE'):_request(value)
        for version in (4,5,8):
            changed=deepcopy(r);changed['schema_version']=version
            with self.assertRaises(ValueError):_request(changed)
        with tempfile.TemporaryDirectory() as tmp:
            result=execute_tune(r,Path(tmp)/'one',max_new_trials=1)
            with self.assertRaisesRegex(ValueError,'TE'):read_solution(Path(result['trial_runs'][0])/'solution')

    def test_linked_polynomial_and_expression_dimensions_preserve_te_model(self):
        from test_expression_tuning import c,op,X
        for version in (2,3,7):
            r=te_request();r.update(schema_version=version,parameter='x',parameter_unit='1',bounds=[0.,.1])
            if version==7:r['geometry_kind']='profile'
            bindings=[]
            for i in (0,1):
                b=dict(path=f'/case/geometry/points_zr_m/{i}/1')
                if version==2:b.update(multiplier=.01,offset_m=.1)
                elif version==3:b['coefficients']=[.1,.01,.002]
                else:b['expression']=op('mul',c(.1,'m'),op('exp',X))
                bindings.append(b)
            r['bindings']=bindings;_request(r)
            with self.subTest(version=version),tempfile.TemporaryDirectory() as tmp:
                result=execute_tune(r,Path(tmp)/'run',max_new_trials=1)
                solution=read_te_run(Path(result['trial_runs'][0])/'solution')
                self.assertEqual(solution.case.model.polarization,'te')
                self.assertIsNone(te_quantities(solution)['r_over_q_circuit_ohm'])

    def test_interior_non_cylinder_is_refused_before_fem_and_keeps_checkpoint(self):
        from test_expression_tuning import c,op,X
        from unittest.mock import patch
        r=te_request();r.update(schema_version=7,geometry_kind='profile',parameter='x',parameter_unit='1',bounds=[0.,1.],
            target_hz=float(C0/(2*math.pi)*math.hypot(jn_zeros(1,1)[0]/.1,math.pi/.205)),frequency_tolerance_hz=1e4)
        r['bindings']=[dict(path='/case/geometry/points_zr_m/1/0',expression=op('add',c(.2,'m'),op('mul',c(.01,'m'),X))),
            dict(path='/case/geometry/points_zr_m/1/1',expression=op('add',c(.1,'m'),op('mul',c(.01,'m'),op('mul',X,op('sub',c(1),X)))))]
        with tempfile.TemporaryDirectory() as tmp:
            first=execute_tune(r,Path(tmp)/'first',max_new_trials=2)
            self.assertEqual(first['decision']['next_trial']['value'],.5)
            with patch('superfish_ng.tuning.execute_project') as solve:
                with self.assertRaisesRegex(ValueError,'TE'):execute_tune(r,Path(tmp)/'failed',checkpoint=first)
                solve.assert_not_called()
            self.assertEqual(replay_tune(first),first)
            self.assertTrue((Path(tmp)/'failed/failure-003.json').exists())

    def test_p1_coarse_target_does_not_bypass_the_refinement_gate(self):
        from superfish_ng import solve
        r=te_request();r['project']['case']['solver']['element_order']=1
        p=_project(r,r['bounds'][0],'search');r.update(target_hz=float(solve(p.case).frequencies_hz[0]),frequency_tolerance_hz=1.,mesh_frequency_tolerance_hz=1.)
        with tempfile.TemporaryDirectory() as tmp:
            result=execute_tune(r,Path(tmp)/'run')
            self.assertEqual(result['status'],'REFINEMENT_FAILED')
            self.assertFalse(result['decision']['mesh_difference_met'])
            self.assertEqual(result['trials'][-1]['parent_index'],0)
            self.assertEqual(read_te_run(Path(result['trial_runs'][-1])/'solution').element_order,1)
            self.assertEqual(replay_tune(result),result)
