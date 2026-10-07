# SPDX-License-Identifier: Apache-2.0
"""Independent physical-coordinate TM derivatives and complete box searches."""
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from superfish_ng.adaptive_efficiency_fields import EfficiencyFieldSampler, COMPONENTS
from superfish_ng.adaptive_efficiency_plan import build_adaptive_efficiency_plan
from superfish_ng.config import Case
from superfish_ng.constants import EPS0, TAU
from superfish_ng.curved_sampling import CurvedFieldSampler
from superfish_ng.curved_solution import CurvedSolution
from superfish_ng.curved_space import case_curved_space
from superfish_ng.io import save_run
from superfish_ng.mesh import make_mesh
from superfish_ng.mesh_input import mesh_to_dict
from superfish_ng.sampling import FieldSampler
from superfish_ng.saved import read_solution
from superfish_ng.solver import solve


class AdaptiveEfficiencyFieldsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = build_adaptive_efficiency_plan()
        cls.case = Case.from_dict(cls.plan['cases'][1]['request']['case'])
        mesh = make_mesh(cls.case)
        cls.space = case_curved_space(cls.case, mesh)
        nodes = cls.space.geometry.points_rz_m
        # u=A+B*r+C*z is exactly in the isoparametric P2 space. Its
        # physical gradient is (B,C), independently of the curved map.
        cls.abc = ((2., 3., -4.), (-5., 7., 11.))
        coefficients = np.column_stack([a+b*nodes[:,0]+c*nodes[:,1] for a,b,c in cls.abc])
        cls.manufactured = CurvedSolution(replace(cls.case, modes=2), cls.space, None, None, np.ones(2),
                                         np.array((1.3e9, 2.7e9)), coefficients, np.zeros(2),
                                         0., 12, mesh_to_dict(mesh))
        refs = np.array(((.2,.3), (.4,.1), (0.,0.), (.5,.5)))
        cls.points = np.concatenate([m.evaluate(refs)['points_rz_m'] for m in cls.space.geometry.local_maps])

    def exact(self, points, modes):
        r,z = points.T
        values = []
        for mode in modes:
            a,b,c = self.abc[mode]
            u = a+b*r+c*z
            omega = TAU*self.manufactured.frequencies_hz[mode]
            values.append(np.column_stack((-r*c/(omega*EPS0), (2*u+r*b)/(omega*EPS0), r*u)))
        return np.stack(values, axis=1)

    def test_curved_physical_linear_u_exact_gradient_all_modes_axis_and_boundary(self):
        original = self.manufactured.u.copy()
        sampler = EfficiencyFieldSampler(self.manufactured)
        result = sampler.evaluate(self.points, modes=(1,0))
        self.assertEqual(result['mode_indices'], [1,0])
        self.assertEqual(result['sample_count'], len(self.points))
        self.assertEqual(result['coverage_status'], 'ALL_SUPPLIED_POINTS_LOCATED')
        self.assertIsNone(result['physical_error_bound'])
        np.testing.assert_allclose(result['fields'], self.exact(self.points, (1,0)), rtol=3e-11, atol=2e-12)
        np.testing.assert_array_equal(self.manufactured.u, original)
        old = CurvedFieldSampler(self.manufactured)
        for output,mode in enumerate((1,0)):
            actual = old.evaluate(self.points, mode=mode)
            expected = np.column_stack([actual[key] for key in COMPONENTS])
            np.testing.assert_allclose(result['fields'][:,output], expected, rtol=2e-12, atol=1e-12)

    def test_tree_candidates_equal_full_padded_boxes_including_extrema(self):
        sampler = EfficiencyFieldSampler(self.manufactured)
        old = sampler.native_sampler
        points = np.vstack((self.points, old.lower, old.upper, (old.lower+old.upper)/2))
        for point in points:
            expected = np.flatnonzero(np.all(point>=old.lower, axis=1)&np.all(point<=old.upper, axis=1))
            np.testing.assert_array_equal(sampler.candidate_cells(point), expected)

    def test_saved_actual_curved_fields_all_points_all_modes_match_original(self):
        case = replace(self.case, modes=2)
        solution = solve(case)
        with tempfile.TemporaryDirectory() as tmp:
            save_run(case, solution, Path(tmp)/'native')
            saved = read_solution(Path(tmp)/'native')
            points = np.concatenate([m.evaluate([[.2,.3]])['points_rz_m'] for m in saved.space.geometry.local_maps])
            result = EfficiencyFieldSampler(saved).evaluate(points)
            old = FieldSampler.from_solution(saved)
            for mode in range(2):
                expected = old.evaluate(points, mode=mode)
                np.testing.assert_allclose(result['fields'][:,mode],
                                           np.column_stack([expected[key] for key in COMPONENTS]),
                                           rtol=2e-12, atol=1e-12)
            np.testing.assert_array_equal(saved.u, solution.u)
            np.testing.assert_array_equal(saved.frequencies_hz, solution.frequencies_hz)

    def test_actual_affine_original_sampler_and_coefficients_preserved(self):
        case = Case.from_dict(self.plan['cases'][0]['request']['case'])
        solution = solve(case)
        points = np.vstack((solution.mesh.points, [[.017,.043], [.071,.183], [0.,.123]]))
        coefficients = solution.u.copy()
        result = EfficiencyFieldSampler(solution).evaluate(points)
        old = FieldSampler.from_solution(solution)
        for mode in range(len(solution.frequencies_hz)):
            values = old.evaluate(points, mode=mode)
            np.testing.assert_array_equal(result['fields'][:,mode], np.column_stack([values[key] for key in COMPONENTS]))
        np.testing.assert_array_equal(solution.u, coefficients)

    def test_invalid_points_modes_and_unsupported_solutions_fail_closed(self):
        sampler = EfficiencyFieldSampler(self.manufactured)
        for points in ([], [[True,False]], [['0','0']], [[1j,0]], [[np.nan,0]], [[0]], [[-1.,0.]]):
            with self.assertRaises(ValueError):
                sampler.evaluate(points)
        for modes in ((), (True,), (0,0), (2,), (-1,), (np.int64(0),), '0'):
            with self.assertRaises(ValueError):
                sampler.evaluate(self.points[:1], modes=modes)
        with self.assertRaisesRegex(ValueError, 'outside'):
            sampler.evaluate([[1.,1.]])
        with self.assertRaises(ValueError):
            EfficiencyFieldSampler(object())
        with self.assertRaises(ValueError):
            EfficiencyFieldSampler(replace(self.manufactured, u=np.full_like(self.manufactured.u, np.nan)))
        with self.assertRaisesRegex(ValueError, 'original P2 space and Case'):
            EfficiencyFieldSampler(replace(self.manufactured, u=self.manufactured.u[:-1]))
        with self.assertRaisesRegex(ValueError, 'original P2 space and Case'):
            EfficiencyFieldSampler(replace(self.manufactured, case=replace(self.manufactured.case, modes=1)))
        te = Case.from_dict(self.plan['cases'][1]['request']['case'])
        te = replace(te, model=replace(te.model, polarization='te'))
        with self.assertRaisesRegex(ValueError, 'TM'):
            EfficiencyFieldSampler(replace(self.manufactured, case=te))

    def test_unresolved_lookup_original_interrupt_and_nonfinite_fields_preserved(self):
        sampler = EfficiencyFieldSampler(self.manufactured)
        point = self.space.geometry.local_maps[0].evaluate([[.2,.3]])['points_rz_m']
        candidates = sampler.candidate_cells(point[0])
        with patch.object(sampler.native_sampler.locators[int(candidates[0])], 'inverse', side_effect=ValueError('budget original')):
            with self.assertRaisesRegex(ValueError, 'UNVERIFIED.*budget original'):
                sampler.evaluate(point)
        interrupted = KeyboardInterrupt('original lookup interruption')
        with patch.object(sampler.native_sampler.locators[int(candidates[0])], 'inverse', side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt) as caught:
                sampler.evaluate(point)
        self.assertIs(caught.exception, interrupted)
        with patch.object(self.manufactured, 'fields_in_cell', return_value={k: np.array([np.nan]) for k in COMPONENTS}):
            with self.assertRaisesRegex(ValueError, 'nonfinite'):
                sampler.evaluate(point)


if __name__ == '__main__':
    unittest.main()
