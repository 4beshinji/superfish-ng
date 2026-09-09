# SPDX-License-Identifier: Apache-2.0
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from superfish_ng.planar_tracking_history import PlanarTrackingHistoryRequest
from superfish_ng.planar_tracking_history_saved import execute_planar_history,extend_planar_history,read_planar_history,history_snapshot
import test_planar_tracking_history as fixtures


class PlanarHistorySavedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):fixtures.PlanarTrackingHistoryTests.setUpClass();cls.source=fixtures.PlanarTrackingHistoryTests.root
    @classmethod
    def tearDownClass(cls):fixtures.PlanarTrackingHistoryTests.tearDownClass()

    def test_owned_copy_extension_and_portable_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);copies=[]
            for name in ('merge','split'):
                target=root/name;shutil.copytree(self.source/name,target);copies.append(target)
            first=execute_planar_history(copies[:1],PlanarTrackingHistoryRequest(1),root/'first');before=history_snapshot(root/'first')
            extended=extend_planar_history(root/'first',copies[1],root/'extended')
            self.assertTrue(extended['can_extend']);self.assertFalse(extended['individual_ids_complete']);self.assertEqual(before,history_snapshot(root/'first'))
            for source in copies:shutil.rmtree(source)
            shutil.rmtree(root/'first');self.assertEqual(extended,read_planar_history(root/'extended'))
            stopped=extend_planar_history(root/'extended',self.source/'unverified',root/'stopped');self.assertFalse(stopped['can_extend'])
            with self.assertRaisesRegex(ValueError,'UNVERIFIED'):extend_planar_history(root/'stopped',self.source/'split',root/'bad')
            self.assertFalse((root/'bad').exists())

    def test_rehashed_summary_and_kind_downgrade_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'run';execute_planar_history([self.source/'merge'],PlanarTrackingHistoryRequest(1),root)
            originals={name:(root/name).read_bytes() for name in ('history-results.json','manifest.json','job.json')}
            for kind in (None,'planar_tracking','single'):
                state=json.loads(originals['job.json']);state['kind']=kind;(root/'job.json').write_text(json.dumps(state))
                with self.assertRaises(ValueError):read_planar_history(root)
            (root/'job.json').write_bytes(originals['job.json'])
            result=json.loads(originals['history-results.json']);result['individual_ids_complete']=True;(root/'history-results.json').write_text(json.dumps(result))
            manifest=json.loads(originals['manifest.json']);manifest['files']['history-results.json']=hashlib.sha256((root/'history-results.json').read_bytes()).hexdigest();(root/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'ancestry replay'):read_planar_history(root)

    def test_real_worker_manager_restart_reentry_and_cancellation(self):
        import time
        from superfish_ng.jobs import JobManager,read_job
        from superfish_ng.planar_tracking import PlanarTrackingRequest
        from superfish_ng.planar_tracking_jobs import execute_planar_tracking
        from superfish_ng.planar_tracking_history_saved import execute_prepared_planar_history
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);manager=JobManager(root/'workspace')
            try:
                identifier=manager.start_planar_history([self.source/'merge',self.source/'split'],PlanarTrackingHistoryRequest(2))
                self.assertEqual(manager.processes[identifier].wait(timeout=120),0)
                directory=manager.directory(identifier);before=history_snapshot(directory)
                self.assertEqual(manager.status(identifier,verify=True)['status'],'complete')
                with self.assertRaisesRegex(ValueError,'fresh queued'):execute_prepared_planar_history(directory)
                self.assertEqual(before,history_snapshot(directory))
                # Detect a disguised history even through the generic job reader.
                state_path=directory/'job.json';raw=state_path.read_bytes();state=json.loads(raw);state['kind']='single';state_path.write_text(json.dumps(state))
                try:
                    with self.assertRaises(ValueError):read_job(directory)
                finally:state_path.write_bytes(raw)
                groups=[dict(indices=[1,2],ids=['mode-1','mode-2'])]
                execute_planar_tracking(self.source/'right',self.source/'right',PlanarTrackingRequest(2,2,None,groups),root/'identity')
                paths=[self.source/'merge',self.source/'split']+[root/'identity']*6
                cancelled=manager.start_planar_history(paths,PlanarTrackingHistoryRequest(len(paths)))
                deadline=time.monotonic()+30
                while manager.status(cancelled)['status']=='queued' and time.monotonic()<deadline:time.sleep(.02)
                self.assertEqual(manager.status(cancelled)['status'],'running')
                self.assertEqual(manager.cancel(cancelled)['status'],'cancelled')
                self.assertIsNotNone(manager.processes[cancelled].poll())
                manager.close();manager=JobManager(root/'workspace')
                self.assertEqual(manager.status(identifier,verify=True)['status'],'complete')
                self.assertEqual(manager.status(cancelled)['status'],'cancelled')
            finally:manager.close()

    def test_copy_mutation_fails_new_output(self):
        import superfish_ng.planar_tracking_history_saved as module
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';shutil.copytree(self.source/'merge',source)
            original=module.shutil.copyfile;changed=False
            def copying(a,b):
                nonlocal changed
                value=original(a,b)
                if not changed:
                    changed=True;path=source/'job.json';data=json.loads(path.read_text());data['stage']='changed';path.write_text(json.dumps(data))
                return value
            with patch.object(module.shutil,'copyfile',side_effect=copying),self.assertRaisesRegex(ValueError,'ancestry changed'):
                execute_planar_history([source],PlanarTrackingHistoryRequest(1),root/'failed')
            self.assertEqual(json.loads((root/'failed/job.json').read_text())['status'],'failed')

    def test_missing_ancestor_after_extension_marks_new_history_failed(self):
        import superfish_ng.planar_tracking_history_saved as module
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);execute_planar_history([self.source/'merge'],PlanarTrackingHistoryRequest(1),root/'first');original=module.execute_planar_history
            def executing(*args):
                result=original(*args);(root/'first/history.json').unlink();return result
            with patch.object(module,'execute_planar_history',side_effect=executing),self.assertRaises(ValueError):
                extend_planar_history(root/'first',self.source/'split',root/'extended')
            self.assertEqual(json.loads((root/'extended/job.json').read_text())['status'],'failed')

    def test_gui_history_extension_and_native_import(self):
        import threading
        from superfish_ng.jobs import JobManager
        from superfish_ng.gui_planar import planar_response
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);manager=JobManager(root/'workspace')
            def request(action,**data):return planar_response(manager,action,data,threading.Lock(),root/'plots')[0]
            try:
                for name in ('merge','split','cross'):
                    shutil.copytree(self.source/name,manager.directory(name))
                document=PlanarTrackingHistoryRequest(1).to_dict()
                self.assertEqual(request('planar-normalize-history',document=document),document)
                with self.assertRaisesRegex(ValueError,'step_count'):request('planar-start-history',document=document,step_ids=[])
                identifier=request('planar-start-history',document=document,step_ids=['merge'])['id']
                self.assertEqual(manager.processes[identifier].wait(timeout=120),0)
                first=manager.directory(identifier);before=history_snapshot(first)
                extended=request('planar-extend-history',id=identifier,next_id='split')['id']
                self.assertEqual(manager.processes[extended].wait(timeout=120),0)
                response=request('planar-history-result',id=extended)
                self.assertEqual(response['request']['step_count'],2);self.assertTrue(response['result']['can_extend']);self.assertFalse(response['result']['individual_ids_complete'])
                with self.assertRaisesRegex(ValueError,'native'):request('planar-extend-history',id=extended,next_id='cross')
                imported=request('planar-history-source',id=extended)['id']
                target=manager.directory(imported)/'solution';source=manager.directory(extended)/'step-0001/current'
                self.assertEqual({p.name:p.read_bytes() for p in source.iterdir()},{p.name:p.read_bytes() for p in target.iterdir()})
                self.assertEqual(before,history_snapshot(first))
            finally:manager.close()

    def test_async_parent_change_prevents_worker_spawn(self):
        from superfish_ng.jobs import JobManager
        import superfish_ng.planar_tracking_history_saved as module
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);execute_planar_history([self.source/'merge'],PlanarTrackingHistoryRequest(1),root/'first')
            manager=JobManager(root/'workspace');original=module._prepare
            def preparing(*args):
                value=original(*args);(root/'first/history.json').unlink();return value
            try:
                with patch.object(module,'_prepare',side_effect=preparing),patch.object(module.subprocess,'Popen') as spawn,self.assertRaises(ValueError):
                    manager.extend_planar_history(root/'first',self.source/'split')
                spawn.assert_not_called();self.assertFalse(manager.processes)
                states=[json.loads(path.read_text()) for path in (root/'workspace').glob('*/job.json')]
                self.assertEqual([state['status'] for state in states],['failed'])
            finally:manager.close()

    def test_cli_start_extend_and_full_replay(self):
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);PlanarTrackingHistoryRequest(1).save(root/'request.json')
            commands=[['execute-planar-history',str(root/'request.json'),'--steps',str(self.source/'merge'),'--out',str(root/'first')],
                      ['extend-planar-history',str(root/'first'),str(self.source/'split'),'--out',str(root/'extended')],
                      ['replay-planar-history',str(root/'extended')]]
            for command,target in zip(commands,('first','extended','extended')):
                done=subprocess.run([sys.executable,'-m','superfish_ng',*command],text=True,capture_output=True,timeout=120)
                self.assertEqual(done.returncode,0,done.stderr);self.assertEqual(json.loads(done.stdout),read_planar_history(root/target))

    def test_rehashed_ancestor_cannot_fabricate_individual_identity(self):
        from superfish_ng.planar_tracking_jobs import _snapshot
        from superfish_ng.planar_tracking_history_saved import _inputs
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'history';execute_planar_history([self.source/'merge',self.source/'split'],PlanarTrackingHistoryRequest(2),root)
            def load(path):return json.loads(path.read_text())
            def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
            def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
            ancestor=root/'step-0000';result_path=ancestor/'tracking-results.json';result=load(result_path)
            result['individual_ids_complete']=True;result['current_mode_ids']=['mode-1','mode-2'];write(result_path,result)
            manifest=load(ancestor/'manifest.json');manifest['files']['tracking-results.json']=digest(result_path);write(ancestor/'manifest.json',manifest)
            snapshot=_snapshot(ancestor);sources=load(root/'sources.json');sources['steps'][0]['files']=snapshot;write(root/'sources.json',sources)
            summary=load(root/'history-results.json');summary['steps'][0]=result;summary['step_sha256'][0]=snapshot;write(root/'history-results.json',summary)
            inputs=_inputs(root);manifest=load(root/'manifest.json');manifest['files']={**inputs,'history-results.json':digest(root/'history-results.json')};write(root/'manifest.json',manifest)
            state=load(root/'job.json');state['input_sha256']=inputs;write(root/'job.json',state)
            with self.assertRaisesRegex(ValueError,'replay|recomputed|correspondence'):read_planar_history(root)

    def test_step_budget_stops_extension_without_discarding_verified_ids(self):
        from superfish_ng.jobs import JobManager
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);result=execute_planar_history([self.source/'merge'],PlanarTrackingHistoryRequest(1,1),root/'history')
            self.assertEqual(result['status'],'PASS');self.assertFalse(result['can_extend']);self.assertIn('max_steps',result['stop_reason'])
            self.assertEqual(result['current_identity_groups'],[dict(indices=[1,2],ids=['mode-1','mode-2'])])
            self.assertEqual(result,read_planar_history(root/'history'))
            with self.assertRaisesRegex(ValueError,'max_steps'):extend_planar_history(root/'history',self.source/'split',root/'forbidden')
            self.assertFalse((root/'forbidden').exists());manager=JobManager(root/'workspace')
            try:
                with self.assertRaisesRegex(ValueError,'max_steps'):manager.extend_planar_history(root/'history',self.source/'split')
                self.assertFalse(manager.processes);self.assertFalse(list((root/'workspace').glob('*/job.json')))
            finally:manager.close()
