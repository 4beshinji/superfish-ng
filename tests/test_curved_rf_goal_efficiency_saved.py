# SPDX-License-Identifier: Apache-2.0
"""Replay rejects changed complete samples and inconsistent historical costs."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from superfish_ng.adaptive_efficiency_timing import PhaseRecorder
from superfish_ng.completion import digest
from superfish_ng.curved_rf_goal_efficiency_saved import _verify_costs, read_curved_rf_goal_efficiency, _implementation_sources
from superfish_ng.curved_rf_goal_efficiency_worker import _sample_event, _prefix_cost


class RFGoalSavedSamplesTests(unittest.TestCase):
    def test_rehashed_field_mode_or_extra_array_change_fails_without_writes(self):
        from test_curved_rf_goal_efficiency_metrics import data
        d=data();field=np.concatenate((d['fields'],np.ones((2,3))))[:,None,:]
        grid=dict(order=16,weights=d['weights'],axis_weights=d['axis_weights'],points=np.ones((3,2)),axis=np.ones((2,2)),
                  density=np.ones(3),reference_fields=d['fields'],reference_axis_ez=d['axis_ez'],quantities=d['quantities'],
                  reference_field_path='/reference',reference_field_sha256='0'*64)
        reference=dict(grids=[grid]);event=dict(index=1,mode_index=0,parent_event_index=0,current_mode_ids=['fundamental'],
                                               quantities=d['quantities'],surface=dict(intervals=d['peak_intervals']))
        parent=deepcopy(event);parent['index']=0
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);previous=root/'parent.npz';np.savez_compressed(previous,fields=field)
            before=[dict(order=16,sample_path=str(previous),sample_sha256=digest(previous))]
            sample=root/'samples-event-002-gauss-16.npz'
            np.savez_compressed(sample,fields=field,mode_ids_json=np.array(json.dumps(['fundamental'])))
            records=[dict(order=16,sample_path=str(sample),sample_sha256=digest(sample),volume_sample_count=3,axis_sample_count=2,
                          native_mode_count=1,reference_path='/reference',reference_sha256='0'*64)]
            original=sample.read_bytes()
            with patch('superfish_ng.curved_rf_goal_efficiency_worker.EfficiencyFieldSampler') as sampler:
                sampler.return_value.evaluate.return_value=dict(fields=field.copy())
                result=_sample_event({},reference,object(),event,root,before,parent,True,PhaseRecorder(),verify_samples=records)
                self.assertEqual(result[1],records);self.assertEqual(sample.read_bytes(),original)
                for changed in ('field','mode','extra'):
                    arrays=dict(fields=field.copy(),mode_ids_json=np.array(json.dumps(['fundamental'])))
                    if changed=='field':arrays['fields'][0,0,0]*=1.02
                    if changed=='mode':arrays['mode_ids_json']=np.array(json.dumps(['wrong']))
                    if changed=='extra':arrays['extra']=np.ones(1)
                    np.savez_compressed(sample,**arrays);bad=deepcopy(records);bad[0]['sample_sha256']=digest(sample)
                    sampler.return_value.evaluate.return_value=dict(fields=field.copy())
                    with self.subTest(changed=changed),self.assertRaises(ValueError):
                        _sample_event({},reference,object(),event,root,before,parent,True,PhaseRecorder(),verify_samples=bad)
                    self.assertEqual(digest(sample),bad[0]['sample_sha256'])


class RFGoalSavedCostTests(unittest.TestCase):
    def document(self):
        clock=iter(range(100));r=PhaseRecorder(clock=lambda:next(clock),rss_reader=lambda:1024)
        with r.phase('initial_plan'):pass
        with r.phase('native_event'):
            with r.phase('native_solve_and_normalization'):pass
        with r.phase('independent_accuracy_and_parent_changes'):pass
        prefix=_prefix_cost(r,None)
        with r.phase('journal_write'):pass
        return dict(event_records=[dict(observed_prefix_cost=prefix)],observed_cost=r.finish())

    def test_nested_costs_prefix_and_no_fake_measurement(self):
        doc=self.document();before=deepcopy(doc)
        self.assertEqual(doc['event_records'][0]['observed_prefix_cost']['native_path_cumulative_seconds'],4.)
        result=_verify_costs(doc)
        self.assertEqual(result,'STRUCTURE_VERIFIED_NOT_REMEASURED');self.assertEqual(doc,before)
        for mutate in ('parent','exclusive','prefix','count','wall','nan'):
            bad=deepcopy(doc)
            if mutate=='parent':bad['observed_cost']['phases'][2]['parent_index']=2
            elif mutate=='exclusive':bad['observed_cost']['phases'][1]['exclusive_seconds']+=1
            elif mutate=='prefix':bad['event_records'][0]['observed_prefix_cost']['native_path_cumulative_seconds']+=1
            elif mutate=='count':bad['observed_cost']['phases'][1]['name']='unobserved_native'
            elif mutate=='wall':bad['observed_cost']['wall_seconds']=0
            else:bad['event_records'][0]['observed_prefix_cost']['recorder_prefix_wall_seconds']=float('nan')
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):_verify_costs(bad)
        prefix=dict(event_records=deepcopy(doc['event_records']))
        self.assertEqual(_verify_costs(prefix),'PREFIX_ONLY_NOT_REMEASURED')

    def test_raw_duplicate_hash_symlink_and_missing_binding_fail_before_reconstruction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'record.json';p.write_text('{"schema_version":1,"schema_version":1}')
            with patch('superfish_ng.curved_rf_goal_efficiency_saved.replay_curved_rf_goal_efficiency') as replay:
                with self.assertRaises(ValueError):read_curved_rf_goal_efficiency(p,expected_sha256=digest(p))
                p.write_text('{}')
                with self.assertRaises(ValueError):read_curved_rf_goal_efficiency(p,expected_sha256='0'*64)
                link=root/'link.json';link.symlink_to(p)
                with self.assertRaises(ValueError):read_curved_rf_goal_efficiency(link,expected_sha256=digest(p))
                replay.assert_not_called()

    def test_memory_unknown_and_submission_clock_keep_their_actual_meaning(self):
        doc=self.document()
        unknown=deepcopy(doc)
        unknown['observed_cost'].update(peak_rss_bytes=None,memory_status='UNKNOWN',memory_reason='unavailable')
        self.assertEqual(_verify_costs(unknown),'STRUCTURE_VERIFIED_NOT_REMEASURED')
        for changed in ('boolean_rss','zero_rss','missing_reason','false_unknown','unknown_status','submission_before_recorder'):
            bad=deepcopy(unknown if changed=='missing_reason' else doc)
            cost=bad['observed_cost']
            if changed=='boolean_rss':cost['peak_rss_bytes']=True
            elif changed=='zero_rss':cost['peak_rss_bytes']=0
            elif changed=='missing_reason':cost['memory_reason']=None
            elif changed=='false_unknown':cost['memory_status']='UNKNOWN'
            elif changed=='unknown_status':cost['memory_status']='PASS'
            else:bad['event_records'][0]['observed_prefix_cost']['submission_prefix_wall_seconds']=0.
            with self.subTest(changed=changed),self.assertRaises(ValueError):_verify_costs(bad)


class RFGoalSavedMetadataTests(unittest.TestCase):
    def test_saved_json_scalar_representation_remains_exact_and_typed(self):
        from superfish_ng.curved_rf_goal_efficiency_saved import _same_saved
        _same_saved(dict(tolerance=1e-13,values=[1,2]),dict(tolerance=np.float64(1e-13),values=(1,2)),'record')
        for bad in (dict(tolerance=True,values=[1,2]),dict(tolerance=1e-13,values=[1.,2]),dict(tolerance=1e-12,values=[1,2])):
            with self.assertRaises(ValueError):_same_saved(bad,dict(tolerance=np.float64(1e-13),values=(1,2)),'record')
        with self.assertRaises(ValueError):_same_saved(dict(tolerance=0.),dict(tolerance=np.float64('nan')),'record')

    def test_complete_original_source_archives_are_required_and_never_executed(self):
        from superfish_ng.jobs import _implementation_hashes
        sources=_implementation_hashes()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'historical-worker.py';p.write_text('raise AssertionError("provenance must not execute")\n')
            sources['curved_rf_goal_efficiency_worker.py']=digest(p)
            aliases={'curved_rf_goal_efficiency_worker.py':str(p)}
            result=_implementation_sources(sources,aliases)
            self.assertEqual(result[str(p)],digest(p))
            p.write_text('changed archive')
            with self.assertRaises(ValueError):_implementation_sources(sources,aliases)
            with self.assertRaises(ValueError):_implementation_sources(sources,dict(aliases,extra=str(p)))
            missing=deepcopy(sources);missing.pop('solver.py')
            with self.assertRaises(ValueError):_implementation_sources(missing,aliases)
            invalid=deepcopy(sources);invalid['../outside.py']='0'*64
            with self.assertRaises(ValueError):_implementation_sources(invalid,aliases)

    def test_strict_complete_metadata_is_not_itself_a_physical_acceptance(self):
        from superfish_ng.curved_rf_goal_efficiency_saved import _preflight,_SCOPE
        from superfish_ng.curved_rf_goal_efficiency_plan import build_curved_rf_goal_efficiency_plan,request_for_curved_rf_goal_efficiency_execution
        from superfish_ng.adaptive_efficiency_domain import _native_files
        row=build_curved_rf_goal_efficiency_plan()['executions'][0];request=request_for_curved_rf_goal_efficiency_execution(row)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);run=root/'event-001';run.mkdir();(run/'case.json').write_text('{}')
            samples=[]
            for order in (16,24):
                p=root/f'samples-event-001-gauss-{order}.npz';p.write_bytes(b'metadata fixture, not a physical field')
                samples.append(dict(order=order,sample_path=str(p),sample_sha256=digest(p),volume_sample_count=3,axis_sample_count=2,native_mode_count=1,reference_path='/reference',reference_sha256='0'*64))
            doc=dict(schema_version=1,document_type='curved_rf_goal_efficiency_worker_checkpoint',execution=row,request=request,
                     status='PAUSED',native_status='UNIFORM_CONTROL',public_checkpoint=None,events=[dict(index=0)],level_runs=[str(run)],
                     native_sources=[_native_files(run)],event_records=[dict(index=0,origin='uniform_control',run=str(run),domain={},moments=[],fixed_moments_passed=True,ritz_passed=True,all_frequencies_hz=[],all_quantities=[],initial_independent_identity=[],samples=samples,observed_prefix_cost={})],observations=[dict(index=0,source_domain_identity_status='UNVERIFIED',reference_orders=[],parent_change=None)],
                     assessment={},reference_bound_inputs={},implementation_sha256={},native_solves_attempted=1,native_solves_completed=1,
                     physical_error_bound=None,development_event_limit=1,scope=_SCOPE)
            from test_curved_rf_goal_efficiency_metrics import fixture
            from superfish_ng.curved_rf_goal_efficiency_metrics import assess_rf_goal_history
            events,observations=fixture(['initial'],[None]);events[0]['current_mode_ids']=request['initial_ids']
            doc.update(events=events,observations=observations,assessment=assess_rf_goal_history(events,observations))
            self.assertEqual(_preflight(doc)[0],request)
            changes=[('extra',True),('schema_version',True),('native_solves_attempted',True),('events',[]),('level_runs',[{}]),
                     ('development_event_limit',0),('native_status','TARGETS_MET'),('physical_error_bound',0.),('scope','changed')]
            for key,value in changes:
                bad=deepcopy(doc);bad[key]=value
                with self.subTest(key=key),self.assertRaises(ValueError):_preflight(bad)
            bad=deepcopy(doc);bad['event_records'][0]['samples'][0]['order']=16.
            with self.assertRaises(ValueError):_preflight(bad)
            bad=deepcopy(doc);bad['events'][0].pop('current_mode_ids')
            with self.assertRaises(ValueError):_preflight(bad)
            rf_row=next(r for r in build_curved_rf_goal_efficiency_plan()['executions'] if r['method']=='rf_goal')
            for malformed in (None,[],{},dict(level_runs=None),dict(level_runs=1),dict(level_runs='x')):
                bad=deepcopy(doc);bad.update(execution=rf_row,request=request_for_curved_rf_goal_efficiency_execution(rf_row),public_checkpoint=malformed)
                with self.subTest(public=malformed),self.assertRaises(ValueError):_preflight(bad)


if __name__=='__main__':unittest.main()
