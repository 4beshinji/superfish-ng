# SPDX-License-Identifier: Apache-2.0
"""History-preserving Study: fixed-domain and variational invariants."""
from dataclasses import replace
import math
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng.curved_refinement_steps import CurvedRefinementStep as Step
from superfish_ng.project import Project
from superfish_ng.studies import Study, execute_study
from superfish_ng.saved import read_solution
from superfish_ng.fem import triangle_quadrature
from test_curved_reflection import half_case


class CurvedHistoryStudyTests(unittest.TestCase):
    def case(self):
        return replace(half_case('z_min', 'magnetic_symmetry'),
                       curved_refinement_steps=(Step('marked', (0,), 5.),))

    def study(self, values=None):
        return Study(Project(self.case()), 'fixed_geometry_convergence',
                     'additional_uniform_refinements', [0, 1] if values is None else values)

    def test_explicit_prefix_roundtrip_and_rejections(self):
        study = self.study([0, 2])
        restored = Study.from_dict(study.to_dict())
        projects = restored.projects()
        self.assertEqual(projects[0].case, self.case())
        self.assertEqual(projects[1].case.curved_refinement_steps,
                         self.case().curved_refinement_steps + (Step('uniform'),)*2)
        self.assertEqual(study.project.case, self.case())
        for values in ([0, 0], [1, 0], [-1, 1], [False, 1], [0, 1.5], [0, 10**9]):
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.study(values)
        for kind, parameter, values in (
                ('mesh_convergence', 'mesh_scale', [1, 2]),
                ('geometry_convergence', '/case/geometry/chord_tolerance_m', [.002, .001]),
                ('sweep', '/case/rf/beta', [.5, 1.]),
                ('fixed_geometry_convergence', '/case/mesh/curved_refinement_levels', [0, 1])):
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'cannot reinterpret'):
                Study(Project(self.case()), kind, parameter, values)
        with self.assertRaises(ValueError):
            Study(Project(half_case('z_min', 'magnetic_symmetry')),
                  'fixed_geometry_convergence', 'additional_uniform_refinements', [0, 1])

    def test_real_study_preserves_volume_and_ritz_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)/'study'
            report = execute_study(self.study(), directory)
            solutions = [read_solution(directory/p['directory']/'solution') for p in report['points']]
            a, b = solutions
            self.assertEqual(a.case, self.case())
            self.assertEqual(b.case.curved_refinement_steps[:-1], a.case.curved_refinement_steps)
            self.assertEqual(a.source_mesh_data, b.source_mesh_data)
            self.assertEqual(len(b.space.geometry.cell_nodes), 4*len(a.space.geometry.cell_nodes))
            # 2*pi*integral r det(J) is exact with this polynomial rule on P2 maps.
            rule = list(triangle_quadrature(order=6))
            q = [n[1:] for n, w in rule]
            w = np.array([w for n, w in rule])
            volumes = []
            for solution in solutions:
                parts = []
                for mapping in solution.space.geometry.local_maps:
                    mapped = mapping.evaluate(q)
                    parts.append(float(w @ (mapped['points_rz_m'][:, 0]*mapped['determinant_m2'])))
                volumes.append(2*math.pi*math.fsum(parts))
            self.assertLess(abs(volumes[1]/volumes[0]-1), 2e-13)
            self.assertLessEqual(b.frequencies_hz[0], a.frequencies_hz[0]*(1+1e-11))
            self.assertIn('uniform restrictions', report['geometry_refinement'])
            self.assertIn('not assessed', report['surface_field'])
