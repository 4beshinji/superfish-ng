# SPDX-License-Identifier: Apache-2.0
import contextlib
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch

from test_static_field_project import cases, solve_and_result
from test_planar_bh_saved import failed_cases as planar_failures
from test_axis_bh_saved import failed_cases as axis_failures
from test_off_axis_bh_saved import failed_cases as off_axis_failures
from superfish_ng import static_field_jobs as static
from superfish_ng.static_field_project import StaticFieldProject
from superfish_ng.jobs import JobManager, read_job
from superfish_ng.nonlinear_magnetic import MagneticNonlinearFailure
from superfish_ng.cli import main
from superfish_ng.model import capabilities


def failure_cases():
    return [case for factory in (planar_failures, axis_failures, off_axis_failures) for case in factory()]


def rehash(directory):
    path = directory / 'manifest.json'; value = json.loads(path.read_text())
    value['files'] = {n:hashlib.sha256((directory / n).read_bytes()).hexdigest() for n in value['files']}
    path.write_text(json.dumps(value))


def wait(manager, identifier):
    end = time.monotonic() + 120
    while time.monotonic() < end:
        state = manager.status(identifier)
        if state['status'] not in ('queued', 'running'):
            process = manager.processes.get(identifier)
            if process is not None: process.wait(timeout=10)
            return state
        time.sleep(.02)
    raise AssertionError('static worker did not finish')


