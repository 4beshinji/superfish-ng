# SPDX-License-Identifier: Apache-2.0
"""Independent polynomial moments and cavity spectra for the P2 core."""
from dataclasses import replace
from math import factorial
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng import Case, make_mesh, solve
from superfish_ng.constants import MU0
from superfish_ng.fem import assemble
from superfish_ng.mesh import Mesh


def triangle():
    return Mesh(np.array([[0.,0.],[1.,0.],[0.,1.]]),np.array([[0,1,2]]),
                np.array([[0,1],[1,2],[2,0]]),np.array(['pec','pec','axis']),
                np.array([0,0,0]),np.array([0,2]))


class QuadraticElementTests(unittest.TestCase):
    def test_basis_partition_derivatives_and_kronecker_values(self):
        from superfish_ng.high_order import basis_p2
        bary=np.array([[1.,0,0],[0,1.,0],[0,0,1.],[.5,.5,0],[0,.5,.5],[.5,0,.5]])
        grad=np.array([[-1.,-1.],[1.,0.],[0.,1.]])
        np.testing.assert_array_equal(np.array([basis_p2(n,grad)[0] for n in bary]),np.eye(6))
        for n in [np.array([.2,.3,.5]),np.array([1/3]*3)]:
            values,derivatives=basis_p2(n,grad)
            self.assertAlmostEqual(values.sum(),1)
            np.testing.assert_allclose(derivatives.sum(axis=0),0,atol=1e-15)

    def test_all_quadratic_polynomial_pair_integrals(self):
        from superfish_ng.high_order import quadratic_space, assemble_p2
        space=quadratic_space(triangle()); k,m=assemble_p2(space)
        r,z=space.dof_points.T
        powers=[(a,b) for a in range(3) for b in range(3-a)]
        moment=lambda a,b: factorial(a)*factorial(b)/factorial(a+b+2)
        for a,b in powers:
            for c,d in powers:
                u,v=r**a*z**b,r**c*z**d
                mass=moment(a+c+3,b+d)
                stiffness=(a+2)*(c+2)*moment(a+c+1,b+d)
                if b*d:stiffness+=b*d*moment(a+c+3,b+d-2)
                with self.subTest(powers=(a,b,c,d)):
                    self.assertAlmostEqual(float(u@(m@v)),mass,places=13)
                    self.assertAlmostEqual(float(u@(k@v)),stiffness,places=13)
        for matrix in [k,m]:
            np.testing.assert_allclose(matrix.toarray(),matrix.toarray().T,atol=1e-15)
            self.assertGreater(np.linalg.eigvalsh(matrix.toarray()).min(),0)

    def test_shared_edges_p1_embedding_and_geometric_scaling(self):
        from superfish_ng.high_order import quadratic_space, assemble_p2
        mesh=make_mesh(Case(((0.,.1),(.2,.1)),nr=3,nz=4,modes=1))
        space=quadratic_space(mesh); k,m=assemble_p2(space)
        embedding=np.zeros((len(space.dof_points),len(mesh.points)))
        embedding[:len(mesh.points)]=np.eye(len(mesh.points))
        edges={}
        for tri,dofs in zip(mesh.triangles,space.cell_dofs):
            for j,(a,b) in enumerate([(0,1),(1,2),(2,0)]):
                key=tuple(sorted([tri[a],tri[b]]))
                self.assertEqual(edges.setdefault(key,dofs[j+3]),dofs[j+3])
                embedding[dofs[j+3],tri[a]]=embedding[dofs[j+3],tri[b]]=.5
        self.assertEqual(len(space.dof_points),len(mesh.points)+len(edges))
        for high,low in zip((k,m),assemble(mesh)):
            np.testing.assert_allclose(embedding.T@high@embedding,low.toarray(),rtol=2e-13,atol=1e-17)
        scaled=replace(mesh,points=mesh.points*3)
        ks,ms=assemble_p2(quadratic_space(scaled))
        np.testing.assert_allclose(ks.toarray(),k.toarray()*3**3,rtol=2e-13,atol=1e-15)
        np.testing.assert_allclose(ms.toarray(),m.toarray()*3**5,rtol=2e-13,atol=1e-17)

    def test_cylinder_spectral_convergence_and_energy_normalization(self):
        from superfish_ng.high_order import solve_p2
        from superfish_ng.analytic import pillbox_spectrum
        exact=np.array([row[0] for row in pillbox_spectrum(.1,.2,3)])
        errors=[]
        for n in [4,8,16]:
            case=Case(((0.,.1),(.2,.1)),nr=n,nz=2*n,modes=3,normalization_j=2.)
            sol=solve_p2(case)
            self.assertEqual(sol.element_order,2)
            self.assertEqual(sol.u.shape,(len(sol.space.dof_points),3))
            np.testing.assert_allclose(MU0*np.pi*(sol.u.T@(sol.mass@sol.u)),2*np.eye(3),atol=1e-10)
            self.assertLess(max(sol.residuals),1e-7)
            errors.append(abs(sol.frequencies_hz/exact-1))
        self.assertTrue(np.all(errors[-1]<1e-5),errors)
        self.assertTrue(np.all(errors[-1]/errors[-2]<.2),errors)
        self.assertTrue(np.all(errors[-1]<abs(solve(case).frequencies_hz/exact-1)))

    def test_symmetry_midpoints_are_constrained_but_axis_is_free(self):
        from superfish_ng.high_order import solve_p2
        from superfish_ng.analytic import tm0np_frequency
        case=Case(((0.,.1),(.1,.1)),nr=10,nz=10,modes=1,z_min='magnetic_symmetry')
        sol=solve_p2(case)
        constrained=sol.space.boundary_dofs[sol.mesh.boundary_tags=='magnetic_symmetry']
        np.testing.assert_array_equal(sol.u[np.unique(constrained)],0.)
        axis=sol.space.axis_dofs
        self.assertTrue(np.any(abs(sol.u[axis])>1))
        self.assertLess(abs(sol.frequencies_hz[0]/tm0np_frequency(.1,.2,p=1)-1),1e-5)

    def test_frequency_scaling_and_mesh_numbering_invariance(self):
        from superfish_ng.high_order import solve_p2
        from superfish_ng.mesh_input import mesh_to_dict
        case=Case(((0.,.1),(.2,.1)),nr=5,nz=8,modes=3)
        mesh=make_mesh(case)
        original=solve_p2(case)
        order=np.random.default_rng(723).permutation(len(mesh.points))
        inverse=np.argsort(order)
        data=mesh_to_dict(mesh)
        data['points']=mesh.points[order].tolist()
        data['triangles']=inverse[mesh.triangles[::-1]].tolist()
        data['boundary_edges']=inverse[mesh.boundary_edges[::-1]].tolist()
        data['boundary_tags']=mesh.boundary_tags[::-1].tolist()
        permuted=solve_p2(case,mesh_data=data)
        scaled=solve_p2(replace(case,profile=((0.,.3),(.6,.3))))
        np.testing.assert_allclose(permuted.frequencies_hz,original.frequencies_hz,rtol=1e-11)
        np.testing.assert_allclose(scaled.frequencies_hz*3,original.frequencies_hz,rtol=1e-11)

    def test_implicit_sampler_refuse_quadratic_solution(self):
        from superfish_ng.high_order import solve_p2
        from superfish_ng.io import save_run
        from superfish_ng.sampling import FieldSampler
        case=Case(((0.,.1),(.2,.1)),nr=4,nz=4,modes=1)
        sol=solve_p2(case)
        for call in [lambda:FieldSampler(sol.mesh.points,sol.mesh.triangles,sol.u,sol.frequencies_hz)]:
            with self.assertRaisesRegex(ValueError,'P1|N02|quadratic|exactly one'):call()
