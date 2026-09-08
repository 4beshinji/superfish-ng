# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import unittest
import numpy as np
from superfish_ng import Case
from superfish_ng.mesh import make_mesh
from superfish_ng.curved_space import curved_space
from superfish_ng.curved_refinement import refine_curved_space
from superfish_ng.curved_marked_refinement import refine_marked_curved_space
from superfish_ng.curved_fem import assemble_curved

class CurvedMarkedRefinementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case=replace(Case.load('examples/curved_ellipse.json'),geometry_order=2)
        cls.parent=curved_space(cls.case,make_mesh(cls.case))
        edge=cls.parent.geometry.boundary_nodes[cls.parent.boundary_tags=='pec'][0,:2]
        cls.marked=next(i for i,nodes in enumerate(cls.parent.geometry.cell_nodes) if all(v in nodes[:3] for v in edge))
        cls.refined=refine_marked_curved_space(cls.parent,[cls.marked])

    def test_local_maps_fields_gradients_and_reference_coverage(self):
        g=self.parent.geometry;r=self.refined;fine=r.space.geometry
        counts=np.bincount(r.parent_cells,minlength=len(g.cell_nodes))
        self.assertEqual(counts[self.marked],4);self.assertIn(1,counts);self.assertLess(len(fine.cell_nodes),4*len(g.cell_nodes))
        u=np.random.default_rng(20260908).normal(size=len(g.points_rz_m));v=r.prolongation@u
        q=np.array([[.2,.3],[.1,.1],[0.,0.]])
        fractions=np.zeros(len(g.cell_nodes))
        for i,mapping in enumerate(fine.local_maps):
            vertices=r.parent_reference_vertices[i];transform=vertices[1:]-vertices[0];owner=r.parent_cells[i]
            fractions[owner]+=np.linalg.det(transform)
            a=g.local_maps[owner].evaluate(vertices[0]+q@transform);b=mapping.evaluate(q)
            np.testing.assert_allclose(a['points_rz_m'],b['points_rz_m'],atol=1e-16,rtol=1e-13)
            uc=u[g.cell_nodes[owner]];uf=v[fine.cell_nodes[i]]
            np.testing.assert_allclose(a['basis_values']@uc,b['basis_values']@uf,atol=1e-13)
            np.testing.assert_allclose(np.einsum('qia,i->qa',a['basis_gradients'],uc),np.einsum('qia,i->qa',b['basis_gradients'],uf),atol=1e-9,rtol=1e-10)
        np.testing.assert_array_equal(fractions,np.ones(len(fractions)))
        self.assertEqual(r.space.edge_check['status'],'PASS');self.assertFalse(fine.points_rz_m.flags.writeable)

    def test_galerkin_mass_and_energy_are_preserved(self):
        coarse=assemble_curved(self.parent,quadrature_order=12);fine=assemble_curved(self.refined.space,quadrature_order=12)
        p=self.refined.prolongation
        for a,b in zip(coarse,fine):self.assertLess(np.linalg.norm((p.T@b@p-a).data)/np.linalg.norm(a.data),1e-10)

    def test_all_selected_matches_existing_uniform_reconstruction(self):
        a=refine_curved_space(self.parent);b=refine_marked_curved_space(self.parent,list(range(len(self.parent.geometry.cell_nodes))))
        for key in ('points_rz_m','cell_nodes','boundary_nodes','boundary_curve_indices','boundary_parameters'):
            np.testing.assert_array_equal(getattr(a.space.geometry,key),getattr(b.space.geometry,key))
        np.testing.assert_array_equal(a.parent_cells,b.parent_cells)
        np.testing.assert_array_equal(a.parent_reference_vertices,b.parent_reference_vertices)
        self.assertEqual((a.prolongation-b.prolongation).nnz,0)

    def test_boundary_is_restricted_not_reprojected_and_constraints_survive(self):
        g=self.parent.geometry;child=self.refined.space.geometry;split={tuple(edge) for edge in self.refined.split_edges};offset=0;differences=[]
        for edge,tag,owner,interval in zip(g.boundary_nodes,self.parent.boundary_tags,g.boundary_curve_indices,g.boundary_parameters):
            a,b,mid=edge;lo,hi=interval;count=2 if tuple(sorted((a,b))) in split else 1
            np.testing.assert_array_equal(self.refined.space.boundary_tags[offset:offset+count],[tag]*count)
            np.testing.assert_array_equal(child.boundary_curve_indices[offset:offset+count],[owner]*count)
            if count==2:
                point=np.array([.375,-.125,.75])@g.points_rz_m[edge]
                np.testing.assert_allclose(child.points_rz_m[child.boundary_nodes[offset,2]],point,atol=1e-16)
                analytic=self.case.curved_contour.curves[int(owner)].evaluate(float((3*lo+hi)/4))['points_zr_m'][::-1]
                if tag=='pec':differences.append(np.linalg.norm(point-analytic))
                np.testing.assert_array_equal(child.boundary_parameters[offset:offset+2],[[lo,(lo+hi)/2],[(lo+hi)/2,hi]])
            else:np.testing.assert_array_equal(child.boundary_nodes[offset],edge)
            offset+=count
        self.assertGreater(max(differences),1e-12)
        from superfish_ng.conics import LineSegment
        from superfish_ng.curved_contour import CurvedContour
        from superfish_ng.mesh_controls import ContourMeshControls
        vertices=((0.,0.),(.1,0.),(.1,.08),(0.,.08))
        case=Case((),curved_contour=CurvedContour(tuple(LineSegment(vertices[i],vertices[(i+1)%4]) for i in range(4)),('axis','pec','pec','magnetic_symmetry'),0.),curve_chord_tolerance_m=.001,contour_mesh=ContourMeshControls(.05),element_order=2,modes=1)
        space=curved_space(case,make_mesh(case));u=np.ones(len(space.geometry.points_rz_m));u[space.constrained_dofs]=0
        for _ in range(2):
            refined=refine_marked_curved_space(space,[0]);u=refined.prolongation@u;space=refined.space
            self.assertTrue(np.all(u[space.constrained_dofs]==0));self.assertTrue(np.all(space.geometry.points_rz_m[space.axis_dofs,0]==0))

    def test_strict_selection_budget_quality_and_parent_metadata(self):
        before=self.parent.geometry.points_rz_m.copy()
        for selection in ([],[True],[-1],[0,0],[len(self.parent.geometry.cell_nodes)],(0,)):
            with self.assertRaises(ValueError):refine_marked_curved_space(self.parent,selection)
        for options in (dict(max_triangles=True),dict(max_triangles=len(self.parent.geometry.cell_nodes)),dict(minimum_corner_angle_deg=59),dict(minimum_corner_angle_deg=0)):
            with self.assertRaises(ValueError):refine_marked_curved_space(self.parent,[self.marked],**options)
        with self.assertRaises(ValueError):refine_marked_curved_space(None,[0])
        with self.assertRaisesRegex(ValueError,'constraints'):
            refine_marked_curved_space(replace(self.parent,axis_dofs=np.array([],dtype=int)),[0])
        bad_geometry=replace(self.parent.geometry,boundary_curve_indices=self.parent.geometry.boundary_curve_indices.astype(float))
        with self.assertRaisesRegex(ValueError,'ancestry'):refine_marked_curved_space(replace(self.parent,geometry=bad_geometry),[0])
        np.testing.assert_array_equal(before,self.parent.geometry.points_rz_m)