class StaticFieldJobTests(unittest.TestCase):
    def test_all_eleven_families_and_orders_execute_original_fem_and_replay(self):
        with tempfile.TemporaryDirectory() as temporary:
            for index, case in enumerate(cases()):
                project = StaticFieldProject(case, 'm' if index % 2 else 'mm')
                directory = Path(temporary) / str(index)
                expected = solve_and_result(case)[1]
                result = static.execute_static_field_project(project, directory)
                self.assertEqual(result['status'], 'complete')
                self.assertEqual(result['outcome'], expected)
                self.assertEqual(result['project'], project.to_dict())
                self.assertEqual(static.read_static_field_job(directory), result)
                state = read_job(directory)
                self.assertEqual(state['kind'], static.KIND)
                self.assertEqual(state['status'], 'complete')
                self.assertEqual(state['numerical_validation'], 'not_checked')
                self.assertEqual(set(p.name for p in (directory/'solution').iterdir()), static.SUCCESS_FILES)

    def test_three_bh_coordinate_families_retain_all_real_failure_histories(self):
        with tempfile.TemporaryDirectory() as temporary:
            for index, case in enumerate(failure_cases()):
                with self.assertRaises(MagneticNonlinearFailure) as caught: static._solve(case)
                directory = Path(temporary) / str(index)
                project = StaticFieldProject(case, 'm')
                result = static.execute_static_field_project(project, directory)
                self.assertEqual(result['status'], 'nonlinear_failed')
                self.assertEqual(result['outcome'], caught.exception.report)
                self.assertEqual(result['project'], project.to_dict())
                self.assertEqual(static.read_static_field_job(directory), result)
                state = read_job(directory)
                self.assertEqual(state['status'], 'failed'); self.assertTrue(state['outcome_saved'])
                self.assertEqual(state['solver_status'], 'nonlinear_failed')
                self.assertEqual(set(p.name for p in (directory/'solution').iterdir()), static.FAILURE_FILES)

    def test_rehashed_case_fields_failure_history_and_removed_kinds_reject(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); base = root / 'success'
            project = StaticFieldProject(next(cases()))
            static.execute_static_field_project(project, base)
            failed = root / 'failure-source'; static.execute_static_field_project(StaticFieldProject(failure_cases()[0]), failed)
            for name in ('kind', 'project', 'result', 'failure', 'summary', 'manifest', 'linked'):
                target = root / name; shutil.copytree(failed if name == 'failure' else base, target)
                if name == 'kind':
                    for file in ('job.json', 'manifest.json'):
                        p = target / file; value = json.loads(p.read_text()); value.pop('kind'); p.write_text(json.dumps(value))
                elif name == 'project':
                    p = target/'project.json'; value=json.loads(p.read_text()); value['case']['name']='different'; p.write_text(json.dumps(value)); rehash(target)
                    p=target/'job.json';value=json.loads(p.read_text());value['project_sha256']=hashlib.sha256((target/'project.json').read_bytes()).hexdigest();p.write_text(json.dumps(value))
                elif name in ('result', 'failure'):
                    p=target/'solution'/('failure.json' if name=='failure' else 'results.json');value=json.loads(p.read_text())
                    if name=='failure':value['reason']='invented failure'
                    else:value['quantities']['invented_energy_j']=0.
                    p.write_text(json.dumps(value));rehash(target/'solution');rehash(target)
                elif name == 'summary':
                    p=target/'job.json';value=json.loads(p.read_text());value['physics']='rf_eigenmode';p.write_text(json.dumps(value))
                elif name == 'manifest':
                    p=target/'manifest.json';value=json.loads(p.read_text());value['files'].pop('solution/manifest.json');p.write_text(json.dumps(value))
                else:
                    p=target/'solution/case.json';p.unlink();p.symlink_to(base/'solution/case.json')
                with self.subTest(name=name), self.assertRaises((ValueError, OSError)): read_job(target)

    def test_exclusive_workers_input_and_implementation_changes_and_interrupted_save(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);project=StaticFieldProject(next(cases()))
            target=root/'complete';static.execute_static_field_project(project,target)
            before={str(p.relative_to(target)):p.read_bytes() for p in target.rglob('*') if p.is_file()}
            with self.assertRaises(FileExistsError):static.execute_static_field_project(project,target)
            with self.assertRaises(ValueError):static.execute_prepared_static_field_project(target)
            self.assertEqual(before,{str(p.relative_to(target)):p.read_bytes() for p in target.rglob('*') if p.is_file()})
            queued=root/'queued';static._prepare(project,queued)
            (queued/'project.json').write_text(replace(project,display_length_unit='m').dumps())
            with self.assertRaisesRegex(ValueError,'after submission'):static.execute_prepared_static_field_project(queued)
            duplicate=root/'duplicate';static._prepare(project,duplicate);(duplicate/'worker.claim').write_text('claimed')
            with self.assertRaises(FileExistsError):static.execute_prepared_static_field_project(duplicate)
            self.assertEqual(read_job(duplicate,verify=False)['status'],'queued')
            changed=root/'changed';actual_solve=static._solve
            def changing(case):
                result=actual_solve(case);(changed/'project.json').write_text(replace(project,display_length_unit='m').dumps());return result
            with patch.object(static,'_solve',side_effect=changing),self.assertRaisesRegex(ValueError,'changed during completion'):
                static.execute_static_field_project(project,changed)
            source=root/'source'
            with patch('superfish_ng.jobs._implementation_hashes',side_effect=[{'a.py':'a'*64},{'a.py':'b'*64}]),self.assertRaisesRegex(ValueError,'implementation changed'):
                static.execute_static_field_project(project,source)
            saving=root/'saving';_,_,saved=static._bindings(project.case)
            def interrupted(case,solution,path):path.mkdir();(path/'case.json').write_text('{}');raise OSError('interrupted save')
            with patch.object(saved,'save_electrostatic_run',side_effect=interrupted),self.assertRaises(OSError):
                static.execute_static_field_project(project,saving)
            for path in (queued,changed,source,saving):
                self.assertEqual(read_job(path,verify=False)['status'],'failed')
                self.assertFalse((path/'manifest.json').exists())
                with self.assertRaises((ValueError,OSError)):static.read_static_field_job(path)

    def test_real_workers_restart_cancel_and_forced_exit_keep_distinct_states(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);manager=JobManager(root);results={}
            try:
                unique={case.to_dict()['format']:case for case in cases()}
                for case in [*unique.values(),failure_cases()[0],failure_cases()[3],failure_cases()[6]]:
                    project=StaticFieldProject(case,'m');identifier=manager.start_static_field(project)
                    state=wait(manager,identifier);result=static.read_static_field_job(manager.directory(identifier))
                    self.assertEqual(state['status'],'failed' if result['status']=='nonlinear_failed' else 'complete')
                    self.assertEqual(result['project'],project.to_dict());results[identifier]=result
                case=next(cases());identifier=manager.start_static_field(StaticFieldProject(case))
                self.assertEqual(manager.cancel(identifier)['status'],'cancelled')
                with self.assertRaises((ValueError,OSError)):static.read_static_field_job(manager.directory(identifier))
                identifier=manager.start_static_field(StaticFieldProject(case));process=manager.processes[identifier];process.kill();process.wait(timeout=10)
                self.assertEqual(manager.status(identifier)['status'],'failed')
                self.assertFalse((manager.directory(identifier)/'manifest.json').exists())
                static._prepare(StaticFieldProject(case),root/'interrupted')
            finally:manager.close()
            manager=JobManager(root)
            try:
                self.assertEqual(manager.status('interrupted')['status'],'interrupted')
                for identifier,result in results.items():
                    self.assertEqual(static.read_static_field_job(manager.directory(identifier)),result)
                    self.assertEqual(manager.status(identifier,verify=True)['status'],'failed' if result['status']=='nonlinear_failed' else 'complete')
            finally:manager.close()

    def test_cli_matches_full_outcomes_and_capabilities_with_zero_one_two_exit_codes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            selected=[next(cases()),list(cases())[8],failure_cases()[0],failure_cases()[3],failure_cases()[6]]
            for index,case in enumerate(selected):
                project=StaticFieldProject(case,'m');source=root/f'{index}.json';project.save(source);target=root/str(index)
                for command in (['solve-static-project',str(source),'--out',str(target)],['replay-static-project',str(target)]):
                    stdout,stderr=io.StringIO(),io.StringIO()
                    with contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):code=main(command)
                    self.assertEqual(code,1 if index>=2 else 0,stderr.getvalue())
                    self.assertEqual(json.loads(stdout.getvalue()),static.read_static_field_job(target))
            with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(['solve-static-project',str(source),'--out',str(target)]),2)
                self.assertEqual(main(['replay-static-project',str(root/'absent')]),2)
            inventory=capabilities()['static_field_jobs']
            self.assertEqual(len(inventory['case_families']),11);self.assertEqual(inventory['kind'],static.KIND)
            self.assertEqual(inventory['cli_exit_codes'],dict(complete=0,retained_nonlinear_failure=1,invalid_or_io=2))
            self.assertFalse(inventory['gui']);self.assertFalse(inventory['study'])


if __name__=='__main__':unittest.main()
