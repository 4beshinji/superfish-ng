# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from superfish_ng.planar import PlanarCase,solve_planar
from superfish_ng.planar_polygon import load_planar_case
from superfish_ng.planar_project import PlanarProject
from superfish_ng.planar_jobs import execute_planar_project
from superfish_ng.planar_saved import save_planar_run,read_planar_run,planar_result
from superfish_ng.project import Project
from superfish_ng.jobs import JobManager,read_job


def example(polygon=False,pol='te'):
    case=(load_planar_case(Path(__file__).resolve().parents[1]/f'examples/planar/triangle_{pol}.json') if polygon else PlanarCase(.31,.2,pol,nx=6,ny=5,modes=3))
    return PlanarProject(case,'m')


def rehash(folder):
    path=folder/'manifest.json';data=json.loads(path.read_text())
    data['files']={name:hashlib.sha256((folder/name).read_bytes()).hexdigest() for name in data['files']}
    path.write_text(json.dumps(data))


class PlanarJobTests(unittest.TestCase):
    def test_project_versions_units_and_strict_axis_separation(self):
        for polygon in (False,True):
            for pol in ('te','tm'):
                project=example(polygon,pol);data=project.to_dict();self.assertEqual(PlanarProject.from_dict(data),project)
                with self.assertRaises(ValueError):Project.from_dict(data)
                for key in ('sections','reflect_full','mesh_data'):
                    bad={**data,key:None}
                    with self.subTest(key=key),self.assertRaises(ValueError):PlanarProject.from_dict(bad)
                for value in ('cm',None,True):
                    with self.assertRaises(ValueError):PlanarProject.from_dict({**data,'display_length_unit':value})
                with self.assertRaises(ValueError):PlanarProject.from_dict({**data,'project_version':True})
                with tempfile.TemporaryDirectory() as temporary:
                    path=Path(temporary)/'project.json';project.save(path);self.assertEqual(PlanarProject.load(path),project)
                    with self.assertRaises(FileExistsError):project.save(path)
                    path.write_text(project.dumps().replace('"project_version": 1','"project_version": 1, "project_version": 1'))
                    with self.assertRaisesRegex(ValueError,'duplicate'):PlanarProject.load(path)

    def test_execute_binds_both_case_versions_to_native(self):
        with tempfile.TemporaryDirectory() as temporary:
            for polygon in (False,True):
                project=example(polygon);folder=Path(temporary)/str(polygon);state=execute_planar_project(project,folder)
                self.assertEqual(state['status'],'complete');self.assertEqual(state['kind'],'planar_solve');self.assertEqual(state['numerical_validation'],'not_checked')
                self.assertGreaterEqual(state['elapsed_seconds'],0)
                self.assertEqual(planar_result(read_planar_run(folder/'solution')),planar_result(solve_planar(project.case)))
                self.assertEqual(PlanarProject.load(folder/'project.json'),project)
                with self.assertRaises(FileExistsError):execute_planar_project(project,folder)

    def test_kind_downgrade_and_required_file_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            for kind in (None,'solve','study'):
                folder=Path(temporary)/str(kind);execute_planar_project(example(),folder)
                for filename in ('job.json','manifest.json'):
                    p=folder/filename;d=json.loads(p.read_text())
                    if kind is None:d.pop('kind')
                    else:d['kind']=kind
                    p.write_text(json.dumps(d))
                with self.subTest(kind=kind),self.assertRaisesRegex(ValueError,'kind=planar_solve'):read_job(folder)
            folder=Path(temporary)/'missing';execute_planar_project(example(),folder)
            p=folder/'manifest.json';data=json.loads(p.read_text());data['files'].pop('solution/manifest.json');p.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'five native files exactly'):read_job(folder)

    def test_rehashed_project_and_rf_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            for field in ('case','rf'):
                folder=Path(temporary)/field;execute_planar_project(example(True,'tm'),folder)
                if field=='case':
                    p=folder/'project.json';d=json.loads(p.read_text());d['case']['rf']['stored_energy_j_per_m']=2;p.write_text(json.dumps(d))
                else:
                    p=folder/'solution/results.json';d=json.loads(p.read_text());d['modes'][0]['q0']*=2;p.write_text(json.dumps(d));rehash(folder/'solution')
                rehash(folder)
                with self.subTest(field=field),self.assertRaises(ValueError):read_job(folder)

    def test_input_change_during_completion_fails(self):
        import superfish_ng.planar_jobs as module
        with tempfile.TemporaryDirectory() as temporary:
            project=example();folder=Path(temporary)/'run';original=module.read_planar_run
            def changed(path):
                result=original(path)
                (folder/'project.json').write_text(replace(project,display_length_unit='mm').dumps())
                return result
            with patch.object(module,'read_planar_run',side_effect=changed),self.assertRaisesRegex(ValueError,'project changed during completion'):
                execute_planar_project(project,folder)
            self.assertEqual(read_job(folder)['status'],'failed');self.assertFalse((folder/'manifest.json').exists())

    def test_implementation_change_and_save_failure_never_complete(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)/'source';before={'a.py':'a'*64};after={'a.py':'b'*64}
            with patch('superfish_ng.jobs._implementation_hashes',side_effect=[before,before,after]),self.assertRaisesRegex(ValueError,'implementation changed'):
                execute_planar_project(example(),folder)
            self.assertEqual(read_job(folder)['status'],'failed')
            folder=Path(temporary)/'disk'
            with patch('superfish_ng.planar_jobs.save_planar_run',side_effect=OSError('disk failure')),self.assertRaises(OSError):execute_planar_project(example(),folder)
            self.assertEqual(read_job(folder)['status'],'failed');self.assertFalse((folder/'manifest.json').exists())

    def test_job_changes_during_verify_rejected(self):
        import superfish_ng.planar_jobs as module
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)/'run';execute_planar_project(example(),folder);original=module.read_planar_run
            def changed(path):
                result=original(path)
                with (folder/'project.json').open('a') as stream:stream.write(' ')
                return result
            with patch.object(module,'read_planar_run',side_effect=changed),self.assertRaisesRegex(ValueError,'changed during verification'):read_job(folder)

    def test_direct_managed_import_restart_and_rerun(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);project=example(True);source=root/'native';save_planar_run(project.case,solve_planar(project.case),source)
            before={p.name:p.read_bytes() for p in source.iterdir()};manager=JobManager(root/'workspace')
            try:
                with patch('superfish_ng.planar_jobs.solve_planar',side_effect=AssertionError('import must preserve saved vectors')):
                    direct=manager.import_planar_result(source)
                    managed=manager.import_planar_result(manager.directory(direct))
                self.assertEqual(manager.status(managed,verify=True)['origin'],'imported')
                self.assertEqual(before,{p.name:p.read_bytes() for p in source.iterdir()})
                for identifier in (direct,managed):
                    self.assertEqual(before,{p.name:p.read_bytes() for p in (manager.directory(identifier)/'solution').iterdir()})
                saved_project=PlanarProject.load(manager.directory(managed)/'project.json')
                manager.close();manager=JobManager(root/'workspace')
                self.assertEqual(manager.status(managed,verify=True)['status'],'complete')
                rerun=execute_planar_project(saved_project,root/'rerun');self.assertEqual(rerun['status'],'complete')
                self.assertEqual(planar_result(read_planar_run(root/'rerun/solution')),planar_result(read_planar_run(source)))
            finally:manager.close()

    def test_import_source_change_during_copy_fails(self):
        import superfish_ng.planar_jobs as module
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);project=example();source=root/'native';save_planar_run(project.case,solve_planar(project.case),source)
            manager=JobManager(root/'workspace');original=module.shutil.copyfile
            def changed(src,dst,*args,**kwargs):
                result=original(src,dst,*args,**kwargs)
                if Path(src).name=='fields.npz':
                    with (source/'case.json').open('a') as stream:stream.write(' ')
                return result
            try:
                with patch.object(module.shutil,'copyfile',side_effect=changed),self.assertRaisesRegex(ValueError,'changed during copying'):manager.import_planar_result(source)
                self.assertEqual(manager.list()[0]['status'],'failed')
            finally:manager.close()

    def test_real_worker_cancel_restart_and_closed_manager(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);manager=JobManager(root/'workspace')
            try:
                first=manager.start_planar(PlanarProject(PlanarCase(.31,.2,nx=300,ny=300,modes=4)))
                self.assertEqual(manager.cancel(first)['status'],'cancelled')
                second=manager.start_planar(example(True,'tm'));deadline=time.monotonic()+20
                while manager.status(second)['status'] in ('queued','running') and time.monotonic()<deadline:time.sleep(.02)
                self.assertEqual(manager.status(second,verify=True)['status'],'complete')
                manager.close();manager=JobManager(root/'workspace')
                self.assertEqual(manager.status(second,verify=True)['status'],'complete')
                manager.close()
                with self.assertRaisesRegex(ValueError,'closed'):manager.start_planar(example())
                with self.assertRaisesRegex(ValueError,'closed'):manager.import_planar_result(manager.directory(second))
            finally:manager.close()

    def test_abandoned_planar_job_remains_interrupted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);folder=root/'abandoned';folder.mkdir();(folder/'job.json').write_text(json.dumps({'status':'running','kind':'planar_solve'}))
            manager=JobManager(root)
            try:
                state=manager.status('abandoned');self.assertEqual(state['status'],'interrupted');self.assertEqual(state['kind'],'planar_solve')
            finally:manager.close()

    def test_worker_reentry_preserves_complete_job_and_claim(self):
        from superfish_ng.planar_jobs import execute_prepared_planar_project,_prepare
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);folder=root/'complete';execute_planar_project(example(),folder)
            before={str(p.relative_to(folder)):p.read_bytes() for p in folder.rglob('*') if p.is_file()}
            with self.assertRaisesRegex(ValueError,'queued planar_solve'):execute_prepared_planar_project(folder)
            self.assertEqual(before,{str(p.relative_to(folder)):p.read_bytes() for p in folder.rglob('*') if p.is_file()})
            folder=root/'claimed';_prepare(example(),folder);(folder/'worker.claim').write_text('already claimed')
            before=(folder/'job.json').read_bytes()
            with self.assertRaises(FileExistsError):execute_prepared_planar_project(folder)
            self.assertEqual(before,(folder/'job.json').read_bytes())

    def test_queued_project_change_is_not_executed(self):
        from superfish_ng.planar_jobs import execute_prepared_planar_project,_prepare
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)/'queued';project=example();_prepare(project,folder)
            (folder/'project.json').write_text(replace(project,display_length_unit='mm').dumps())
            with patch('superfish_ng.planar_jobs.solve_planar',side_effect=AssertionError('changed input must not solve')):
                with self.assertRaisesRegex(ValueError,'changed after submission'):execute_prepared_planar_project(folder)
            self.assertEqual(read_job(folder)['status'],'failed');self.assertFalse((folder/'solution').exists())

    def test_cli_uses_dedicated_project(self):
        from superfish_ng.cli import main
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);project=example(True,'tm');path=root/'project.json';project.save(path);folder=root/'job'
            self.assertEqual(main(['execute-planar-project',str(path),'--out',str(folder)]),0)
            self.assertEqual(read_job(folder)['status'],'complete')
            self.assertEqual(PlanarProject.load(folder/'project.json'),project)


if __name__=='__main__':unittest.main()
