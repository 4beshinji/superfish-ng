# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import time
import unittest
from superfish_ng.jobs import JobManager
from superfish_ng.gui_tuning import tuning_response


class GuiTuningTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.manager=JobManager(self.root);self.addCleanup(self.manager.close)
        self.request=json.loads(Path('examples/tuning/pillbox_length.json').read_text())
    def action(self,action,**data):return tuning_response(self.manager,action,data)
    def wait(self,identifier):
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            if self.manager.status(identifier)['status'] not in ('queued','running'):return self.action('tune-result',id=identifier)
            time.sleep(.025)
        self.fail('GUI tune timed out')

    def test_start_exact_replay_and_resume(self):
        first=self.wait(self.action('start-tune',request=self.request,max_new_trials=2)['id'])
        self.assertEqual(first['document']['status'],'PAUSED')
        self.assertEqual(self.action('replay-tune',document=first['serialized']),first)
        final=self.wait(self.action('resume-tune',document=first['serialized'])['id'])
        self.assertEqual(final['document']['status'],'TUNED');self.assertEqual(final['document']['trials'][-1]['current_mode_ids'].index('TM011'),1)
        self.assertEqual(self.action('replay-tune',document=final['serialized']),final)
        with self.assertRaisesRegex(ValueError,'PAUSED'):self.action('resume-tune',document=final['serialized'])

    def test_checkpoint_selection_rejects_foreign_tampered_and_linked_files(self):
        identifier=self.action('start-tune',request=self.request,max_new_trials=2)['id']
        first=self.wait(identifier)
        self.assertEqual(self.action('tune-checkpoints',id=identifier),dict(id=identifier,indices=[1,2],verified=False))
        self.assertEqual(self.action('open-tune-checkpoint',id=identifier,index=2),first)
        selected=self.action('open-tune-checkpoint',id=identifier,index=1)
        self.assertEqual(len(selected['document']['trials']),1)
        path=self.manager.directory(identifier)/'execution/checkpoint-001.json';original=path.read_bytes()
        changed=deepcopy(selected['document']);changed['trials'][0]['value']=.5
        path.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError,'replay'):self.action('open-tune-checkpoint',id=identifier,index=1)
        path.write_bytes(original)
        other=self.action('start-tune',request=self.request,max_new_trials=1)['id'];self.wait(other)
        path.write_bytes((self.manager.directory(other)/'execution/checkpoint-001.json').read_bytes())
        with self.assertRaisesRegex(ValueError,'another tuning job'):self.action('open-tune-checkpoint',id=identifier,index=1)
        path.unlink();path.symlink_to(self.manager.directory(other)/'execution/checkpoint-001.json')
        self.assertEqual(self.action('tune-checkpoints',id=identifier)['indices'],[2])
        with self.assertRaisesRegex(ValueError,'symlink'):self.action('open-tune-checkpoint',id=identifier,index=1)
        for index in (True,0,-1,1.,'1','../1'):
            with self.assertRaises(ValueError):self.action('open-tune-checkpoint',id=identifier,index=index)

    def test_cancelled_job_checkpoints_survive_manager_restart_and_resume(self):
        self.request['project']['case']['mesh'].update(nr=64,nz=64)
        identifier=self.action('start-tune',request=self.request)['id']
        with self.assertRaisesRegex(ValueError,'stopped'):self.action('tune-checkpoints',id=identifier)
        directory=self.manager.directory(identifier)
        deadline=time.monotonic()+30
        while not (directory/'execution/checkpoint-001.json').is_file():
            if time.monotonic()>deadline:self.fail('first tune checkpoint timed out')
            time.sleep(.01)
        self.manager.cancel(identifier)
        self.assertEqual(self.manager.status(identifier)['status'],'cancelled')
        self.manager.close();self.manager=JobManager(self.root);self.addCleanup(self.manager.close)
        listing=self.action('tune-checkpoints',id=identifier)
        self.assertIn(1,listing['indices'])
        first=self.action('open-tune-checkpoint',id=identifier,index=1)
        resumed=self.wait(self.action('resume-tune',document=first['serialized'],max_new_trials=1)['id'])
        self.assertEqual(resumed['document']['trial_runs'][:1],first['document']['trial_runs'])
        self.assertEqual(len(resumed['document']['trials']),2)

    def test_strict_transport_and_changed_checkpoint(self):
        for action,data in [('start-tune',dict(request=self.request,unknown=True)),('tune-result',dict(id='../x')),
                ('replay-tune',dict(document={'document_type':'wrong'}))]:
            with self.assertRaises(ValueError):self.action(action,**data)
        first=self.wait(self.action('start-tune',request=self.request,max_new_trials=1)['id'])
        changed=deepcopy(first['document']);changed['trials'][0]['value']=.5
        with self.assertRaisesRegex(ValueError,'replay'):self.action('replay-tune',document=json.dumps(changed))
        with self.assertRaises(ValueError):self.action('resume-tune',document=first['serialized'],request=self.request)

    def test_unverified_cannot_resume_and_other_job_kind_is_rejected(self):
        self.request['controls']['minimum_overlap']=1.
        result=self.wait(self.action('start-tune',request=self.request)['id'])
        self.assertEqual(result['document']['status'],'UNVERIFIED')
        with self.assertRaises(ValueError):self.action('resume-tune',document=result['serialized'])
        from superfish_ng.jobs import execute_project
        from superfish_ng.project import Project
        execute_project(Project.from_dict(self.request['project']),self.root/'individual')
        with self.assertRaisesRegex(ValueError,'tune job'):self.action('tune-result',id='individual')
