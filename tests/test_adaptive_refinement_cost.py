# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path
import tempfile
import unittest
from superfish_ng.jobs import JobManager
from superfish_ng.adaptive_refinement_cost import refinement_cost_summary


class RefinementCostTests(unittest.TestCase):
    def test_missing_invalid_and_external_times_are_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            manager=JobManager(directory);self.addCleanup(manager.close)
            root=Path(directory);job=root/'one';job.mkdir();(job/'execution').mkdir()
            request={'schema_version':5}
            result=dict(request=request,level_runs=[str(job/'execution/event-001'),str(root/'external-run')],sources=[{},{}])
            (job/'adaptive-refinement-request.json').write_text(json.dumps(dict(request=request,checkpoint=None)))
            for value in (None,True,-1,'12'):
                (job/'job.json').write_text(json.dumps(dict(kind='adaptive_refinement',status='complete',elapsed_seconds=value)))
                cost=refinement_cost_summary(manager,result)
                self.assertFalse(cost['all_event_owners_timed']);self.assertEqual(cost['unknown_event_indices'],[0,1])
                self.assertEqual(cost['recorded_seconds'],0)
            (job/'job.json').write_text(json.dumps(dict(kind='adaptive_refinement',status='complete',elapsed_seconds=12.5)))
            cost=refinement_cost_summary(manager,result)
            self.assertEqual(cost['recorded_seconds'],12.5);self.assertEqual(cost['unknown_event_indices'],[1])
            (job/'adaptive-refinement-request.json').write_text(json.dumps(dict(request={'schema_version':4},checkpoint=None)))
            self.assertEqual(refinement_cost_summary(manager,result)['unknown_event_indices'],[0,1])

    def test_symlink_metadata_is_not_followed(self):
        with tempfile.TemporaryDirectory() as directory:
            manager=JobManager(directory);self.addCleanup(manager.close)
            root=Path(directory);job=root/'one';job.mkdir();(job/'execution').mkdir()
            (job/'adaptive-refinement-request.json').symlink_to('/unavailable-external-file')
            result=dict(request={'schema_version':5},level_runs=[str(job/'execution/event-001')],sources=[{}])
            cost=refinement_cost_summary(manager,result)
            self.assertEqual(cost['unknown_event_indices'],[0]);self.assertIn('symlink',cost['jobs'][0]['unavailable_reason'])
