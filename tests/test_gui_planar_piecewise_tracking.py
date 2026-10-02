# SPDX-License-Identifier: Apache-2.0
"""Strict GUI transport for explicit charts and original piecewise laws."""
import json
from pathlib import Path
import tempfile
import unittest
from superfish_ng.gui_planar import planar_tracking_response
from superfish_ng.jobs import JobManager
from superfish_ng.planar_piecewise_mapping import PlanarPiecewiseMapping
from superfish_ng.planar_tracking import PlanarTrackingRequest
from superfish_ng.planar_tuning import planar_tune_mapping, trial_planar_project
from test_planar_piecewise_tuning import shape_request


class PlanarPiecewiseTrackingGuiTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.manager = JobManager(Path(temporary.name)/'workspace')
        self.addCleanup(self.manager.close)

    def requests(self):
        raw = shape_request(nx=4)
        previous = dict(value=0., phase='search')
        current = dict(value=1., phase='search')
        meshes = [trial_planar_project(raw, t['value'], t['phase']).case.mesh
                  for t in (previous, current)]
        return [PlanarTrackingRequest(1, 1, ['first'], mapping=mapping).to_dict()
                for mapping in (PlanarPiecewiseMapping(*meshes),
                                planar_tune_mapping(raw, previous, current))]

    def test_exact_json_declarations_and_no_job_allocation(self):
        manager = self.manager
        for request in self.requests():
            with self.subTest(version=request['tracking_version']):
                response, _ = planar_tracking_response(manager, 'planar-normalize-tracking',
                                                      dict(document=json.dumps(request)))
                self.assertEqual(response, request)
        self.assertEqual(manager.list(), [])

    def test_raw_duplicate_mapping_and_controls_are_rejected(self):
        manager = self.manager
        for request in self.requests():
            text = json.dumps(request)
            name = json.dumps(request['mapping']['name'])
            for invalid in (text.replace('"name": '+name,
                                         '"name": '+name+', "name": '+name, 1),
                            text.replace('"minimum_overlap": 0.9',
                                         '"minimum_overlap": 0.9, "minimum_overlap": 0.1', 1)):
                with self.subTest(version=request['tracking_version']), self.assertRaisesRegex(ValueError, 'duplicate'):
                    planar_tracking_response(manager, 'planar-normalize-tracking', dict(document=invalid))
        self.assertEqual(manager.list(), [])


if __name__ == '__main__':
    unittest.main()
