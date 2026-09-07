# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import math
from pathlib import Path
import tempfile
import unittest
from superfish_ng import Case
from superfish_ng.conics import LineSegment, EllipseArc
from superfish_ng.curved_contour import CurvedContour
from superfish_ng.mesh_controls import ContourMeshControls
from superfish_ng.project import Project
from superfish_ng.studies import Study, execute_study, compare_refinement, _physical_spec
from superfish_ng.analytic_sphere import SphereTM
from superfish_ng.jobs import read_job


class CurvedStudyTests(unittest.TestCase):
    def case(self):
        radius = .08
        return Case((), curved_contour=CurvedContour((LineSegment((0, 0), (2*radius, 0)),
                    EllipseArc((radius, 0), (radius, radius), 0, math.pi)), ('axis', 'pec'), 1e-14),
                    curve_chord_tolerance_m=.0008, contour_mesh=ContourMeshControls(.02),
                    element_order=2, geometry_order=2, modes=1)

    def test_curved_study_retains_geometry_and_matches_sphere(self):
        case = self.case()
        study = Study(Project.from_dict(case.to_dict()), 'mesh_convergence', 'mesh_scale', [1, 2])
        self.assertTrue(all(p.case.geometry_order == 2 for p in study.projects()))
        expected = SphereTM(.08)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)/'study'
            report = execute_study(study, directory)
            self.assertEqual(read_job(directory)['status'], 'complete')
            self.assertEqual(report['comparisons'][0]['status'], 'PASS')
            self.assertIn('not a fixed-discrete-geometry', report['geometry_refinement'])
            self.assertIn('not assessed', report['surface_field'])
            for point in report['points']:
                mode = point['modes'][0]
                self.assertLess(abs(mode['frequency_hz']/expected.frequency_hz-1), .001)
                self.assertLess(abs(mode['r_over_q_accelerator_ohm']/expected.quantities()['r_over_q_accelerator_ohm']-1), .01)
            same = compare_refinement(directory/'point-001/solution', directory/'point-001/solution')
            self.assertAlmostEqual(same['modes'][0]['field_overlap'], 1.)
            self.assertEqual(same['modes'][0]['axis_relative_l2'], 0.)

    def test_quadrature_changes_numerics_but_beta_changes_physics(self):
        case = self.case()
        self.assertEqual(_physical_spec(case), _physical_spec(replace(case, quadrature_order=12)))
        self.assertNotEqual(_physical_spec(case), _physical_spec(replace(case, beta=.9)))
