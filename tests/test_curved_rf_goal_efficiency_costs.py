# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
from types import SimpleNamespace
import tempfile
import json
import unittest
from unittest.mock import patch

import numpy as np
from scipy.sparse import csc_matrix
from scipy.sparse.linalg import splu

from superfish_ng import curved_rf_adjoint as adjoint
from superfish_ng.adaptive_efficiency_observation import observe_selected_calls
from superfish_ng.adaptive_efficiency_timing import PhaseRecorder


class RFGoalLinearSolveObservationTests(unittest.TestCase):
    def test_original_superlu_result_rhs_and_failure_identity_are_preserved(self):
        from superfish_ng.curved_rf_goal_efficiency_observation import observe_adjoint_linear_solves
        def call(factor,rhs):return factor.solve(rhs)
        factor=splu(csc_matrix([[3.,1.],[1.,2.]]));rhs=np.array([1.,4.]);before=rhs.copy();expected=factor.solve(rhs)
        clock=iter([0.,1.,4.,5.]);recorder=PhaseRecorder(clock=lambda:next(clock),rss_reader=lambda:None)
        with observe_adjoint_linear_solves(recorder,callers=[call]):actual=call(factor,rhs)
        np.testing.assert_array_equal(rhs,before);np.testing.assert_array_equal(actual,expected)
        self.assertEqual(recorder.finish()['phases'][0]['inclusive_seconds'],3.)
        observed=[];recorder=PhaseRecorder()
        with self.assertRaises(ValueError) as caught:
            with observe_adjoint_linear_solves(recorder,callers=[call]):
                try:call(factor,np.zeros(3))
                except ValueError as error:observed.append(error);raise
        self.assertIs(caught.exception,observed[0])
        phase=recorder.finish()['phases'][0]
        self.assertEqual(phase['status'],'FAILED');self.assertEqual(phase['exception_type'],'C_EXCEPTION_TYPE_UNAVAILABLE')

    def test_other_caller_existing_profiler_and_foreign_replacement_are_preserved(self):
        import sys
        from superfish_ng.curved_rf_goal_efficiency_observation import observe_adjoint_linear_solves
        factor=splu(csc_matrix([[2.]]))
        def selected():return factor.solve(np.ones(1))
        def outside():return factor.solve(np.ones(1))
        recorder=PhaseRecorder();previous=sys.getprofile();foreign=lambda *args:None
        try:
            with observe_adjoint_linear_solves(recorder,callers=[selected]):outside()
            self.assertEqual(recorder.finish()['phases'],[])
            sys.setprofile(foreign)
            with self.assertRaises(ValueError):
                with observe_adjoint_linear_solves(PhaseRecorder()):self.fail('existing profiler must be retained')
            self.assertIs(sys.getprofile(),foreign);sys.setprofile(None)
            with self.assertRaisesRegex(ValueError,'changed outside'):
                with observe_adjoint_linear_solves(PhaseRecorder()):sys.setprofile(foreign)
            self.assertIs(sys.getprofile(),foreign)
        finally:sys.setprofile(previous)

    def test_full_adjoint_matches_unobserved_and_complete_spectral_invariant(self):
        from test_curved_rf_adjoint import CurvedRFAdjointTests
        from superfish_ng.curved_rf_goal_efficiency_worker import observation_bindings
        fixture=CurvedRFAdjointTests();solution=fixture.solution();expected=adjoint.r_over_q_adjoint(solution)
        recorder=PhaseRecorder()
        from superfish_ng.curved_rf_goal_efficiency_observation import observe_adjoint_linear_solves
        with observe_adjoint_linear_solves(recorder),observe_selected_calls(recorder,observation_bindings()):actual=adjoint.r_over_q_adjoint(solution)
        for name in ('accelerator_adjoint','circuit_adjoint'):np.testing.assert_array_equal(getattr(actual,name),getattr(expected,name))
        self.assertEqual(actual.accelerator_lagrange_multiplier,expected.accelerator_lagrange_multiplier)
        self.assertLess(actual.relative_gauge_error,1e-12)
        phases=recorder.finish()['phases'];self.assertEqual(sum(p['name']=='adjoint_linear_solve' for p in phases),1)
        self.assertEqual(sum(p['name']=='adjoint_factorization' for p in phases),1)

    def test_production_scope_profiles_only_the_original_adjoint_call_and_restores_aliases(self):
        import sys
        from superfish_ng import curved_rf_goal_indicator as indicator
        from superfish_ng.curved_rf_goal_efficiency_observation import observe_adjoint_linear_solves
        originals=(adjoint.r_over_q_adjoint,indicator.r_over_q_adjoint);seen=[];sentinel=object()
        def original(*args,**kwargs):seen.append(sys.getprofile());return sentinel
        with patch.object(adjoint,'r_over_q_adjoint',original),patch.object(indicator,'r_over_q_adjoint',original):
            with observe_adjoint_linear_solves(PhaseRecorder()):
                self.assertIsNone(sys.getprofile())
                self.assertIs(adjoint.r_over_q_adjoint(),sentinel)
                self.assertIsNone(sys.getprofile())
                self.assertIs(indicator.r_over_q_adjoint(),sentinel)
            self.assertIs(adjoint.r_over_q_adjoint,original);self.assertIs(indicator.r_over_q_adjoint,original)
        self.assertTrue(all(callable(v) for v in seen));self.assertEqual(len(seen),2)
        self.assertEqual((adjoint.r_over_q_adjoint,indicator.r_over_q_adjoint),originals)


