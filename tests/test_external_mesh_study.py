# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
import json,math,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from superfish_ng import Case,solve
from superfish_ng.project import Project
from superfish_ng.project_mesh_operations import replace_project_mesh
from superfish_ng.studies import Study,execute_study
from superfish_ng.mesh import element_geometry,make_mesh
from superfish_ng.mesh_input import mesh_from_dict,mesh_to_dict
from test_project_mesh import explicit_project
from test_curve_partitions import partition_case
from superfish_ng.curved_refinement_steps import CurvedRefinementStep


class ExternalMeshStudyTests(unittest.TestCase):
    def test_uniform_subdivisions_preserve_polygon_volume_and_ritz_for_p1_p2(self):
        for order in (1,2):
            p=explicit_project(Case(((0.,.1),(.2,.1)),nr=3,nz=4,modes=1,element_order=order))
            before=p.to_dict();study=Study(p,'fixed_geometry_convergence','additional_uniform_refinements',[0,1,2])
            with patch('superfish_ng.mesh.make_mesh',side_effect=AssertionError('explicit mesh must not be regenerated')):
                projects=study.projects()
            self.assertEqual(projects[0].to_dict(),before);self.assertEqual(p.to_dict(),before)
            frequencies=[]
            for level,q in enumerate(projects):
                mesh=mesh_from_dict(q.case,q.mesh_data);self.assertEqual(len(mesh.triangles),24*4**level)
                area=element_geometry(mesh)[1]/2
                self.assertLess(abs(float(np.sum(area))/.02-1),1e-12)
                volume=2*math.pi*np.sum(area*mesh.points[mesh.triangles,0].mean(axis=1))
                self.assertLess(abs(volume/(math.pi*.1**2*.2)-1),1e-12)
                np.testing.assert_array_equal(mesh.points[:len(p.mesh_data['points'])],p.mesh_data['points'])
                frequencies.append(solve(q.case,mesh_data=q.mesh_data).frequencies_hz[0])
            self.assertTrue(all(b<a for a,b in zip(frequencies,frequencies[1:])))

    def test_replacement_strict_atomic_and_can_detach_after_geometry_edit(self):
        p=explicit_project(Case(((0.,.1),(.2,.1)),nr=3,nz=4,modes=1));before=p.to_dict()
        mesh=json.dumps(p.mesh_data);attached=replace_project_mesh(Project(p.case),mesh)
        self.assertEqual(attached.to_dict(),before)
        for value in ('null','[]','{"schema_version":1,"schema_version":1}',{},dict(p.mesh_data,unsupported=True)):
            with self.subTest(value=str(value)[:30]),self.assertRaises(ValueError):replace_project_mesh(p,value)
            self.assertEqual(p.to_dict(),before)
        changed=deepcopy(before);changed['case']['geometry']['points_zr_m'][1][0]=.3
        detached=replace_project_mesh(changed,None)
        self.assertIsNone(detached.mesh_data);self.assertEqual(detached.case.length,.3)
        self.assertEqual(detached.to_dict()['project_version'],1)

    def test_marked_history_replacement_and_refinement_budget(self):
        p=explicit_project(replace(partition_case(),curved_refinement_steps=(CurvedRefinementStep('marked',(0,),1.),)))
        self.assertEqual(replace_project_mesh(p,p.mesh_data).to_dict(),p.to_dict())
        automatic=mesh_to_dict(make_mesh(p.case))
        with self.assertRaisesRegex(ValueError,'marked-cell history'):replace_project_mesh(p,automatic)
        with self.assertRaisesRegex(ValueError,'marked-cell history'):replace_project_mesh(p,None)
        straight=explicit_project(Case(((0.,.1),(.2,.1)),nr=3,nz=4,modes=1))
        with self.assertRaisesRegex(ValueError,'max_triangles'):
            Study(straight,'fixed_geometry_convergence','additional_uniform_refinements',[0,100000]).projects()
        for values in ([1,0],[0,1.],[0,True],[-1,0]):
            with self.assertRaises(ValueError):Study(straight,'fixed_geometry_convergence','additional_uniform_refinements',values)

    def test_native_study_report_uses_imported_mesh(self):
        p=explicit_project(Case(((0.,.1),(.2,.1)),nr=3,nz=4,modes=1,element_order=2))
        study=Study(p,'fixed_geometry_convergence','additional_uniform_refinements',[0,1])
        with tempfile.TemporaryDirectory() as tmp:
            report=execute_study(study,Path(tmp)/'study')
            self.assertIn('same polygonal domain',report['geometry_refinement'])
            self.assertEqual(Study.from_dict(study.to_dict()).to_dict(),study.to_dict())
