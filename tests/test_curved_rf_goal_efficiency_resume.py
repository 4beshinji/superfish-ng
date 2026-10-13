# SPDX-License-Identifier: Apache-2.0
"""Resume must verify the original prefix before starting another native solve."""
from pathlib import Path
from copy import deepcopy
import json
import tempfile
import unittest
from unittest.mock import patch

from superfish_ng.curved_rf_goal_efficiency_resume import resume_curved_rf_goal_efficiency_worker
from superfish_ng.curved_rf_goal_efficiency_resume import verify_resume_origin,_verify_interruption
from superfish_ng.completion import digest


class RFGoalResumeInputTests(unittest.TestCase):
    def test_raw_nonobject_and_versioned_archives_are_strict(self):
        from superfish_ng.curved_rf_goal_efficiency_saved import _preflight,_implementation_sources
        from superfish_ng.jobs import _implementation_hashes
        for bad in (None,[],1,True,'journal'):
            with self.subTest(value=bad),self.assertRaises(ValueError):_preflight(bad)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'old.py';path.write_text('raise AssertionError("source archive must not execute")\n')
            sources=_implementation_hashes();sources['curved_rf_goal_efficiency_saved.py']=digest(path)
            bound=_implementation_sources(sources,archives={digest(path):str(path)})
            self.assertEqual(bound[str(path)],digest(path))
            for invalid in ({'wrong':str(path)},{digest(path):'relative.py'},{'0'*64:str(path)}):
                with self.subTest(invalid=invalid),self.assertRaises(ValueError):_implementation_sources(sources,archives=invalid)

    def test_bad_limit_existing_output_and_missing_original_hash_do_not_solve(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/'new'
            with patch('superfish_ng.curved_rf_adaptive_refinement.solve') as solve:
                for limit in (True,0,1.5):
                    with self.assertRaises(ValueError):
                        resume_curved_rf_goal_efficiency_worker('/missing',out,expected_sha256='0'*64,max_new_events=limit)
                with self.assertRaises(FileExistsError):
                    resume_curved_rf_goal_efficiency_worker('/missing',root,expected_sha256='0'*64)
                with self.assertRaises(ValueError):
                    resume_curved_rf_goal_efficiency_worker('/missing',out,expected_sha256='0'*64)
                solve.assert_not_called()
            self.assertFalse(out.exists())

    def test_original_prefix_cannot_be_rewritten_or_terminal_success_resumed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'result.json'
            parent=dict(status='PAUSED',execution={},request={},reference_bound_inputs={},observed_cost={},
                        events=[dict(index=0)],level_runs=['/original'],native_sources=[{}],event_records=[{}],observations=[{}])
            path.write_text(json.dumps(parent))
            document=deepcopy(parent)
            for name in ('events','level_runs','native_sources','event_records','observations'):document[name].append({})
            document['resume_origin']=dict(journal_path=str(path),journal_sha256=digest(path),event_count=1,implementation_aliases={},interruption_files={})
            with patch('superfish_ng.curved_rf_goal_efficiency_resume.read_curved_rf_goal_efficiency',return_value=dict(document=parent,bound_inputs={})):
                self.assertEqual(verify_resume_origin(document),{str(path):digest(path)})
                for field in ('events','level_runs','native_sources','event_records','observations'):
                    bad=deepcopy(document);bad[field][0]='changed'
                    with self.subTest(field=field),self.assertRaises(ValueError):verify_resume_origin(bad)
                parent['status']='TARGETS_MET'
                with self.assertRaises(ValueError):verify_resume_origin(document)

    def test_interrupt_requires_original_partial_costs_and_terminal_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);failure=root/'failure.json';process=root/'process.json'
            failure.write_text(json.dumps(dict(status='FAILED',error_type='KeyboardInterrupt',preceding_level_runs=['/first'],native_solves_attempted=2,native_solves_completed=1,observed_cost=dict(status='FAILED'))))
            process.write_text(json.dumps(dict(document_type='adaptive_efficiency_process_cost',status='PROCESS_FAILED',exit_code=-2)))
            parent=dict(level_runs=['/first']);origin=dict(journal_path=str(root/'checkpoint-001.json'),event_count=1,interruption_files={str(p):digest(p) for p in (failure,process)})
            bound={};_verify_interruption(parent,origin,bound);self.assertEqual(bound,origin['interruption_files'])
            for bad in ({}, {str(failure):digest(failure)}):
                with self.assertRaises(ValueError):_verify_interruption(parent,dict(origin,interruption_files=bad),{})
            process.write_text(json.dumps(dict(document_type='adaptive_efficiency_process_cost',status='PROCESS_EXITED',exit_code=0)))
            origin['interruption_files'][str(process)]=digest(process)
            with self.assertRaises(ValueError):_verify_interruption(parent,origin,{})


if __name__=='__main__':unittest.main()
