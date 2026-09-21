# SPDX-License-Identifier: Apache-2.0
import json,tempfile,threading,unittest
from pathlib import Path
from superfish_ng.gui_hphi import hphi_response
from superfish_ng.jobs import JobManager
from superfish_ng.hphi_project import HphiProject
from test_curved_hphi_tuning_saved import request


class CurvedHphiTuneGuiTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.manager=JobManager(self.root/'jobs');self.addCleanup(self.manager.close)
        self.lock=threading.Lock();self.q=request();self.q['project']['display_length_unit']='m'

    def call(self,action,**data):
        return hphi_response(self.manager,action,data,self.lock,self.root/'cache')[0]

    def test_strict_normalize_curved_request(self):
        self.assertEqual(self.call('hphi-normalize-tune',request=json.dumps(self.q)),self.q)
        bad={**self.q,'parameter':'stored_energy_j'}
        with self.assertRaises(ValueError):self.call('hphi-start-tune',request=bad)
        self.assertEqual(self.manager.list(),[])

    def test_worker_checkpoints_resume_and_original_project_import(self):
        identifier=self.call('hphi-start-tune',request=self.q,max_new_trials=1)['id']
        self.assertEqual(self.manager.processes[identifier].wait(timeout=180),0)
        self.assertEqual(self.call('hphi-tune-checkpoints',id=identifier)['indices'],[0,1])
        empty=self.call('hphi-open-tune-checkpoint',id=identifier,index=0)
        self.assertEqual(empty['document']['trials'],[])
        first=self.call('hphi-tune-result',id=identifier)
        self.assertEqual(first['document']['status'],'PAUSED')
        imported=self.call('hphi-tune-trial',document=first['serialized'],index=1)
        trial=Path(first['document']['trial_runs'][0]);destination=self.manager.directory(imported['id'])
        self.assertEqual(imported['mode'],1)
        self.assertEqual(HphiProject.load(destination/'project.json').to_dict(),HphiProject.load(trial/'project.json').to_dict())
        for p in (trial/'solution').iterdir():self.assertEqual(p.read_bytes(),(destination/'solution'/p.name).read_bytes())
        resumed=self.call('hphi-resume-tune',document=first['serialized'],max_new_trials=1)['id']
        self.assertEqual(self.manager.processes[resumed].wait(timeout=180),0)
        original=self.manager.directory(identifier)
        self.manager.close()
        original.rename(self.root/'original-moved')
        self.manager=JobManager(self.root/'jobs');self.addCleanup(self.manager.close)
        final=self.call('hphi-open-tune-checkpoint',id=resumed,index=2)
        self.assertEqual(len(final['document']['trials']),2)
        self.assertEqual(final['document']['trials'][:1],first['document']['trials'])
        self.assertEqual(self.call('hphi-replay-tune',document=final['serialized']),final)
