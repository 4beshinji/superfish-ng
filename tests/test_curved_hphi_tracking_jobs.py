# SPDX-License-Identifier: Apache-2.0
from contextlib import ExitStack
from dataclasses import replace
from pathlib import Path
import hashlib,json,shutil,tempfile,unittest
from superfish_ng.curved_hphi_tracking_jobs import execute_curved_hphi_tracking,read_curved_hphi_tracking,_prepare,execute_prepared_curved_hphi_tracking
from superfish_ng.hphi_native import save_hphi_run
from superfish_ng.hphi_jobs import execute_hphi_project
from superfish_ng.hphi_project import HphiProject
from superfish_ng.jobs import JobManager,read_job
from test_curved_hphi_tuning_saved import request as tune_request
from superfish_ng.curved_hphi_shape_tuning import CurvedHphiShapeLaw
from superfish_ng.curved_hphi_tune_trials import build_curved_hphi_tune_trial,curved_hphi_trial_comparison
from superfish_ng.curved_hphi import solve_curved_hphi


def pair():
    data=tune_request();project=HphiProject.from_dict(data['project'])
    law=CurvedHphiShapeLaw.from_dict(data['shape_law'])
    a,b=[build_curved_hphi_tune_trial(project,law,value) for value in (1.,1.05)]
    q=curved_hphi_trial_comparison(a,b,previous_mode_ids=['TEM'],previous_mode_count=1,current_mode_count=1)
    return tuple(solve_curved_hphi(t.project.case) for t in (a,b)),q


def sources(root,managed=False):
    (a,b),request=pair()
    previous,current=root/'previous-source',root/'current-source'
    if managed:execute_hphi_project(HphiProject(a.case,display_length_unit='m'),previous)
    else:save_hphi_run(a.case,a,previous)
    save_hphi_run(b.case,b,current)
    return previous,current,request


class CurvedHphiTrackingJobTests(unittest.TestCase):
    def test_portable_owned_projects_native_and_rehashed_result_rejection(self):
        with tempfile.TemporaryDirectory() as t,ExitStack() as cleanup:
            root=Path(t);a,b,q=sources(root,managed=True)
            original={str(p.relative_to(root)):p.read_bytes() for parent in (a,b) for p in parent.rglob('*') if p.is_file()}
            run=root/'tracking';report=execute_curved_hphi_tracking(a,b,q,run);self.assertEqual(report['status'],'PASS')
            for path,data in original.items():self.assertEqual((root/path).read_bytes(),data)
            self.assertEqual((run/'previous/project.json').read_bytes(),(a/'project.json').read_bytes())
            a.rename(root/'moved-previous');b.rename(root/'moved-current')
            self.assertEqual(read_curved_hphi_tracking(run),report);self.assertEqual(read_job(run)['status'],'complete')
            manager=JobManager(root/'imports');cleanup.callback(manager.close)
            imported=manager.import_hphi_result(run/'previous')
            self.assertEqual(HphiProject.load(manager.directory(imported)/'project.json').display_length_unit,'m')
            self.assertEqual({p.name:p.read_bytes() for p in (manager.directory(imported)/'solution').iterdir()},
                             {p.name:p.read_bytes() for p in (run/'previous/solution').iterdir()})
            with self.assertRaises(FileExistsError):execute_curved_hphi_tracking(run/'previous',run/'current',q,run)
            p=run/'tracking-results.json';data=json.loads(p.read_text());data['current_mode_ids'][0]='forged';p.write_text(json.dumps(data))
            p=run/'manifest.json';manifest=json.loads(p.read_text());manifest['files']['tracking-results.json']=hashlib.sha256((run/'tracking-results.json').read_bytes()).hexdigest();p.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):read_curved_hphi_tracking(run)

    def test_worker_cancel_restart_and_forged_kind_cannot_change_routing(self):
        with tempfile.TemporaryDirectory() as t,ExitStack() as cleanup:
            root=Path(t);a,b,q=sources(root);manager=JobManager(root/'jobs');cleanup.callback(manager.close)
            cancelled=manager.start_curved_hphi_tracking(a,b,q);self.assertEqual(manager.cancel(cancelled)['status'],'cancelled')
            identifier=manager.start_curved_hphi_tracking(a,b,q);self.assertEqual(manager.processes[identifier].wait(timeout=180),0)
            directory=manager.directory(identifier);report=read_curved_hphi_tracking(directory);self.assertEqual(report['status'],'PASS')
            manager.close();manager=JobManager(root/'jobs');cleanup.callback(manager.close)
            self.assertEqual(manager.status(cancelled)['status'],'cancelled');self.assertEqual(manager.status(identifier,verify=True)['status'],'complete')
            for name in ('job.json','manifest.json'):
                p=directory/name;raw=json.loads(p.read_text());raw['kind']='hphi_convergence';p.write_text(json.dumps(raw))
            with self.assertRaises(ValueError):read_job(directory)

    def test_queued_input_change_and_linked_native_are_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);a,b,q=sources(root);run=root/'prepared';_prepare(a,b,q,run)
            p=run/'tracking.json';raw=json.loads(p.read_text());raw['controls']['minimum_overlap']=.8;p.write_text(json.dumps(raw))
            with self.assertRaisesRegex(ValueError,'queued hphi tracking inputs changed'):execute_prepared_curved_hphi_tracking(run)
            self.assertEqual(json.loads((run/'job.json').read_text())['status'],'failed')
            with self.assertRaises(ValueError):execute_prepared_curved_hphi_tracking(run)
            linked=root/'linked-source';shutil.copytree(b,linked);(linked/'fields.npz').unlink();(linked/'fields.npz').symlink_to(b/'fields.npz')
            with self.assertRaises(ValueError):execute_curved_hphi_tracking(a,linked,q,root/'must-not-exist')
            self.assertFalse((root/'must-not-exist').exists())
            with self.assertRaises(ValueError):execute_curved_hphi_tracking(a,b,replace(q,controls=replace(q.controls,max_dofs=1)),root/'budget-fail')
            self.assertFalse((root/'budget-fail').exists())
            with self.assertRaises(ValueError):execute_curved_hphi_tracking(a,b,replace(q,max_sample_points=1),root/'samples-fail')
            self.assertFalse((root/'samples-fail').exists())
            from test_hphi_tracking import pair as straight_pair
            (straight,_),_=straight_pair();save_hphi_run(straight.case,straight,root/'straight')
            with self.assertRaisesRegex(ValueError,'original curved Hphi'):
                execute_curved_hphi_tracking(root/'straight',b,q,root/'physics-fail')
            self.assertFalse((root/'physics-fail').exists())


if __name__=='__main__':unittest.main()
