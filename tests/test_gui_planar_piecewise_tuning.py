# SPDX-License-Identifier: Apache-2.0
"""GUI ownership of piecewise tune requests, stopped prefixes and native fields."""
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng.jobs import JobManager
from superfish_ng.gui_planar_tuning import planar_tuning_response
from superfish_ng.planar_tuning_jobs import INPUT, RESULT
from test_planar_piecewise_tuning import shape_request


class PlanarPiecewiseTuneGuiTests(unittest.TestCase):
    def test_owned_checkpoint_import_and_resume_after_original_job_moves(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); manager = JobManager(root/'workspace')
            try:
                raw = shape_request(nx=4)
                normalized = planar_tuning_response(manager, 'planar-normalize-tune', dict(request=json.dumps(raw)))
                self.assertEqual(normalized, raw)
                first = planar_tuning_response(manager, 'planar-start-tune', dict(request=raw, max_new_trials=1))['id']
                self.assertEqual(manager.processes[first].wait(timeout=180), 0)
                opened = planar_tuning_response(manager, 'planar-open-tune-checkpoint', dict(id=first, index=1))
                self.assertEqual(opened['document']['schema_version'], 2)
                self.assertEqual(opened['document']['request'], raw)
                before = (manager.directory(first)/INPUT).read_bytes()
                imported = planar_tuning_response(manager, 'planar-tune-trial', dict(document=opened['serialized'], index=1))
                self.assertEqual(imported['mode'], 1)
                source = manager.directory(first)/'execution/trial-001/solution'
                target = manager.directory(imported['id'])/'solution'
                for path in source.glob('*.npz'):
                    with np.load(path) as a, np.load(target/path.name) as b:
                        self.assertEqual(set(a.files), set(b.files))
                        for key in a.files: np.testing.assert_array_equal(a[key], b[key])
                self.assertEqual((source/'results.json').read_bytes(), (target/'results.json').read_bytes())
                second = planar_tuning_response(manager, 'planar-resume-tune', dict(document=opened['serialized'], max_new_trials=1))['id']
                manager.processes.pop(first)
                manager.directory(first).rename(root/'original-moved')
                self.assertEqual(manager.processes[second].wait(timeout=180), 0)
                inherited = planar_tuning_response(manager, 'planar-open-tune-checkpoint', dict(id=second, index=1))
                self.assertEqual(inherited['document']['trials'], opened['document']['trials'])
                self.assertEqual(inherited['document']['trial_sources_sha256'], opened['document']['trial_sources_sha256'])
                self.assertEqual(before, (root/'original-moved'/INPUT).read_bytes())
                result = planar_tuning_response(manager, 'planar-tune-result', dict(id=second))
                self.assertEqual(result['document']['status'], 'PAUSED')
                self.assertEqual(planar_tuning_response(manager, 'planar-replay-tune', dict(document=result['serialized'])), result)
                manager.close(); manager = JobManager(root/'workspace')
                self.assertEqual(planar_tuning_response(manager, 'planar-tune-result', dict(id=second)), result)
                self.assertTrue((manager.directory(second)/RESULT).is_file())
            finally: manager.close()


if __name__ == '__main__':
    unittest.main()
