# SPDX-License-Identifier: Apache-2.0
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch

from test_static_field_project import cases, solve_and_result, planar_bh, axis_bh, off_axis_bh
from test_static_field_jobs import failure_cases, wait
from superfish_ng import static_field_study_jobs as static
from superfish_ng.static_field_study import StaticFieldStudy
from superfish_ng.static_field_project import StaticFieldProject
from superfish_ng.static_field_jobs import read_static_field_job, _solve
from superfish_ng.nonlinear_magnetic import MagneticNonlinearFailure
from superfish_ng.jobs import JobManager, read_job
from superfish_ng.cli import main
from superfish_ng.model import capabilities


def rehash(directory):
    path = directory / 'manifest.json'; data = json.loads(path.read_text())
    data['files'] = {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in data['files']}
    path.write_text(json.dumps(data))


class StaticFieldStudyJobTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.root = Path(self.temporary.name)

    def tearDown(self): self.temporary.cleanup()

    def simple(self): return StaticFieldStudy(StaticFieldProject(next(cases())), 'excitation_scale', (-1., 1.))

    def mixed(self, factory=planar_bh):
        return StaticFieldStudy(StaticFieldProject(factory(n=2)[0]), 'excitation_scale', (0., 1., 1000.))

    def test_all_eleven_families_orders_and_parameters_keep_full_point_results(self):
        formats = set()
        for index, case in enumerate(cases()):
            formats.add(case.to_dict()['format'])
            for parameter, values in (('uniform_scale', (.5, 1.)), ('excitation_scale', (-1., 1.))):
                study = StaticFieldStudy(StaticFieldProject(case, 'm' if index % 2 else 'mm'), parameter, values)
                directory = self.root / f'{index}-{parameter}'; result = static.execute_static_field_study(study, directory)
                self.assertEqual(result['execution_status'], 'complete'); self.assertTrue(result['all_points_successful'])
                self.assertEqual(result['successful_points'], 2); self.assertEqual(result['nonlinear_failed_points'], 0)
                self.assertEqual(result['study'], study.to_dict()); self.assertEqual(result['mode_tracking'], 'not_applicable')
                self.assertEqual(result['solution_branch_tracking'], 'not_performed'); self.assertEqual(result['numerical_validation'], 'not_checked')
                for point, value, project in zip(result['points'], values, study.projects()):
                    self.assertEqual(point['value'], value); self.assertEqual(point['result']['project'], project.to_dict())
                    self.assertEqual(point['result']['outcome'], solve_and_result(project.case)[1])
                    self.assertEqual(point['result'], read_static_field_job(directory / point['directory']))
                    self.assertEqual(len(list((directory / point['directory'] / 'solution').iterdir())), 5)
                self.assertEqual(static.read_static_field_study(directory), result)
                self.assertEqual(read_job(directory)['kind'], static.KIND)
        self.assertEqual(len(formats), 11)

    def test_mixed_success_and_actual_bh_failures_complete_execution_without_invented_fields(self):
        studies = [self.mixed(factory) for factory in (planar_bh, axis_bh, off_axis_bh)]
        studies += [StaticFieldStudy(StaticFieldProject(case), 'uniform_scale', (1., 2.)) for case in failure_cases()]
        for index, study in enumerate(studies):
            directory = self.root / str(index); result = static.execute_static_field_study(study, directory)
            self.assertEqual(read_job(directory)['status'], 'complete'); self.assertFalse(result['all_points_successful'])
            self.assertEqual(result['execution_status'], 'complete')
            successes = failures = 0
            for point, project in zip(result['points'], study.projects()):
                try: _solve(project.case)
                except MagneticNonlinearFailure as failure:
                    failures += 1; self.assertEqual(point['result']['status'], 'nonlinear_failed')
                    self.assertEqual(point['result']['outcome'], failure.report)
                    self.assertEqual({p.name for p in (directory / point['directory'] / 'solution').iterdir()}, {'case.json', 'failure.json', 'manifest.json'})
                else:
                    successes += 1; self.assertEqual(point['result']['status'], 'complete')
            self.assertEqual(result['successful_points'], successes); self.assertEqual(result['nonlinear_failed_points'], failures)
            if index < 3: self.assertEqual((successes, failures), (2, 1))
            self.assertEqual(static.read_static_field_study(directory), result)

    def test_rehashed_points_summary_provenance_and_kind_downgrades_reject(self):
        base = self.root / 'base'; static.execute_static_field_study(self.simple(), base)
        for index, change in enumerate(('summary', 'count', 'state-array', 'point-project', 'point-native', 'implementation', 'extra-point', 'missing-point', 'linked-native', 'kind', 'status')):
            directory = self.root / str(index); shutil.copytree(base, directory)
            if change == 'summary':
                path = directory / 'study-results.json'; data = json.loads(path.read_text()); data['points'][0]['index'] = True; path.write_text(json.dumps(data))
            elif change in ('count', 'state-array', 'status'):
                path = directory / 'job.json'; data = json.loads(path.read_text())
                if change == 'count': data['computed_points'] = True
                elif change == 'state-array': data = []
                else: data['status'] = 'failed'
                path.write_text(json.dumps(data))
            elif change == 'point-project':
                path = directory / 'point-0000/project.json'; data = json.loads(path.read_text()); data['display_length_unit'] = 'm'; path.write_text(json.dumps(data)); rehash(path.parent)
            elif change == 'point-native':
                path = directory / 'point-0000/solution/results.json'; data = json.loads(path.read_text()); data['quantities']['energy_j'] *= 2; path.write_text(json.dumps(data)); rehash(path.parent.parent)
            elif change == 'implementation':
                path = directory / 'point-0000/manifest.json'; data = json.loads(path.read_text()); name = next(iter(data['implementation_sha256'])); data['implementation_sha256'][name] = 'f' * 64; path.write_text(json.dumps(data))
            elif change == 'extra-point': (directory / 'point-extra').mkdir()
            elif change == 'missing-point': shutil.rmtree(directory / 'point-0001')
            elif change == 'linked-native':
                path = directory / 'point-0000/solution/results.json'; path.unlink(); path.symlink_to(base / 'point-0000/solution/results.json')
            else:
                for name in ('job.json', 'manifest.json'):
                    path = directory / name; data = json.loads(path.read_text()); data.pop('kind'); path.write_text(json.dumps(data))
            if change != 'missing-point': rehash(directory)
            with self.assertRaises((ValueError, OSError)): static.read_static_field_study(directory)
            with self.assertRaises((ValueError, OSError)): read_job(directory)

    def test_input_source_and_point_changes_partial_failure_and_duplicate_workers_reject(self):
        study = self.simple(); prepared = self.root / 'queued'; static._prepare(study, prepared)
        path = prepared / 'study.json'; path.write_bytes(path.read_bytes() + b'\n')
        with patch.object(static, 'execute_static_field_project', side_effect=AssertionError('must not solve')):
            with self.assertRaisesRegex(ValueError, 'after submission'): static.execute_prepared_static_field_study(prepared)
        duplicate = self.root / 'duplicate'; static._prepare(study, duplicate); (duplicate / 'worker.claim').write_text('owned\n')
        with self.assertRaises(FileExistsError): static.execute_prepared_static_field_study(duplicate)
        complete = self.root / 'complete'; static.execute_static_field_study(study, complete)
        before = {str(p.relative_to(complete)): p.read_bytes() for p in complete.rglob('*') if p.is_file()}
        with self.assertRaises(ValueError): static.execute_prepared_static_field_study(complete)
        with self.assertRaises(FileExistsError): static.execute_static_field_study(study, complete)
        self.assertEqual(before, {str(p.relative_to(complete)): p.read_bytes() for p in complete.rglob('*') if p.is_file()})
        original = static.execute_static_field_project
        for change in ('input', 'previous-point', 'save-failure'):
            directory = self.root / change; calls = 0
            def modified(project, point):
                nonlocal calls
                calls += 1
                if change == 'save-failure' and calls == 2: raise OSError('simulated second-point disk failure')
                result = original(project, point)
                target = directory / ('study.json' if change == 'input' else 'point-0000/solution/results.json')
                if change == 'input' or change == 'previous-point' and calls == 2: target.write_bytes(target.read_bytes() + b'\n')
                return result
            with patch.object(static, 'execute_static_field_project', side_effect=modified):
                with self.assertRaises((ValueError, OSError)): static.execute_static_field_study(study, directory)
            state = read_job(directory, verify=False); self.assertEqual(state['status'], 'failed'); self.assertFalse(state['outcome_saved'])
            with self.assertRaises((ValueError, OSError)): static.read_static_field_study(directory)
        implementation = static._implementation_hashes(); changed = dict(implementation); changed[next(iter(changed))] = 'e' * 64
        with patch.object(static, '_implementation_hashes', side_effect=[implementation, changed]):
            with self.assertRaisesRegex(ValueError, 'implementation changed'): static.execute_static_field_study(study, self.root / 'source-change')
        original_read = static.read_static_field_study
        def changed_after_read(directory):
            result = original_read(directory); path = directory / 'study.json'; path.write_bytes(path.read_bytes() + b'\n'); return result
        with patch.object(static, 'read_static_field_study', side_effect=changed_after_read):
            with self.assertRaisesRegex(ValueError, 'changed during completion'): static.execute_static_field_study(study, self.root / 'completion-change')

    def test_real_workers_restart_cancel_and_forced_exit_preserve_distinct_states(self):
        workspace = self.root / 'workspace'; completed = []
        with contextlib.closing(JobManager(workspace)) as manager:
            for study in (self.simple(), self.mixed(axis_bh)):
                identifier = manager.start_static_field_study(study); state = wait(manager, identifier)
                self.assertEqual(state['status'], 'complete'); result = static.read_static_field_study(manager.directory(identifier))
                self.assertEqual(result['study'], study.to_dict()); completed.append((identifier, result))
            identifier = manager.start_static_field_study(self.simple()); manager.cancel(identifier)
            self.assertEqual(manager.status(identifier)['status'], 'cancelled')
            with self.assertRaises((ValueError, OSError)): static.read_static_field_study(manager.directory(identifier))
            identifier = manager.start_static_field_study(self.simple()); process = manager.processes[identifier]; process.kill(); process.wait(timeout=10)
            self.assertEqual(manager.status(identifier)['status'], 'failed')
            with self.assertRaises((ValueError, OSError)): static.read_static_field_study(manager.directory(identifier))
        with contextlib.closing(JobManager(workspace)) as manager:
            for identifier, result in completed:
                self.assertEqual(manager.status(identifier)['status'], 'complete'); self.assertEqual(static.read_static_field_study(manager.directory(identifier)), result)

    def test_cli_all_success_mixed_failures_invalid_input_and_existing_studies(self):
        for index, study in enumerate((self.simple(), self.mixed())):
            source = self.root / f'{index}.json'; study.save(source); target = self.root / str(index)
            output, errors = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors): status = main(['solve-static-study', str(source), '--out', str(target)])
            self.assertEqual(status, index, errors.getvalue()); result = json.loads(output.getvalue()); self.assertEqual(result, static.read_static_field_study(target))
            output = io.StringIO()
            with contextlib.redirect_stdout(output): self.assertEqual(main(['replay-static-study', str(target)]), index)
            self.assertEqual(json.loads(output.getvalue()), result)
            with contextlib.redirect_stderr(io.StringIO()): self.assertEqual(main(['solve-static-study', str(source), '--out', str(target)]), 2)
        bad = self.root / 'bad.json'; bad.write_text(source.read_text().replace('"study_version": 1', '"study_version": 1, "study_version": 1'))
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['solve-static-study', str(bad), '--out', str(self.root / 'invalid')]), 2)
            self.assertEqual(main(['replay-static-study', str(self.root / 'absent')]), 2)
        self.assertFalse((self.root / 'invalid').exists())
        inventory = capabilities()['static_field_study_jobs']; self.assertEqual(inventory['kind'], static.KIND)
        self.assertEqual(len(inventory['case_families']), 11); self.assertFalse(inventory['gui'])
        self.assertEqual(inventory['cli_exit_codes'], dict(all_points_successful=0, completed_with_nonlinear_failures=1, invalid_incomplete_or_io=2))
        self.assertTrue(capabilities()['static_field_study']['execution'])
