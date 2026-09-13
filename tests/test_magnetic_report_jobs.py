# SPDX-License-Identifier: Apache-2.0
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from superfish_ng import magnetic_report_jobs as magnetic
from superfish_ng.jobs import JobManager, read_job, _write_json, _digest
from superfish_ng.planar_magnetostatic_saved import _snapshot
from superfish_ng.planar_magnetic_force_saved import export_planar_magnetic_force
from superfish_ng.off_axis_magnetic_force_saved import export_off_axis_magnetic_force
from superfish_ng.planar_magnetic_multipole_saved import export_planar_magnetic_multipoles
from test_planar_magnetic_force_saved import fixture as linear_fixture
from test_planar_magnetic_force_material_saved import fixture as material_fixture
from test_off_axis_magnetic_force_saved import fixture as axial_fixture
from test_planar_magnetic_multipole_saved import fixture as multipole_fixture


def report_fixture(root, kind='linear', virtual=False):
    root.mkdir()
    report = root / 'report.json'
    if kind == 'multipole':
        source, _, _, request = multipole_fixture(root)
        result = export_planar_magnetic_multipoles(source, report, request)
    elif kind == 'axial':
        source, request, _ = axial_fixture(root, 2, virtual)
        result = export_off_axis_magnetic_force(source, report, request)
    elif kind == 'linear':
        source, _, _, _, _, request = linear_fixture(root, order=1, virtual=virtual)
        result = export_planar_magnetic_force(source, report, request)
    else:
        source, _, request = material_fixture(root, 'bh' if kind in ('bh', 'failure') else 'recoil', 1,
                                             virtual or kind == 'failure', 'first' if kind == 'failure' else None)
        result = export_planar_magnetic_force(source, report, request)
    return source, report, result


class MagneticReportJobTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.manager = JobManager(self.root / 'workspace')
        self.addCleanup(self.manager.close)

    def prepared(self, source, report, name='prepared'):
        directory = self.manager.directory(name)
        magnetic._prepare(magnetic._input(source, report)[0], directory)
        return directory

    def test_real_workers_import_all_report_families_with_exact_owned_sources(self):
        for kind in ('linear', 'multipole', 'axial'):
            source, report, expected = report_fixture(self.root / kind, kind)
            native, raw = _snapshot(source), report.read_bytes()
            identifier = magnetic.start_magnetic_report(self.manager, source, report)
            self.assertEqual(self.manager.processes[identifier].wait(timeout=90), 0)
            directory = self.manager.directory(identifier)
            self.assertEqual(read_job(directory)['kind'], magnetic.KIND)
            self.assertEqual(magnetic.verify_magnetic_report_job(directory), expected)
            self.assertEqual(_snapshot(directory / 'source'), native)
            self.assertEqual((directory / 'report.json').read_bytes(), raw)
            self.assertEqual(_snapshot(source), native)
            self.assertEqual(report.read_bytes(), raw)

    def test_rehashed_report_tamper_and_removed_kind_cannot_bypass_fem_replay(self):
        source, report, _ = report_fixture(self.root / 'linear')
        directory = self.prepared(source, report)
        magnetic.execute_prepared_magnetic_report(directory)
        before = {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file()}
        changed = json.loads((directory / 'report.json').read_text())
        changed['force']['force_xy_n_per_m'][0] += 1.
        _write_json(directory / 'report.json', changed)
        request = json.loads((directory / 'request.json').read_text())
        request['report_sha256'] = _digest(directory / 'report.json')
        _write_json(directory / 'request.json', request)
        manifest = json.loads((directory / 'manifest.json').read_text())
        for name in ('report.json', 'request.json'):
            manifest['files'][name] = _digest(directory / name)
        _write_json(directory / 'manifest.json', manifest)
        with self.assertRaisesRegex(ValueError, 'FEM replay'):
            read_job(directory)
        for name, raw in before.items():
            (directory / name).write_bytes(raw)
        for name in ('job.json', 'manifest.json'):
            data = json.loads((directory / name).read_text()); data.pop('kind')
            _write_json(directory / name, data)
        with self.assertRaisesRegex(ValueError, 'dedicated'):
            read_job(directory)

    def test_changed_submission_or_original_during_replay_keeps_failed_job(self):
        source, report, _ = report_fixture(self.root / 'linear')
        raw = report.read_bytes()
        directory = self.prepared(source, report)
        report.write_bytes(raw + b'\n')
        with self.assertRaisesRegex(ValueError, 'after submission'):
            magnetic.execute_prepared_magnetic_report(directory)
        self.assertEqual(read_job(directory)['status'], 'failed')
        self.assertFalse((directory / 'manifest.json').exists())
        report.write_bytes(raw)
        directory = self.prepared(source, report, 'during')
        original = magnetic._replay
        def changed(*args):
            value = original(*args); report.write_bytes(raw + b'\n'); return value
        with patch.object(magnetic, '_replay', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'during import'):
                magnetic.execute_prepared_magnetic_report(directory)
        self.assertEqual(read_job(directory)['status'], 'failed')
        self.assertFalse((directory / 'manifest.json').exists())

    def test_material_work_failure_remains_failure_inside_completed_import(self):
        source, report, expected = report_fixture(self.root / 'failure', 'failure')
        directory = self.prepared(source, report)
        magnetic.execute_prepared_magnetic_report(directory)
        state = read_job(directory)
        self.assertEqual(state['status'], 'complete')
        self.assertEqual(state['report_status'], 'virtual_work_failed')
        self.assertEqual(state['numerical_validation'], 'not_checked')
        self.assertEqual(magnetic.verify_magnetic_report_job(directory), expected)
        self.assertIsNone(expected['stress_virtual_work_comparison'][-1]['difference'])
        self.assertTrue(expected['virtual_work']['failure']['nonlinear_failure']['history'])

    def test_links_duplicate_worker_and_interrupted_publication_reject(self):
        source, report, _ = report_fixture(self.root / 'linear')
        link = self.root / 'linked'; link.symlink_to(source, target_is_directory=True)
        with self.assertRaises(ValueError): magnetic.start_magnetic_report(self.manager, link, report)
        link = self.root / 'linked.json'; link.symlink_to(report)
        with self.assertRaises(ValueError): magnetic.start_magnetic_report(self.manager, source, link)
        directory = self.prepared(source, report)
        original = _write_json
        def interrupted(path, value):
            if path.name == 'manifest.json': raise OSError('publication interrupted')
            return original(path, value)
        with patch('superfish_ng.jobs._write_json', side_effect=interrupted):
            with self.assertRaisesRegex(OSError, 'interrupted'):
                magnetic.execute_prepared_magnetic_report(directory)
        self.assertEqual(read_job(directory)['status'], 'failed')
        self.assertFalse((directory / 'manifest.json').exists())
        with self.assertRaisesRegex(ValueError, 'new queued'):
            magnetic.execute_prepared_magnetic_report(directory)

    def test_real_worker_cancel_and_restart_preserve_completed_import(self):
        source, report, _ = report_fixture(self.root / 'linear', virtual=True)
        directory = self.prepared(source, report)
        magnetic.execute_prepared_magnetic_report(directory)
        identifier = magnetic.start_magnetic_report(self.manager, source, report)
        self.assertEqual(self.manager.cancel(identifier)['status'], 'cancelled')
        self.prepared(source, report, 'unfinished')
        self.manager.close()
        manager = JobManager(self.root / 'workspace'); self.addCleanup(manager.close)
        self.assertEqual(manager.status('unfinished')['status'], 'interrupted')
        self.assertEqual(read_job(directory)['status'], 'complete')


if __name__ == '__main__':
    unittest.main()
