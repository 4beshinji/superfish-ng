# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
import numpy as np
from scipy.integrate import dblquad
from superfish_ng import Case,solve
from superfish_ng.mesh import make_mesh
from superfish_ng.mesh_input import mesh_to_dict
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution
from superfish_ng.piecewise_remesh_tracking import track_piecewise_remesh_modes
from superfish_ng.saved_mode_tracking import save_mode_tracking,read_mode_tracking,validate_tracking_controls
from superfish_ng.mode_tracking_history import start_mode_history,extend_mode_history

class PiecewiseRemeshTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.cases=[Case(((0.,1.),(.5,1.),(1.,1.)),nr=5,nz=6,modes=1,element_order=2),
                    Case(((0.,1.),(.35,.8),(1.,1.)),nr=7,nz=9,modes=1,element_order=2)]
        self.maps=[mesh_to_dict(make_mesh(replace(self.cases[0],nr=2,nz=2)))]
        current=deepcopy(self.maps[0])
        for p in current['points']:
            if p[1]==.5:p[0]*=.8;p[1]=.35
        self.maps.append(current);self.solutions=[]
        for i,c in enumerate(self.cases):save_run(c,solve(c),self.root/str(i));self.solutions.append(read_solution(self.root/str(i)))
        self.controls=dict(mapping='piecewise_remesh',comparison_meshes=self.maps,sample_order=10,minimum_overlap=.8,
            minimum_assignment_margin=.05,relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)

    def test_variable_physical_weight_against_independent_integrals(self):
        for s in self.solutions:s.u[:]=1.
        result=track_piecewise_remesh_modes(*self.solutions,['polynomial'],**self.controls)
        cross=old=new=0.
        for triangle in self.maps[0]['triangles']:
            vertices=[np.array(m['points'])[triangle] for m in self.maps]
            det=[np.linalg.det(np.column_stack((v[1]-v[0],v[2]-v[0]))) for v in vertices]
            def radius(k,x,y):return (vertices[k][0]*(1-x-y)+vertices[k][1]*x+vertices[k][2]*y)[0]
            def integrate(fn):return dblquad(lambda y,x:fn(x,y),0.,1.,lambda x:0.,lambda x:1-x,epsabs=1e-11,epsrel=1e-11)[0]
            cross+=integrate(lambda x,y:(radius(0,x,y)*radius(1,x,y))**1.5*np.sqrt(det[0]*det[1]))
            old+=integrate(lambda x,y:radius(0,x,y)**3*det[0]);new+=integrate(lambda x,y:radius(1,x,y)**3*det[1])
        expected=cross/np.sqrt(old*new)
        self.assertLess(expected,.999)
        self.assertAlmostEqual(result['matches'][0]['minimum_principal_overlap'],expected,places=8)

    def test_saved_native_nonaffine_history_and_reverse(self):
        request=dict(schema_version=1,previous_run='0',current_run='1',previous_ids=['A'],controls=self.controls)
        pair=save_mode_tracking(request,self.root/'pair.json',base_directory=self.root)
        self.assertEqual(read_mode_tracking(self.root/'pair.json'),pair)
        self.assertEqual(pair['status'],'PASS')
        history=extend_mode_history(start_mode_history(pair),dict(current_run='0',controls=dict(self.controls,comparison_meshes=self.maps[::-1])),base_directory=self.root)
        self.assertEqual(history['status'],'PASS');self.assertEqual(history['current_mode_ids'],['A'])
        self.assertAlmostEqual(pair['tracking']['matches'][0]['minimum_principal_overlap'],history['steps'][1]['tracking']['matches'][0]['minimum_principal_overlap'],places=14)

    def test_folded_or_missing_comparison_cells_and_wrong_boundary_rejected(self):
        for kind in ('flip','missing','boundary','fold'):
            bad=deepcopy(self.maps)
            if kind=='flip':bad[1]['triangles'][0]=bad[1]['triangles'][0][::-1]
            elif kind=='missing':
                for mesh in bad:mesh['triangles'].pop()
            elif kind=='fold':bad[1]['points'][4][1]=2.
            else:bad[1]['points'][2][0]+=.1
            with self.subTest(kind=kind),self.assertRaises(ValueError):
                track_piecewise_remesh_modes(*self.solutions,['A'],**dict(self.controls,comparison_meshes=bad))

    def test_solver_connectivity_is_independent_of_comparison_mesh(self):
        result=track_piecewise_remesh_modes(*self.solutions,['A'],**self.controls)
        m=result['physical_mapping'];self.assertEqual(m['comparison_triangle_count'],8)
        self.assertTrue(all(n>8 for n in m['solver_triangle_counts']));self.assertNotEqual(*m['solver_triangle_counts'])

    def test_strict_nested_schema_controls_and_quadrature_order(self):
        validate_tracking_controls(self.controls)
        for bad in ([],[self.maps[0]],deepcopy(self.maps)):
            if len(bad)==2:bad[0]['unknown']=True
            with self.assertRaises(ValueError):validate_tracking_controls(dict(self.controls,comparison_meshes=bad))
        with self.assertRaises(ValueError):validate_tracking_controls(dict(self.controls,affine_map={}))
        with self.assertRaises(ValueError):track_piecewise_remesh_modes(*self.solutions,['A'],**dict(self.controls,sample_order=33))
