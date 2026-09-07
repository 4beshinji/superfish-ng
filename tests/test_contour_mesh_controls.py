# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from superfish_ng import Case,solve
from superfish_ng.contour import Contour
from superfish_ng.mesh_controls import ContourMeshControls
from superfish_ng.contour_mesh import quality_contour_mesh
from superfish_ng.mesh_input import mesh_to_dict
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution


class ContourMeshControlTests(unittest.TestCase):
    def case(self):
        return Case((),contour=Contour(((0,0),(.2,0),(.2,.1),(0,.1)),('axis','pec','pec','pec')),
                    contour_mesh=ContourMeshControls(.05,15.,3000,5),modes=1,element_order=2)

    def test_case_saved_result_and_reloaded_controls(self):
        case = self.case()
        data = case.to_dict()
        self.assertEqual(Case.from_dict(data),case)
        self.assertEqual(data['schema_version'],3)
        controls = case.contour_mesh.to_dict()
        mesh = quality_contour_mesh(case,**controls)
        sol = solve(case,mesh_data=mesh_to_dict(mesh))
        automatic = solve(case)
        import numpy as np
        np.testing.assert_array_equal(automatic.mesh.points,sol.mesh.points)
        np.testing.assert_array_equal(automatic.mesh.triangles,sol.mesh.triangles)
        np.testing.assert_array_equal(automatic.frequencies_hz,sol.frequencies_hz)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'run'
            save_run(case,sol,out)
            self.assertEqual(Case.load(out/'case.json').contour_mesh,case.contour_mesh)
            self.assertEqual(read_solution(out).case.contour_mesh,case.contour_mesh)
            repeated = solve(Case.load(out/'case.json'))
            np.testing.assert_array_equal(repeated.u,automatic.u)
        self.assertEqual(data,case.to_dict())

    def test_strict_values_geometry_and_versions(self):
        valid = self.case().to_dict()
        for key,values in {'max_edge_m':[0,True,None,float('inf')],
                           'min_angle_deg':[0,60,True,None],
                           'max_triangles':[0,1.5,True], 'max_rounds':[0,True]}.items():
            for value in values:
                data = deepcopy(valid)
                data['mesh']['contour_mesh'][key] = value
                with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                    Case.from_dict(data)
        for payload in ({},{'max_edge_m':.05,'unknown':1},None):
            data = deepcopy(valid)
            data['mesh']['contour_mesh'] = payload
            with self.assertRaises(ValueError):Case.from_dict(data)
        profile = Case(((0,.1),(.2,.1))).to_dict()
        profile['mesh']['contour_mesh'] = {'max_edge_m':.05}
        with self.assertRaisesRegex(ValueError,'schema_version 3'):Case.from_dict(profile)
        with self.assertRaisesRegex(ValueError,'contour geometry'):
            Case(((0,.1),(.2,.1)),contour_mesh=ContourMeshControls(.05))
