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
from superfish_ng import gui_static_field_studies as gui
from superfish_ng import static_field_study_jobs as jobs
from superfish_ng.jobs import JobManager
from superfish_ng.static_field_project import StaticFieldProject
from superfish_ng.static_field_study import StaticFieldStudy
from superfish_ng.model import capabilities


class StaticFieldStudyGuiTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name); self.manager = JobManager(self.root / 'workspace'); self.addCleanup(self.manager.close)
        self.access = gui.StaticFieldStudyAccess(self.manager); self.addCleanup(self.access.close)

    def call(self, action, **data): return gui.static_field_study_response(self.manager, self.access, action, data)

    def ready(self, identifier, index=None, access=None):
        access = access or self.access; end = time.monotonic() + 180
        while time.monotonic() < end:
            result = access.result(identifier) if index is None else access.point(identifier, index)
            if result['status'] != 'verifying':
                self.assertEqual(result['status'], 'ready', result); return result
            time.sleep(.01)
        self.fail('static Study display verification timed out')

    def prepare(self, identifier, case, parameter='excitation_scale', values=(0., 1.)):
        study = StaticFieldStudy(StaticFieldProject(case, 'mm'), parameter, values)
        path = self.manager.directory(identifier); result = jobs.execute_static_field_study(study, path)
        return path, study, result

    def test_all_families_parameters_units_and_strict_json_input(self):
        for case in cases():
            for parameter, values in [('uniform_scale', (1., 2.)), ('excitation_scale', (-0., 1.))]:
                study = StaticFieldStudy(StaticFieldProject(case, 'm'), parameter, values)
                for unit in (None, 'm', 'mm'):
                    result, media = self.call('static-study-validate', document=study.dumps(), display_length_unit=unit)
                    expected = study.to_dict(); expected['project']['display_length_unit'] = unit or 'm'
                    self.assertEqual(result, expected)
                    raw, _ = self.call('static-study-download-input', document=study.dumps(), display_length_unit=unit)
                    self.assertEqual(raw, StaticFieldStudy.from_dict(expected).dumps().encode())
                    if parameter == 'excitation_scale': self.assertIn(b'-0.0', raw)
        text = study.dumps().replace('"study_version": 1', '"study_version": 1, "study_version": 1')
        for document in (text, {}, None, '[]', '{"format":"unknown"}'):
            with self.assertRaises(ValueError): self.call('static-study-validate', document=document, display_length_unit=None)
        for unit in (True, 1, [], 'cm'):
            with self.assertRaises(ValueError): self.call('static-study-validate', document=study.dumps(), display_length_unit=unit)

    def test_every_family_order_and_parameter_retains_all_points_original_fields_and_bytes(self):
        for number, case in enumerate(cases()):
            for parameter, values in [('uniform_scale', (1., 2.)), ('excitation_scale', (0., 1.))]:
                path, study, expected = self.prepare(str(number) + '-' + parameter, case, parameter, values)
                result = self.ready(path.name); self.assertEqual(result['summary'], expected)
                self.assertEqual(len(result['files']), 14)
                for index, project in enumerate(study.projects()):
                    point = self.ready(path.name, index); view = point['view']; solution, outcome = solve_and_result(project.case)
                    self.assertEqual(point['point'], expected['points'][index]); self.assertEqual(view['project'], project.to_dict())
                    self.assertEqual(view['outcome'], outcome); self.assertEqual(view['solver_status'], 'complete')
                    mesh = project.case.partition.mesh; points = getattr(mesh, 'points_xy_m', None)
                    if points is None: points = mesh.points_rz_m
                    probe = solution.probe_at(points[mesh.triangles].mean(axis=1))
                    self.assertEqual(view['plot']['cell_center_probe'], probe)
                    self.assertEqual(view['plot']['points_m'], points.tolist()); self.assertEqual(view['plot']['triangles'], mesh.triangles.tolist())
                    self.assertEqual(view['plot']['field_units'], {name: gui.FIELD_UNITS[name] for name in probe['fields']})
                    self.assertEqual(len(point['files']), 6)
                for name in result['files']: self.assertEqual(self.access.download(path.name, name), (path / name).read_bytes())

    def test_actual_failures_keep_complete_study_separate_from_success_and_no_plot(self):
        for number, case in enumerate(failure_cases()):
            path, study, expected = self.prepare('failed-' + str(number), case, 'uniform_scale', (1., 1.))
            result = self.ready(path.name); self.assertEqual(result['summary'], expected)
            self.assertFalse(result['summary']['all_points_successful']); self.assertEqual(result['summary']['nonlinear_failed_points'], 2)
            self.assertEqual(self.manager.status(path.name)['status'], 'complete'); self.assertEqual(len(result['files']), 10)
            for index in range(2):
                point = self.ready(path.name, index); self.assertIsNone(point['view']['plot'])
                self.assertEqual(point['view']['outcome'], expected['points'][index]['result']['outcome'])
                self.assertEqual(point['view']['solver_status'], 'nonlinear_failed')
            for name in result['files']: self.assertEqual(self.access.download(path.name, name), (path / name).read_bytes())

    def test_async_full_replay_lazy_points_restart_copies_and_tamper_reject(self):
        path, study, expected = self.prepare('example', next(cases()))
        entered = threading.Event(); release = threading.Event(); original = gui.read_static_field_study
        def paused(directory): entered.set(); self.assertTrue(release.wait(10)); return original(directory)
        with patch.object(gui, 'read_static_field_study', side_effect=paused) as replay:
            self.assertEqual(self.access.result(path.name)['status'], 'verifying'); self.assertTrue(entered.wait(5))
            try:
                self.assertEqual(self.access.point(path.name, 0)['status'], 'verifying')
                with self.assertRaisesRegex(ValueError, 'wait'): self.access.download(path.name, 'study.json')
            finally: release.set()
            result = self.ready(path.name); self.assertEqual(replay.call_count, 1)
            result['summary']['points'].clear(); self.assertEqual(len(self.ready(path.name)['summary']['points']), 2)
        with patch.object(gui, 'static_field_view', wraps=gui.static_field_view) as render:
            self.ready(path.name, 0); self.ready(path.name, 0); self.assertEqual(render.call_count, 1)
            self.ready(path.name, 1); self.assertEqual(render.call_count, 2)
        self.access.close(); self.access = gui.StaticFieldStudyAccess(self.manager); self.addCleanup(self.access.close)
        with patch.object(gui, 'read_static_field_study', wraps=original) as replay:
            self.assertEqual(self.ready(path.name)['summary'], expected); self.assertEqual(replay.call_count, 1)
        changed = path / 'point-0001/project.json'; changed.write_text(changed.read_text() + ' ')
        for operation in (lambda: self.access.result(path.name), lambda: self.access.point(path.name, 0), lambda: self.access.download(path.name, 'study.json')):
            with self.assertRaisesRegex(ValueError, 'changed after'): operation()
        self.access.close(); self.access = gui.StaticFieldStudyAccess(self.manager); self.addCleanup(self.access.close)
        end = time.monotonic() + 15
        while time.monotonic() < end:
            result = self.access.result(path.name)
            if result['status'] != 'verifying': break
            time.sleep(.01)
        self.assertEqual(result['status'], 'failed'); self.assertNotIn('summary', result)

    def test_real_worker_success_mixed_outcomes_and_cancelled_never_display_complete(self):
        from test_static_field_project import planar_bh, axis_bh, off_axis_bh
        studies = [StaticFieldStudy(StaticFieldProject(next(cases())), 'excitation_scale', (0., 1.))]
        studies.extend(StaticFieldStudy(StaticFieldProject(factory(n=2)[0]), 'excitation_scale', (0., 1., 1000.))
                       for factory in (planar_bh, axis_bh, off_axis_bh))
        for study in studies:
            result, _ = self.call('static-study-solve', document=study.dumps(), display_length_unit=None)
            state = wait(self.manager, result['id']); self.assertEqual(state['status'], 'complete')
            summary = self.ready(result['id'])['summary']; self.assertEqual(summary['study'], study.to_dict())
            for index in range(len(study.values)): self.ready(result['id'], index)
        path = self.manager.directory('queued'); jobs._prepare(studies[0], path)
        self.assertEqual(self.access.result(path.name)['status'], 'queued')
        self.manager.cancel(path.name); result = self.access.result(path.name)
        self.assertEqual(result['status'], 'cancelled'); self.assertNotIn('summary', result)
        listed, _ = self.call('static-study-jobs'); self.assertEqual(len(listed), 5)

    def test_strict_actions_selection_downloads_closed_access_and_capabilities(self):
        path, _, _ = self.prepare('example', next(cases())); self.ready(path.name)
        for index in (True, -1, 2, '0', None):
            with self.assertRaises(ValueError): self.access.point(path.name, index)
        for name in ('../study.json', 'job.json', 'manifest.json', 'point-0000/job.json', 'point-0000/../study.json', None):
            with self.assertRaises(ValueError): self.access.download(path.name, name)
        for action, data in [('unknown', {}), ('static-study-jobs', dict(extra=1)), ('static-study-point', dict(id=path.name, index=0, mode=1))]:
            with self.assertRaises(ValueError): self.call(action, **data)
        inventory = capabilities()['static_field_study_gui']; self.assertEqual(inventory['gui_actions'], gui.ACTIONS)
        self.assertEqual(inventory['field_units'], gui.FIELD_UNITS); self.assertEqual(len(inventory['case_families']), 11)
        self.assertTrue(inventory['gui']); self.assertTrue(inventory['study'])
        self.access.close()
        with self.assertRaisesRegex(ValueError, 'closed'): self.access.result(path.name)


if __name__ == '__main__': unittest.main()
