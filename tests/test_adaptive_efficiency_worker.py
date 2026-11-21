# SPDX-License-Identifier: Apache-2.0
"""Actual native/reference/ancestry integration and original exception identity."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from superfish_ng.adaptive_efficiency_analytic_grid import build_analytic_efficiency_grid
from superfish_ng.adaptive_efficiency_plan import build_adaptive_efficiency_plan
from superfish_ng.adaptive_efficiency_reference import load_efficiency_reference, verify_reference_bytes
from superfish_ng.adaptive_efficiency_worker import execute_efficiency_worker, _field_change, _prefix_cost
from superfish_ng.adaptive_refinement import _assemble
from superfish_ng.completion import digest
from superfish_ng.config import Case
from superfish_ng.mesh import make_mesh
from superfish_ng.mesh_input import mesh_to_dict
from superfish_ng.saved import read_solution


class AdaptiveEfficiencyWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=build_adaptive_efficiency_plan()
        cls.temp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.temp.name)
        rows=[]
        for row in cls.plan['cases'][:2]:
            case=Case.from_dict(row['request']['case']);mesh=mesh_to_dict(make_mesh(case))
            for order in (16,24):
                grid=build_analytic_efficiency_grid(row['id'],case,mesh,order=order)
                arrays={k:v for k,v in grid.items() if isinstance(v,np.ndarray)}
                metadata={k:v for k,v in grid.items() if k not in arrays}
                npz=cls.root/f'{row["id"]}-{order}.npz'
                np.savez_compressed(npz,**arrays)
                meta=cls.root/f'{row["id"]}-{order}.json';meta.write_text(json.dumps(metadata))
                rows.append(dict(case_id=row['id'],order=order,path=meta.name,sha256=digest(meta),
                                 field_path=npz.name,field_sha256=digest(npz)))
        repo=Path(__file__).resolve().parents[1]
        names=('src/superfish_ng/analytic.py','src/superfish_ng/analytic_sphere.py',
               'src/superfish_ng/adaptive_efficiency_analytic_grid.py')
        manifest=dict(document_type='n06_fixed_analytic_reference_grids',status='REFERENCE_PREPARATION_ACCEPTED',
                      fixed_input_sources=cls.plan['input_sources'],source_sha256={p:digest(repo/p) for p in names},grids=rows)
        path=cls.root/'manifest.json';path.write_text(json.dumps(manifest))
        cls.bindings=dict(analytic_manifest=dict(path=str(path),sha256=digest(path)))

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def execution(self,case,method):
        return next(row for row in self.plan['executions'] if row['case_id']==case and row['method']==method and row['repetition']==1)

    def test_actual_uniform_cylinder_reference_fields_and_original_native_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=execute_efficiency_worker(self.execution('cylinder','uniform'),self.bindings,Path(tmp)/'uniform',max_new_levels=3)
            self.assertEqual(len(result['levels']),3)
            self.assertEqual([r['triangles'] for r in result['levels']],[40,160,640])
            self.assertTrue(all(r['domain']['status']=='DOMAIN_VERIFIED' and r['ritz_passed'] and r['fixed_moments_passed'] for r in result['levels']))
            self.assertTrue(result['levels'][0]['initial_independent_identity']['passed'])
            self.assertTrue(all(r['current_mode_ids']==['fundamental','second'] for r in result['levels']))
            for grid in (0,1):
                errors=[r['reference_accuracy'][grid]['accuracy']['relative_errors']['electric_relative_l2'] for r in result['levels']]
                self.assertTrue(all(b<a for a,b in zip(errors,errors[1:])))
                self.assertLess(errors[-1],.005)
            self.assertTrue(all(e['accuracy']['status']=='PASS' for e in result['levels'][-1]['reference_accuracy']))
            self.assertEqual(result['observed_cost']['status'],'COMPLETE')
            costs=[r['observed_prefix_cost'] for r in result['levels']]
            self.assertTrue(all(c['recorder_prefix_wall_seconds']>=c['native_path_cumulative_seconds'] for c in costs))
            self.assertTrue(all(c['submission_prefix_wall_seconds'] is None for c in costs))
            self.assertTrue(all(b['native_path_cumulative_seconds']>a['native_path_cumulative_seconds'] for a,b in zip(costs,costs[1:])))
            names={p['name'] for p in result['observed_cost']['phases']}
            self.assertIn('assembly',names);self.assertIn('eigenproblem',names)
            self.assertNotIn('residual_marking',names)
            self.assertEqual(json.loads((Path(tmp)/'uniform/result.json').read_text()),result)
            self.assertIsNone(result['physical_error_bound'])

    def test_actual_adaptive_sphere_matches_original_prescribed_native_prefix(self):
        execution=self.execution('sphere','adaptive')
        with tempfile.TemporaryDirectory() as tmp:
            result=execute_efficiency_worker(execution,self.bindings,Path(tmp)/'adaptive',max_new_levels=2)
            self.assertEqual(len(result['levels']),2)
            old,_=_assemble(execution['request'],result['level_runs'])
            for expected,current in zip(old['levels'],result['levels']):
                for key in ('current_mode_ids','marked_cells','refinement_kind','quantities','indicator','quadrature_check','surface'):
                    self.assertEqual(expected[key],current[key])
                self.assertTrue(current['domain']['initial_source_mesh_exact_match'])
            self.assertEqual(result['status'],'PAUSED')
            self.assertIsNone(result['confirmed_accuracy_hit_index'])
            self.assertIn('residual_marking',{p['name'] for p in result['observed_cost']['phases']})

    def test_actual_adaptive_affine_matches_original_selection_and_tracking(self):
        execution=self.execution('cylinder','adaptive')
        with tempfile.TemporaryDirectory() as tmp:
            result=execute_efficiency_worker(execution,self.bindings,Path(tmp)/'adaptive',max_new_levels=2)
            old,_=_assemble(execution['request'],result['level_runs'])
            for expected,current in zip(old['levels'],result['levels']):
                for key in ('current_mode_ids','marked_cells','refinement_kind','quantities','indicator','surface'):
                    self.assertEqual(expected[key],current[key])
            self.assertEqual(result['levels'][1]['refinement_kind'],'residual')
            self.assertTrue(result['levels'][1]['tracking']['tracking']['individual_ids_complete'])

    def test_invalid_execution_missing_changed_reference_fail_before_fem_output(self):
        changed=deepcopy(self.execution('cylinder','uniform'));changed['request']['relative_tolerances']['frequency_hz']=.01
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'rejected'
            with patch('superfish_ng.adaptive_efficiency_worker.solve') as solver:
                with self.assertRaisesRegex(ValueError,'fixed N05 row'):
                    execute_efficiency_worker(changed,self.bindings,out)
                bad=deepcopy(self.bindings);bad['analytic_manifest']['sha256']='0'*64
                with self.assertRaisesRegex(ValueError,'SHA256 differs'):
                    execute_efficiency_worker(self.execution('cylinder','uniform'),bad,out)
                with self.assertRaisesRegex(ValueError,'submission_origin'):
                    execute_efficiency_worker(self.execution('cylinder','uniform'),self.bindings,out,submission_origin=float('nan'))
                solver.assert_not_called()
            self.assertFalse(out.exists())
            with self.assertRaisesRegex(ValueError,'missing required'):
                load_efficiency_reference('rounded-two-lobe',self.bindings)

    def test_original_solver_failure_cost_and_observed_bindings_restored(self):
        error=RuntimeError('original native solve failure')
        def failing_solver(*args,**kwargs):raise error
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'failed'
            with patch('superfish_ng.adaptive_efficiency_worker.solve',new=failing_solver):
                with self.assertRaises(RuntimeError) as caught:
                    execute_efficiency_worker(self.execution('cylinder','uniform'),self.bindings,out)
                self.assertIs(caught.exception,error)
                from superfish_ng import adaptive_efficiency_worker as worker
                self.assertIs(worker.solve,failing_solver)
            report=json.loads((out/'failure.json').read_text())
            self.assertEqual(report['observed_cost']['status'],'FAILED')
            self.assertEqual(report['preceding_level_runs'],[])
            self.assertFalse((out/'result.json').exists())

    def test_field_confirmation_uses_previous_native_norm_and_one_h_sign(self):
        grid=dict(weights=np.ones(2),axis_weights=np.ones(1))
        original=np.array([[2.,3.,4.],[1.,2.,3.],[0.,3.,0.]])
        scaled=original*1.006
        value=_field_change(original,scaled,grid)
        self.assertFalse(value['passed'])
        self.assertAlmostEqual(value['relative_errors']['electric_relative_l2'],.006,places=14)
        self.assertTrue(_field_change(original,-original,grid)['passed'])
        electric_only=original.copy();electric_only[:,:2]*=-1
        value=_field_change(original,electric_only,grid)
        self.assertFalse(value['passed']);self.assertAlmostEqual(value['relative_errors']['electric_relative_l2'],2.)

    def test_native_rf_ready_does_not_accept_vetoed_reference_and_keeps_uniform_confirmation(self):
        from superfish_ng.adaptive_efficiency_accuracy import assess_efficiency_samples
        def veto(*args,**kwargs):
            score=assess_efficiency_samples(*args,**kwargs)
            score['status']='FAIL';score['gates']['electric_relative_l2']=False
            score['control_test_veto']=True
            return score
        with tempfile.TemporaryDirectory() as tmp:
            with patch('superfish_ng.adaptive_efficiency_worker.assess_efficiency_samples',new=veto):
                result=execute_efficiency_worker(self.execution('cylinder','uniform'),self.bindings,Path(tmp)/'vetoed',max_new_levels=5)
            self.assertEqual(len(result['levels']),5)
            self.assertTrue(any(r['native_quantity_confirmation']['passed'] for r in result['levels'][:-1]))
            self.assertTrue(all(r['refinement_kind']=='uniform_confirmation' for r in result['levels'][1:]))
            self.assertEqual(result['status'],'PAUSED')
            self.assertIsNone(result['first_accuracy_hit_index'])
            self.assertIsNone(result['confirmed_accuracy_hit_index'])
            self.assertEqual(result['physical_acceptance_status'],'NOT_CONFIRMED')

    def test_prefix_native_root_costs_do_not_add_children_or_reference_twice(self):
        from types import SimpleNamespace
        rows=[dict(parent_index=None,name=n,inclusive_seconds=v) for n,v in
              (('initial_mesh_and_quality',2.),('native_level',5.),('next_refinement_plan',3.),('full_native_reference_metrics',9.))]
        rows.append(dict(parent_index=1,name='assembly',inclusive_seconds=4.))
        recorder=SimpleNamespace(snapshot=lambda:dict(phases=rows,wall_seconds=25.))
        value=_prefix_cost(recorder,None)
        self.assertEqual(value['native_path_cumulative_seconds'],10.)
        self.assertEqual(value['recorder_prefix_wall_seconds'],25.)
        self.assertIsNone(value['submission_prefix_wall_seconds'])

    def test_adaptive_native_stop_continues_uniform_when_reference_is_vetoed(self):
        from superfish_ng.adaptive_efficiency_accuracy import assess_efficiency_samples
        def veto(*args,**kwargs):
            score=assess_efficiency_samples(*args,**kwargs)
            score['status']='FAIL';score['gates']['electric_relative_l2']=False
            score['control_test_veto']=True
            return score
        with tempfile.TemporaryDirectory() as tmp:
            with patch('superfish_ng.adaptive_efficiency_worker.assess_efficiency_samples',new=veto):
                result=execute_efficiency_worker(self.execution('cylinder','adaptive'),self.bindings,Path(tmp)/'vetoed',max_new_levels=6)
            native_stops=[r for r in result['levels'] if r.get('original_native_next_decision',{}).get('status')=='TARGETS_MET']
            self.assertTrue(native_stops)
            for row in native_stops:
                self.assertEqual(result['levels'][row['index']+1]['refinement_kind'],'uniform_confirmation')
            self.assertIsNone(result['confirmed_accuracy_hit_index'])
            self.assertFalse(any(r['physical_reference_targets_met'] for r in result['levels']))


if __name__=='__main__':unittest.main()
