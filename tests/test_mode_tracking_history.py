# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from superfish_ng import Case,solve
from superfish_ng.io import save_run
from superfish_ng.saved_mode_tracking import build_saved_mode_tracking
from superfish_ng.mode_tracking_history import start_mode_history,extend_mode_history,replay_mode_history,save_mode_history,read_mode_history

class ModeHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup);cls.root=Path(cls.tmp.name)
        for name,length,modes in [('a',.055,3),('b',.075,3),('c',.08,3),('short',.08,2)]:
            case=Case(((0.,.1),(length,.1)),nr=8,nz=8,modes=modes,element_order=2)
            save_run(case,solve(case),cls.root/name)
        cls.controls=dict(mapping='normalized_cylinder',sample_order=12,minimum_overlap=.98,minimum_assignment_margin=.05,relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)

    def pair(self,**changes):
        request=dict(schema_version=1,previous_run='a',current_run='b',previous_ids=['TM010','TM020','TM011'],controls=self.controls)
        request.update(changes)
        return build_saved_mode_tracking(request,base_directory=self.root)

    def extend(self,history,current='c'):
        return extend_mode_history(history,dict(current_run=current,controls=self.controls),base_directory=self.root)

    def test_crossing_resume_preserves_ids_and_original_document(self):
        first=start_mode_history(self.pair());original=deepcopy(first)
        second=self.extend(first)
        self.assertEqual(first,original);self.assertEqual(second['status'],'PASS')
        self.assertEqual(second['current_mode_ids'],['TM010','TM011','TM020'])
        self.assertEqual(second['steps'][1]['tracking']['previous_identity_groups'],first['current_identity_groups'])
        path=self.root/'resume.json';save_mode_history(second,path)
        self.assertEqual(read_mode_history(path),second)
        with self.assertRaises(FileExistsError):save_mode_history(second,path)

    def test_unverified_step_is_retained_and_stops_extension(self):
        failed=self.extend(start_mode_history(self.pair()),'short')
        self.assertEqual(len(failed['steps']),2);self.assertEqual(failed['status'],'UNVERIFIED')
        self.assertFalse(failed['can_extend']);self.assertIsNotNone(failed['stop_reason'])
        path=self.root/'failed.json';save_mode_history(failed,path);self.assertEqual(read_mode_history(path),failed)
        with self.assertRaisesRegex(ValueError,'unresolved'):self.extend(failed)

    def test_subspace_has_no_arbitrary_individual_id_propagation(self):
        controls=dict(self.controls,relative_cluster_gap=.9)
        history=start_mode_history(self.pair(controls=controls))
        self.assertEqual(history['steps'][0]['status'],'PASS')
        self.assertEqual(history['status'],'PASS');self.assertTrue(history['can_extend'])
        self.assertFalse(history['individual_ids_complete'])
        self.assertEqual(self.extend(history)['status'],'UNVERIFIED')

    def test_individually_valid_but_disconnected_steps_are_rejected(self):
        good=self.extend(start_mode_history(self.pair()))
        for replacement in [self.pair(current_run='c'),self.pair(previous_run='b',current_run='c',previous_ids=['wrong','ids','here'])]:
            changed=deepcopy(good);changed['steps'][1]=replacement
            with self.assertRaisesRegex(ValueError,'continuity'):replay_mode_history(changed)
        for key,value in [('current_mode_ids',['wrong']),('schema_version',True),('can_extend',False),('steps',[])]:
            changed=deepcopy(good);changed[key]=value
            with self.assertRaises(ValueError):replay_mode_history(changed)

    def test_stale_ancestor_blocks_resume_and_strict_extension(self):
        history=start_mode_history(self.pair());path=self.root/'a'/'save_complete.json';original=path.read_bytes()
        try:
            path.write_bytes(original+b'\n')
            with self.assertRaisesRegex(ValueError,'replay'):self.extend(history)
        finally:path.write_bytes(original)
        with self.assertRaises(ValueError):extend_mode_history(history,dict(current_run='c',controls=self.controls,previous_ids=['override']),base_directory=self.root)

    def test_cli_start_extend_replay(self):
        from superfish_ng.cli import main
        pair_path=self.root/'pair.json';pair_path.write_text(json.dumps(self.pair()))
        first=self.root/'cli-first.json';second=self.root/'cli-second.json';request=self.root/'extension.json'
        request.write_text(json.dumps(dict(current_run='c',controls=self.controls)))
        self.assertEqual(main(['start-mode-history',str(pair_path),'--out',str(first)]),0)
        self.assertEqual(main(['extend-mode-history',str(first),str(request),'--out',str(second)]),0)
        self.assertEqual(main(['replay-mode-history',str(second)]),0)
        self.assertEqual(read_mode_history(second)['current_mode_ids'],['TM010','TM011','TM020'])
