# SPDX-License-Identifier: Apache-2.0
"""TE sweeps preserve energy normalization and distinguish ranks from identities."""
from copy import deepcopy
from pathlib import Path
import json
import tempfile
import unittest
import numpy as np
from superfish_ng import Case
from superfish_ng.model import Model
from superfish_ng.project import Project
from superfish_ng.studies import Study, execute_study
from superfish_ng.study_mode_tracking import build_study_mode_tracking
from superfish_ng.completion import digest
from superfish_ng.te_saved import read_te_run
from test_te_mode_tracking import CONTROLS


class TEStudyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = Project(Case(((0., .1), (.15, .1)), nr=12, nz=18,
                                   modes=2, element_order=2, model=Model(polarization='te')))

    def study(self, values=(1., 4.)):
        return Study(self.project, 'sweep', '/case/rf/normalization_j', list(values))

    def request(self, run):
        return dict(schema_version=1, study_run=str(run.resolve()),
                    initial_ids=['first', 'second'], step_controls=[deepcopy(CONTROLS)])

    def test_normalization_changes_fields_not_spectrum_or_geometry_factor(self):
        run = self.root / 'sweep'
        result = execute_study(self.study(), run)
        self.assertEqual(result['physics'], 'axisymmetric_m0_te')
        self.assertEqual(result['numerical_status'], 'UNVERIFIED')
        self.assertEqual(result['mode_tracking'], 'not performed; independent spectra')
        first, second = [read_te_run(run / p['directory'] / 'solution') for p in result['points']]
        np.testing.assert_allclose(np.abs(second.coefficients_v_per_m2), 2*np.abs(first.coefficients_v_per_m2), atol=1e-6, rtol=1e-10)
        for a, b in zip(*(p['modes'] for p in result['points'])):
            self.assertAlmostEqual(a['frequency_hz']/b['frequency_hz'], 1.)
            self.assertAlmostEqual(a['geometry_factor_ohm']/b['geometry_factor_ohm'], 1.)
            self.assertAlmostEqual(b['stored_energy_j']/a['stored_energy_j'], 4.)
            self.assertAlmostEqual(b['wall_loss_w']/a['wall_loss_w'], 4.)
            self.assertIsNone(a['r_over_q_accelerator_ohm'])
            self.assertIsNone(b['r_over_q_circuit_ohm'])
        self.assertEqual(build_study_mode_tracking(self.request(run))['status'], 'PASS')

    def test_rejects_forged_zero_even_with_updated_outer_hash(self):
        run = self.root / 'sweep'
        execute_study(self.study(), run)
        path, manifest = run/'study-results.json', run/'manifest.json'
        summary = json.loads(path.read_text())
        summary['points'][0]['modes'][0]['r_over_q_accelerator_ohm'] = 0.
        path.write_text(json.dumps(summary))
        outer = json.loads(manifest.read_text())
        outer['files']['study-results.json'] = digest(path)
        manifest.write_text(json.dumps(outer))
        with self.assertRaisesRegex(ValueError, 'summary differs'):
            build_study_mode_tracking(self.request(run))

    def test_invalid_later_point_fails_before_creating_output(self):
        run = self.root/'invalid'
        with self.assertRaises(ValueError):
            execute_study(self.study((1., -1.)), run)
        self.assertFalse(run.exists())

    def test_convergence_preserves_strict_parameter_validation(self):
        with self.assertRaisesRegex(ValueError, 'mesh convergence requires'):
            Study(self.project, 'mesh_convergence', 'nr', [1, 2])
