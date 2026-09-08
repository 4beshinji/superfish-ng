# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from superfish_ng import Case,solve
from superfish_ng.io import save_run
from superfish_ng.saved_mode_tracking import build_saved_mode_tracking,save_mode_tracking,read_mode_tracking,replay_mode_tracking

class SavedModeTrackingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup);cls.root=Path(cls.tmp.name)
        for name,length,modes in (('a',.055,3),('b',.075,3),('short',.075,2)):
            case=Case(((0.,.1),(length,.1)),nr=8,nz=8,modes=modes,element_order=2)
            save_run(case,solve(case),cls.root/name)

    def request(self):
        return dict(schema_version=1,previous_run='a',current_run='b',previous_ids=['TM010','TM020','TM011'],controls=dict(
            mapping='normalized_cylinder',sample_order=12,minimum_overlap=.98,minimum_assignment_margin=.05,
            relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8))

    def test_saved_replay_uses_fields_and_preserves_frequency_rank_change(self):
        out=self.root/'tracking.json'
        result=save_mode_tracking(self.request(),out,base_directory=self.root)
        self.assertEqual(result['status'],'PASS')
        self.assertEqual(result['tracking']['current_mode_ids'],['TM010','TM011','TM020'])
        self.assertEqual(result['request']['previous_run'],str(self.root/'a'))
        self.assertIn('fields.npz',result['sources'][0]['sha256'])
        with patch('superfish_ng.solver.solve',side_effect=AssertionError('must use saved fields')):
            self.assertEqual(read_mode_tracking(out),result)
        original=out.read_bytes()
        with self.assertRaises(FileExistsError):save_mode_tracking(self.request(),out,base_directory=self.root)
        self.assertEqual(out.read_bytes(),original)

    def test_modified_tracking_controls_id_source_and_schema_rejected(self):
        result=build_saved_mode_tracking(self.request(),base_directory=self.root)
        variants=[]
        altered=deepcopy(result);altered['tracking']['current_mode_ids'][0]='changed';variants.append(altered)
        altered=deepcopy(result);altered['request']['controls']['minimum_overlap']=.8;variants.append(altered)
        altered=deepcopy(result);altered['sources'][0]['sha256']['fields.npz']='0'*64;variants.append(altered)
        altered=deepcopy(result);altered['schema_version']=2;variants.append(altered)
        for changed in variants:
            with self.assertRaisesRegex(ValueError,'replay'):replay_mode_tracking(changed)
        changed=deepcopy(result);changed['request']['previous_run']='relative'
        with self.assertRaisesRegex(ValueError,'absolute'):replay_mode_tracking(changed)

    def test_source_change_during_comparison_prevents_output(self):
        from superfish_ng.mode_tracking import track_cylindrical_modes
        target=self.root/'a'/'results.json';original=target.read_bytes();out=self.root/'unstable.json'
        def changed(*args,**kwargs):
            report=track_cylindrical_modes(*args,**kwargs);target.write_bytes(original+b'\n');return report
        try:
            with patch('superfish_ng.saved_mode_tracking.track_cylindrical_modes',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'changed during'):save_mode_tracking(self.request(),out,base_directory=self.root)
            self.assertFalse(out.exists())
        finally:target.write_bytes(original)

    def test_valid_but_different_source_identity_is_rejected(self):
        result=build_saved_mode_tracking(self.request(),base_directory=self.root)
        marker=self.root/'a'/'save_complete.json';original=marker.read_bytes()
        try:
            # Whitespace keeps a valid completion JSON but changes its byte identity.
            marker.write_bytes(original+b'\n')
            with self.assertRaisesRegex(ValueError,'replay'):replay_mode_tracking(result)
        finally:marker.write_bytes(original)

    def test_unverified_results_are_saved_and_replayable(self):
        request=self.request();request['current_run']='short';out=self.root/'unknown.json'
        result=save_mode_tracking(request,out,base_directory=self.root)
        self.assertEqual(result['status'],'UNVERIFIED');self.assertTrue(out.is_file())
        self.assertEqual(read_mode_tracking(out),result)
        self.assertTrue(result['tracking']['unmatched_previous'])

    def test_strict_request_and_cli_relative_paths(self):
        from superfish_ng.cli import main
        request=self.request();source=self.root/'request.json';out=self.root/'cli-tracking.json'
        source.write_text(json.dumps(request))
        self.assertEqual(main(['track-modes',str(source),'--out',str(out)]),0)
        self.assertEqual(main(['replay-mode-tracking',str(out)]),0)
        request['current_run']='short';source.write_text(json.dumps(request));unknown=self.root/'cli-unknown.json'
        self.assertEqual(main(['track-modes',str(source),'--out',str(unknown)]),1)
        self.assertEqual(main(['replay-mode-tracking',str(unknown)]),1)
        for changed in (dict(request,extra=True),dict(request,schema_version=True)):
            with self.assertRaises(ValueError):build_saved_mode_tracking(changed,base_directory=self.root)
        changed=deepcopy(request);del changed['controls']['sample_order']
        with self.assertRaises(ValueError):build_saved_mode_tracking(changed,base_directory=self.root)

if __name__=='__main__':unittest.main()
