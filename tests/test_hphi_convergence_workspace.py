# SPDX-License-Identifier: Apache-2.0
from contextlib import ExitStack
import hashlib,json,tempfile,threading,unittest
from pathlib import Path
from superfish_ng.hphi_convergence_jobs import read_hphi_convergence_job
from superfish_ng.hphi_convergence_saved import read_hphi_convergence
from superfish_ng.jobs import JobManager,read_job
from superfish_ng.gui_hphi import hphi_response
from test_hphi_convergence import request


class HphiConvergenceWorkspaceTests(unittest.TestCase):
    def test_worker_cancel_restart_and_gui_level_preserve_project_and_native(self):
        with tempfile.TemporaryDirectory() as t,ExitStack() as cleanup:
            root=Path(t);manager=JobManager(root/'jobs');cleanup.callback(manager.close);q=request()
            cancelled=manager.start_hphi_convergence(q);self.assertEqual(manager.cancel(cancelled)['status'],'cancelled')
            identifier=manager.start_hphi_convergence(q);self.assertEqual(manager.processes[identifier].wait(timeout=90),0)
            directory=manager.directory(identifier);report=read_hphi_convergence_job(directory);self.assertEqual(read_hphi_convergence(directory),report)
            state=manager.status(identifier,verify=True);self.assertEqual(state['status'],'complete');self.assertEqual(state['numerical_validation'],report['status'])
            original={str(p.relative_to(directory)):p.read_bytes() for p in directory.glob('point-*/solution/*') if p.is_file()}
            lock=threading.Lock()
            def api(action,**data):return hphi_response(manager,action,data,lock,root/'cache')[0]
            self.assertEqual(api('hphi-normalize-convergence',document=q.to_dict()),q.to_dict())
            reply=api('hphi-convergence-result',id=identifier);self.assertEqual(reply['result'],report)
            imported=api('hphi-convergence-point',id=identifier,index=1)['id'];point=api('hphi-result',id=imported)
            self.assertEqual(point['project'],q.projects[1].to_dict())
            target=manager.directory(imported)/'solution';self.assertEqual({p.name:p.read_bytes() for p in target.iterdir()},{p.name:p.read_bytes() for p in (directory/'point-0001/solution').iterdir()})
            with self.assertRaises(ValueError):api('hphi-convergence-point',id=identifier,index=True)
            manager.close();manager=JobManager(root/'jobs');cleanup.callback(manager.close)
            self.assertEqual(manager.status(identifier,verify=True)['status'],'complete');self.assertEqual(manager.status(cancelled)['status'],'cancelled')
            self.assertEqual(original,{str(p.relative_to(directory)):p.read_bytes() for p in directory.glob('point-*/solution/*') if p.is_file()})

    def test_rehashed_kind_and_request_change_rejected(self):
        with tempfile.TemporaryDirectory() as t,ExitStack() as cleanup:
            root=Path(t);manager=JobManager(root/'jobs');cleanup.callback(manager.close)
            identifier=manager.start_hphi_convergence(request());self.assertEqual(manager.processes[identifier].wait(timeout=90),0);directory=manager.directory(identifier)
            for name in ('job.json','manifest.json'):
                p=directory/name;raw=json.loads(p.read_text());raw['kind']='hphi_study';p.write_text(json.dumps(raw))
            with self.assertRaises(ValueError):read_job(directory)
            for name in ('job.json','manifest.json'):
                p=directory/name;raw=json.loads(p.read_text());raw['kind']='hphi_convergence';p.write_text(json.dumps(raw))
            p=directory/'convergence.json';raw=json.loads(p.read_text());raw['thresholds']['frequency_relative']=.9;p.write_text(json.dumps(raw))
            p=directory/'manifest.json';raw=json.loads(p.read_text());raw['files']['convergence.json']=hashlib.sha256((directory/'convergence.json').read_bytes()).hexdigest();p.write_text(json.dumps(raw))
            with self.assertRaises(ValueError):read_job(directory)


if __name__=='__main__':unittest.main()
