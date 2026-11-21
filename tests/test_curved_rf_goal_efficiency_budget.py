# SPDX-License-Identifier: Apache-2.0
"""Budget refusal is a measured non-success, never an omitted failed phase."""
from copy import deepcopy
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from superfish_ng.adaptive_efficiency_timing import PhaseRecorder
from superfish_ng.curved_rf_goal_efficiency_saved import _verify_costs


class RFGoalBudgetCostTests(unittest.TestCase):
    def document(self, *, initial=False, root='next_uniform_plan', failure_name='refinement_and_quality', caught_inside=False):
        from superfish_ng.curved_rf_goal_efficiency_worker import _prefix_cost
        clock=iter(range(100));r=PhaseRecorder(clock=lambda:next(clock),rss_reader=lambda:1024);records=[]
        if not initial:
            with r.phase('initial_plan'):pass
            if root!='native_event':
                with r.phase('native_event'):pass
                with r.phase('independent_accuracy_and_parent_changes'):pass
                records=[dict(observed_prefix_cost=_prefix_cost(r,None))]
        try:
            with r.phase(root):
                try:
                    with r.phase(failure_name):raise ValueError('uniform refinement exceeds max_triangles')
                except ValueError:
                    if not caught_inside:raise
        except ValueError:pass
        if root=='native_event' and not initial:
            with r.phase('independent_accuracy_and_parent_changes'):pass
            records=[dict(observed_prefix_cost=_prefix_cost(r,None))]
        return dict(status='REFINEMENT_LIMIT',stop_reason='uniform refinement exceeds max_triangles',
                    event_records=records,observed_cost=r.finish())

    def test_caught_budget_costs_retain_failed_phases_and_exact_elapsed_values(self):
        for initial,root,caught in [(False,'next_uniform_plan',False),(True,'initial_plan',False),
                                    (False,'complete_public_replay',True),(False,'native_event',True)]:
            # Public assembly catches its own planning exception: its outer
            # replay/event phase completes while the actual guard stays FAILED.
            d=self.document(initial=initial,root=root,caught_inside=caught)
            before=deepcopy(d)
            self.assertEqual(_verify_costs(d),'STRUCTURE_VERIFIED_WITH_CAUGHT_BUDGET_FAILURE_NOT_REMEASURED')
            self.assertEqual(d,before);self.assertEqual(d['observed_cost']['status'],'FAILED')
        for status in ('PAUSED','TARGETS_MET','LEVEL_LIMIT'):
            bad=self.document();bad['status']=status
            with self.subTest(status=status),self.assertRaises(ValueError):_verify_costs(bad)
        for root,leaf in [('reference_verification','refinement_and_quality'),('next_uniform_plan','eigenproblem')]:
            with self.subTest(root=root,leaf=leaf),self.assertRaises(ValueError):_verify_costs(self.document(root=root,failure_name=leaf))
        bad=self.document();bad['observed_cost']['phases'][-1]['exception_type']='RuntimeError'
        with self.assertRaises(ValueError):_verify_costs(bad)
        bad=self.document();bad['observed_cost']['status']='COMPLETE'
        with self.assertRaises(ValueError):_verify_costs(bad)
        for root in ('native_event','complete_public_replay'):
            with self.subTest(uncaught_root=root),self.assertRaises(ValueError):_verify_costs(self.document(root=root))


class RFGoalBudgetGeometryTests(unittest.TestCase):
    def test_uniform_four_way_restriction_refuses_before_allocating_over_budget(self):
        from superfish_ng.config import Case
        from superfish_ng.curved_refinement_steps import CurvedRefinementStep
        from superfish_ng.mesh import make_mesh
        from superfish_ng.curved_space import curved_space
        from superfish_ng import curved_adaptive_refinement as curved
        case=Case.load(Path(__file__).resolve().parents[1]/'examples/curved_ellipse.json')
        space=curved_space(case,make_mesh(case));count=len(space.geometry.cell_nodes)
        original=space.geometry.points_rz_m.copy()
        with patch.object(curved,'refine_curved_space') as refine:
            with self.assertRaisesRegex(ValueError,'max_triangles'):
                curved._apply(space,CurvedRefinementStep('uniform'),4*count-1)
            refine.assert_not_called()
        refined=curved._apply(space,CurvedRefinementStep('uniform'),4*count)
        self.assertEqual(len(refined.geometry.cell_nodes),4*count)
        self.assertTrue((space.geometry.points_rz_m==original).all())


class RFGoalBudgetResumeTests(unittest.TestCase):
    def test_equal_prefix_requires_terminal_initial_stop_and_paused_parent(self):
        from superfish_ng.completion import digest
        from superfish_ng.curved_rf_goal_efficiency_resume import _origin_metadata,verify_resume_origin
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'parent.json'
            parent=dict(status='PAUSED',execution={},request={},reference_bound_inputs={},observed_cost={},
                        events=[dict(index=0)],level_runs=['/original'],native_sources=[{}],event_records=[{}],observations=[{}])
            path.write_text(json.dumps(parent))
            origin=dict(journal_path=str(path),journal_sha256=digest(path),event_count=1,implementation_aliases={},interruption_files={})
            document=dict(deepcopy(parent),status='REFINEMENT_LIMIT',resume_origin=origin,planning_stop=dict(stage='initial_resume_plan'))
            with self.assertRaises(ValueError):_origin_metadata(origin,1)
            _origin_metadata(origin,1,terminal_without_new_events=True)
            with self.assertRaises(ValueError):_origin_metadata(origin,0,terminal_without_new_events=True)
            with patch('superfish_ng.curved_rf_goal_efficiency_resume.read_curved_rf_goal_efficiency',return_value=dict(document=parent,bound_inputs={})) as read:
                self.assertEqual(verify_resume_origin(document),{str(path):digest(path)})
                for status,stage in [('PAUSED','initial_resume_plan'),('TARGETS_MET','initial_resume_plan'),('REFINEMENT_LIMIT','next_uniform_plan')]:
                    bad=deepcopy(document);bad.update(status=status,planning_stop=dict(stage=stage))
                    with self.subTest(status=status,stage=stage),self.assertRaises(ValueError):verify_resume_origin(bad)
                # An equal-length child can never recurse to another terminal child.
                path.write_text(json.dumps(dict(parent,status='REFINEMENT_LIMIT')))
                bad=deepcopy(document);bad['resume_origin']['journal_sha256']=digest(path)
                read.reset_mock()
                with self.assertRaisesRegex(ValueError,'PAUSED before recursive'):verify_resume_origin(bad)
                read.assert_not_called()


if __name__=='__main__':unittest.main()
