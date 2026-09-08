# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from superfish_ng import Case, solve
from superfish_ng.completion import digest
from superfish_ng.curved_refinement_steps import CurvedRefinementStep as Step
from superfish_ng.curved_space import case_curved_space
from superfish_ng.curved_refinement import refine_curved_space
from superfish_ng.curved_marked_refinement import refine_marked_curved_space
from superfish_ng.curved_saved import geometry_arrays
from superfish_ng.io import save_run
from superfish_ng.mesh import make_mesh
from superfish_ng.saved import read_solution
from superfish_ng.project import Project
from superfish_ng.studies import Study
from test_curved_reflection import half_case


class CurvedRefinementStepsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = half_case('z_min', 'magnetic_symmetry')
        cls.steps = (Step('marked', (0,), 5.), Step('uniform'), Step('marked', (1,), 5.))
        cls.case = replace(cls.base, curved_refinement_steps=cls.steps)
        cls.solution = solve(cls.case)

    def test_ordered_maps_match_manual_restrictions_and_old_uniform(self):
        base = case_curved_space(self.base, make_mesh(self.base))
        manual = refine_marked_curved_space(base, [0], minimum_corner_angle_deg=5.).space
        manual = refine_curved_space(manual).space
        manual = refine_marked_curved_space(manual, [1], minimum_corner_angle_deg=5.).space
        for key, value in geometry_arrays(manual).items():
            np.testing.assert_array_equal(value, geometry_arrays(self.solution.space)[key])
        old = replace(self.base, curved_refinement_levels=1)
        new = replace(self.base, curved_refinement_steps=(Step('uniform'),))
        for key, value in geometry_arrays(case_curved_space(old, make_mesh(old))).items():
            np.testing.assert_array_equal(value, geometry_arrays(case_curved_space(new, make_mesh(new)))[key])
        self.assertEqual(Case.from_dict(self.case.to_dict()), self.case)
        self.assertNotIn('curved_refinement_steps', self.base.to_dict()['mesh'])

    def test_strict_history_and_mesh_budget(self):
        original = self.case.to_dict()
        invalid = [None, [], {}, [{'kind':'unknown'}], [{'kind':'uniform','marked_cells':[]}],
                   [{'kind':'marked','marked_cells':[], 'minimum_corner_angle_deg':5}],
                   [{'kind':'marked','marked_cells':[True], 'minimum_corner_angle_deg':5}],
                   [{'kind':'marked','marked_cells':[0,0], 'minimum_corner_angle_deg':5}],
                   [{'kind':'marked','marked_cells':[-1], 'minimum_corner_angle_deg':5}],
                   [{'kind':'marked','marked_cells':[0]}],
                   [{'kind':'marked','marked_cells':[0], 'minimum_corner_angle_deg':60}],
                   [{'kind':'marked','marked_cells':[0], 'minimum_corner_angle_deg':float('nan')}]]
        for history in invalid:
            with self.subTest(history=history), self.assertRaises(ValueError):
                data = deepcopy(original); data['mesh']['curved_refinement_steps'] = history
                Case.from_dict(data)
        with self.assertRaisesRegex(ValueError, 'conflicts'):
            replace(self.case, curved_refinement_levels=1)
        with self.assertRaisesRegex(ValueError, 'immutable'):
            replace(self.case, curved_refinement_steps=list(self.steps))
        with self.assertRaisesRegex(ValueError, 'geometry_order=2'):
            replace(self.case, geometry_order=1, quadrature_order=8)
        for steps in ((Step('marked',(1000000,),5.),), (Step('uniform'),)):
            case = replace(self.base, curved_refinement_steps=steps,
                           contour_mesh=replace(self.base.contour_mesh, max_triangles=100))
            with self.assertRaisesRegex(ValueError, 'step 1'):
                case_curved_space(case, make_mesh(self.base))
        with self.assertRaisesRegex(ValueError, 'cannot reinterpret'):
            Study(Project(self.case), 'fixed_geometry_convergence', '/case/mesh/curved_refinement_levels', [0,1])

    def test_native_roundtrip_revalidates_without_eigensolve(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)/'run'
            result = save_run(self.case, self.solution, directory)
            with patch('superfish_ng.curved_solution.eigsh', side_effect=AssertionError('must not solve')):
                restored = read_solution(directory)
            self.assertEqual(restored.case, self.case)
            np.testing.assert_array_equal(restored.u, self.solution.u)
            np.testing.assert_array_equal(restored.frequencies_hz, self.solution.frequencies_hz)
            self.assertEqual(result['field_space']['curved_refinement_steps'], self.case.to_dict()['mesh']['curved_refinement_steps'])
            original = (directory/'results.json').read_text()
            for section in ('field_space', 'geometry_approximation'):
                changed = json.loads(original)
                changed[section]['curved_refinement_steps'][0]['marked_cells'] = [2]
                (directory/'results.json').write_text(json.dumps(changed))
                marker_path = directory/'save_complete.json'
                marker = json.loads(marker_path.read_text())
                marker['files']['results.json'] = digest(directory/'results.json')
                marker_path.write_text(json.dumps(marker))
                with self.assertRaisesRegex(ValueError, 'history'):
                    read_solution(directory)

    def test_reflection_keeps_half_domain_history_in_source_only(self):
        from superfish_ng.curved_reflection import reflect_curved_solution
        full, solution = reflect_curved_solution(self.case, self.solution)
        self.assertEqual(full.curved_refinement_steps, ())
        self.assertEqual(solution.reflection_source_case, self.case)
        self.assertLess(max(solution.residuals), 1e-7)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)/'reflected'
            save_run(full, solution, directory)
            with patch('superfish_ng.curved_solution.eigsh', side_effect=AssertionError('must not solve')):
                restored = read_solution(directory)
            self.assertEqual(restored.reflection_source_case.curved_refinement_steps, self.steps)
            np.testing.assert_array_equal(restored.u, solution.u)
