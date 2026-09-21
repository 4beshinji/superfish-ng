# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from pathlib import Path
from copy import deepcopy
import json,tempfile,unittest
import numpy as np
from test_curved_hphi_tracking_crossing import coax
from test_curved_hphi_tracking import request
from superfish_ng.curved_hphi import solve_curved_hphi
from superfish_ng.hphi_native import save_hphi_run
from superfish_ng.curved_hphi_tracking_jobs import execute_curved_hphi_tracking
from superfish_ng.curved_hphi_identity_recovery import CurvedHphiIdentityRecoveryRequest
from superfish_ng.curved_hphi_tracking_history import CurvedHphiTrackingHistoryRequest,verify_curved_hphi_history_steps
from superfish_ng.curved_hphi_tracking_history_saved import execute_curved_hphi_history,read_curved_hphi_history
from superfish_ng.jobs import JobManager


class CurvedHphiHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)
        a,b=[solve_curved_hphi(coax(length,shear=1/64)) for length in (.05859375,.0703125)]
        for name,s in (('a',a),('b',b)):save_hphi_run(s.case,s,cls.root/name)
        cls.comparison=replace(request(a,b,'declared_quadratic'),previous_mode_ids=['radial','TEM'])
        grouped=replace(cls.comparison,controls=replace(cls.comparison.controls,relative_cluster_gap=.15))
        reverse=replace(request(b,a,'declared_quadratic'),previous_mode_ids=['TEM','radial'])
        cls.first=execute_curved_hphi_tracking(cls.root/'a',cls.root/'b',grouped,cls.root/'enter')
        execute_curved_hphi_tracking(cls.root/'b',cls.root/'a',reverse,cls.root/'continue')
        cls.placement=dict(after_step_index=0,request=CurvedHphiIdentityRecoveryRequest(0,cls.comparison).to_dict())
        # Independent approximate TEM shape in the declared small quadratic shear.
        for solution,rank in ((a,1),(b,0)):
            r,z=solution.space.dof_points.T
            length=.05859375 if rank==1 else .0703125
            exact=np.cos(np.pi*(z-r*r/64)/length);actual=solution.coefficients[:,rank];mass=solution.mass
            overlap=abs(actual@(mass@exact))/np.sqrt((actual@(mass@actual))*(exact@(mass@exact)))
            if overlap<=.999:raise AssertionError('TEM-like physical branch is not independently resolved')

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def history_request(self,n=1):return CurvedHphiTrackingHistoryRequest(n,3,[self.placement])

    def test_owned_recovery_extension_and_source_move(self):
        self.assertEqual(self.first['status'],'PASS');self.assertFalse(self.first['individual_ids_complete'])
        paths=[self.root/'enter',self.root/'continue']
        with self.assertRaisesRegex(ValueError,'individual IDs'):
            verify_curved_hphi_history_steps(paths,CurvedHphiTrackingHistoryRequest(2))
        history=self.root/'history';result=execute_curved_hphi_history(paths[:1],self.history_request(),history)
        self.assertEqual(result['current_mode_ids'],['TEM','radial'])
        self.assertTrue(result['can_extend'])
        event=result['identity_recoveries'][0]
        self.assertEqual(event['status'],'PASS')
        self.assertEqual(event['anchor_native_sha256'],{k.removeprefix('previous/solution/'):v for k,v in result['step_sha256'][0].items() if k.startswith('previous/solution/')})
        (self.root/'enter').rename(self.root/'enter-moved')
        try:
            self.assertEqual(read_curved_hphi_history(history),result)
            manager=JobManager(self.root/'workers')
            try:
                identifier=manager.extend_curved_hphi_history(history,self.root/'continue')
                self.assertEqual(manager.processes[identifier].wait(timeout=600),0)
                directory=manager.directory(identifier)
                final=read_curved_hphi_history(directory)
                self.assertEqual(final['current_mode_ids'],['radial','TEM'])
                self.assertEqual(final['identity_recoveries'],result['identity_recoveries'])
                for path in (history/'step-0000').rglob('*'):
                    if path.is_file():self.assertEqual(path.read_bytes(),(directory/'step-0000'/path.relative_to(history/'step-0000')).read_bytes())
            finally:manager.close()
            manager=JobManager(self.root/'workers')
            try:self.assertEqual(manager.status(identifier,verify=True)['status'],'complete')
            finally:manager.close()
            path=history/'history-results.json';raw=path.read_bytes();bad=json.loads(raw)
            bad['identity_recoveries'][0]['assessment']['current_mode_ids'].reverse();path.write_text(json.dumps(bad))
            try:
                with self.assertRaises(ValueError):read_curved_hphi_history(history)
            finally:path.write_bytes(raw)
        finally:(self.root/'enter-moved').rename(self.root/'enter')

    def test_strict_anchor_and_guard_refusal(self):
        raw=self.history_request().to_dict()
        self.assertEqual(CurvedHphiTrackingHistoryRequest.from_dict(raw).to_dict(),raw)
        for change in ({'history_version':True},{'recoveries':None},{'recoveries':[]},{'recoveries':[self.placement,self.placement]}):
            with self.assertRaises(ValueError):CurvedHphiTrackingHistoryRequest.from_dict({**raw,**change})
        future=deepcopy(self.placement);future['request']['anchor_snapshot_index']=1
        with self.assertRaises(ValueError):CurvedHphiTrackingHistoryRequest(1,3,[future])
        wrong=deepcopy(self.placement);wrong['request']['comparison']['previous_mode_ids']=['TEM','radial']
        with self.assertRaisesRegex(ValueError,'anchor IDs differ'):
            verify_curved_hphi_history_steps([self.root/'enter'],CurvedHphiTrackingHistoryRequest(1,3,[wrong]))
        bad=deepcopy(self.placement);bad['request']['comparison']['controls']['relative_cluster_gap']=.9
        result=verify_curved_hphi_history_steps([self.root/'enter'],CurvedHphiTrackingHistoryRequest(1,3,[bad]))
        self.assertEqual(result['status'],'UNVERIFIED');self.assertFalse(result['can_extend'])
        with self.assertRaisesRegex(ValueError,'UNVERIFIED'):
            verify_curved_hphi_history_steps([self.root/'enter',self.root/'continue'],CurvedHphiTrackingHistoryRequest(2,3,[bad]))

    def test_native_continuity_and_unrecovered_group_budget(self):
        limited=verify_curved_hphi_history_steps([self.root/'enter'],CurvedHphiTrackingHistoryRequest(1,1))
        self.assertEqual(limited['status'],'PASS');self.assertFalse(limited['can_extend'])
        self.assertFalse(limited['individual_ids_complete'])
        self.assertEqual(limited['current_mode_ids'],[None,None])
        self.assertEqual(limited['current_identity_groups'],[dict(indices=[1,2],ids=['TEM','radial'])])
        with self.assertRaisesRegex(ValueError,'native spectrum'):
            verify_curved_hphi_history_steps([self.root/'enter',self.root/'enter'],CurvedHphiTrackingHistoryRequest(2))
