# SPDX-License-Identifier: Apache-2.0
"""Local mesh subdivision must preserve the physical FEM space and boundary."""
from dataclasses import replace
import unittest
import numpy as np
from superfish_ng import Case,solve
from superfish_ng.mesh import make_mesh,element_geometry
from superfish_ng.mesh_input import mesh_to_dict,mesh_from_dict
from superfish_ng.fem import assemble
from superfish_ng.high_order import quadratic_space,assemble_p2,basis_p2
from superfish_ng.marked_refinement import refine_marked_cells


class MarkedRefinementTests(unittest.TestCase):
    def test_locality_boundary_volume_and_input_preservation(self):
        case=Case(((0.,.1),(.2,.1)),nr=6,nz=8,modes=1)
        mesh=make_mesh(case);before=mesh_to_dict(mesh)
        result=refine_marked_cells(case,mesh,[40])
        self.assertEqual(mesh_to_dict(mesh),before)
        mesh_from_dict(case,mesh_to_dict(result.mesh))
        self.assertGreater(len(result.mesh.triangles),len(mesh.triangles))
        self.assertLess(len(result.mesh.triangles),4*len(mesh.triangles))
        self.assertTrue(np.any(np.bincount(result.parent_cells)==1))
        self.assertEqual(np.bincount(result.parent_cells)[40],4)
        p,det,_=element_geometry(result.mesh)
        self.assertAlmostEqual(float(np.sum(det/2)),.1*.2,places=14)
        self.assertAlmostEqual(float(np.pi*np.sum(det*p[:,:,0].mean(axis=1))),np.pi*.1**2*.2,places=14)
        self.assertEqual(set(result.mesh.boundary_tags),{'axis','pec'})

    def test_p1_p2_field_gradient_and_galerkin_energy_identity(self):
        for order in (1,2):
            case=Case(((0.,.1),(.2,.08)),nr=4,nz=5,modes=1,element_order=order)
            mesh=make_mesh(case);result=refine_marked_cells(case,mesh,[4,13])
            a=quadratic_space(mesh) if order==2 else None;b=quadratic_space(result.mesh) if order==2 else None
            old_nodes=a.cell_dofs if a else mesh.triangles;new_nodes=b.cell_dofs if b else result.mesh.triangles
            u=np.random.default_rng(404).normal(size=result.prolongation.shape[1]);v=result.prolongation@u
            _,_,old_grad=element_geometry(mesh);_,_,new_grad=element_geometry(result.mesh)
            for cell,parent in enumerate(result.parent_cells):
                n=np.array([.2,.3,.5]);mapped=n@result.parent_barycentric_vertices[cell]
                if order==2:
                    na,ga=basis_p2(mapped,old_grad[parent]);nb,gb=basis_p2(n,new_grad[cell])
                else:na,ga=mapped,old_grad[parent];nb,gb=n,new_grad[cell]
                np.testing.assert_allclose(na@u[old_nodes[parent]],nb@v[new_nodes[cell]],rtol=1e-12,atol=1e-13)
                np.testing.assert_allclose(ga.T@u[old_nodes[parent]],gb.T@v[new_nodes[cell]],rtol=1e-12,atol=1e-11)
            old_matrices=assemble_p2(a) if a else assemble(mesh);new_matrices=assemble_p2(b) if b else assemble(result.mesh)
            for old,new in zip(old_matrices,new_matrices):
                delta=result.prolongation.T@new@result.prolongation-old
                self.assertLess(np.linalg.norm(delta.data)/np.linalg.norm(old.data),1e-12)

    def test_uniform_limit_constraints_and_native_variational_monotonicity(self):
        for order in (1,2):
            case=Case(((0.,.1),(.2,.1)),nr=4,nz=5,modes=2,element_order=order,z_min='magnetic_symmetry')
            old=solve(case);result=refine_marked_cells(case,old.mesh,list(range(len(old.mesh.triangles))))
            self.assertEqual(len(result.mesh.triangles),4*len(old.mesh.triangles))
            coarse=quadratic_space(old.mesh) if order==2 else None;fine=quadratic_space(result.mesh) if order==2 else None
            old_boundary=coarse.boundary_dofs if coarse else old.mesh.boundary_edges
            new_boundary=fine.boundary_dofs if fine else result.mesh.boundary_edges
            u=np.ones(result.prolongation.shape[1]);u[np.unique(old_boundary[old.mesh.boundary_tags=='magnetic_symmetry'])]=0
            self.assertTrue(np.all((result.prolongation@u)[np.unique(new_boundary[result.mesh.boundary_tags=='magnetic_symmetry'])]==0))
            current=solve(case,mesh_data=mesh_to_dict(result.mesh))
            self.assertTrue(np.all(current.frequencies_hz<=old.frequencies_hz*(1+2e-12)))
            self.assertTrue(np.all(result.mesh.points[result.mesh.axis_nodes,0]==0))

    def test_folded_contour_tags_and_strict_limits(self):
        case=Case.load('examples/contour_folded.json');mesh=make_mesh(case)
        result=refine_marked_cells(case,mesh,[0])
        mesh_from_dict(case,mesh_to_dict(result.mesh));self.assertEqual(set(result.mesh.boundary_tags),set(mesh.boundary_tags))
        for marked in ([],[True],[-1],[len(mesh.triangles)],[0,0],[.1]):
            with self.assertRaises(ValueError):refine_marked_cells(case,mesh,marked)
        with self.assertRaisesRegex(ValueError,'max_triangles'):refine_marked_cells(case,mesh,[0],max_triangles=len(mesh.triangles))
        with self.assertRaisesRegex(ValueError,'angle'):refine_marked_cells(case,mesh,[0],minimum_angle_deg=59.)
        for angle in (True,0.,60.,float('nan')):
            with self.assertRaises(ValueError):refine_marked_cells(case,mesh,[0],minimum_angle_deg=angle)
        curved=replace(Case.load('examples/curved_ellipse.json'),geometry_order=2)
        with self.assertRaisesRegex(ValueError,'straight'):refine_marked_cells(curved,make_mesh(curved),[0])
