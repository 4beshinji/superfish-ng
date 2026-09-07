# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng import Case, solve
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution
from superfish_ng.project import Project
from superfish_ng.studies import Study
from superfish_ng.curved_space import case_curved_space
from superfish_ng.mesh import make_mesh


class FixedCurvedCaseTests(unittest.TestCase):
    def case(self):
        case = Case.load(Path(__file__).resolve().parents[1]/'examples/curved_ellipse.json')
        return replace(case, geometry_order=2, curved_refinement_levels=1)

    def test_refined_native_save_reconstructs_same_space_and_rf(self):
        case = self.case()
        self.assertEqual(Case.from_dict(case.to_dict()), case)
        solution = solve(case)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'run'
            result = save_run(case, solution, path)
            saved = read_solution(path)
            np.testing.assert_array_equal(saved.u, solution.u)
            np.testing.assert_array_equal(saved.space.geometry.points_rz_m, solution.space.geometry.points_rz_m)
            self.assertEqual(result['field_space']['curved_refinement_levels'], 1)
            self.assertIn('no analytic curve reprojection', result['geometry_approximation']['representation'])
            self.assertNotIn('node_displacements_m', np.load(path/'fields.npz').files)
            # Level 0 retains the previous storage declaration/array contract.
            coarse = replace(case, curved_refinement_levels=0)
            self.assertNotIn('curved_refinement_levels', coarse.to_dict()['mesh'])

    def test_strict_levels_and_preallocation_limit(self):
        case = self.case()
        for value in (-1, True, .5):
            with self.assertRaisesRegex(ValueError, 'nonnegative integer'):
                replace(case, curved_refinement_levels=value)
        with self.assertRaisesRegex(ValueError, 'geometry_order'):
            replace(case, geometry_order=1)
        limited = replace(case, contour_mesh=replace(case.contour_mesh, max_triangles=500))
        mesh = make_mesh(replace(limited, curved_refinement_levels=0))
        with self.assertRaisesRegex(ValueError, 'exceeds max_triangles'):
            case_curved_space(limited, mesh)

    def test_study_changes_only_refinement_levels(self):
        case = replace(self.case(), curved_refinement_levels=0)
        project = Project.from_dict(case.to_dict())
        study = Study(project, 'fixed_geometry_convergence', '/case/mesh/curved_refinement_levels', [0, 1])
        self.assertEqual(Study.from_dict(study.to_dict()).to_dict(), study.to_dict())
        cases = [p.case for p in study.projects()]
        self.assertEqual(cases, [case, replace(case, curved_refinement_levels=1)])
        for values in ([0, 0], [1, 0], [0, 1.5], [0, True]):
            with self.assertRaises(ValueError):
                Study(project, 'fixed_geometry_convergence', '/case/mesh/curved_refinement_levels', values)
