# SPDX-License-Identifier: Apache-2.0
"""Physical sizing preserves the domain and improves independent PEC traces."""
from dataclasses import replace
import unittest
import numpy as np
from superfish_ng import Case, make_mesh, solve
from superfish_ng.mesh import make_base_mesh, validate_profile_mesh
from superfish_ng.fem import assemble


class PhysicalMeshTests(unittest.TestCase):
    def test_strict_sizes_and_roundtrip(self):
        base = Case(((0., .045), (.025, .045), (.065, .105), (.09, .105)))
        case = replace(base, boundary_max_edge_m=.002, corner_max_edge_m=.001, corner_radius_m=.004)
        self.assertEqual(Case.from_dict(case.to_dict()), case)
        for name in ('boundary_max_edge_m', 'corner_max_edge_m', 'corner_radius_m'):
            for value in (0, -1, True, float('nan'), float('inf')):
                with self.assertRaises(ValueError):
                    replace(case, **{name: value})
            data = case.to_dict()
            data['mesh'][name] = None
            with self.assertRaises(ValueError):
                Case.from_dict(data)
        with self.assertRaises(ValueError):
            replace(base, corner_radius_m=.01)
        with self.assertRaises(ValueError):
            Case.from_dict(dict(case.to_dict(), schema_version=1))

    def test_physical_lengths_domain_and_weighted_volume(self):
        for kind in ('profile', 'stepped_profile'):
            profile = ((0., .045), (.025, .045), (.025 if kind == 'stepped_profile' else .065, .105), (.09, .105))
            case = Case(profile, nr=8, nz=12, geometry_type=kind,
                        boundary_max_edge_m=.004, corner_max_edge_m=.002, corner_radius_m=.006,
                        z_max='magnetic_symmetry')
            mesh = make_mesh(case)
            validate_profile_mesh(case, mesh)
            ends = mesh.points[mesh.boundary_edges[mesh.boundary_tags != 'axis']]
            self.assertLessEqual(np.linalg.norm(ends[:, 1]-ends[:, 0], axis=1).max(), .004*(1+1e-12))
            # Old axial/radial counts fail this independent physical length bound.
            old = make_base_mesh(case)
            ends_old = old.points[old.boundary_edges[old.boundary_tags != 'axis']]
            self.assertGreater(np.linalg.norm(ends_old[:, 1]-ends_old[:, 0], axis=1).max(), .004)
            edges = mesh.points[mesh.triangles[:, [[0, 1], [1, 2], [2, 0]]]].reshape(-1, 2, 2)
            delta = edges[:, 1]-edges[:, 0]
            length = np.linalg.norm(delta, axis=1)
            for corner in np.array(profile[1:-1])[:, ::-1]:
                t = np.clip(np.sum((corner-edges[:, 0])*delta, axis=1)/length**2, 0, 1)
                near = np.linalg.norm(edges[:, 0]+t[:, None]*delta-corner, axis=1) <= .006
                self.assertLessEqual(length[near].max(), .002*(1+1e-12))
            _, m = assemble(mesh)
            one = np.ones(len(mesh.points))
            # Integral r^3 dr dz = integral R(z)^4/4 dz, exact polynomial fixture.
            exact = sum((zb-za)*sum(ra**(4-i)*rb**i for i in range(5))/20
                        for (za, ra), (zb, rb) in zip(profile, profile[1:]))
            self.assertAlmostEqual(float(one @ (m @ one))/exact, 1., places=12)
            self.assertIn('magnetic_symmetry', mesh.boundary_tags)

    def test_corner_refinement_reduces_independent_pec_trace_defect(self):
        import sys
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(root/'scripts'))
        from evaluate_surface_fields import sharp_probes, surface_data, probe_surface
        base = replace(Case.load(root/'examples/shaped_cell.json'), nr=48, nz=82, modes=1)
        defects = []
        for case in (base, replace(base, boundary_max_edge_m=.105/48,
                                  corner_max_edge_m=.105/48/4, corner_radius_m=.01)):
            data = surface_data(solve(case))
            traces = [probe_surface(*data, p['point_rz_m']) for p in sharp_probes(base)
                      if p['corner_index'] in (1, 4) and p['distance_m'] == .001]
            defects.append(max(p['tangential_e_max_v_per_m']/p['e_max_v_per_m'] for p in traces))
        # Exact PEC has Et=0. This is not a cross-code or algebraic-residual gate.
        self.assertGreater(defects[0], .1)
        self.assertLess(defects[1], .07)
        self.assertLess(defects[1], defects[0]/3)

    def test_refined_pillbox_physics(self):
        from superfish_ng.analytic import pillbox_tm_mode
        from superfish_ng.rf import quantities
        case = Case(((0., .075), (.08, .075)), nr=24, nz=24, modes=1, boundary_max_edge_m=.001)
        q = quantities(case, solve(case))
        exact = pillbox_tm_mode(.075, .08)
        for key in ('frequency_hz', 'r_over_q_accelerator_ohm', 'geometry_factor_ohm'):
            self.assertLess(abs(q[key]/exact[key]-1), .005)


if __name__ == '__main__':
    unittest.main()