class RFGoalJournalPublicationTests(unittest.TestCase):
    def test_complete_journal_is_exclusive_and_failed_link_keeps_staged_evidence(self):
        from superfish_ng.curved_rf_goal_efficiency_worker import _write
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'checkpoint.json';_write(path,dict(answer=42))
            before=path.read_bytes();self.assertEqual(json.loads(before),dict(answer=42));self.assertEqual(list(root.iterdir()),[path])
            with self.assertRaises(FileExistsError):_write(path,{})
            self.assertEqual(path.read_bytes(),before)
            with patch('superfish_ng.curved_rf_goal_efficiency_io.os.link',side_effect=OSError('disk publication failed')):
                with self.assertRaises(OSError):_write(root/'next.json',dict(next=1))
            self.assertFalse((root/'next.json').exists());staged=list(root.glob('.*/*'));self.assertEqual(len(staged),1)
            self.assertEqual(json.loads(staged[0].read_text()),dict(next=1))

    def test_partial_json_is_not_published_and_original_exception_survives(self):
        from superfish_ng.curved_rf_goal_efficiency_worker import _write
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'checkpoint-001.json';error=KeyboardInterrupt('during serialization')
            def fail(value,stream,**kwargs):stream.write('{"partial":');raise error
            with patch('json.dump',fail),self.assertRaises(KeyboardInterrupt) as caught:_write(path,{'value':1})
            self.assertIs(caught.exception,error);self.assertFalse(path.exists())
            partials=list(Path(tmp).glob('.*/*'));self.assertEqual(len(partials),1)
            self.assertEqual(partials[0].read_text(),'{"partial":')

    def test_reporting_failure_does_not_hide_original_and_resume_plan_index_is_correct(self):
        from superfish_ng import curved_rf_goal_efficiency_worker as worker
        from superfish_ng.curved_rf_goal_efficiency_plan import build_curved_rf_goal_efficiency_plan,request_for_curved_rf_goal_efficiency_execution
        row=build_curved_rf_goal_efficiency_plan()['executions'][0];request=request_for_curved_rf_goal_efficiency_execution(row)
        original=KeyboardInterrupt('original initial plan interruption')
        def interrupt(*args,**kwargs):raise original
        def reporting_failure(*args,**kwargs):raise OSError('failure reporting unavailable')
        def no_solve(*args,**kwargs):self.fail('no FEM after initial plan interruption')
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(worker.curved,'next_plan',interrupt),patch.object(worker,'_write',reporting_failure):
                with self.assertRaises(KeyboardInterrupt) as caught:
                    worker._execute_worker_events(row,request,Path(tmp)/'new',{},PhaseRecorder(),{})
                self.assertIs(caught.exception,original);self.assertIn('failure recording also failed',caught.exception.__notes__[-1])
            prefix=dict(events=[{}],level_runs=['/original'],observations=[{}],native_sources=[{}],public_checkpoint=None,
                        event_records=[dict(samples=[],initial_independent_identity=[dict(passed=True)])])
            origin=dict(journal_path='/original/checkpoint-001.json',journal_sha256='1'*64)
            with patch.object(worker,'read_solution',interrupt),patch.object(worker.native,'solve',no_solve):
                with self.assertRaises(KeyboardInterrupt):
                    worker._execute_worker_events(row,request,Path(tmp)/'resumed',{},PhaseRecorder(),{},prefix=prefix,resume_origin=origin)
            failure=json.loads((Path(tmp)/'resumed/failure.json').read_text())
            self.assertEqual(failure['event_index'],1);self.assertEqual(failure['active_stage'],'initial_plan')
            self.assertEqual(failure['checkpoint_level_runs'],['/original'])
            self.assertEqual(failure['last_complete_checkpoint'],dict(path=origin['journal_path'],sha256=origin['journal_sha256']))


class RFGoalObservationVersionTests(unittest.TestCase):
    def test_declared_new_observation_cannot_omit_c_solve_after_factorization(self):
        from superfish_ng.curved_rf_goal_efficiency_saved import _verify_costs
        from superfish_ng.curved_rf_goal_efficiency_worker import _prefix_cost
        for observed in (False,True):
            clock=iter(range(100));r=PhaseRecorder(clock=lambda:next(clock),rss_reader=lambda:1024)
            with r.phase('initial_plan'):pass
            with r.phase('native_event'):
                with r.phase('rf_adjoint'):
                    with r.phase('adjoint_factorization'):pass
                    if observed:
                        with r.phase('adjoint_linear_solve'):pass
            with r.phase('independent_accuracy_and_parent_changes'):pass
            doc=dict(observation_schema_version=2,event_records=[dict(observed_prefix_cost=_prefix_cost(r,None))],observed_cost=r.finish())
            if observed:self.assertEqual(_verify_costs(doc),'STRUCTURE_VERIFIED_NOT_REMEASURED')
            else:
                with self.assertRaises(ValueError):_verify_costs(doc)
                doc.pop('observation_schema_version')
                self.assertEqual(_verify_costs(doc),'STRUCTURE_VERIFIED_NOT_REMEASURED')


if __name__=='__main__':unittest.main()
