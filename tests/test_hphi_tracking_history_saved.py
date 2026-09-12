# SPDX-License-Identifier: Apache-2.0
from contextlib import ExitStack
import hashlib,json,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from superfish_ng.jobs import JobManager,read_job
from superfish_ng.hphi_tracking_history import HphiTrackingHistoryRequest
from superfish_ng.hphi_tracking_history_saved import execute_hphi_history,extend_hphi_history,read_hphi_history,history_snapshot
from test_hphi_tracking_history import fixture


class HphiHistorySavedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory();cls.source=Path(cls.temporary.name);fixture(cls.source)
    @classmethod
    def tearDownClass(cls):cls.temporary.cleanup()

    def test_owned_copy_extension_source_move_and_budget_stop(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);shutil.copytree(self.source/'group',root/'source');shutil.copytree(self.source/'group-back',root/'next')
            execute_hphi_history([root/'source'],HphiTrackingHistoryRequest(1,2),root/'first');before=history_snapshot(root/'first')
            result=extend_hphi_history(root/'first',root/'next',root/'extended');self.assertFalse(result['can_extend']);self.assertFalse(result['individual_ids_complete']);self.assertEqual(before,history_snapshot(root/'first'))
            for name in ('source','next','first'):(root/name).rename(root/('moved-'+name))
            self.assertEqual(result,read_hphi_history(root/'extended'))
            with self.assertRaisesRegex(ValueError,'max_steps'):extend_hphi_history(root/'extended',self.source/'group',root/'bad')
            self.assertFalse((root/'bad').exists())

    def test_rehashed_summary_ancestor_and_disguised_kind_rejected(self):
        from superfish_ng.hphi_tracking_jobs import _snapshot
        from superfish_ng.hphi_tracking_history_saved import _inputs
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/'history';execute_hphi_history([self.source/'group'],HphiTrackingHistoryRequest(1),root)
            path=root/'job.json';raw=path.read_bytes();state=json.loads(raw);state['kind']='single';path.write_text(json.dumps(state))
            with self.assertRaises(ValueError):read_job(root)
            path.write_bytes(raw)
            def load(p):return json.loads(p.read_text())
            def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
            def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
            ancestor=root/'step-0000';p=ancestor/'tracking-results.json';result=load(p);result['individual_ids_complete']=True;result['current_mode_ids']=['mode-1','mode-2'];write(p,result)
            manifest=load(ancestor/'manifest.json');manifest['files']['tracking-results.json']=digest(p);write(ancestor/'manifest.json',manifest)
            snapshot=_snapshot(ancestor);sources=load(root/'sources.json');sources['steps'][0]['files']=snapshot;write(root/'sources.json',sources)
            summary=load(root/'history-results.json');summary['steps'][0]=result;summary['step_sha256'][0]=snapshot;write(root/'history-results.json',summary)
            inputs=_inputs(root);manifest=load(root/'manifest.json');manifest['files']={**inputs,'history-results.json':digest(root/'history-results.json')};write(root/'manifest.json',manifest)
            state=load(root/'job.json');state['input_sha256']=inputs;write(root/'job.json',state)
            with self.assertRaisesRegex(ValueError,'replay|recomputed|correspondence'):read_hphi_history(root)

    def test_worker_extension_restart_cancel_and_reentry(self):
        from superfish_ng.hphi_tracking_history_saved import execute_prepared_hphi_history
        with tempfile.TemporaryDirectory() as t,ExitStack() as cleanup:
            root=Path(t);manager=JobManager(root/'workspace');cleanup.callback(manager.close)
            first=manager.start_hphi_history([self.source/'forward'],HphiTrackingHistoryRequest(1));self.assertEqual(manager.processes[first].wait(timeout=180),0)
            extended=manager.extend_hphi_history(manager.directory(first),self.source/'reverse');self.assertEqual(manager.processes[extended].wait(timeout=180),0)
            self.assertTrue(read_hphi_history(manager.directory(extended))['individual_ids_complete'])
            before=history_snapshot(manager.directory(first))
            with self.assertRaisesRegex(ValueError,'fresh queued'):execute_prepared_hphi_history(manager.directory(first))
            self.assertEqual(before,history_snapshot(manager.directory(first)))
            cancelled=manager.start_hphi_history([self.source/'forward'],HphiTrackingHistoryRequest(1));self.assertEqual(manager.cancel(cancelled)['status'],'cancelled')
            manager.close();manager=JobManager(root/'workspace');cleanup.callback(manager.close)
            self.assertEqual(manager.status(extended,verify=True)['status'],'complete');self.assertEqual(manager.status(cancelled)['status'],'cancelled')

    def test_ancestor_change_during_copy_or_before_spawn_fails_new_history(self):
        from superfish_ng import hphi_tracking_history_saved as module
        with tempfile.TemporaryDirectory() as t,ExitStack() as cleanup:
            root=Path(t);source=root/'source';shutil.copytree(self.source/'forward',source);copy=module.shutil.copyfile;changed=False
            def copying(a,b):
                nonlocal changed
                result=copy(a,b)
                if not changed:
                    changed=True;path=source/'job.json';data=json.loads(path.read_text());data['stage']='changed';path.write_text(json.dumps(data))
                return result
            with patch.object(module.shutil,'copyfile',side_effect=copying),self.assertRaisesRegex(ValueError,'ancestry changed'):execute_hphi_history([source],HphiTrackingHistoryRequest(1),root/'failed')
            self.assertEqual(json.loads((root/'failed/job.json').read_text())['status'],'failed')
            execute_hphi_history([self.source/'forward'],HphiTrackingHistoryRequest(1),root/'first');manager=JobManager(root/'workspace');cleanup.callback(manager.close);prepare=module._prepare
            def preparing(*args):
                result=prepare(*args);(root/'first/history.json').unlink();return result
            with patch.object(module,'_prepare',side_effect=preparing),patch.object(module.subprocess,'Popen') as spawn,self.assertRaises(ValueError):manager.extend_hphi_history(root/'first',self.source/'reverse')
            spawn.assert_not_called();self.assertFalse(manager.processes)
            self.assertEqual([json.loads(p.read_text())['status'] for p in (root/'workspace').glob('*/job.json')],['failed'])

    def test_gui_ordered_history_extension_and_each_original_side(self):
        import threading
        from superfish_ng.gui_hphi import hphi_response
        with tempfile.TemporaryDirectory() as t,ExitStack() as cleanup:
            root=Path(t);manager=JobManager(root/'workspace');cleanup.callback(manager.close);lock=threading.Lock()
            def api(action,**data):return hphi_response(manager,action,data,lock,root/'plots')[0]
            for name in ('group','group-back','forward'):shutil.copytree(self.source/name,manager.directory(name))
            document=HphiTrackingHistoryRequest(1,3).to_dict();self.assertEqual(api('hphi-normalize-history',document=document),document)
            with self.assertRaises(ValueError):api('hphi-start-history',document=document,step_ids=[])
            first=api('hphi-start-history',document=document,step_ids=['group'])['id'];self.assertEqual(manager.processes[first].wait(timeout=180),0)
            before=history_snapshot(manager.directory(first));extended=api('hphi-extend-history',id=first,next_id='group-back')['id'];self.assertEqual(manager.processes[extended].wait(timeout=180),0)
            reply=api('hphi-history-result',id=extended);self.assertEqual(reply['request']['step_count'],2);self.assertFalse(reply['result']['individual_ids_complete']);self.assertTrue(reply['result']['can_extend']);self.assertEqual(len(reply['sources']['steps']),2)
            for index,side in ((0,'previous'),(1,'current')):
                imported=api('hphi-history-source',id=extended,index=index,side=side)['id'];target=manager.directory(imported);source=manager.directory(extended)/f'step-{index:04d}'/side
                self.assertEqual((target/'project.json').read_bytes(),(source/'project.json').read_bytes())
                self.assertEqual({p.name:p.read_bytes() for p in (target/'solution').iterdir()},{p.name:p.read_bytes() for p in (source/'solution').iterdir()})
            count=len(manager.list())
            for index,side in ((True,'previous'),(-1,'current'),(2,'current'),(0,False)):
                with self.assertRaises(ValueError):api('hphi-history-source',id=extended,index=index,side=side)
            with self.assertRaises(ValueError):api('hphi-extend-history',id=extended,next_id='forward')
            self.assertEqual(len(manager.list()),count);self.assertEqual(before,history_snapshot(manager.directory(first)))
