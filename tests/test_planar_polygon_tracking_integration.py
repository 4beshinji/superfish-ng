# SPDX-License-Identifier: Apache-2.0
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng.planar_mesh import PlanarMesh
from superfish_ng.planar_polygon import PlanarPolygonCase
from superfish_ng.planar_refinement import refine_planar_mesh
from superfish_ng.planar import solve_planar
from superfish_ng.planar_saved import save_planar_run
from superfish_ng.planar_tracking import PlanarTrackingRequest,track_planar_modes
from superfish_ng.planar_tracking_polygon import PolygonScaleMapping
from superfish_ng.planar_tracking_jobs import execute_planar_tracking,read_planar_tracking,_snapshot
from superfish_ng.jobs import JobManager


class PolygonTrackingIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        points=np.array([[0.,0.],[.2,0.],[.2,.2]])
        mesh=PlanarMesh.create(points,points,[[0,1,2]])
        for _ in range(3):mesh=refine_planar_mesh(mesh)
        finer=refine_planar_mesh(mesh)
        scaled=PlanarMesh.create(finer.polygon_xy_m*2,finer.points_xy_m*2,finer.triangles)
        cls.pairs={pol:(solve_planar(PlanarPolygonCase(mesh,pol,1,3)),solve_planar(PlanarPolygonCase(scaled,pol,2,3,3.))) for pol in ('te','tm')}

    def request(self):
        return PlanarTrackingRequest(1,1,['fundamental'],mapping=PolygonScaleMapping(2.,current_refinements=1))

    def test_versions_and_mapping_rejection(self):
        legacy=PlanarTrackingRequest().to_dict();self.assertEqual(legacy['tracking_version'],1)
        self.assertEqual(PlanarTrackingRequest.from_dict(legacy).to_dict(),legacy)
        current=self.request().to_dict();self.assertEqual(current['tracking_version'],2)
        self.assertEqual(PlanarTrackingRequest.from_dict(current).to_dict(),current)
        for bad in ({**current,'tracking_version':1},{**current,'tracking_version':True},{**legacy,'tracking_version':2},{**current,'mapping':{**current['mapping'],'rotation':0}}):
            with self.assertRaises(ValueError):PlanarTrackingRequest.from_dict(bad)

    def test_mixed_order_forward_reverse_and_guard(self):
        for a,b in self.pairs.values():
            forward=track_planar_modes(a,b,self.request())
            reverse=track_planar_modes(b,a,PlanarTrackingRequest(1,1,['fundamental'],mapping=PolygonScaleMapping(.5,previous_refinements=1)))
            for result in (forward,reverse):
                self.assertEqual(result['status'],'PASS');self.assertEqual(result['current_mode_ids'],['fundamental']);self.assertEqual(result['result_version'],2)
                self.assertEqual(result['physical_mapping']['reference_measure'],'previous physical xy area in m^2')
            self.assertAlmostEqual(forward['matches'][0]['minimum_principal_overlap'],reverse['matches'][0]['minimum_principal_overlap'],places=12)
            with self.assertRaisesRegex(ValueError,'guard'):
                track_planar_modes(a,b,PlanarTrackingRequest(3,3,['a','b','c'],mapping=self.request().mapping))

    def test_real_worker_full_replay_and_rehashed_result_rejection(self):
        a,b=self.pairs['tm']
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);save_planar_run(a.case,a,root/'previous');save_planar_run(b.case,b,root/'current')
            manager=JobManager(root/'workspace')
            try:
                identifier=manager.start_planar_tracking(root/'previous',root/'current',self.request())
                self.assertEqual(manager.processes[identifier].wait(timeout=60),0)
                folder=manager.directory(identifier);before=_snapshot(folder)
                self.assertEqual(manager.status(identifier,verify=True)['status'],'complete')
                self.assertEqual(read_planar_tracking(folder)['request'],self.request().to_dict());self.assertEqual(_snapshot(folder),before)
                data=json.loads((folder/'tracking-results.json').read_text());data['physical_mapping']['declaration']['scale']=3
                (folder/'tracking-results.json').write_text(json.dumps(data));manifest=json.loads((folder/'manifest.json').read_text());manifest['files']['tracking-results.json']=hashlib.sha256((folder/'tracking-results.json').read_bytes()).hexdigest();(folder/'manifest.json').write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValueError,'full native'):read_planar_tracking(folder)
            finally:manager.close()

    def test_invalid_source_pair_creates_no_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);a,b=self.pairs['tm'];te=self.pairs['te'][1]
            for name,s in [('a',a),('b',b),('te',te)]:save_planar_run(s.case,s,root/name)
            with self.assertRaisesRegex(ValueError,'polarization'):
                execute_planar_tracking(root/'a',root/'te',self.request(),root/'wrong-pol')
            self.assertFalse((root/'wrong-pol').exists())
            wrong=PlanarTrackingRequest(1,1,['fundamental'],mapping=PolygonScaleMapping(1.9,current_refinements=1))
            with self.assertRaisesRegex(ValueError,'coordinates'):
                execute_planar_tracking(root/'a',root/'b',wrong,root/'wrong-scale')
            self.assertFalse((root/'wrong-scale').exists())
