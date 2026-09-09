# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from superfish_ng import Case
from superfish_ng.project import Project
from superfish_ng.jobs import JobManager,read_job,_state
from superfish_ng.rf_optimization_jobs import execute_prepared_rf_optimization
from superfish_ng.rf_optimization_checkpoints import list_optimization_checkpoints,open_optimization_checkpoint


def request():
    data=json.loads(Path('examples/optimization/curved_rf.json').read_text())
    raw=Case.load('examples/curved_ellipse.json').to_dict()
    raw['mesh']['geometry_order']=2;raw['mesh']['contour_mesh'].update(max_edge_m=.08,min_angle_deg=5.)
    raw['geometry']['chord_tolerance_m']=.008
    data['project']=Project(Case.from_dict(raw)).to_dict();data['max_trials']=2
    # This is an intentional failed RF design, not a successful optimization.
    data['criteria']['constraints'][0]=dict(quantity='r_over_q_accelerator_ohm',lower=1e9)
    return data


class RFOptimizationJobTests(unittest.TestCase):
    def test_checkpoint_cannot_exceed_submitted_job_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);directory=root/'limited';(directory/'execution').mkdir(parents=True)
            _state(directory,'cancelled',kind='rf_optimization')
            (directory/'rf-optimization-request.json').write_text(json.dumps(dict(request=request(),max_new_trials=1,checkpoint=None)))
            (directory/'execution/checkpoint-002.json').write_text('{}')
            manager=JobManager(root)
            try:
                # Isolate the ownership/budget predicate; numerical replay is tested with actual fields below.
                with patch('superfish_ng.rf_optimization_checkpoints.replay_rf_optimization',return_value=dict(request=request())):
                    with self.assertRaisesRegex(ValueError,'budget'):open_optimization_checkpoint(manager,'limited',2)
            finally:manager.close()

    def test_invalid_preflight_creates_no_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager=JobManager(tmp)
            try:
                for changes,limit in ((dict(extra=True),None),({},True),({},0)):
                    with self.assertRaises(ValueError):manager.start_rf_optimization(dict(request(),**changes),max_new_trials=limit)
                self.assertEqual(manager.list(),[])
            finally:manager.close()

    def test_cancel_restart_owned_checkpoint_resume_and_nested_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);manager=JobManager(root)
            try:
                req=request();identifier=manager.start_rf_optimization(req)
                checkpoint=root/identifier/'execution/checkpoint-001.json';deadline=time.monotonic()+180
                while time.monotonic()<deadline:
                    try:
                        json.loads(checkpoint.read_text());break
                    except (OSError,ValueError):time.sleep(.02)
                self.assertTrue(checkpoint.is_file())
                with self.assertRaisesRegex(ValueError,'stopped'):list_optimization_checkpoints(manager,identifier)
                self.assertEqual(manager.cancel(identifier)['status'],'cancelled')
                manager.close();manager=JobManager(root)
                self.assertEqual(list_optimization_checkpoints(manager,identifier)['indices'],[1])
                saved=open_optimization_checkpoint(manager,identifier,1)
                self.assertEqual(saved['completed_fem_solves'],3)
                foreign=root/'foreign';(foreign/'execution').mkdir(parents=True)
                (foreign/'rf-optimization-request.json').write_bytes((root/identifier/'rf-optimization-request.json').read_bytes())
                (foreign/'execution/checkpoint-001.json').write_bytes(checkpoint.read_bytes())
                _state(foreign,'cancelled',kind='rf_optimization')
                with self.assertRaisesRegex(ValueError,'another'):open_optimization_checkpoint(manager,'foreign',1)
                second=manager.start_rf_optimization(req,checkpoint=saved);deadline=time.monotonic()+300
                while manager.status(second)['status'] in ('queued','running') and time.monotonic()<deadline:time.sleep(.05)
                state=manager.status(second,verify=True)
                self.assertEqual(state['status'],'complete');self.assertNotEqual(state['optimization_status'],'SEARCH_COMPLETE')
                self.assertEqual(state['computed_fem_solves'],6);self.assertFalse(state['can_resume'])
                self.assertEqual(state['numerical_validation'],'not_checked')
                manager.close();manager=JobManager(root)
                self.assertEqual(manager.status(second,verify=True),state)
                manifest=root/second/'manifest.json';original=manifest.read_text();data=json.loads(original)
                del data['files']['execution/trial-002/level-1/solution/fields.npz'];manifest.write_text(json.dumps(data))
                with self.assertRaisesRegex(ValueError,'omits'):manager.status(second,verify=True)
                manifest.write_text(original)
                source=root/identifier/'execution/trial-001/level-0/job.json';source.write_text(source.read_text()+' ')
                with self.assertRaises(ValueError):manager.status(second,verify=True)
            finally:manager.close()

    def test_request_race_never_publishes_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);path=directory/'rf-optimization-request.json'
            path.write_text(json.dumps(dict(request=request(),max_new_trials=1,checkpoint=None)))
            def changed(*args,**kwargs):
                path.write_text(path.read_text()+' ')
                return {}
            with patch('superfish_ng.rf_optimization_jobs.execute_rf_optimization',side_effect=changed):
                with self.assertRaisesRegex(RuntimeError,'request changed'):execute_prepared_rf_optimization(directory)
            self.assertEqual(read_job(directory)['status'],'failed');self.assertFalse((directory/'manifest.json').exists())
