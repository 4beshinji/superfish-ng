# SPDX-License-Identifier: Apache-2.0
"""Offline tests of unit/convention conversion using invented reference values."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('comparison_script', Path(__file__).resolve().parents[1] / 'scripts/compare_superfish.py')
comparison = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)

FIXTURE = '''Program SFO written by synthetic fixture
Program SFO 7.17 released fixture-date
Treating the problem geometry as a single full cell:
FREQ 1000 frequency MHz
ENERGY 2 energy J
POWER 400 power W
ZLONG 10 length cm
EZERO 1000000 peak V/m
T 0.6 cosine integral
  S = 0.8
RS 0.01 ohm
EMAX 2000000 V/m
FMU0 1.256637061e-6 H/m
HMAX 3000 A/m
NPINP 100 nodes
Normal-conductor resistivity = 1.72410 microOhm-cm
Z(cm)      Ez(V/m)
 0 1000000
 5 1000000
 10 1000000
end
'''


class SuperfishComparisonTests(unittest.TestCase):
    def parse(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.sfo'
            path.write_text(text)
            return comparison.parse_sfo(path)

    def test_peak_voltage_energy_and_resistivity_conventions(self):
        parsed = self.parse(FIXTURE)
        self.assertEqual(parsed['version'], '7.17 released fixture-date')
        q = parsed['quantities']
        self.assertAlmostEqual(q['active_length_m'], .1)
        self.assertAlmostEqual(q['transit_time_factor_abs'], 1.)
        self.assertAlmostEqual(q['vacc_v'], 100000.)
        self.assertAlmostEqual(q['q0'], 31415926.53589793)
        self.assertAlmostEqual(q['r_over_q_accelerator_ohm'], .7957747154594768)
        self.assertAlmostEqual(q['r_over_q_circuit_ohm'], .3978873577297384)
        self.assertAlmostEqual(q['conductivity_s_per_m'] * 1.7241e-8, 1.)
        json.dumps({'quantities': q, 'axis_gate': q['axis_voltage_vs_sfo_relative_difference'] < .001}, allow_nan=False)

    def test_half_cell_reference_rejected(self):
        with self.assertRaisesRegex(ValueError, 'full cell'):
            self.parse(FIXTURE.replace('single full cell', 'single half cell'))

    def test_missing_energy_and_incomplete_axis_rejected(self):
        for bad in [FIXTURE.replace('ENERGY 2 energy J\n', ''), FIXTURE.replace(' 10 1000000', ' 9 1000000')]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.parse(bad)

    def test_generated_deck_has_complete_wall_segments_and_center(self):
        case = comparison.Case(((0., .045), (.025, .045), (.065, .105), (.115, .105), (.155, .045), (.18, .045)))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            comparison.write_deck(case, root, .1, 1270.)
            self.assertIn('1 2 3 4 5 6 7\n', (root/'cavity.seg').read_text())
            self.assertIn('zctr=9.0', (root/'cavity.af').read_text())
            self.assertIn('$po x=6.5, y=10.5 $', (root/'cavity.af').read_text())

    def test_sf7_signed_components_are_preserved_in_si(self):
        text = '  (cm) (cm) (MV/m) (MV/m) (MV/m) (A/m)\n0 0 2 0 2 0\n4 0 0 0 0 0\n8 0 -2 0 2 0\nend\n'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'sf7.txt'
            path.write_text(text)
            fields = comparison.read_sf7_line(path)
            self.assertEqual(fields[-1, 0], .08)
            self.assertEqual(fields[-1, 2], -2e6)
            self.assertEqual(fields[-1, 4], 2e6)


if __name__ == '__main__':
    unittest.main()
