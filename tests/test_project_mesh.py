# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import numpy as np
from superfish_ng import Case,solve
from superfish_ng.project import Project
from superfish_ng.mesh import make_mesh
from superfish_ng.mesh_input import mesh_to_dict
from superfish_ng.jobs import execute_project,JobManager,read_job
from superfish_ng.saved import read_solution
from superfish_ng.studies import Study


def explicit_project(case):
    data=mesh_to_dict(make_mesh(case));n=len(data['points'])
    data['points'].reverse()
    for name in ('triangles','boundary_edges'):data[name]=[[n-1-i for i in row] for row in data[name]]
    return Project(case,mesh_data=data)


class ProjectMeshTests(unittest.TestCase):
    def test_project_changed_during_solve_cannot_publish_completion(self):
        p=explicit_project(Case(((0.,.1),(.2,.1)),nr=4,nz=6,modes=1))
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'run'
            def changed(case,**kwargs):
                raw=json.loads((out/'project.json').read_text());raw['case']['name']='changed during solve'
                (out/'project.json').write_text(json.dumps(raw))
                return solve(case,**kwargs)
            with patch('superfish_ng.jobs.solve',side_effect=changed):
                with self.assertRaisesRegex(RuntimeError,'project input changed'):execute_project(p,out)
            self.assertEqual(read_job(out,verify=False)['status'],'failed')
            self.assertFalse((out/'manifest.json').exists())

    def test_strict_version_snapshot_and_legacy_roundtrip(self):
        case=Case(((0.,.1),(.2,.1)),nr=4,nz=6,modes=1)
        old=Project(case).to_dict();self.assertEqual(old,Project.from_dict(old).to_dict())
        p=explicit_project(case);raw=p.to_dict();self.assertEqual(raw['project_version'],2)
        self.assertEqual(Project.from_dict(raw).to_dict(),raw)
        raw['mesh_data']['points'][0][0]+=1
        self.assertNotEqual(raw,p.to_dict())
        for change in (dict(mesh_data=None),dict(project_version=1),dict(unknown=True)):
            with self.assertRaises(ValueError):Project.from_dict(dict(p.to_dict(),**change))
        broken=p.to_dict();broken['mesh_data']['boundary_tags'][0]='unsupported'
        with self.assertRaises(ValueError):Project.from_dict(broken)
        with self.assertRaises(ValueError):Study(p,'mesh_convergence','mesh_scale',[1,2])

    def test_supplied_connectivity_is_used_for_affine_and_curved_jobs(self):
        base=Case(((0.,.1),(.2,.1)),nr=4,nz=6,modes=1)
        raw=Case.load('examples/curved_ellipse.json').to_dict();raw['mesh']['geometry_order']=2
        raw['mesh']['contour_mesh'].update(max_edge_m=.08,min_angle_deg=5.);raw['geometry']['chord_tolerance_m']=.008
        cases=[base,replace(base,element_order=2),Case.from_dict(raw)]
        with tempfile.TemporaryDirectory() as tmp:
            for index,case in enumerate(cases):
                p=explicit_project(case);expected=solve(case,mesh_data=p.mesh_data);reference=solve(case);out=Path(tmp)/str(index)
                np.testing.assert_allclose(expected.frequencies_hz,reference.frequencies_hz,rtol=1e-11,atol=0)
                with patch('superfish_ng.solver.make_mesh',side_effect=AssertionError('must use supplied mesh')),patch('superfish_ng.curved_solution.make_mesh',side_effect=AssertionError('must use supplied mesh')):
                    execute_project(p,out)
                self.assertEqual(read_job(out)['status'],'complete')
                saved=read_solution(out/'solution')
                np.testing.assert_array_equal(saved.frequencies_hz,expected.frequencies_hz)
                self.assertEqual(json.loads((out/'solution/mesh.json').read_text()),p.mesh_data)
                if case.geometry_order==2:
                    projects=Study(p,'fixed_geometry_convergence','/case/mesh/curved_refinement_levels',[0,1]).projects()
                    self.assertTrue(all(x.mesh_data==p.mesh_data for x in projects))
                (out/'solution/mesh.json').write_text('{}')
                with self.assertRaises(ValueError):read_job(out)

    def test_cli_managed_job_restart_and_reflection(self):
        from superfish_ng.cli import main
        case=Case(((0.,.1),(.1,.1)),nr=4,nz=6,modes=1,z_min='electric_symmetry')
        p=replace(explicit_project(case),reflect_full=True)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p.save(root/'project.json')
            self.assertEqual(main(['run-project',str(root/'project.json'),'--out',str(root/'cli')]),0)
            manager=JobManager(root/'jobs')
            try:
                identifier=manager.start(p);deadline=time.monotonic()+20
                while manager.status(identifier)['status'] in ('queued','running'):
                    if time.monotonic()>deadline:self.fail('explicit mesh job timed out')
                    time.sleep(.025)
                self.assertEqual(manager.status(identifier,verify=True)['status'],'complete')
            finally:manager.close()
            reopened=JobManager(root/'jobs')
            try:self.assertEqual(reopened.status(identifier,verify=True)['status'],'complete')
            finally:reopened.close()
            a=read_solution(root/'cli/solution');b=read_solution(root/'jobs'/identifier/'solution')
            np.testing.assert_array_equal(a.frequencies_hz,b.frequencies_hz)
            self.assertAlmostEqual(a.case.length,.2)
