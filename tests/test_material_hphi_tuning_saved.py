# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from pathlib import Path
import json,tempfile,unittest
from unittest.mock import patch
import numpy as np
from test_material_hphi_tuning import request
from superfish_ng.material_hphi_saved import read_material_hphi_run,material_hphi_result


class MaterialHphiTuneSavedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from superfish_ng.material_hphi_tuning_saved import execute_material_hphi_tune
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name);cls.request=request()
        cls.first=execute_material_hphi_tune(cls.request,cls.root/'first',max_new_trials=1)
        cls.second=execute_material_hphi_tune(cls.request,cls.root/'second',checkpoint=cls.first,max_new_trials=1)

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def test_owned_portable_replay_and_resume_preserve_full_native(self):
        from superfish_ng.material_hphi_tuning_saved import read_material_hphi_tune
        self.assertEqual(self.first['status'],'PAUSED');self.assertEqual(self.second['status'],'PAUSED')
        self.assertEqual(len(self.second['trial_runs']),2)
        with patch('superfish_ng.material_hphi_tuning_saved.solve_material_hphi',side_effect=AssertionError('replay solved')):
            self.assertEqual(read_material_hphi_tune(self.root/'second/checkpoint-002.json'),self.second)
        a,b=[read_material_hphi_run(Path(c['trial_runs'][0])/'solution') for c in (self.first,self.second)]
        np.testing.assert_array_equal(a.coefficients,b.coefficients)
        np.testing.assert_array_equal(a.frequencies_hz,b.frequencies_hz)
        self.assertEqual(material_hphi_result(a),material_hphi_result(b))
        self.assertEqual(a.case.to_dict(),b.case.to_dict())
        for run in self.second['trial_runs']:
            self.assertEqual({p.name for p in Path(run).iterdir()},{'project.json','solution'})
        raw=json.loads((self.root/'second/checkpoint-002.json').read_text())
        self.assertEqual(raw['trial_runs'],['trial-001','trial-002'])

    def test_moving_source_and_whole_owned_output_needs_no_original(self):
        from superfish_ng.material_hphi_tuning_saved import read_material_hphi_tune
        original=self.root/'first';moved=self.root/'first-moved';original.rename(moved)
        target=self.root/'second';relocated=self.root/'second-moved';target.rename(relocated)
        try:
            replay=read_material_hphi_tune(relocated/'checkpoint-002.json')
            self.assertEqual(replay['trials'],self.second['trials'])
            self.assertEqual(replay['trial_runs'],[str(relocated/f'trial-{i:03d}') for i in (1,2)])
        finally:relocated.rename(target);moved.rename(original)

    def test_tampering_paths_and_request_mismatch_rejected(self):
        from superfish_ng.material_hphi_tuning_saved import read_material_hphi_tune,replay_material_hphi_tune,execute_material_hphi_tune
        fields=Path(self.second['trial_runs'][0])/'solution/fields.npz';original=fields.read_bytes()
        try:
            fields.write_bytes(original+b'changed')
            with self.assertRaises(ValueError):read_material_hphi_tune(self.root/'second/checkpoint-002.json')
        finally:fields.write_bytes(original)
        for name,value in (('schema_version',True),('can_resume',1),('format','superfish_ng_hphi_tune_checkpoint'),('extra',0)):
            bad=deepcopy(self.second);bad[name]=value
            with self.assertRaises(ValueError):replay_material_hphi_tune(bad)
        bad=deepcopy(self.second);bad['trials'][0]['frequency_hz']*=1.01
        with self.assertRaises(ValueError):replay_material_hphi_tune(bad)
        changed=deepcopy(self.request);changed['target_hz']*=2
        with self.assertRaisesRegex(ValueError,'request differs'):
            execute_material_hphi_tune(changed,self.root/'rejected',checkpoint=self.first)
        self.assertFalse((self.root/'rejected').exists())
        with self.assertRaises(FileExistsError):execute_material_hphi_tune(self.request,self.root/'first')

    def test_failed_resume_preserves_verified_prefix(self):
        from superfish_ng.material_hphi_tuning_saved import execute_material_hphi_tune,read_material_hphi_tune
        target=self.root/'failed-resume'
        with patch('superfish_ng.material_hphi_tuning_saved.solve_material_hphi',side_effect=RuntimeError('injected solve failure')):
            with self.assertRaisesRegex(RuntimeError,'injected solve failure'):
                execute_material_hphi_tune(self.request,target,checkpoint=self.first,max_new_trials=1)
        prefix=read_material_hphi_tune(target/'checkpoint-001.json')
        self.assertEqual(prefix['trials'],self.first['trials'])
        self.assertTrue(prefix['can_resume'])
        self.assertFalse((target/'checkpoint-002.json').exists())
        failure=json.loads((target/'failure-002.json').read_text())
        self.assertEqual(failure['status'],'FAILED')
        self.assertEqual(failure['preceding_trial_runs'],prefix['trial_runs'])

    def test_traversal_and_symbolic_links_rejected_before_native_read(self):
        from superfish_ng.material_hphi_tuning_saved import replay_material_hphi_tune,read_material_hphi_tune
        raw=json.loads((self.root/'first/checkpoint-001.json').read_text())
        for path in ('../first/trial-001',str(self.root/'second/trial-001')):
            bad=deepcopy(raw);bad['trial_runs']=[path]
            with self.assertRaises(ValueError):replay_material_hphi_tune(bad,base_directory=self.root/'first')
        link=self.root/'checkpoint-link.json';link.symlink_to(self.root/'first/checkpoint-001.json')
        with self.assertRaises(ValueError):read_material_hphi_tune(link)
        fields=Path(self.first['trial_runs'][0])/'solution/fields.npz';backup=fields.with_suffix('.backup')
        fields.rename(backup);fields.symlink_to(backup)
        try:
            with self.assertRaises(ValueError):read_material_hphi_tune(self.root/'first/checkpoint-001.json')
        finally:fields.unlink();backup.rename(fields)
