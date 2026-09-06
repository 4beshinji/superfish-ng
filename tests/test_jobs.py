# SPDX-License-Identifier: Apache-2.0
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from superfish_ng.project import Project
from superfish_ng.jobs import execute_project, read_job, JobManager


def project(n=8):
    return Project.from_dict({'schema_version':1,'geometry':{'type':'pillbox','radius_m':.06,'length_m':.09},
                              'mesh':{'nr':n,'nz':n},'solver':{'modes':2}})


class JobTests(unittest.TestCase):
    def test_complete_manifest_detects_missing_output_and_overwrite(self):
        with tempfile.TemporaryDirectory() as root:
            out=Path(root)/'run'
            execute_project(project(),out)
            self.assertEqual(read_job(out)['status'],'complete')
            with self.assertRaises(FileExistsError): execute_project(project(),out)
            (out/'solution'/'fields.npz').unlink()
            with self.assertRaisesRegex(ValueError,'missing|integrity'): read_job(out)

    def test_save_failure_never_completes(self):
        with tempfile.TemporaryDirectory() as root:
            out=Path(root)/'run'
            with patch('superfish_ng.jobs.save_run',side_effect=OSError('disk failure')):
                with self.assertRaises(OSError): execute_project(project(),out)
            state=read_job(out)
            self.assertEqual(state['status'],'failed')
            self.assertIn('disk failure',state['error'])
            self.assertFalse((out/'manifest.json').exists())

    def test_background_cancel_and_retry(self):
        with tempfile.TemporaryDirectory() as root:
            manager=JobManager(root)
            first=manager.start(project(300))
            manager.cancel(first)
            self.assertEqual(manager.status(first)['status'],'cancelled')
            second=manager.start(project())
            deadline=time.monotonic()+15
            while manager.status(second)['status'] in ('queued','running') and time.monotonic()<deadline:
                time.sleep(.05)
            self.assertEqual(manager.status(second)['status'],'complete')
            self.assertNotEqual(first,second)
            manager.close()

    def test_abandoned_running_is_not_success(self):
        with tempfile.TemporaryDirectory() as root:
            out=Path(root)/'abandoned';out.mkdir()
            (out/'job.json').write_text(json.dumps({'status':'running'}))
            manager=JobManager(root)
            self.assertEqual(manager.status('abandoned')['status'],'interrupted')
            manager.close()
