# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
import numpy as np
from scipy.integrate import quad
from superfish_ng import Case,solve
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution
from superfish_ng.mesh_input import mesh_to_dict
from superfish_ng.curved_solution import CurvedSolution
from superfish_ng.quadratic_geometry import QuadraticTriangle
from superfish_ng.paired_mesh_tracking import track_paired_mesh_modes,_geometry
from superfish_ng.saved_mode_tracking import save_mode_tracking,read_mode_tracking
from superfish_ng.mode_tracking_history import start_mode_history,extend_mode_history

CONTROLS=dict(minimum_overlap=.98,minimum_assignment_margin=.05,relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)

class PairedMeasureTests(unittest.TestCase):
    def triangle(self,curvature=0.):
        bary=np.array([[1,0,0],[0,1,0],[0,0,1],[.5,.5,0],[0,.5,.5],[.5,0,.5]])
        x,y=bary[:,1],bary[:,2];points=np.column_stack((x,y*(1+curvature*x)))
        solution=object.__new__(CurvedSolution)
        geometry=SimpleNamespace(points_rz_m=points,cell_nodes=np.array([[0,1,2,3,4,5]]),boundary_nodes=np.array([[0,1,3],[1,2,4],[2,0,5]]),local_maps=(QuadraticTriangle(points),))
        solution.space=SimpleNamespace(geometry=geometry,boundary_tags=np.array(['pec','pec','axis']))
        solution.u=np.ones((6,1));solution.frequencies_hz=np.array([1.])
        return solution

    def test_curved_variable_jacobian_against_independent_integral(self):
        a,b=self.triangle(),self.triangle(.5)
        result=track_paired_mesh_modes(a,b,['A'],mapping='paired_mesh',sample_order=10,vertex_pairs=[[0,0],[1,1],[2,2]],**CONTROLS)
        cross=quad(lambda x:x**3*(1-x)*np.sqrt(1+.5*x),0,1,epsabs=1e-14)[0]
        expected=cross/np.sqrt((1/20)*(1/20+.5/30))
        self.assertAlmostEqual(result['matches'][0]['minimum_principal_overlap'],expected,places=13)
        self.assertLess(expected,1-1e-5)

    def test_strict_bijection_boundary_and_budget(self):
        a=self.triangle()
        for pairs in [[],[[0,0],[1,1],[2,1]],[[False,0],[1,1],[2,2]],[[0,1],[1,0],[2,2]]]:
            with self.assertRaises(ValueError):track_paired_mesh_modes(a,a,['A'],mapping='paired_mesh',sample_order=3,vertex_pairs=pairs,**CONTROLS)
        b=self.triangle();b.space.boundary_tags[0]='magnetic_symmetry'
        with self.assertRaisesRegex(ValueError,'boundaries'):track_paired_mesh_modes(a,b,['A'],mapping='paired_mesh',sample_order=3,vertex_pairs=[[i,i] for i in range(3)],**CONTROLS)
        with self.assertRaisesRegex(ValueError,'sample_order'):track_paired_mesh_modes(a,a,['A'],mapping='paired_mesh',sample_order=True,vertex_pairs=[[i,i] for i in range(3)],**CONTROLS)

        from superfish_ng.mesh import make_mesh
        mesh=make_mesh(Case(((0.,.1),(.1,.1)),nr=16,nz=16,modes=1))
        big=SimpleNamespace(mesh=mesh)
        identity=[[i,i] for i in range(len(mesh.points))]
        with self.assertRaisesRegex(ValueError,'262144'):
            track_paired_mesh_modes(big,big,['A'],mapping='paired_mesh',sample_order=32,vertex_pairs=identity,**CONTROLS)
        changed=deepcopy(identity);changed[18][1],changed[19][1]=changed[19][1],changed[18][1]
        with self.assertRaisesRegex(ValueError,'connectivity'):
            track_paired_mesh_modes(big,big,['A'],mapping='paired_mesh',sample_order=2,vertex_pairs=changed,**CONTROLS)

class PairedMeshFEMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup);cls.root=Path(cls.tmp.name);cls.saved={};cls.pairs={}
        for kind in ('folded','ellipse'):
            data=Case.load(Path('examples')/('contour_folded.json' if kind=='folded' else 'curved_ellipse.json')).to_dict()
            data['mesh']['contour_mesh']['max_edge_m']=.025 if kind=='folded' else .08
            data['mesh']['contour_mesh']['min_angle_deg']=5.
            if kind=='ellipse':data['mesh']['geometry_order']=2;data['geometry']['chord_tolerance_m']=.008
            case=Case.from_dict(data);solution=solve(case)
            mesh=deepcopy(solution.source_mesh_data) if isinstance(solution,CurvedSolution) else mesh_to_dict(solution.mesh)
            scaled=deepcopy(data)
            if kind=='folded':scaled['geometry']['vertices_zr_m']=[[2*z,2*r] for z,r in data['geometry']['vertices_zr_m']]
            else:
                for curve in scaled['geometry']['curves']:
                    for key in ('start_zr_m','end_zr_m','center_zr_m','semiaxes_m'):
                        if key in curve:curve[key]=[2*x for x in curve[key]]
                scaled['geometry']['chord_tolerance_m']*=2
                scaled['geometry']['join_tolerance_m']*=2
            scaled_case=Case.from_dict(scaled)
            # Deliberately reverse vertex numbering and cell order, and rotate local corners.
            count=len(mesh['points']);perm=np.arange(count-1,-1,-1)
            mesh['points']=(2*np.array(mesh['points'])[perm]).tolist()
            mesh['triangles']=perm[np.array(mesh['triangles'])[::-1]][:,[1,2,0]].tolist()
            mesh['boundary_edges']=perm[np.array(mesh['boundary_edges'])].tolist()
            new=solve(scaled_case,mesh_data=mesh)
            for name,c,s in [('a',case,solution),('b',scaled_case,new)]:save_run(c,s,cls.root/f'{kind}-{name}')
            cls.saved[kind]=[read_solution(cls.root/f'{kind}-{name}') for name in ('a','b')]
            cls.pairs[kind]=[[i,int(perm[i])] for i in sorted(set(map(int,_geometry(cls.saved[kind][0])[1].ravel()))) ]

    def test_folded_similarity_survives_vertex_cell_and_corner_permutation(self):
        a,b=self.saved['folded'];np.testing.assert_allclose(a.frequencies_hz,2*b.frequencies_hz,rtol=1e-10)
        for q in (3,5):
            report=track_paired_mesh_modes(a,b,['A'],mapping='paired_mesh',sample_order=q,vertex_pairs=self.pairs['folded'],**CONTROLS)
            self.assertEqual(report['status'],'PASS');self.assertGreater(report['matches'][0]['minimum_principal_overlap'],1-1e-12)

    def test_native_curved_similarity_uses_actual_quadratic_cells(self):
        a,b=self.saved['ellipse'];self.assertIsInstance(a,CurvedSolution)
        np.testing.assert_allclose(a.frequencies_hz,2*b.frequencies_hz,rtol=1e-10)
        for q in (3,5):
            report=track_paired_mesh_modes(a,b,['A'],mapping='paired_mesh',sample_order=q,vertex_pairs=self.pairs['ellipse'],**CONTROLS)
            self.assertEqual(report['status'],'PASS');self.assertGreater(report['matches'][0]['minimum_principal_overlap'],1-1e-12)

    def test_saved_correspondence_and_history_require_explicit_pairing(self):
        controls=dict(CONTROLS,mapping='paired_mesh',sample_order=3,vertex_pairs=self.pairs['folded'])
        request=dict(schema_version=1,previous_run='folded-a',current_run='folded-b',previous_ids=['A'],controls=controls)
        pair=save_mode_tracking(request,self.root/'pair.json',base_directory=self.root)
        self.assertEqual(read_mode_tracking(self.root/'pair.json'),pair)
        back=dict(controls,vertex_pairs=[[b,a] for a,b in self.pairs['folded']])
        history=extend_mode_history(start_mode_history(pair),dict(current_run='folded-a',controls=back),base_directory=self.root)
        self.assertEqual(history['status'],'PASS')
        broken=deepcopy(request);del broken['controls']['vertex_pairs']
        with self.assertRaises(ValueError):save_mode_tracking(broken,self.root/'missing.json',base_directory=self.root)
