# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from superfish_ng import Case
from superfish_ng.project import Project
from superfish_ng.studies import Study,execute_study
from superfish_ng.completion import digest
from superfish_ng.study_mode_tracking import build_study_mode_tracking,save_study_mode_tracking,read_study_mode_tracking,replay_study_mode_tracking

class StudyModeTrackingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup);cls.root=Path(cls.tmp.name)
        case=Case(((0.,.1),(.055,.1)),nr=8,nz=8,modes=3,element_order=2)
        study=Study(Project.from_dict(case.to_dict()),'sweep','/case/geometry/points_zr_m/1/0',[.055,.075,.08])
        execute_study(study,cls.root/'study')
        cls.controls=dict(mapping='normalized_cylinder',sample_order=12,minimum_overlap=.98,minimum_assignment_margin=.05,relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)

    def request(self):return dict(schema_version=1,study_run='study',initial_ids=['TM010','TM020','TM011'],step_controls=[dict(self.controls),dict(self.controls)])

    def test_complete_study_crossing_and_saved_replay_without_resolving(self):
        out=self.root/'tracking.json'
        with patch('superfish_ng.jobs.solve',side_effect=AssertionError('must use saved fields')):
            result=save_study_mode_tracking(self.request(),out,base_directory=self.root)
            self.assertEqual(read_study_mode_tracking(out),result)
        self.assertEqual(result['status'],'PASS');self.assertEqual(result['visited_point_indices'],[0,1,2])
        self.assertEqual(result['point_results'][1]['current_mode_ids'],['TM010','TM011','TM020'])
        self.assertEqual(result['point_results'][2]['current_mode_ids'],['TM010','TM011','TM020'])
        self.assertEqual(result['unvisited_point_indices'],[])
        with self.assertRaises(FileExistsError):save_study_mode_tracking(self.request(),out,base_directory=self.root)
        original=json.loads((self.root/'study'/'study-results.json').read_text())
        self.assertEqual(original['mode_tracking'],'not performed; independent spectra')

    def test_unverified_pair_stops_without_skipping_and_checks_unused_controls(self):
        request=self.request();request['step_controls'][0]['minimum_overlap']=1
        out=self.root/'unknown.json';result=save_study_mode_tracking(request,out,base_directory=self.root)
        self.assertEqual(result['status'],'UNVERIFIED');self.assertEqual(result['unvisited_point_indices'],[2])
        self.assertEqual(result['point_results'][2]['status'],'NOT_VISITED');self.assertIsNone(result['point_results'][2]['current_mode_ids'])
        self.assertEqual(read_study_mode_tracking(out),result)
        request['step_controls'][1]['unsupported']=True
        with self.assertRaises(ValueError):build_study_mode_tracking(request,base_directory=self.root)

    def test_incomplete_point_is_not_skipped(self):
        path=self.root/'study'/'point-002'/'job.json';original=path.read_bytes()
        try:
            state=json.loads(original);state['status']='failed';path.write_text(json.dumps(state))
            with self.assertRaisesRegex(ValueError,'incomplete'):build_study_mode_tracking(self.request(),base_directory=self.root)
        finally:path.write_bytes(original)

    def test_coherently_rehashed_but_reordered_study_summary_is_rejected(self):
        path=self.root/'study'/'study-results.json';manifest=self.root/'study'/'manifest.json'
        original=path.read_bytes();old_manifest=manifest.read_bytes()
        try:
            report=json.loads(original);report['points'][0],report['points'][1]=report['points'][1],report['points'][0]
            path.write_text(json.dumps(report));data=json.loads(old_manifest);data['files']['study-results.json']=digest(path);manifest.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'order'):build_study_mode_tracking(self.request(),base_directory=self.root)
        finally:path.write_bytes(original);manifest.write_bytes(old_manifest)

    def test_source_mutation_and_saved_document_modification_rejected(self):
        from superfish_ng.mode_tracking_history import start_mode_history
        path=self.root/'study'/'job.json';original=path.read_bytes();out=self.root/'unstable.json'
        def changing(pair):
            result=start_mode_history(pair);path.write_bytes(original+b'\n');return result
        try:
            with patch('superfish_ng.study_mode_tracking.start_mode_history',side_effect=changing):
                with self.assertRaisesRegex(ValueError,'changed'):save_study_mode_tracking(self.request(),out,base_directory=self.root)
            self.assertFalse(out.exists())
        finally:path.write_bytes(original)
        result=build_study_mode_tracking(self.request(),base_directory=self.root);changed=deepcopy(result);changed['point_results'][1]['current_mode_ids'][0]='fake'
        with self.assertRaisesRegex(ValueError,'replay'):replay_study_mode_tracking(changed)

    def test_cli_request_relative_paths_and_strict_configuration(self):
        from superfish_ng.cli import main
        request_path=self.root/'request.json';request_path.write_text(json.dumps(self.request()));out=self.root/'cli.json'
        self.assertEqual(main(['track-study-modes',str(request_path),'--out',str(out)]),0)
        self.assertEqual(main(['replay-study-mode-tracking',str(out)]),0)
        for modify in [lambda r:r.update(schema_version=True),lambda r:r['step_controls'].pop(),lambda r:r['step_controls'][1].update(sample_order=True)]:
            request=self.request();modify(request)
            with self.assertRaises(ValueError):build_study_mode_tracking(request,base_directory=self.root)
