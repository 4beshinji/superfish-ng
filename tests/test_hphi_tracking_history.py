# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from superfish_ng.hphi_native import save_hphi_run
from superfish_ng.hphi_tracking_jobs import execute_hphi_tracking
from superfish_ng.hphi_tracking_history import HphiTrackingHistoryRequest,verify_hphi_history_steps
from test_hphi_tracking import pair


def fixture(root):
    (a,b),q=pair()
    for name,solution in (('a',a),('b',b)):save_hphi_run(solution.case,solution,root/name)
    reverse=replace(q,previous_comparison_mesh=q.current_comparison_mesh,current_comparison_mesh=q.previous_comparison_mesh)
    groups=[dict(indices=[1,2],ids=['mode-1','mode-2'])]
    for name,left,right,request in (
            ('forward','a','b',q),('reverse','b','a',reverse),
            ('group','a','b',replace(q,previous_mode_ids=None,previous_identity_groups=groups)),
            ('group-back','b','a',replace(reverse,previous_mode_ids=None,previous_identity_groups=groups)),
            ('unverified','b','a',replace(reverse,controls=replace(reverse.controls,minimum_overlap=1.)))):
        execute_hphi_tracking(root/left,root/right,request,root/name)
    return a,b,q,reverse


class HphiTrackingHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory();cls.root=Path(cls.temporary.name);fixture(cls.root)
    @classmethod
    def tearDownClass(cls):cls.temporary.cleanup()
    def verify(self,*names):return verify_hphi_history_steps([self.root/name for name in names],HphiTrackingHistoryRequest(len(names)))

    def test_strict_request_and_history_budget(self):
        q=HphiTrackingHistoryRequest(2,3);self.assertEqual(HphiTrackingHistoryRequest.from_dict(q.to_dict()),q)
        for args in ((0,1),(True,3),(2,False),(4,3)):
            with self.assertRaises(ValueError):HphiTrackingHistoryRequest(*args)
        for change in ({'history_version':True},{'extra':0},{'max_steps':'3'}):
            with self.assertRaises(ValueError):HphiTrackingHistoryRequest.from_dict({**q.to_dict(),**change})
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'request.json';q.save(path);self.assertEqual(HphiTrackingHistoryRequest.load(path),q)
            with self.assertRaises(FileExistsError):q.save(path)
        with self.assertRaises(ValueError):verify_hphi_history_steps([],q)

    def test_native_spectrum_and_identity_continuity(self):
        result=self.verify('forward','reverse');self.assertEqual(result['current_mode_ids'],['mode-1','mode-2']);self.assertTrue(result['can_extend'])
        with self.assertRaisesRegex(ValueError,'native spectrum'):self.verify('forward','forward')
        # The grouped step passes independently, but its basis IDs cannot be
        # reconstructed from a later individually labelled reverse comparison.
        with self.assertRaisesRegex(ValueError,'individual IDs'):self.verify('group','reverse')

    def test_group_continuation_unverified_stop_and_step_limit(self):
        grouped=self.verify('group','group-back');self.assertEqual(grouped['status'],'PASS');self.assertEqual(grouped['current_mode_ids'],[None,None]);self.assertEqual(grouped['current_identity_groups'],[dict(indices=[1,2],ids=['mode-1','mode-2'])])
        stopped=self.verify('forward','unverified');self.assertEqual(stopped['status'],'UNVERIFIED');self.assertFalse(stopped['can_extend']);self.assertIsNone(stopped['current_identity_groups'])
        with self.assertRaisesRegex(ValueError,'after an UNVERIFIED'):self.verify('forward','unverified','forward')
        limited=verify_hphi_history_steps([self.root/'forward'],HphiTrackingHistoryRequest(1,1));self.assertEqual(limited['status'],'PASS');self.assertFalse(limited['can_extend']);self.assertIn('max_steps',limited['stop_reason'])

    def test_ancestor_mutation_during_later_replay_is_rejected(self):
        from superfish_ng import hphi_tracking_history as module
        read=module.read_hphi_tracking;path=self.root/'forward/job.json';raw=path.read_bytes()
        def changing(directory):
            result=read(directory)
            if Path(directory).name=='reverse':
                value=json.loads(raw);value['stage']='changed';path.write_text(json.dumps(value))
            return result
        try:
            with patch.object(module,'read_hphi_tracking',side_effect=changing),self.assertRaisesRegex(ValueError,'ancestry changed'):self.verify('forward','reverse')
        finally:path.write_bytes(raw)
