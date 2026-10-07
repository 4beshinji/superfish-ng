# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
import io,json
from pathlib import Path
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from superfish_ng.gui import read_api_request,create_server
from superfish_ng.gui_planar import planar_response
from superfish_ng.gui_planar_curved import SELECTION
from superfish_ng.jobs import JobManager
from superfish_ng.planar_curved_tuning_jobs import _prepare,execute_prepared_planar_curved_tune,INPUT
from superfish_ng.planar_curved_tracking_history import PlanarCurvedTrackingHistoryRequest
from superfish_ng.planar_curved_identity_recovery import PlanarCurvedIdentityRecoveryRequest
from test_planar_curved_tuning import small_request,workspace
from test_planar_curved_tracking_history import native_chain
from test_planar_curved_identity_recovery import solutions,compare


def snapshot(path):return {p.relative_to(path).as_posix():p.read_bytes() for p in path.rglob('*') if p.is_file()}


class PlanarCurvedGuiTests(unittest.TestCase):
    def setUp(self):
        self.scope=workspace(self._testMethodName);self.root=self.scope.__enter__();self.addCleanup(self.scope.__exit__,None,None,None)
        self.manager=JobManager(self.root/'jobs');self.addCleanup(lambda:self.manager.close())
        self.lock=threading.Lock()

    def call(self,operation,**data):return planar_response(self.manager,'planar-curved-'+operation,data,self.lock,self.root/'cache')[0]
    def wait(self,identifier):self.assertEqual(self.manager.processes[identifier].wait(timeout=240),0)
    def natives(self):
        paths=native_chain(self.root);return [self.manager.import_planar_result(path) for path in paths]
    def pair(self,previous,current,request):
        identifier=self.call('start-tracking',document=request.to_dict(),previous_id=previous,current_id=current)['id']
        self.wait(identifier);return identifier
    def native_equal(self,source,identifier):
        if (source/'solution').is_dir():source=source/'solution'
        self.assertEqual(snapshot(source),snapshot(self.manager.directory(identifier)/'solution'))

    def test_strict_normalization_and_foreign_kind_allocate_no_jobs(self):
        a,c,b,_=solutions();tracking=compare(a,c).to_dict();recovery=PlanarCurvedIdentityRecoveryRequest(0,compare(a,b)).to_dict()
        raw=small_request();history=PlanarCurvedTrackingHistoryRequest(1,3).to_dict()
        for operation,key,value in [('normalize-tracking','document',tracking),('normalize-recovery','request',recovery),
                ('normalize-history','document',history),('normalize-tune','request',raw)]:
            self.assertEqual(self.call(operation,**{key:json.dumps(value)}),value)
            for data in ({},{key:value,'extra':0},{key:'{"format":"x","format":"y"}'},{key:dict(value,extra=0)}):
                with self.assertRaises(ValueError):self.call(operation,**data)
        for request in (dict(raw,schema_version=True),dict(raw,parameter='radius_m')):
            with self.assertRaises(ValueError):self.call('start-tune',request=request)
        with self.assertRaises(ValueError):self.call('start-tune',request=raw,max_new_trials=True)
        for operation in ('tune-result','tracking-result','history-result'):
            with self.assertRaises(ValueError):self.call(operation,id='../outside')
        self.assertEqual(self.manager.list(),[])

    def test_original_pair_import_and_late_source_mutation_are_bound(self):
        a,_,b,_=solutions();ids=self.natives();identifier=self.pair(ids[0],ids[2],compare(a,b))
        result=self.call('tracking-result',id=identifier);self.assertEqual(result['result']['current_mode_ids'],['even-x','odd-x'])
        before=snapshot(self.manager.directory(identifier))
        for side,index in [('previous',0),('current',2)]:
            imported=self.call('tracking-source',id=identifier,side=side)['id']
            self.native_equal(self.manager.directory(ids[index]),imported)
        self.assertEqual(snapshot(self.manager.directory(identifier)),before)
        from superfish_ng.gui_planar_curved import read_planar_curved_tracking
        path=self.manager.directory(identifier)/'execution/tracking-results.json'
        original=path.read_bytes()
        def changed(directory):
            report=read_planar_curved_tracking(directory);path.write_bytes(original+b' ');return report
        count=len(self.manager.list())
        try:
            with patch('superfish_ng.gui_planar_curved.read_planar_curved_tracking',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'changed'):self.call('tracking-source',id=identifier,side='current')
            self.assertEqual(len(self.manager.list()),count)
        finally:path.write_bytes(original)
        with self.assertRaises(ValueError):self.call('tracking-source',id=identifier,side='other')

    def test_actual_anchor_recovery_extension_parent_bytes_and_native_fields(self):
        a,c,b,later=solutions();ids=self.natives()
        pair0=self.pair(ids[0],ids[1],compare(a,c));pair1=self.pair(ids[1],ids[2],compare(c,b,True))
        history=self.call('start-history',document=PlanarCurvedTrackingHistoryRequest(2,3).to_dict(),step_ids=[pair0,pair1])['id'];self.wait(history)
        unresolved=self.call('history-result',id=history);self.assertEqual(unresolved['result']['current_mode_ids'],[None,None])
        before=snapshot(self.manager.directory(history));recovery=PlanarCurvedIdentityRecoveryRequest(0,compare(a,b)).to_dict()
        recovered=self.call('recover-history',id=history,request=recovery)['id'];self.wait(recovered)
        result=self.call('history-result',id=recovered);self.assertEqual(result['result']['current_mode_ids'],['even-x','odd-x'])
        self.assertEqual(result['result']['identity_recoveries'][0]['recovered_frequencies_hz'],dict(zip(['even-x','odd-x'],b.frequencies_hz[:2])))
        self.assertEqual(snapshot(self.manager.directory(history)),before)
        pair2=self.pair(ids[2],ids[3],replace(compare(b,later),previous_mode_ids=['even-x','odd-x']))
        extended=self.call('extend-history',id=recovered,next_id=pair2)['id'];self.wait(extended)
        result=self.call('history-result',id=extended);self.assertEqual(result['result']['current_mode_ids'],['even-x','odd-x'])
        self.assertFalse(result['result']['can_extend'])
        imported=self.call('history-source',id=extended)['id'];self.native_equal(self.manager.directory(ids[3]),imported)
        count=len(self.manager.list())
        with self.assertRaises(ValueError):self.call('extend-history',id=extended,next_id=pair2)
        self.assertEqual(len(self.manager.list()),count)

    def test_owned_tune_save_replay_resume_live_source_move_and_rank_import(self):
        raw=small_request();first=self.call('start-tune',request=raw,max_new_trials=1)['id'];self.wait(first)
        opened=self.call('open-tune-checkpoint',id=first,index=1);self.assertEqual(json.loads(opened['serialized'])['format'],SELECTION)
        self.assertEqual(self.call('replay-tune',document=opened['serialized']),opened)
        self.assertEqual(self.call('tune-checkpoints',id=first)['indices'],[0,1])
        source=Path(opened['document']['trial_runs'][0]);original=snapshot(source)
        imported=self.call('tune-trial',document=opened['serialized'],index=1);self.assertEqual(imported['mode'],1)
        self.native_equal(source,imported['id'])
        self.manager.close();self.manager=JobManager(self.root/'jobs')
        second=self.call('resume-tune',document=opened['serialized'],max_new_trials=1)['id']
        process=self.manager.processes[second];self.assertIsNone(process.poll())
        self.manager.directory(first).rename(self.root/'first-unavailable');self.assertIsNone(process.poll());self.wait(second)
        result=self.call('tune-result',id=second);self.assertEqual(result['document']['status'],'PAUSED')
        self.assertEqual(result['document']['trials'][0],opened['document']['trials'][0])
        for name in ('ancestry','execution'):self.assertEqual(snapshot(self.manager.directory(second)/name/'trial-001'),original)
        self.assertAlmostEqual(result['document']['trials'][0]['frequency_hz']/result['document']['trials'][1]['frequency_hz'],1.4,places=10)
        with self.assertRaises(ValueError):self.call('replay-tune',document=opened['serialized'])
        self.assertEqual(self.call('replay-tune',document=result['serialized']),result)
        bad=json.loads(result['serialized']);bad['checkpoint']['trials'][0]['frequency_hz']*=1.01
        with self.assertRaises(ValueError):self.call('replay-tune',document=bad)
        (self.root/'runtime-evidence.json').write_text(json.dumps(dict(first_id=first,second_id=second,source_moved_while_live=True,worker_exit=process.returncode)))

    def test_failed_zero_selection_is_saved_bound_and_resumed_with_original_request(self):
        raw=small_request();directory=self.manager.directory('failed-zero');_prepare(raw,directory,max_new_trials=1)
        with patch('superfish_ng.planar_curved_tuning_saved.execute_planar_project',side_effect=RuntimeError('FEM failed')):
            with self.assertRaises(RuntimeError):execute_prepared_planar_curved_tune(directory)
        result=self.call('open-tune-checkpoint',id='failed-zero',index=0);self.assertEqual(result['document']['trials'],[])
        self.assertEqual(self.call('replay-tune',document=result['serialized']),result)
        self.assertEqual(self.call('tune-checkpoints',id='failed-zero')['indices'],[0])
        before=snapshot(directory);resumed=self.call('resume-tune',document=result['serialized'],max_new_trials=1)['id'];self.wait(resumed)
        self.assertEqual(snapshot(directory),before);self.assertEqual(len(self.call('tune-result',id=resumed)['document']['trials']),1)
        bad=json.loads(result['serialized']);bad['checkpoint']['request']['target_hz']*=2
        with self.assertRaises(ValueError):self.call('resume-tune',document=bad,max_new_trials=1)
        path=directory/INPUT;original=path.read_bytes();data=json.loads(original);data['request']['target_hz']*=2;path.write_text(json.dumps(data))
        try:
            with self.assertRaises(ValueError):self.call('replay-tune',document=result['serialized'])
        finally:path.write_bytes(original)

    def test_true_doublet_unverified_keeps_null_and_forbids_target_import_or_resume(self):
        identifier=self.call('start-tune',request=small_request('te'))['id'];self.wait(identifier)
        result=self.call('tune-result',id=identifier);self.assertEqual(result['document']['status'],'UNVERIFIED')
        self.assertIsNone(result['document']['trials'][0]['frequency_hz']);count=len(self.manager.list())
        with self.assertRaises(ValueError):self.call('resume-tune',document=result['serialized'])
        with self.assertRaises(ValueError):self.call('tune-trial',document=result['serialized'],index=1)
        self.assertEqual(self.call('replay-tune',document=result['serialized']),result);self.assertEqual(len(self.manager.list()),count)

    def test_real_http_curved_assets_authenticated_strict_actions_and_small_native_hint(self):
        server=create_server(self.root/'http');thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base,token=server.launch_url.split('/#')
        def request(data,authenticated=True,hint=None):
            headers={'Content-Type':'application/json','Origin':base}
            if authenticated:headers['X-NG-Token']=token
            if hint is not None:headers['X-NG-Action']=hint
            return urlopen(Request(base+'/api',json.dumps(data).encode(),headers),timeout=30)
        try:
            for name,fragment in [('planar-curved.html','曲線の比較・調整'),('planar-curved.js','X-NG-Action'),('planar.html','/planar-curved.html')]:
                with urlopen(base+'/'+name,timeout=10) as response:self.assertIn(fragment,response.read().decode())
            data=dict(action='planar-curved-normalize-tune',request=small_request())
            with request(data) as response:self.assertEqual(json.load(response),data['request'])
            for bad,authenticated,hint in [(data,False,None),(dict(data,extra=0),True,None),
                    (data,True,'planar-curved-replay-tune')]:
                with self.assertRaises(HTTPError):request(bad,authenticated,hint)
            with request(dict(action='jobs')) as response:self.assertEqual(json.load(response),[])
        finally:server.shutdown();thread.join(timeout=10);server.server_close();server.manager.close()

    def test_large_checkpoint_hint_is_action_bound_without_relaxing_existing_limits(self):
        action='planar-curved-replay-tune';raw=json.dumps(dict(action=action,document='x'*(65*1024*1024))).encode()
        stream=io.BytesIO(raw)
        with self.assertRaisesRegex(ValueError,'64 MiB'):read_api_request(stream,str(len(raw)))
        self.assertEqual(stream.tell(),0)
        result=read_api_request(io.BytesIO(raw),str(len(raw)),action_hint=action);self.assertEqual(len(result['document']),65*1024*1024)
        for hint in ('planar-curved-resume-tune','planar-curved-tune-trial'):
            with self.assertRaisesRegex(ValueError,'differs'):read_api_request(io.BytesIO(raw),str(len(raw)),action_hint=hint)
        stream=io.BytesIO(b'{}')
        with self.assertRaisesRegex(ValueError,'128 MiB'):read_api_request(stream,str(128*1024*1024+1),action_hint=action)
        self.assertEqual(stream.tell(),0)
        unrelated=json.dumps(dict(action='jobs',padding='x'*(5*1024*1024))).encode()
        with self.assertRaisesRegex(ValueError,'4 MiB'):read_api_request(io.BytesIO(unrelated),str(len(unrelated)))
        with self.assertRaisesRegex(ValueError,'differs'):read_api_request(io.BytesIO(unrelated),str(len(unrelated)),action_hint=action)
