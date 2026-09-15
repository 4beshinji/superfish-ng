# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import threading
import unittest
import numpy as np
from superfish_ng.gui_planar import planar_response
from superfish_ng.jobs import JobManager
from superfish_ng.planar_tuning import read_planar_tune
from test_planar_tuning import request


class PlanarTuningGuiTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.manager=JobManager(self.root/'jobs');self.addCleanup(self.manager.close)
        self.lock=threading.Lock();self.raw=request()
    def call(self,action,**data):
        return planar_response(self.manager,action,data,self.lock,self.root/'cache')[0]
    def wait(self,identifier):
        self.assertEqual(self.manager.processes[identifier].wait(timeout=60),0)
        return self.manager.status(identifier,verify=True)

    def test_normalization_preserves_strict_original_json(self):
        self.assertEqual(self.call('planar-normalize-tune',request=json.dumps(self.raw)),self.raw)
        duplicate=json.dumps(self.raw).replace('"minimum_overlap": 0.9','"minimum_overlap": 0.9, "minimum_overlap": 0.95')
        with self.assertRaisesRegex(ValueError,'duplicate'):self.call('planar-start-tune',request=duplicate)
        for data in ({},{'request':self.raw,'extra':0}):
            with self.assertRaises(ValueError):self.call('planar-normalize-tune',**data)
        self.assertEqual(self.manager.list(),[])

    def test_checkpoint_resume_and_actual_target_rank_native_import(self):
        first=self.call('planar-start-tune',request=self.raw,max_new_trials=2)['id'];self.wait(first)
        result=self.call('planar-tune-result',id=first)
        self.assertEqual(result['document']['status'],'PAUSED')
        self.assertEqual(self.call('planar-tune-checkpoints',id=first)['indices'],[1,2])
        opened=self.call('planar-open-tune-checkpoint',id=first,index=1)
        self.assertEqual(len(opened['document']['trials']),1)
        for index,rank in ((1,2),(2,1)):
            imported=self.call('planar-tune-trial',document=result['serialized'],index=index)
            self.assertEqual(imported['mode'],rank)
            original=Path(result['document']['trial_runs'][index-1])/'solution'
            target=self.manager.directory(imported['id'])/'solution'
            for p in original.glob('*.npz'):
                with np.load(p) as a,np.load(target/p.name) as b:
                    self.assertEqual(set(a.files),set(b.files))
                    for k in a.files:np.testing.assert_array_equal(a[k],b[k])
        resumed=self.call('planar-resume-tune',document=result['serialized'])['id'];self.wait(resumed)
        final=self.call('planar-tune-result',id=resumed)
        self.assertEqual(final['document']['status'],'TUNED')
        self.assertEqual(self.call('planar-replay-tune',document=final['serialized']),final)
        with self.assertRaises(ValueError):self.call('planar-resume-tune',document=final['serialized'])
        with self.assertRaises(ValueError):self.call('planar-tune-trial',document=final['serialized'],index=True)

    def test_foreign_checkpoint_and_unverified_target_rejected(self):
        first=self.call('planar-start-tune',request=self.raw,max_new_trials=1)['id'];self.wait(first)
        second=self.call('planar-start-tune',request=self.raw,max_new_trials=1)['id'];self.wait(second)
        source=self.manager.directory(first)/'execution/checkpoint-001.json'
        target=self.manager.directory(second)/'execution/checkpoint-001.json';target.write_bytes(source.read_bytes())
        with self.assertRaisesRegex(ValueError,'another tuning job'):
            self.call('planar-open-tune-checkpoint',id=second,index=1)
        raw=dict(self.raw,bounds=[.18,.2]);ident=self.call('planar-start-tune',request=raw)['id'];self.wait(ident)
        result=self.call('planar-tune-result',id=ident)
        self.assertEqual(result['document']['status'],'UNVERIFIED')
        with self.assertRaisesRegex(ValueError,'individually confirmed'):
            self.call('planar-tune-trial',document=result['serialized'],index=2)
        tampered=deepcopy(result['document']);tampered['trials'][-1]['frequency_hz']=1.
        with self.assertRaises(ValueError):self.call('planar-replay-tune',document=tampered)

    def test_stopped_checkpoint_rejects_changed_submitted_envelope(self):
        ident=self.call('planar-start-tune',request=self.raw,max_new_trials=1)['id'];self.wait(ident)
        path=self.manager.directory(ident)/'planar-tune-request.json'
        value=json.loads(path.read_text());value['max_new_trials']=2;path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'input changed'):
            self.call('planar-open-tune-checkpoint',id=ident,index=1)
