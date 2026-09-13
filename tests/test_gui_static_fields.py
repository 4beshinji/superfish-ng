# SPDX-License-Identifier: Apache-2.0
import copy
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from test_static_field_project import cases, solve_and_result
from test_static_field_jobs import failure_cases, wait
from superfish_ng import gui_static_fields as gui
from superfish_ng import static_field_jobs as static
from superfish_ng.jobs import JobManager
from superfish_ng.static_field_project import StaticFieldProject
from superfish_ng.model import capabilities


class StaticFieldGuiTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.manager=JobManager(self.root/'workspace');self.addCleanup(self.manager.close)
        self.access=gui.StaticFieldAccess(self.manager);self.addCleanup(self.access.close)

    def call(self,action,**data):return gui.static_field_response(self.manager,self.access,action,data)

    def ready(self,identifier,access=None):
        access=self.access if access is None else access;end=time.monotonic()+120
        while time.monotonic()<end:
            result=access.result(identifier)
            if result['status']!='verifying':
                self.assertEqual(result['status'],'ready',result);return result
            time.sleep(.01)
        self.fail('static display verification timed out')

    def prepare(self,identifier,case):
        path=self.manager.directory(identifier);project=StaticFieldProject(case,'m')
        result=static.execute_static_field_project(project,path);return path,result

    def test_all_case_inputs_units_duplicate_keys_and_downloaded_project_bytes(self):
        for case in cases():
            original=case.to_dict();project=StaticFieldProject(case,'m')
            for unit in (None,'m','mm'):
                value,media=self.call('static-project-validate',document=project.dumps(),display_length_unit=unit)
                self.assertEqual(value['case'],original);self.assertEqual(value['display_length_unit'],unit or 'm')
                raw,media=self.call('static-project-download',document=project.dumps(),display_length_unit=unit)
                self.assertEqual(raw,StaticFieldProject.from_dict(value).dumps().encode());self.assertEqual(media,'application/json')
        text=project.dumps().replace('"project_version": 1','"project_version": 1, "project_version": 1')
        with self.assertRaisesRegex(ValueError,'duplicate'):self.call('static-project-validate',document=text,display_length_unit=None)
        for unit in (True,[],1,'cm'):
            with self.assertRaises(ValueError):self.call('static-project-validate',document=project.dumps(),display_length_unit=unit)
        for value in ({},None,[],1):
            with self.assertRaises(ValueError):self.call('static-project-validate',document=value,display_length_unit=None)
        with self.assertRaises(ValueError):self.call('static-project-validate',document='{"format":"unknown"}',display_length_unit=None)

    def test_every_static_family_and_order_displays_original_cell_center_fields_and_full_results(self):
        for index,case in enumerate(cases()):
            path,expected=self.prepare(str(index),case);result=self.ready(path.name);view=result['view']
            self.assertEqual(view['project'],expected['project']);self.assertEqual(view['outcome'],expected['outcome'])
            solution,reference=solve_and_result(case);self.assertEqual(view['outcome'],reference)
            mesh=case.partition.mesh;points=getattr(mesh,'points_xy_m',None)
            if points is None:points=mesh.points_rz_m
            expected_probe=solution.probe_at(points[mesh.triangles].mean(axis=1))
            self.assertEqual(view['plot']['cell_center_probe'],expected_probe)
            self.assertEqual(view['plot']['points_m'],points.tolist());self.assertEqual(view['plot']['triangles'],mesh.triangles.tolist())
            self.assertEqual(view['plot']['boundary_edges'],mesh.boundary_edges.tolist())
            self.assertEqual(view['plot']['field_units'],{key:gui.FIELD_UNITS[key] for key in expected_probe['fields']})
            self.assertEqual(view['measure'],'per_unit_length' if 'points_xy_m' in expected_probe else 'full_axisymmetric_domain')
            self.assertEqual(len(view['not_applicable']),4);self.assertEqual(len(result['files']),6)
            for name in result['files']:self.assertEqual(self.access.download(path.name,name),(path/name).read_bytes())

    def test_all_bh_failure_types_keep_original_history_and_no_plot(self):
        for index,case in enumerate(failure_cases()):
            path,expected=self.prepare(str(index),case);result=self.ready(path.name);view=result['view']
            self.assertEqual(view['solver_status'],'nonlinear_failed');self.assertIsNone(view['plot'])
            self.assertEqual(view['outcome'],expected['outcome']);self.assertEqual(view['project'],expected['project'])
            self.assertEqual(len(result['files']),4);self.assertNotIn('solution/results.json',result['files'])
            for name in result['files']:self.assertEqual(self.access.download(path.name,name),(path/name).read_bytes())

    def test_async_verification_restart_copy_ownership_and_changed_files_reject(self):
        path,expected=self.prepare('example',next(cases()));entered=threading.Event();release=threading.Event();original=gui.static_field_view
        def paused(directory):entered.set();self.assertTrue(release.wait(10));return original(directory)
        with patch.object(gui,'static_field_view',side_effect=paused) as replay:
            result=self.access.result(path.name);self.assertEqual(result['status'],'verifying');self.assertTrue(entered.wait(5))
            try:
                with self.assertRaisesRegex(ValueError,'wait'):self.access.download(path.name,'project.json')
            finally:release.set()
            first=self.ready(path.name);self.assertEqual(replay.call_count,1)
            first['view']['project']['case']['name']='caller copy';self.assertNotEqual(self.ready(path.name)['view']['project']['case']['name'],'caller copy')
        self.access.close();self.access=gui.StaticFieldAccess(self.manager);self.addCleanup(self.access.close)
        with patch.object(gui,'static_field_view',wraps=original) as replay:
            self.assertEqual(self.ready(path.name)['view']['outcome'],expected['outcome']);self.assertEqual(replay.call_count,1)
        project=path/'project.json';project.write_text(project.read_text()+' ')
        with self.assertRaisesRegex(ValueError,'changed after'):self.access.result(path.name)
        with self.assertRaisesRegex(ValueError,'changed after'):self.access.download(path.name,'project.json')
        self.access.close();self.access=gui.StaticFieldAccess(self.manager);self.addCleanup(self.access.close)
        end=time.monotonic()+10
        while time.monotonic()<end:
            result=self.access.result(path.name)
            if result['status']!='verifying':break
            time.sleep(.01)
        self.assertEqual(result['status'],'failed');self.assertNotIn('view',result)

    def test_real_worker_actions_success_saved_failure_and_cancelled_project(self):
        for case in [next(cases()),failure_cases()[0],failure_cases()[3],failure_cases()[6]]:
            project=StaticFieldProject(case,'m')
            result,media=self.call('static-project-solve',document=project.dumps(),display_length_unit=None)
            state=wait(self.manager,result['id']);view=self.ready(result['id'])['view']
            self.assertEqual(view['project'],project.to_dict())
            self.assertEqual(state['status'],'failed' if view['solver_status']=='nonlinear_failed' else 'complete')
        path=self.manager.directory('queued');static._prepare(StaticFieldProject(next(cases())),path)
        result=self.access.result(path.name);self.assertEqual(result['status'],'queued');self.assertNotIn('view',result)
        self.manager.cancel(path.name);result=self.access.result(path.name);self.assertEqual(result['status'],'cancelled');self.assertNotIn('view',result)
        listed,_=self.call('static-field-jobs');self.assertEqual(len(listed),5)

    def test_strict_actions_closed_access_download_traversal_and_capability_contract(self):
        path,_=self.prepare('example',next(cases()));self.ready(path.name)
        for name in ('../project.json','job.json','manifest.json','solution/../project.json',None):
            with self.assertRaises(ValueError):self.call('static-field-download',id=path.name,file=name)
        for action,data in [('static-field-result',dict(id=path.name,mode=1)),('static-field-jobs',dict(extra=1)),('unknown',{})]:
            with self.assertRaises(ValueError):self.call(action,**data)
        inventory=capabilities()['static_field_gui'];self.assertEqual(inventory['field_units'],gui.FIELD_UNITS)
        self.assertEqual(inventory['gui_actions'],gui.ACTIONS);self.assertEqual(len(inventory['case_families']),11)
        self.assertTrue(inventory['gui']);self.assertFalse(inventory['study'])
        self.access.close()
        with self.assertRaisesRegex(ValueError,'closed'):self.access.result(path.name)


if __name__=='__main__':unittest.main()
