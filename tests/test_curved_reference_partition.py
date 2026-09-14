# SPDX-License-Identifier: Apache-2.0
"""Physical area/volume from independent charts of native quadratic spaces."""
import unittest
import numpy as np
from superfish_ng import Case
from superfish_ng.project import Project
from superfish_ng.conics import LineSegment
from superfish_ng.curved_contour import CurvedContour
from superfish_ng.fem import triangle_quadrature


def rectangle_project(alternate=False, scale=(1., 1.), levels=0):
    radius, length = .1*scale[0], .2*scale[1]
    vertices = ((0., 0.), (length, 0.), (length, radius), (0., radius))
    curves = tuple(LineSegment(a, b) for a, b in zip(vertices, vertices[1:]+vertices[:1]))
    case = Case((), curved_contour=CurvedContour(curves, ('axis', 'pec', 'pec', 'pec'), 1e-14),
                geometry_order=2, element_order=2, modes=1, quadrature_order=8,
                curved_refinement_levels=levels, curve_chord_tolerance_m=.001)
    mesh = dict(schema_version=1, length_unit='m', coordinate_order='rz', index_base=0,
                points=[[0., 0.], [radius, 0.], [radius, length], [0., length]],
                triangles=[[0, 1, 3], [1, 2, 3]] if alternate else [[0, 1, 2], [0, 2, 3]],
                boundary_edges=[[0, 3], [3, 2], [2, 1], [1, 0]], boundary_tags=['axis', 'pec', 'pec', 'pec'])
    return Project(case, mesh_data=mesh)


CHART = [[0, 0], [1, 0], [1, 1], [0, 1]]


