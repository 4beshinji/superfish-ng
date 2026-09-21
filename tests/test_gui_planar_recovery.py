# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path
import tempfile
import threading
import unittest
from superfish_ng.gui_planar import planar_response
from superfish_ng.jobs import JobManager
from superfish_ng.planar_tracking import PlanarTrackingRequest
from superfish_ng.planar_identity_recovery import PlanarIdentityRecoveryRequest
from superfish_ng.planar_tracking_history import PlanarTrackingHistoryRequest
from superfish_ng.planar_tracking_history_saved import history_snapshot
from test_planar_tracking_history import PlanarTrackingHistoryTests as Fixtures


class PlanarRecoveryGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):Fixtures.setUpClass()
    @classmethod
    def tearDownClass(cls):Fixtures.tearDownClass()
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.manager=JobManager(self.root/'jobs');self.addCleanup(self.manager.close)
        self.lock=threading.Lock();self.recovery=PlanarIdentityRecoveryRequest(0,PlanarTrackingRequest()).to_dict()
    def call(self,action,**data):return planar_response(self.manager,action,data,self.lock,self.root/'cache')[0]
    def wait(self,identifier):
        self.assertEqual(self.manager.processes[identifier].wait(timeout=240),0)
        return self.call('planar-history-result',id=identifier)
    def initial(self,square=False):
        names=['merge'] if square else ['merge','split']
        identifier=self.manager.start_planar_history([Fixtures.root/n for n in names],PlanarTrackingHistoryRequest(len(names)))
        self.wait(identifier);return identifier

    def test_recover_extend_reopen_and_import_original_fields(self):
        initial=self.initial();before=history_snapshot(self.manager.directory(initial))
        self.assertEqual(self.call('planar-normalize-recovery',request=json.dumps(self.recovery)),self.recovery)
        identifier=self.call('planar-recover-history',id=initial,request=json.dumps(self.recovery))['id']
        result=self.wait(identifier)
        self.assertEqual(result['result']['current_mode_ids'],['mode-2','mode-1'])
        self.assertEqual(result['result']['steps'][-1]['current_mode_ids'],[None,None])
        self.assertEqual(self.call('planar-normalize-history',document=result['request']),result['request'])
        self.assertEqual(before,history_snapshot(self.manager.directory(initial)))
        imported=self.call('planar-history-source',id=identifier)['id']
        source=self.manager.directory(identifier)/'step-0001/current'
        destination=self.manager.directory(imported)/'solution'
        for path in source.iterdir():
            if path.is_file():self.assertEqual(path.read_bytes(),(destination/path.name).read_bytes(),path.name)
        pair=self.manager.start_planar_tracking(Fixtures.root/'right',Fixtures.root/'right',PlanarTrackingRequest(2,2,['mode-2','mode-1']))
        self.assertEqual(self.manager.processes[pair].wait(timeout=240),0)
        extended=self.call('planar-extend-history',id=identifier,next_id=pair)['id']
        final=self.wait(extended)
        self.assertEqual(final['result']['current_mode_ids'],['mode-2','mode-1'])
        self.assertEqual(len(final['result']['identity_recoveries']),1)
        self.manager.close();self.manager=JobManager(self.root/'jobs');self.addCleanup(self.manager.close)
        self.assertEqual(self.call('planar-history-result',id=extended),final)

    def test_strict_request_and_true_degeneracy_stay_unverified(self):
        duplicate=json.dumps(self.recovery).replace('"anchor_snapshot_index": 0','"anchor_snapshot_index": 0, "anchor_snapshot_index": 1')
        with self.assertRaisesRegex(ValueError,'duplicate'):self.call('planar-normalize-recovery',request=duplicate)
        with self.assertRaises(ValueError):self.call('planar-normalize-recovery',request=self.recovery,extra=1)
        self.assertEqual(self.manager.list(),[])
        initial=self.initial(True)
        identifier=self.call('planar-recover-history',id=initial,request=self.recovery)['id']
        result=self.wait(identifier)['result']
        self.assertEqual(result['status'],'UNVERIFIED');self.assertFalse(result['can_extend'])
        self.assertIsNone(result['identity_recoveries'][0]['recovered_frequencies_hz'])
        self.assertEqual(result['current_mode_ids'],[None,None])
