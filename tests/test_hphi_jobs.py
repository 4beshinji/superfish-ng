# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import numpy as np
from scripts.hphi_mesh_reference import rectangular_holes
from superfish_ng.coaxial import CoaxialCase
from superfish_ng.hphi_mesh import HphiMeshCase
from superfish_ng.meridional_mesh import MeridionalMesh
from superfish_ng.hphi_project import HphiProject
from superfish_ng.hphi_native import solve_hphi,save_hphi_run,read_hphi_run,hphi_result
from superfish_ng.hphi_jobs import execute_hphi_project,execute_prepared_hphi_project,_prepare
from superfish_ng.jobs import JobManager,read_job
from superfish_ng.project import Project


def example(mesh=False,order=2):
    case=(HphiMeshCase(MeridionalMesh(**rectangular_holes(1)),element_order=order,modes=3) if mesh
          else CoaxialCase(.025,.05,.18,nr=3,nz=6,element_order=order,modes=3))
    return HphiProject(case,'m')


def rehash(folder):
    p=folder/'manifest.json';data=json.loads(p.read_text())
    data['files']={name:hashlib.sha256((folder/name).read_bytes()).hexdigest() for name in data['files']}
    p.write_text(json.dumps(data))


class HphiJobTests(unittest.TestCase):
    def test_project_contract_and_exclusive_save(self):
        for mesh in (False,True):
            project=example(mesh);data=project.to_dict();self.assertEqual(HphiProject.from_dict(data),project)
            with self.assertRaises(ValueError):Project.from_dict(data)
            for key,value in [('project_version',True),('display_length_unit','cm'),('reflect_full',True),('mesh_data',None)]:
                with self.assertRaises(ValueError):HphiProject.from_dict({**data,key:value})
            with tempfile.TemporaryDirectory() as temporary:
                path=Path(temporary)/'project.json';project.save(path);self.assertEqual(HphiProject.load(path),project)
                with self.assertRaises(FileExistsError):project.save(path)
                path.write_text(project.dumps().replace('"project_version": 1','"project_version": 1, "project_version": 1'))
                with self.assertRaisesRegex(ValueError,'duplicate'):HphiProject.load(path)

    def test_actual_cli_binds_both_native_types_and_units(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for mesh in (False,True):
                project=example(mesh);path=root/f'{mesh}.json';project.save(path);run=root/f'run{mesh}'
                done=subprocess.run([sys.executable,'-m','superfish_ng','execute-hphi-project',str(path),'--out',str(run)],capture_output=True,text=True)
                self.assertEqual(done.returncode,0,done.stderr)
                state=read_job(run);self.assertEqual(state,json.loads(done.stdout))
                self.assertEqual(state['kind'],'hphi_solve');self.assertEqual(state['status'],'complete')
                self.assertEqual(state['numerical_validation'],'not_checked');self.assertEqual(state['case_format'],project.case.to_dict()['format'])
                self.assertEqual(HphiProject.load(run/'project.json'),project)
                result=hphi_result(read_hphi_run(run/'solution'))
                direct=hphi_result(solve_hphi(project.case))
                for saved_mode,direct_mode in zip(result['modes'],direct['modes']):
                    self.assertEqual(saved_mode.keys(),direct_mode.keys())
                    for key,value in saved_mode.items():
                        if isinstance(value,(int,float,list)):
                            np.testing.assert_allclose(value,direct_mode[key],rtol=1e-11,atol=0)
                        elif isinstance(value,dict):
                            self.assertEqual(value.keys(),direct_mode[key].keys())
                            np.testing.assert_allclose(list(value.values()),list(direct_mode[key].values()),rtol=1e-11,atol=0)
                        else:self.assertEqual(value,direct_mode[key])
                self.assertIn('energy in J',result['conventions']['normalization'])
                self.assertIsNone(result['modes'][0]['r_over_q_circuit_ohm'])
                with self.assertRaises(FileExistsError):execute_hphi_project(project,run)

    def test_kind_downgrade_and_rehashed_mismatches_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for mesh in (False,True):
                run=root/f'kind{mesh}';execute_hphi_project(example(mesh),run)
                for name in ('job.json','manifest.json'):
                    p=run/name;data=json.loads(p.read_text());data['kind']='solve';p.write_text(json.dumps(data))
                with self.assertRaisesRegex(ValueError,'kind=hphi_solve'):read_job(run)
                run=root/f'project{mesh}';execute_hphi_project(example(mesh),run)
                p=run/'project.json';data=json.loads(p.read_text());data['case']['rf']['stored_energy_j']=2.;p.write_text(json.dumps(data));rehash(run)
                with self.assertRaisesRegex(ValueError,'differs from the job Project'):read_job(run)
                run=root/f'rf{mesh}';execute_hphi_project(example(mesh),run)
                p=run/'solution/results.json';data=json.loads(p.read_text());data['modes'][0]['q0']*=2;p.write_text(json.dumps(data));rehash(run/'solution');rehash(run)
                with self.assertRaises(ValueError):read_job(run)
            run=root/'missing';execute_hphi_project(example(),run)
            p=run/'manifest.json';data=json.loads(p.read_text());data['files'].pop('solution/manifest.json');p.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'five native files exactly'):read_job(run)

    def test_completion_changes_and_save_failure_never_complete(self):
        import superfish_ng.hphi_jobs as module
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);project=example(True);run=root/'changed';original=module.read_hphi_run
            def change(path):
                result=original(path);(run/'project.json').write_text(replace(project,display_length_unit='mm').dumps());return result
            with patch.object(module,'read_hphi_run',side_effect=change):
                with self.assertRaisesRegex(ValueError,'project changed during completion'):execute_hphi_project(project,run)
            self.assertEqual(read_job(run)['status'],'failed');self.assertFalse((run/'manifest.json').exists())
            run=root/'source'
            with patch('superfish_ng.jobs._implementation_hashes',side_effect=[{'a':'a'*64},{'a':'b'*64}]):
                with self.assertRaisesRegex(ValueError,'implementation changed'):execute_hphi_project(project,run)
            self.assertEqual(read_job(run)['status'],'failed')
            run=root/'disk'
            with patch.object(module,'save_hphi_run',side_effect=OSError('disk failure')):
                with self.assertRaises(OSError):execute_hphi_project(project,run)
            self.assertEqual(read_job(run)['status'],'failed');self.assertFalse((run/'manifest.json').exists())

    def test_import_preserves_coefficients_and_supports_restart_rerun(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);manager=JobManager(root/'workspace')
            try:
                for mesh in (False,True):
                    project=example(mesh);source=root/f'native{mesh}';save_hphi_run(project.case,solve_hphi(project.case),source)
                    before={p.name:p.read_bytes() for p in source.iterdir()}
                    with patch('superfish_ng.hphi_jobs.solve_hphi',side_effect=AssertionError('import must preserve saved vectors')):
                        direct=manager.import_hphi_result(source);managed=manager.import_hphi_result(manager.directory(direct))
                    for identifier in (direct,managed):
                        self.assertEqual(before,{p.name:p.read_bytes() for p in (manager.directory(identifier)/'solution').iterdir()})
                        self.assertEqual(manager.status(identifier,verify=True)['origin'],'imported')
                    saved=HphiProject.load(manager.directory(managed)/'project.json')
                    manager.close();manager=JobManager(root/'workspace')
                    self.assertEqual(manager.status(managed,verify=True)['status'],'complete')
                    execute_hphi_project(saved,root/f'rerun{mesh}')
                    self.assertEqual(hphi_result(read_hphi_run(root/f'rerun{mesh}/solution')),hphi_result(read_hphi_run(source)))
                    self.assertEqual(before,{p.name:p.read_bytes() for p in source.iterdir()})
            finally:manager.close()

    def test_source_change_during_import_and_verify_rejected(self):
        import superfish_ng.hphi_jobs as module
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);project=example(True);source=root/'source';save_hphi_run(project.case,solve_hphi(project.case),source)
            manager=JobManager(root/'workspace');original=module.shutil.copyfile
            def change(src,dst,*args,**kwargs):
                result=original(src,dst,*args,**kwargs)
                if Path(src).name=='fields.npz':
                    with (source/'case.json').open('a') as stream:stream.write(' ')
                return result
            try:
                with patch.object(module.shutil,'copyfile',side_effect=change):
                    with self.assertRaisesRegex(ValueError,'changed during copying'):manager.import_hphi_result(source)
                self.assertEqual(manager.list()[0]['status'],'failed')
            finally:manager.close()
            run=root/'verify';execute_hphi_project(project,run);original_read=module.read_hphi_run
            def change_verify(path):
                result=original_read(path)
                with (run/'project.json').open('a') as stream:stream.write(' ')
                return result
            with patch.object(module,'read_hphi_run',side_effect=change_verify):
                with self.assertRaisesRegex(ValueError,'changed during verification'):read_job(run)

    def test_real_worker_cancel_restart_and_closed_manager(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);manager=JobManager(root/'workspace')
            try:
                identifier=manager.start_hphi(HphiProject(CoaxialCase(.025,.05,.18,nr=150,nz=150)))
                self.assertEqual(manager.cancel(identifier)['status'],'cancelled')
                for mesh in (False,True):
                    identifier=manager.start_hphi(example(mesh));deadline=time.monotonic()+20
                    while manager.status(identifier)['status'] in ('queued','running') and time.monotonic()<deadline:time.sleep(.02)
                    self.assertEqual(manager.status(identifier,verify=True)['status'],'complete')
                    manager.close();manager=JobManager(root/'workspace')
                    self.assertEqual(manager.status(identifier,verify=True)['status'],'complete')
                manager.close()
                with self.assertRaisesRegex(ValueError,'closed'):manager.start_hphi(example())
                with self.assertRaisesRegex(ValueError,'closed'):manager.import_hphi_result(manager.directory(identifier))
            finally:manager.close()

    def test_queued_change_reentry_claim_and_abandoned_recovery(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);project=example();run=root/'queued';_prepare(project,run)
            (run/'project.json').write_text(replace(project,display_length_unit='mm').dumps())
            with patch('superfish_ng.hphi_jobs.solve_hphi',side_effect=AssertionError('changed input must not solve')):
                with self.assertRaisesRegex(ValueError,'changed after submission'):execute_prepared_hphi_project(run)
            self.assertEqual(read_job(run)['status'],'failed');self.assertFalse((run/'solution').exists())
            run=root/'complete';execute_hphi_project(project,run)
            before={str(p.relative_to(run)):p.read_bytes() for p in run.rglob('*') if p.is_file()}
            with self.assertRaisesRegex(ValueError,'queued hphi_solve'):execute_prepared_hphi_project(run)
            self.assertEqual(before,{str(p.relative_to(run)):p.read_bytes() for p in run.rglob('*') if p.is_file()})
            run=root/'claimed';_prepare(project,run);(run/'worker.claim').write_text('claimed')
            before=(run/'job.json').read_bytes()
            with self.assertRaises(FileExistsError):execute_prepared_hphi_project(run)
            self.assertEqual((run/'job.json').read_bytes(),before)
            workspace=root/'abandoned-workspace';run=workspace/'abandoned';run.mkdir(parents=True)
            (run/'job.json').write_text(json.dumps(dict(status='running',kind='hphi_solve')))
            manager=JobManager(workspace)
            try:self.assertEqual(manager.status('abandoned')['status'],'interrupted')
            finally:manager.close()
