# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from superfish_ng import gui_magnetic_reports as gui
from superfish_ng import magnetic_report_jobs as magnetic
from superfish_ng.jobs import JobManager, _state
from superfish_ng.model import capabilities
from test_magnetic_report_jobs import report_fixture


class MagneticReportGuiTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.manager = JobManager(self.root / 'workspace'); self.addCleanup(self.manager.close)
        self.access = gui.MagneticReportAccess(self.manager); self.addCleanup(self.access.close)

    def call(self, action, **data):
        return gui.magnetic_report_response(self.manager, self.access, action, data)

    def completed(self, kind='linear', virtual=False):
        source, report, expected = report_fixture(self.root / kind, kind, virtual)
        directory = self.manager.directory(kind)
        magnetic._prepare(magnetic._input(source, report)[0], directory)
        magnetic.execute_prepared_magnetic_report(directory)
        return directory, expected

    def ready(self, identifier):
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            result, media = self.call('magnetic-report-result', id=identifier)
            if result['status'] != 'verifying':
                self.assertEqual(result['status'], 'ready', result)
                return result['view']
            time.sleep(.01)
        self.fail('magnetic report asynchronous verification did not finish')

    def test_original_multipole_frame_absolute_coefficients_and_four_traces(self):
        directory, expected = self.completed('multipole')
        view = self.ready(directory.name)
        extraction = expected['extraction']; series = extraction['series']
        self.assertEqual(view['frame'], series['frame'])
        self.assertEqual([row['normal_t'] for row in view['coefficients']], series['normal_t'])
        self.assertEqual([row['skew_t'] for row in view['coefficients']], series['skew_t'])
        self.assertEqual(view['convention'], series['convention'])
        self.assertEqual(view['traces'], extraction['traces'])
        self.assertEqual(len(view['traces']), 4)
        self.assertEqual(view['virtual_work_status'], 'not_applicable')
        self.assertEqual(view['source_case'], json.loads((directory / 'source/case.json').read_text()))

    def test_planar_two_torques_axial_total_units_and_unperformed_work(self):
        for kind in ('linear', 'axial'):
            directory, report = self.completed(kind)
            view = self.ready(directory.name)
            force = report['force']
            self.assertEqual(view['virtual_work_status'], 'not_performed')
            self.assertIsNone(view['virtual_work']); self.assertIsNone(view['work_comparison'])
            if kind == 'linear':
                self.assertEqual([r['value'] for r in view['quantities']], [*force['force_xy_n_per_m'],
                    force['torque_z_nm_per_m'], force['nodal_rotation_stress_torque_z_nm_per_m']])
                self.assertEqual([r['unit'] for r in view['quantities']], ['N/m', 'N/m', 'N m/m', 'N m/m'])
                self.assertNotEqual(view['quantities'][2]['name'], view['quantities'][3]['name'])
                self.assertEqual(view['origin_xy_m'], force['origin_xy_m'])
            else:
                self.assertEqual(view['quantities'], [dict(name='軸方向力 Fz', value=force['force_z_n'], unit='N')])
                self.assertEqual(view['work_potential_unit'], 'J'); self.assertIsNone(view['origin_xy_m'])

    def test_completed_recoil_work_and_actual_bh_failure_preserve_nulls_and_cases(self):
        for kind in ('recoil', 'failure'):
            directory, report = self.completed(kind, virtual=True)
            view = self.ready(directory.name)
            self.assertEqual(view['virtual_work_status'], 'failed' if kind == 'failure' else 'complete')
            self.assertEqual(view['virtual_work'], report['virtual_work'])
            self.assertEqual(view['work_comparison'], report['stress_virtual_work_comparison'])
            self.assertEqual(view['work_potential_unit'], 'J/m')
            if kind == 'failure':
                self.assertIsNone(view['work_comparison'][-1]['virtual_work_value'])
                self.assertIsNone(view['work_comparison'][-1]['difference'])
                self.assertTrue(view['virtual_work']['failure']['nonlinear_failure']['history'])
            self.assertEqual(self.call('magnetic-report-download', id=directory.name, file='report.json')[0],
                             (directory / 'report.json').read_bytes())

    def test_async_replay_cache_is_hash_bound_and_never_returns_shared_mutable_values(self):
        directory, report = self.completed()
        entered, release = threading.Event(), threading.Event()
        original = gui.verify_magnetic_report_job
        def delayed(*args):
            entered.set(); self.assertTrue(release.wait(5)); return original(*args)
        with patch.object(gui, 'verify_magnetic_report_job', side_effect=delayed) as replay:
            try:
                self.assertEqual(self.call('magnetic-report-result', id=directory.name)[0]['status'], 'verifying')
                self.assertTrue(entered.wait(2))
                with self.assertRaisesRegex(ValueError, 'wait for'):
                    self.call('magnetic-report-download', id=directory.name, file='report.json')
            finally:
                release.set()
            first = self.ready(directory.name)
            first['quantities'][0]['value'] = 100.
            self.assertEqual(self.ready(directory.name)['quantities'][0]['value'], report['force']['force_xy_n_per_m'][0])
            self.assertEqual(replay.call_count, 1)
        path = directory / 'report.json'; path.write_bytes(path.read_bytes() + b'\n')
        for action, data in (('magnetic-report-result', {}), ('magnetic-report-download', {'file':'report.json'})):
            with self.assertRaisesRegex(ValueError, 'changed after'):
                self.call(action, id=directory.name, **data)

    def test_restart_replays_originals_and_all_downloads_preserve_bytes(self):
        directory, _ = self.completed('axial', virtual=True)
        self.ready(directory.name)
        self.access.close(); self.manager.close()
        self.manager = JobManager(self.root / 'workspace'); self.addCleanup(self.manager.close)
        self.access = gui.MagneticReportAccess(self.manager); self.addCleanup(self.access.close)
        original = gui.verify_magnetic_report_job
        with patch.object(gui, 'verify_magnetic_report_job', wraps=original) as replay:
            view = self.ready(directory.name)
            self.assertEqual(replay.call_count, 1)
        for name in ['report.json', 'request.json', *('source/' + n for n in view['source_native_sha256'])]:
            self.assertEqual(self.call('magnetic-report-download', id=directory.name, file=name)[0], (directory / name).read_bytes())
        with self.assertRaises(ValueError): self.call('magnetic-report-download', id=directory.name, file='../job.json')
        path = directory / 'source/case.json'; path.write_bytes(path.read_bytes() + b'\n')
        with self.assertRaises(ValueError): self.ready(directory.name)

    def test_strict_actions_real_import_and_capabilities_keep_rf_jobs_separate(self):
        source, report, _ = report_fixture(self.root / 'linear')
        for action, data in (('magnetic-report-import', {}), ('magnetic-report-import', {'source':str(source), 'report':str(report), 'extra':0}),
                             ('magnetic-report-result', {'id':'../'}), ('magnetic-report-import', {'source':True, 'report':str(report)})):
            with self.assertRaises(ValueError): self.call(action, **data)
        directory = self.manager.directory('rf'); directory.mkdir(); _state(directory, 'queued', kind='solve')
        with self.assertRaisesRegex(ValueError, 'dedicated'): self.call('magnetic-report-result', id='rf')
        identifier = self.call('magnetic-report-import', source=str(source), report=str(report))[0]['id']
        self.assertEqual(self.manager.processes[identifier].wait(timeout=90), 0)
        self.ready(identifier)
        self.assertEqual([r['id'] for r in self.call('magnetic-report-jobs')[0]], [identifier])
        inventory = capabilities()['magnetic_report_gui']
        self.assertEqual(set(inventory['gui_actions']), set(gui.ACTIONS))
        self.assertEqual(inventory['units']['planar_force'], 'N/m')
        self.assertEqual(inventory['units']['axial_force'], 'N')
        self.assertFalse(inventory['case_editor']); self.assertTrue(inventory['gui'])


if __name__ == '__main__':
    unittest.main()
