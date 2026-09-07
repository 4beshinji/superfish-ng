# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import unittest
import numpy as np
from superfish_ng import Case,solve
from superfish_ng.conics import LineSegment
from superfish_ng.curved_contour import CurvedContour
from superfish_ng.mesh_controls import ContourMeshControls
from superfish_ng.curved_solution import solve_curved
from superfish_ng.constants import MU0,EPS0,TAU


class CurvedSolutionTests(unittest.TestCase):
    def case(self,tag='pec'):
        vertices=((0.,0.),(.1,0.),(.1,.08),(0.,.08))
        return Case((),curved_contour=CurvedContour(tuple(LineSegment(vertices[i],vertices[(i+1)%4])
                    for i in range(4)),('axis','pec','pec',tag),0.),curve_chord_tolerance_m=.001,
                    contour_mesh=ContourMeshControls(.025),element_order=2,modes=2,normalization_j=2.)

    def test_affine_spectrum_constraints_and_energy(self):
        for tag in ('pec','magnetic_symmetry','electric_symmetry'):
            case=self.case(tag)
            actual,expected=solve_curved(case),solve(case)
            np.testing.assert_allclose(actual.frequencies_hz,expected.frequencies_hz,rtol=1e-10)
            np.testing.assert_allclose(actual.u,expected.u,rtol=1e-8,atol=1e-5)
            gram=MU0*np.pi*actual.u.T@(actual.mass@actual.u)
            np.testing.assert_allclose(gram,2*np.eye(2),atol=1e-12)
            if len(actual.space.constrained_dofs):
                self.assertTrue(np.all(actual.u[actual.space.constrained_dofs]==0))
            self.assertLess(actual.residuals.max(),1e-7)

    def test_physical_linear_field_chain_rule(self):
        from pathlib import Path
        case=Case.load(Path(__file__).resolve().parents[1]/'examples/curved_ellipse.json')
        solution=solve_curved(case)
        cell=int(np.argmax(solution.space.geometry.node_displacements_m[solution.space.geometry.cell_nodes].max(axis=1)))
        points=solution.space.geometry.points_rz_m
        # Manufactured physical u=1+2r+3z is reproduced by isoparametric P2.
        solution.u[:,0]=1+2*points[:,0]+3*points[:,1]
        fields=solution.fields_in_cell(cell,[[.2,.3],[.1,.1]])
        r,z=fields['points_rz_m'].T
        u=1+2*r+3*z
        omega=TAU*solution.frequencies_hz[0]
        np.testing.assert_allclose(fields['Hphi_A_per_m'],r*u)
        np.testing.assert_allclose(fields['Er_quadrature_V_per_m'],-3*r/(omega*EPS0))
        np.testing.assert_allclose(fields['Ez_quadrature_V_per_m'],(2*u+2*r)/(omega*EPS0))
        for cell,mode in ((True,0),(-1,0),(0,True),(0,2)):
            with self.assertRaises(ValueError):
                solution.fields_in_cell(cell,[[.2,.3]],mode)
        with self.assertRaisesRegex(ValueError,'element_order'):
            solve_curved(replace(self.case(),element_order=1))