class CurvedReferencePartitionTests(unittest.TestCase):
    def build(self, projects, charts=None):
        from superfish_ng.curved_reference_partition import build_curved_reference_partition
        return build_curved_reference_partition(*projects, reference_vertices=charts or [CHART, CHART],
                                                max_pair_tests=100000, max_triangles=1000)

    def test_independent_connectivity_and_history_integrate_physical_area_volume(self):
        projects = [rectangle_project(), rectangle_project(True, (1.25, .75), 1)]
        overlay = self.build(projects)
        self.assertEqual(overlay.report['final_cell_counts'], [2, 8])
        rule = list(triangle_quadrature(order=4))
        q = np.array([b[1:] for b, _ in rule]); weights = np.array([w for _, w in rule])
        for side, scale in enumerate([(1., 1.), (1.25, .75)]):
            values = overlay.evaluate(side, q)
            area = sum(float(x['determinant_m2'] @ weights) for x in values)
            volume = sum(float((2*np.pi*x['points_rz_m'][:, 0]*x['determinant_m2']) @ weights) for x in values)
            self.assertAlmostEqual(area, .02*np.prod(scale), places=14)
            self.assertAlmostEqual(volume, np.pi*(.1*scale[0])**2*.2*scale[1], places=14)

    def test_declared_boundary_shift_and_inverted_chart_fail(self):
        projects = [rectangle_project(), rectangle_project(True)]
        for chart in [[[1, 0], [2, 0], [2, 1], [1, 1]], [[0, 0], [0, 1], [1, 1], [1, 0]]]:
            with self.subTest(chart=chart), self.assertRaises(ValueError):
                self.build(projects, [CHART, chart])

    def test_version_five_tracks_independent_native_fields(self):
        from superfish_ng import solve
        from superfish_ng.piecewise_remesh_tracking import track_piecewise_remesh_modes
        from test_curved_piecewise_remesh_tracking import CONTROLS
        projects = [rectangle_project(levels=2), rectangle_project(True, levels=2)]
        solutions = [solve(p.case, mesh_data=p.mesh_data) for p in projects]
        documents = [dict(schema_version=5, source_mesh=p.mesh_data, reference_vertices=CHART,
                          boundary_pairing='declared_reference_polylines', max_pair_tests=10000)
                     for p in projects]
        result = track_piecewise_remesh_modes(*solutions, ['TM010'], **dict(CONTROLS, comparison_meshes=documents))
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['current_mode_ids'], ['TM010'])
        mapping = result['physical_mapping']
        self.assertEqual(mapping['common_reference_partition']['final_cell_counts'], [2, 2])
        self.assertEqual(mapping['solver_triangle_counts'], [32, 32])
        np.testing.assert_allclose(mapping['axisymmetric_volumes_m3'], [np.pi*.1**2*.2]*2, rtol=1e-13)

    def test_nonaffine_quadratic_maps_match_independent_boundary_integrals(self):
        from dataclasses import replace
        from test_curved_piecewise_remesh_tracking import curved_comparison_fixture
        from superfish_ng.curved_space import case_curved_space
        from superfish_ng.mesh_input import mesh_from_dict
        cases, documents = curved_comparison_fixture()
        projects = [Project(cases[0], mesh_data=documents[0]['source_mesh']),
                    Project(replace(cases[1], curved_refinement_levels=1), mesh_data=documents[1]['source_mesh'])]
        charts = [documents[0]['source_mesh']['points']]*2
        overlay = self.build(projects, charts)
        rule = list(triangle_quadrature(order=5))
        q = np.array([b[1:] for b, _ in rule]); weights = np.array([w for _, w in rule])
        t, w = np.polynomial.legendre.leggauss(4); t = (t+1)/2; w = w/2
        basis = np.column_stack((2*(t-.5)*(t-1), 2*t*(t-.5), 4*t*(1-t)))
        derivative = np.column_stack((4*t-3, 4*t-1, 4-8*t))
        for side, project in enumerate(projects):
            space = case_curved_space(project.case, mesh_from_dict(project.case, project.mesh_data))
            boundary_area = boundary_volume = 0.
            for edge in space.geometry.boundary_nodes:
                points = space.geometry.points_rz_m[edge]
                values, gradient = basis @ points, derivative @ points
                boundary_area += float(w @ (values[:, 0]*gradient[:, 1]-values[:, 1]*gradient[:, 0]))/2
                boundary_volume += float(w @ (np.pi*values[:, 0]**2*gradient[:, 1]))
            data = overlay.evaluate(side, q)
            area = sum(float(weights @ x['determinant_m2']) for x in data)
            volume = sum(float(weights @ (2*np.pi*x['points_rz_m'][:, 0]*x['determinant_m2'])) for x in data)
            self.assertAlmostEqual(area, abs(boundary_area), places=13)
            self.assertAlmostEqual(volume, abs(boundary_volume), places=13)

    def test_saved_pair_replay_and_chart_tampering(self):
        from copy import deepcopy
        from pathlib import Path
        import tempfile
        from superfish_ng import solve
        from superfish_ng.io import save_run
        from superfish_ng.saved_mode_tracking import build_saved_mode_tracking, replay_mode_tracking
        from test_curved_piecewise_remesh_tracking import CONTROLS
        projects = [rectangle_project(levels=1), rectangle_project(True, levels=1)]
        documents = [dict(schema_version=5, source_mesh=p.mesh_data, reference_vertices=CHART,
                          boundary_pairing='declared_reference_polylines', max_pair_tests=10000) for p in projects]
        with tempfile.TemporaryDirectory() as tmp:
            paths = [Path(tmp)/str(i) for i in range(2)]
            for p, path in zip(projects, paths):
                save_run(p.case, solve(p.case, mesh_data=p.mesh_data), path)
            original = {str(p): p.read_bytes() for folder in paths for p in folder.rglob('*') if p.is_file()}
            pair = build_saved_mode_tracking(dict(schema_version=1, previous_run=str(paths[0]), current_run=str(paths[1]),
                previous_ids=['TM010'], controls=dict(CONTROLS, comparison_meshes=documents)))
            self.assertEqual(replay_mode_tracking(pair), pair)
            changed = deepcopy(pair)
            changed['tracking']['physical_mapping']['common_reference_partition']['triangles'][0]['previous_cell'] += 1
            with self.assertRaises(ValueError):
                replay_mode_tracking(changed)
            self.assertEqual({p: Path(p).read_bytes() for p in original}, original)

    def test_version_five_strict_declarations(self):
        from copy import deepcopy
        from superfish_ng.piecewise_remesh_tracking import validate_comparison_meshes
        documents = [dict(schema_version=5, source_mesh=rectangle_project(side == 1).mesh_data,
                          reference_vertices=deepcopy(CHART), boundary_pairing='declared_reference_polylines',
                          max_pair_tests=10000) for side in (0, 1)]
        mutations = [lambda m: m.update(unrecognized=1), lambda m: m.update(schema_version=4),
                     lambda m: m.update(boundary_pairing='same_curve_fractions'),
                     lambda m: m.update(max_pair_tests=True), lambda m: m.update(max_pair_tests=9999),
                     lambda m: m.update(curved_refinement_levels=True),
                     lambda m: m.update(reference_vertices=None), lambda m: m['reference_vertices'].pop(),
                     lambda m: m['reference_vertices'][0].append(0),
                     lambda m: m['reference_vertices'][0].__setitem__(0, True),
                     lambda m: m['reference_vertices'][0].__setitem__(0, float('nan'))]
        for i, mutate in enumerate(mutations):
            changed = deepcopy(documents); mutate(changed[1])
            with self.subTest(mutation=i), self.assertRaises(ValueError):
                validate_comparison_meshes(changed)
        validate_comparison_meshes(documents)
