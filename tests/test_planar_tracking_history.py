# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from superfish_ng.planar import PlanarCase,solve_planar
from superfish_ng.planar_saved import save_planar_run
from superfish_ng.planar_tracking import PlanarTrackingRequest
from superfish_ng.planar_tracking_jobs import execute_planar_tracking
from superfish_ng.planar_tracking_history import PlanarTrackingHistoryRequest,verify_planar_history_steps


class PlanarTrackingHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory();cls.root=Path(cls.temporary.name)
        for name,width in [('left',.18),('square',.2),('right',.22)]:
            case=PlanarCase(width,.2,nx=6,ny=6,element_order=2,modes=3)
            save_planar_run(case,solve_planar(case),cls.root/name)
        execute_planar_tracking(cls.root/'left',cls.root/'square',PlanarTrackingRequest(),cls.root/'merge')
        groups=[dict(indices=[1,2],ids=['mode-1','mode-2'])]
        execute_planar_tracking(cls.root/'square',cls.root/'right',PlanarTrackingRequest(2,2,None,groups),cls.root/'split')
        execute_planar_tracking(cls.root/'left',cls.root/'right',PlanarTrackingRequest(),cls.root/'cross')
        execute_planar_tracking(cls.root/'right',cls.root/'right',PlanarTrackingRequest(2,1,None,groups),cls.root/'unverified')
        # Each of these pairs passes by itself but would falsify the prior history.
        execute_planar_tracking(cls.root/'square',cls.root/'right',PlanarTrackingRequest(2,2,['new-a','new-b']),cls.root/'relabel')
        execute_planar_tracking(cls.root/'square',cls.root/'right',PlanarTrackingRequest(1,1,['a']),cls.root/'trim')

    @classmethod
    def tearDownClass(cls):cls.temporary.cleanup()

    def verify(self,*names):
        return verify_planar_history_steps([self.root/name for name in names],PlanarTrackingHistoryRequest(len(names)))

    def test_strict_request_roundtrip_and_step_budget(self):
        request=PlanarTrackingHistoryRequest(2,3);self.assertEqual(request,PlanarTrackingHistoryRequest.from_dict(request.to_dict()))
        for values in ((0,3),(True,3),(2,False),(4,3)):
            with self.assertRaises(ValueError):PlanarTrackingHistoryRequest(*values)
        for change in ({'history_version':True},{'extra':1},{'max_steps':'3'}):
            with self.assertRaises(ValueError):PlanarTrackingHistoryRequest.from_dict({**request.to_dict(),**change})
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'request.json';request.save(path);self.assertEqual(PlanarTrackingHistoryRequest.load(path),request)
            with self.assertRaises(FileExistsError):request.save(path)
        with self.assertRaisesRegex(ValueError,'step_count'):verify_planar_history_steps([],request)

    def test_subspace_continuity_retains_identity_set(self):
        result=self.verify('merge','split');self.assertEqual(result['status'],'PASS');self.assertTrue(result['can_extend'])
        self.assertFalse(result['individual_ids_complete']);self.assertEqual(result['current_mode_ids'],[None,None])
        self.assertEqual(result['current_identity_groups'],[dict(indices=[1,2],ids=['mode-1','mode-2'])])
        self.assertEqual(len(result['step_sha256']),2)

    def test_individually_passed_pairs_are_not_sufficient(self):
        self.assertEqual(self.verify('cross')['status'],'PASS');self.assertEqual(self.verify('merge')['status'],'PASS')
        with self.assertRaisesRegex(ValueError,'native spectrum'):self.verify('cross','merge')
        with self.assertRaisesRegex(ValueError,'individual IDs'):self.verify('merge','relabel')
        with self.assertRaisesRegex(ValueError,'band count'):self.verify('merge','trim')

    def test_unverified_final_pair_is_retained_and_blocks_extension(self):
        result=self.verify('merge','split','unverified');self.assertEqual(result['status'],'UNVERIFIED');self.assertFalse(result['can_extend'])
        self.assertIsNone(result['current_identity_groups']);self.assertEqual(len(result['steps']),3)
        with self.assertRaisesRegex(ValueError,'after an UNVERIFIED'):self.verify('merge','split','unverified','unverified')

    def test_ancestor_change_during_later_replay_is_rejected(self):
        from superfish_ng import planar_tracking_history as module
        original=module.read_planar_tracking;path=self.root/'merge/job.json';raw=path.read_bytes()
        def changing(directory):
            result=original(directory)
            if Path(directory).name=='split':
                data=json.loads(raw);data['stage']='changed ancestor';path.write_text(json.dumps(data))
            return result
        try:
            with patch.object(module,'read_planar_tracking',side_effect=changing),self.assertRaisesRegex(ValueError,'ancestry changed'):
                self.verify('merge','split')
        finally:path.write_bytes(raw)
