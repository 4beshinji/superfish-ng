# SPDX-License-Identifier: Apache-2.0
"""Synthetic SF7 fixtures only; tests never launch Wine."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from evaluate_wine_surface_fields import parse_sf7_tables, probe_input, inset_probes, write_surface_deck
from evaluate_surface_fields import fillet_case
from report_wine_surface_fields import boundary_edges
from superfish_ng import Case


class WineSurfaceDiagnosticTests(unittest.TestCase):
    def test_multiple_signed_tables_and_units(self):
        header = ' (cm) (cm) (MV/m) (MV/m) (MV/m) (A/m)\n'
        block = header+' 1 2 -3 4 5 6\n 2 2 0 -2 2 -3\n 3 2 0 1 1 0\nEnd line\n'
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'sf7.txt'
            path.write_text(block+block)
            tables = parse_sf7_tables(path)
            self.assertEqual(len(tables), 2)
            self.assertEqual(tables[0][0, 0], .01)
            self.assertEqual(tables[1][0, 2], -3e6)
            self.assertEqual(tables[1][1, 5], -3)
            path.write_text(block.replace('-3 4 5', '-3 4 7'))
            with self.assertRaisesRegex(ValueError, 'magnitudes'):
                parse_sf7_tables(path)
            path.write_text('No results\n')
            with self.assertRaisesRegex(ValueError, 'missing'):
                parse_sf7_tables(path)

    def test_all_corner_sides_are_exported_without_the_singular_vertex(self):
        base = Case.load(ROOT/'examples/shaped_cell.json')
        text, groups = probe_input(base)
        self.assertEqual(text.count('line plotfiles'), 16)
        self.assertEqual(len(groups), 16)
        self.assertTrue(text.endswith('end\n'))
        self.assertTrue(all(p['distance_m'] > 0 for group in groups for p in group))

    def test_normal_offsets_stay_in_vacuum_and_keep_wall_distance(self):
        import numpy as np
        base = Case.load(ROOT/'examples/shaped_cell.json')
        for p in inset_probes(base, 1e-6):
            r, z = p['point_rz_m']
            self.assertLess(r, np.interp(z, *np.array(base.profile).T))
            self.assertAlmostEqual(np.linalg.norm(np.array(p['point_rz_m'])-p['surface_point_rz_m']), 1e-6, places=14)

    def test_automesh_boundary_units_and_closure(self):
        import numpy as np
        text = ('Region 1 mesh points\n K L X Y\n'
                '1 1 0 0\n1 2 0 2\n2 2 3 2\n2 1 3 0\n1 1 0 0\nRegion 1 done\n')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'outaut.txt'
            path.write_text(text)
            edges = boundary_edges(path)
            self.assertEqual(edges.shape, (4, 2, 2))
            np.testing.assert_allclose(edges[0, 1], [.02, 0])
            self.assertAlmostEqual(np.linalg.norm(edges[:, 1]-edges[:, 0], axis=1).sum(), .1)
            path.write_text(text.replace('2 1 3 0\n1 1 0 0', '2 1 3 0'))
            with self.assertRaisesRegex(ValueError, 'closed'):
                boundary_edges(path)

    def test_tangent_control_exports_both_documented_arc_directions(self):
        base = fillet_case(Case.load(ROOT/'examples/shaped_cell.json'))
        with tempfile.TemporaryDirectory() as folder:
            write_surface_deck(base, Path(folder), .1)
            text = (Path(folder)/'cavity.af').read_text()
            self.assertEqual(text.count('nt=4, radius=0.3'), 2)
            self.assertEqual(text.count('nt=5, radius=0.3'), 2)
            self.assertEqual(text.count('$po '), len(base.profile)+3)


if __name__ == '__main__':
    unittest.main()
