# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import time
import unittest
from superfish_ng.constants import C0
from superfish_ng.jobs import JobManager
from superfish_ng.planar_jobs import _job_hashes
from superfish_ng.planar_tuning import read_planar_tune
from superfish_ng.planar_tuning_jobs import RESULT
from test_planar_tuning_recovery import recovery_request


class PlanarTuneRecoveryJobTests(unittest.TestCase):
    def test_cli_search_worker_final_refinement_and_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);raw=recovery_request()
            request=root/'request.json';request.write_text(json.dumps(raw))
            command=subprocess.run([sys.executable,'-m','superfish_ng','tune-planar',str(request),
                '--out',str(root/'search'),'--max-new-trials','2'],capture_output=True,text=True,timeout=240)
            self.assertEqual(command.returncode,0,command.stderr)
            original=read_planar_tune(root/'search/checkpoint-002.json')
            self.assertEqual(original['trials'][-1]['identity_recovery']['status'],'PASS')
            before=[_job_hashes(Path(p)) for p in original['trial_runs']]
            manager=JobManager(root/'workspace')
            try:
                identifier=manager.start_planar_tune(raw,checkpoint=original)
                self.assertEqual(manager.processes[identifier].wait(timeout=240),0)
                self.assertEqual(manager.status(identifier,verify=True)['tuning_status'],'TUNED')
                result=read_planar_tune(manager.directory(identifier)/RESULT)
                event=result['trials'][-1]['identity_recovery']
                self.assertEqual((event['parent_trial_index'],event['anchor_trial_index']),(1,0))
                self.assertEqual(result['trials'][-1]['current_mode_ids'],['x','y'])
                self.assertEqual(result['trial_sources_sha256'][:2],before)
                manager.close();manager=JobManager(root/'workspace')
                self.assertEqual(manager.status(identifier,verify=True)['tuning_status'],'TUNED')
                self.assertEqual(before,[_job_hashes(Path(p)) for p in original['trial_runs']])
                path=manager.directory(identifier)/'execution/checkpoint-003.json'
                saved=path.read_bytes();data=json.loads(saved)
                data['trials'][-1]['identity_recovery']['anchor_trial_index']=1
                path.write_text(json.dumps(data))
                with self.assertRaises(ValueError):manager.status(identifier,verify=True)
                path.write_bytes(saved)
            finally:manager.close()

    def test_actual_cancel_after_verified_initial_and_recovered_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);manager=JobManager(root/'workspace');raw=recovery_request()
            raw.update(target_hz=C0/(2*.2112),frequency_tolerance_hz=1e-5,parameter_tolerance=1e-15,max_trials=60)
            try:
                identifier=manager.start_planar_tune(raw)
                checkpoint=manager.directory(identifier)/'execution/checkpoint-001.json'
                prior=None;deadline=time.monotonic()+120
                while time.monotonic()<deadline:
                    try:prior=read_planar_tune(checkpoint);break
                    except (OSError,ValueError):time.sleep(.01)
                self.assertIsNotNone(prior)
                self.assertEqual(prior['trials'][0]['initial_tracking']['status'],'PASS')
                self.assertIsNone(manager.processes[identifier].poll())
                self.assertEqual(manager.cancel(identifier)['status'],'cancelled')
                self.assertIsNotNone(manager.processes[identifier].poll())
                self.assertEqual(read_planar_tune(checkpoint),prior)
                resumed=manager.start_planar_tune(raw,checkpoint=prior,max_new_trials=1)
                self.assertEqual(manager.processes[resumed].wait(timeout=240),0)
                result=read_planar_tune(manager.directory(resumed)/RESULT)
                self.assertEqual(result['status'],'PAUSED')
                self.assertEqual(result['trials'][-1]['identity_recovery']['status'],'PASS')
                self.assertEqual(result['trials'][-1]['current_mode_ids'],['x','y'])
                self.assertFalse((manager.directory(resumed)/'execution/trial-001').exists())
            finally:manager.close()


if __name__=='__main__':unittest.main()
