# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng import Case, solve
from superfish_ng.high_order import solve_p2
from superfish_ng.display import display_fields
from superfish_ng.constants import EPS0, TAU
from superfish_ng.io import write_vtk


class DisplayTests(unittest.TestCase):
    def test_p2_tessellation_area_polynomial_samples_and_vtk(self):
        case=Case(((0.,.1),(.2,.1)),nr=3,nz=4,modes=1)
        solution=solve_p2(case)
        r,z=solution.space.dof_points.T
        solution.u[:,0]=1+2*r+3*z+4*r*r+5*r*z+6*z*z
        points,triangles,h,(er,ez,hc)=display_fields(solution)
        self.assertEqual(len(triangles),4*len(solution.mesh.triangles))
        vertices=points[triangles]
        delta1,delta2=vertices[:,1]-vertices[:,0],vertices[:,2]-vertices[:,0]
        det=delta1[:,0]*delta2[:,1]-delta1[:,1]*delta2[:,0]
        self.assertTrue(np.all(det>0))
        self.assertAlmostEqual(det.sum()/2,.02,places=14)
        r,z=vertices.mean(axis=1).T
        u=1+2*r+3*z+4*r*r+5*r*z+6*z*z
        omega=TAU*solution.frequencies_hz[0]
        np.testing.assert_allclose(er,-r*(3+5*r+12*z)/(omega*EPS0),atol=1e-12)
        np.testing.assert_allclose(ez,(2*u+r*(2+8*r+5*z))/(omega*EPS0),atol=1e-12)
        np.testing.assert_allclose(hc,r*u,atol=1e-14)
        np.testing.assert_array_equal(h,points[:,0]*solution.u[:,0])
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'p2.vtk'
            write_vtk(path,solution,0)
            text=path.read_text()
            self.assertIn(f'POINTS {len(points)} double',text)
            self.assertIn(f'CELLS {len(triangles)} {4*len(triangles)}',text)
            self.assertIn(f'CELL_DATA {len(triangles)}',text)
            saved_er=text.split('SCALARS Er_quadrature_V_per_m double 1\nLOOKUP_TABLE default\n')[1].split('SCALARS')[0]
            np.testing.assert_array_equal(np.fromstring(saved_er,sep=' '),er)

    def test_p1_display_preserves_original_mesh_and_fields(self):
        from superfish_ng.rf import cell_fields
        solution=solve(Case(((0.,.1),(.2,.1)),nr=3,nz=4,modes=1))
        points,triangles,h,fields=display_fields(solution)
        np.testing.assert_array_equal(points,solution.mesh.points)
        np.testing.assert_array_equal(triangles,solution.mesh.triangles)
        for actual,expected in zip(fields,cell_fields(solution,0)):
            np.testing.assert_array_equal(actual,expected)
