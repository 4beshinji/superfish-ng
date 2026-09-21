# SPDX-License-Identifier: Apache-2.0
"""Owned history identities follow independently identified coaxial branches."""
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from superfish_ng.hphi_native import save_hphi_run
from superfish_ng.hphi_tracking import HphiTrackingRequest
from superfish_ng.hphi_geometry_mapping import coaxial_dimension_mapping
from superfish_ng.hphi_identity_recovery import HphiIdentityRecoveryRequest
from superfish_ng.hphi_tracking_history import HphiTrackingHistoryRequest, verify_hphi_history_steps
from superfish_ng.hphi_tracking_history_saved import execute_hphi_history, read_hphi_history, extend_hphi_history
from superfish_ng.hphi_tracking_jobs import execute_hphi_tracking
import test_hphi_identity_recovery as reference


class HphiRecoveredHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
        reference.HphiIdentityRecoveryTests.setUpClass()
        fixture=reference.HphiIdentityRecoveryTests
        a,d,c=fixture.solutions
        for name,solution in (('anchor',a),('degenerate',d),('current',c)):
            save_hphi_run(solution.case,solution,cls.root/name)
        first=HphiTrackingRequest(fixture.meshes[0],fixture.meshes[1],previous_mode_ids=['TEM','radial'],
            geometry_mapping=coaxial_dimension_mapping(a.case,d.case))
        second=replace(fixture.inherited,geometry_mapping=fixture.inherited_map)
        final=HphiTrackingRequest(fixture.meshes[2],fixture.meshes[0],previous_mode_ids=['radial','TEM'],
            geometry_mapping=coaxial_dimension_mapping(c.case,a.case))
        for name,left,right,request in (('enter','anchor','degenerate',first),('leave','degenerate','current',second),
                                        ('continue','current','anchor',final)):
            execute_hphi_tracking(cls.root/left,cls.root/right,request,cls.root/name)
        cls.placement=dict(after_step_index=1,request=HphiIdentityRecoveryRequest(0,fixture.comparison,fixture.anchor_map).to_dict())

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def request(self,count=2):return HphiTrackingHistoryRequest(count,5,[self.placement])

    def test_recovery_binds_prior_native_and_allows_only_recovered_continuation(self):
        paths=[self.root/name for name in ('enter','leave','continue')]
        with self.assertRaisesRegex(ValueError,'individual IDs'):
            verify_hphi_history_steps(paths,HphiTrackingHistoryRequest(3))
        result=verify_hphi_history_steps(paths,self.request(3))
        self.assertEqual(result['status'],'PASS')
        self.assertEqual(result['current_mode_ids'],['TEM','radial'])
        event=result['identity_recoveries'][0]
        self.assertEqual(event['assessment']['current_mode_ids'],['radial','TEM'])
        self.assertEqual(event['anchor_native_sha256'],{k.removeprefix('previous/solution/'):v
            for k,v in result['step_sha256'][0].items() if k.startswith('previous/solution/')})
        wrong=json.loads(json.dumps(self.placement))
        wrong['request']['comparison']['previous_mode_ids']=['radial','TEM']
        with self.assertRaisesRegex(ValueError,'anchor IDs differ'):
            verify_hphi_history_steps(paths[:2],HphiTrackingHistoryRequest(2,5,[wrong]))
        future=json.loads(json.dumps(self.placement));future['request']['anchor_snapshot_index']=1
        with self.assertRaisesRegex(ValueError,'anchor lacks verified individual IDs'):
            verify_hphi_history_steps(paths[:2],HphiTrackingHistoryRequest(2,5,[future]))

    def test_cli_owned_replay_and_extension_preserve_recovery_after_source_move(self):
        from superfish_ng.cli import main
        request=self.request();request.save(self.root/'history-request.json')
        history=self.root/'history'
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(['execute-hphi-history',str(self.root/'history-request.json'),
                '--steps',str(self.root/'enter'),str(self.root/'leave'),'--out',str(history)]),0)
        first=read_hphi_history(history)
        self.assertEqual(first['current_mode_ids'],['radial','TEM'])
        for name in ('enter','leave'):(self.root/name).rename(self.root/(name+'-moved'))
        try:
            with redirect_stdout(io.StringIO()) as stream:
                self.assertEqual(main(['replay-hphi-history',str(history)]),0)
            self.assertEqual(json.loads(stream.getvalue()),first)
            from superfish_ng.jobs import JobManager
            manager=JobManager(self.root/'workers')
            try:
                identifier=manager.extend_hphi_history(history,self.root/'continue')
                self.assertEqual(manager.processes[identifier].wait(timeout=600),0)
                extended=manager.directory(identifier)
                final=read_hphi_history(extended)
            finally:
                manager.close()
            self.assertEqual(final['current_mode_ids'],['TEM','radial'])
            self.assertEqual(final['request']['recoveries'],request.to_dict()['recoveries'])
            self.assertEqual(final['identity_recoveries'],first['identity_recoveries'])
            for step in ('step-0000','step-0001'):
                for path in (history/step).rglob('*'):
                    if path.is_file():self.assertEqual(path.read_bytes(),(extended/step/path.relative_to(history/step)).read_bytes())
            result_path=history/'history-results.json';raw=result_path.read_bytes()
            changed=json.loads(raw);changed['identity_recoveries'][0]['assessment']['current_mode_ids'].reverse()
            result_path.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):read_hphi_history(history)
            result_path.write_bytes(raw)
        finally:
            for name in ('enter','leave'):(self.root/(name+'-moved')).rename(self.root/name)

    def test_strict_placements_and_failed_recovery_forbid_extension(self):
        raw=self.request().to_dict()
        self.assertEqual(HphiTrackingHistoryRequest.from_dict(raw).to_dict(),raw)
        for change in ({'history_version':True},{'recoveries':None},{'recoveries':[]},
                       {'recoveries':[self.placement,self.placement]}):
            with self.assertRaises(ValueError):HphiTrackingHistoryRequest.from_dict({**raw,**change})
        bad=json.loads(json.dumps(self.placement));bad['request']['comparison']['controls']['relative_cluster_gap']=.9
        request=HphiTrackingHistoryRequest(2,5,[bad])
        result=verify_hphi_history_steps([self.root/'enter',self.root/'leave'],request)
        self.assertEqual(result['status'],'UNVERIFIED')
        self.assertFalse(result['can_extend'])
        with self.assertRaisesRegex(ValueError,'UNVERIFIED'):
            verify_hphi_history_steps([self.root/name for name in ('enter','leave','continue')],
                                     HphiTrackingHistoryRequest(3,5,[bad]))
