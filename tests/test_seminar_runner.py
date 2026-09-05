# SPDX-License-Identifier: Apache-2.0
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
from superfish_ng import Case, solve


@unittest.skipUnless(importlib.util.find_spec('matplotlib'), 'optional plotting dependency not installed')
class SeminarRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
        import seminar_pillbox
        cls.runner = seminar_pillbox

    def test_tm011_identification_when_radial_mode_interleaves(self):
        case = Case(((0., .075), (.04, .075)), nr=24, nz=14, modes=4)
        solution = solve(case)
        index, overlap = self.runner.identify_pillbox_mode(case, solution, 1)
        self.assertEqual(index, 2)  # TM020 lies below TM011 at this length.
        self.assertGreater(overlap, .99)

    def test_reference_energy_and_signed_voltage_remain_consistent(self):
        z = np.linspace(0, .08, 801)
        field = np.cos(np.pi*z/.08)*1e6
        sf = {'axis': np.column_stack((z, field)), 'quantities': {
            'frequency_hz': 2.4e9, 'stored_energy_j': 2., 'wall_loss_w': 300.,
            'q0': 2*np.pi*2.4e9*2/300, 'geometry_factor_ohm': 2.,
            'surface_resistance_ohm': .01, 'conductivity_s_per_m': 5.8e7, 'active_length_m': .08}}
        q1, e1 = self.runner.signed_axis_metrics(sf, np.column_stack((z, field/np.sqrt(2))), 1.)
        q9, e9 = self.runner.signed_axis_metrics(sf, np.column_stack((z, field*3/np.sqrt(2))), 9.)
        self.assertAlmostEqual(q9['vacc_v']/q1['vacc_v'], 3.)
        self.assertAlmostEqual(q9['wall_loss_w']/q1['wall_loss_w'], 9.)
        self.assertEqual(q1['r_over_q_accelerator_ohm'], q9['r_over_q_accelerator_ohm'])
        self.assertAlmostEqual(2*np.pi*q9['frequency_hz']*q9['stored_energy_j']/q9['wall_loss_w'], q9['q0'])
        self.assertLess(e1, 1e-12)
        self.assertLess(e9, 1e-12)

    def test_saved_multicell_import_checks_axis_against_stored_field(self):
        from seminar_multicell import read_native
        from superfish_ng.io import save_run
        case = Case(((0., .075), (.08, .075)), nr=6, nz=8, modes=2)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'run'
            save_run(case, solve(case), path)
            _, axes = read_native(path, case)
            axes[0][0, 1] *= 1.1
            np.savetxt(path/'axis_001.csv', axes[0], delimiter=',', header='z_m,Ez_quadrature_V_per_m', comments='')
            with self.assertRaises(ValueError): read_native(path, case)
