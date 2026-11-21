# SPDX-License-Identifier: Apache-2.0
"""Independent domain, size and Galerkin invariants for boundary remeshing."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import numpy as np

from superfish_ng.project import Project, parse_json
from superfish_ng.curved_remesh_generation import generate_curved_remesh_plan
from superfish_ng.curved_project_remesh import remesh_curved_project
from superfish_ng.curved_space import case_curved_space
from superfish_ng.mesh_input import mesh_from_dict
from superfish_ng.curved_marked_refinement import refine_marked_curved_space
from superfish_ng.curved_refinement import refine_curved_space
from superfish_ng.curved_same_domain_tracking import compare_quadratic_space_boundaries
from test_curved_project_remesh import remesh_fixture
from test_curved_selection_charts import symmetry

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / 'examples/curved_boundary_remesh'
sys.path.insert(0, str(ROOT / 'scripts'))


def fixture(name='nonaffine'):
    return (Project.load(EXAMPLES / f'{name}-project.json'),
            parse_json((EXAMPLES / f'{name}-settings.json').read_text()))


def space(project):
    return case_curved_space(project.case, mesh_from_dict(project.case, project.mesh_data))


def measurements(native):
    # Independent endpoint-chord measurements; do not call generation helpers.
    g = native.geometry
    triangles = g.points_rz_m[g.cell_nodes[:, :3]]
    u, v = triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0]
    areas = (u[:, 0]*v[:, 1]-u[:, 1]*v[:, 0])/2
    edges = np.unique(np.sort(g.cell_nodes[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2), axis=1), axis=0)
    ends = g.points_rz_m[edges]
    return areas, edges, ends, np.linalg.norm(ends[:, 1]-ends[:, 0], axis=1)


class CurvedBoundaryRemeshTests(unittest.TestCase):
    def test_examples_preserve_whole_boundary_green_and_known_field_integrals(self):
        from validate_large_curved_mesh_selection import boundary_moments
        from validate_curved_selection_transfer import moments
        from superfish_ng.curved_fem import assemble_curved
        for name, cells, boundary in (('rectangle', 128, 32), ('nonaffine', 84, 28)):
            source, settings = fixture(name)
            before, request = deepcopy(source.to_dict()), deepcopy(settings)
            with self.subTest(example=name), patch('superfish_ng.solver.solve', side_effect=AssertionError('unexpected solve')):
                plan = generate_curved_remesh_plan(source, settings)
                self.assertEqual(plan['schema_version'], 1)
                target = remesh_curved_project(source, plan)
                old, new = space(source), space(target)
                self.assertEqual((len(new.geometry.cell_nodes), len(new.geometry.boundary_nodes)), (cells, boundary))
                self.assertNotEqual(len(new.geometry.boundary_nodes), len(old.geometry.boundary_nodes))
                areas, _, _, lengths = measurements(new)
                self.assertGreater(float(areas.min()), 0)
                self.assertLessEqual(float(areas.max()), settings['max_chord_triangle_area_m2']*(1+1e-12))
                self.assertLessEqual(float(lengths.max()), settings['max_chord_edge_m']*(1+1e-12))
                report = compare_quadratic_space_boundaries(source.case, old, target.case, new)
                self.assertLessEqual(report['maximum_coefficient_distance_m'], report['roundoff_tolerance_m'])
                totals = [sum((moments(s.geometry.points_rz_m[c]) for c in s.geometry.cell_nodes), np.zeros(3)) for s in (old, new)]
                np.testing.assert_allclose(totals[1], totals[0], rtol=3e-12, atol=0)
                green = boundary_moments(new)
                np.testing.assert_allclose(totals[1][:2], np.abs(list(green.values())), rtol=3e-12, atol=0)
                _, mass = assemble_curved(new, quadrature_order=12)
                one = np.ones(mass.shape[0])
                self.assertLess(abs(float(one@mass@one)/totals[1][2]-1), 3e-12)
                a, b = source.case.to_dict(), target.case.to_dict()
                for raw in (a, b):
                    raw['mesh'].pop('curved_refinement_levels', None)
                    raw['mesh'].pop('curved_refinement_steps', None)
                self.assertEqual(a, b)
                self.assertEqual(source.to_dict(), before)
                self.assertEqual(settings, request)

    def test_original_case_global_boundary_and_corner_sizes_apply_to_final_edges(self):
        from superfish_ng.mesh_controls import ContourMeshControls
        source, settings = fixture('rectangle')
        source = replace(source, case=replace(source.case, contour_mesh=ContourMeshControls(.06, min_angle_deg=1),
                         boundary_max_edge_m=.04, corner_max_edge_m=.025, corner_radius_m=.03))
        settings = dict(settings, max_chord_edge_m=.2, max_chord_triangle_area_m2=.1)
        target = remesh_curved_project(source, generate_curved_remesh_plan(source, settings))
        native = space(target)
        _, edges, ends, lengths = measurements(native)
        self.assertLessEqual(float(lengths.max()), .06*(1+1e-12))
        boundary = {tuple(sorted(e[:2])) for e in native.geometry.boundary_nodes}
        corners = np.array([[0., 0.], [.1, 0.], [.1, .2], [0., .2]])
        for edge, end, length in zip(edges, ends, lengths):
            if tuple(edge) in boundary and not np.all(end[:, 0] == 0):
                self.assertLessEqual(length, .04*(1+1e-12))
            direction = end[1]-end[0]
            for corner in corners:
                fraction = min(1., max(0., float((corner-end[0])@direction)/length**2))
                if np.linalg.norm(end[0]+fraction*direction-corner) <= .03*(1+1e-12):
                    self.assertLessEqual(length, .025*(1+1e-12))

    def test_frozen_child_prolongations_preserve_parent_energy_and_mass(self):
        from superfish_ng.curved_fem import assemble_curved
        source, settings = fixture()
        plan = generate_curved_remesh_plan(source, settings)
        target = remesh_curved_project(source, plan)
        current = space(replace(target, case=replace(target.case, curved_refinement_steps=())))
        coarse = assemble_curved(current, quadrature_order=12)
        for step in target.case.curved_refinement_steps:
            refined = refine_marked_curved_space(current, list(step.marked_cells),
                         minimum_corner_angle_deg=step.minimum_corner_angle_deg, split_pattern=step.split_pattern)
            fine = assemble_curved(refined.space, quadrature_order=12)
            for a, b in zip(coarse, fine):
                self.assertLess(np.linalg.norm((refined.prolongation.T@b@refined.prolongation-a).data)/np.linalg.norm(a.data), 1e-10)
            current, coarse = refined.space, fine
        np.testing.assert_array_equal(current.geometry.points_rz_m, space(target).geometry.points_rz_m)

    def test_similarity_preserves_patterns_and_independent_geometric_scaling(self):
        from superfish_ng.curved_project_transform import transform_curved_project
        from validate_curved_selection_transfer import moments
        source, settings = fixture()
        large = transform_curved_project(source, dict(radial_scale=2., axial_scale=2., axial_shear=0.), rf_coordinates='axial')
        large = replace(large, case=replace(large.case, contour_mesh=replace(large.case.contour_mesh, max_edge_m=.16)))
        scaled = dict(settings, max_chord_edge_m=2*settings['max_chord_edge_m'],
                      max_chord_triangle_area_m2=4*settings['max_chord_triangle_area_m2'])
        plans = [generate_curved_remesh_plan(p, s) for p, s in ((source, settings), (large, scaled))]
        self.assertEqual(plans[0]['curved_refinement_steps'], plans[1]['curved_refinement_steps'])
        self.assertEqual(plans[0]['source_mesh']['triangles'], plans[1]['source_mesh']['triangles'])
        natives = [space(remesh_curved_project(p, plan)) for p, plan in zip((source, large), plans)]
        np.testing.assert_array_equal(natives[1].geometry.points_rz_m, 2*natives[0].geometry.points_rz_m)
        totals = [sum((moments(s.geometry.points_rz_m[c]) for c in s.geometry.cell_nodes), np.zeros(3)) for s in natives]
        np.testing.assert_allclose(totals[1]/totals[0], [4, 8, 32], rtol=3e-12, atol=0)

    def test_old_interior_numbering_and_automatic_source_do_not_control_seed(self):
        source, settings = fixture()
        _, other_plan, _ = remesh_fixture()
        other = remesh_curved_project(source, other_plan)
        raw = other.to_dict(); raw['case']['mesh'].pop('curved_refinement_steps')
        mesh = raw['mesh_data']; count = len(mesh['points'])
        mesh['points'].reverse(); mesh['triangles'].reverse(); mesh['boundary_edges'].reverse(); mesh['boundary_tags'].reverse()
        for key in ('triangles', 'boundary_edges'):
            mesh[key] = [[count-1-i for i in row] for row in mesh[key]]
        expected = generate_curved_remesh_plan(source, settings)
        self.assertEqual(generate_curved_remesh_plan(Project.from_dict(raw), settings), expected)
        auto = replace(source, mesh_data=None, case=replace(source.case, curved_refinement_steps=()))
        self.assertEqual(generate_curved_remesh_plan(auto, settings), expected)

    def test_old_finer_history_can_be_coarsened_below_its_cell_and_boundary_counts(self):
        source, settings = fixture('rectangle')
        source = replace(source, case=replace(source.case, curved_refinement_levels=4))
        settings = dict(settings, max_triangles=128, max_boundary_edges=32)
        old = space(source)
        target = remesh_curved_project(source, generate_curved_remesh_plan(source, settings))
        new = space(target)
        self.assertEqual((len(old.geometry.cell_nodes), len(old.geometry.boundary_nodes)), (512, 64))
        self.assertEqual((len(new.geometry.cell_nodes), len(new.geometry.boundary_nodes)), (128, 32))

    def test_explicit_history_precedes_auto_steps_and_is_frozen_for_replay(self):
        source, settings = fixture('rectangle')
        del settings['curved_refinement_levels']
        settings['curved_refinement_steps'] = [dict(kind='marked', marked_cells=[0], minimum_corner_angle_deg=1.), dict(kind='uniform')]
        plan = generate_curved_remesh_plan(source, settings)
        steps = plan['curved_refinement_steps']
        self.assertEqual(steps[0]['marked_cells'], [0])
        self.assertIn('split_pattern', steps[0])
        self.assertEqual(steps[1], dict(kind='uniform'))
        self.assertGreater(len(steps), 2)
        self.assertEqual(generate_curved_remesh_plan(source, dict(settings, curved_refinement_steps=deepcopy(steps))), plan)
        wrong = fixture()[0].to_dict()['case']['mesh']['curved_refinement_steps']
        with self.assertRaisesRegex(ValueError, 'topology'):
            generate_curved_remesh_plan(source, dict(settings, curved_refinement_steps=wrong))
        for field in ('max_triangles', 'max_boundary_edges'):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, field):
                generate_curved_remesh_plan(source, dict(settings, **{field: 4}))

    def test_boundary_and_uniform_budgets_are_checked_before_child_allocation(self):
        source, settings = fixture('rectangle')
        with patch('superfish_ng.curved_marked_refinement.refine_marked_curved_space', side_effect=AssertionError('allocated child')):
            with self.assertRaisesRegex(ValueError, 'max_boundary_edges'):
                generate_curved_remesh_plan(source, dict(settings, max_boundary_edges=4))
        with patch('superfish_ng.curved_refinement.refine_curved_space', side_effect=AssertionError('allocated uniform child')):
            with self.assertRaisesRegex(ValueError, 'max_boundary_edges'):
                generate_curved_remesh_plan(source, dict(settings, max_boundary_edges=4, curved_refinement_levels=1))
        for name in ('reject-root-coarsening', 'reject-size-budget'):
            source, _ = fixture()
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'max_boundary_edges'):
                generate_curved_remesh_plan(source, parse_json((EXAMPLES/f'{name}.json').read_text()))

    def test_round_quality_case_and_cell_limits_fail_without_partial_plans(self):
        source, settings = fixture('rectangle')
        for request, message in ((dict(settings, max_rounds=1), 'max_rounds'),
                                 (dict(settings, max_triangles=7), 'max_triangles'),
                                 (dict(settings, max_triangles=250001), 'original Case limit'),
                                 (dict(settings, minimum_corner_angle_deg=59., max_seed_rounds=1), 'max_seed_rounds')):
            with self.subTest(request=request), self.assertRaisesRegex(ValueError, message):
                generate_curved_remesh_plan(source, request)
        no_steps = generate_curved_remesh_plan(source, dict(settings, max_chord_edge_m=1., max_chord_triangle_area_m2=1.))
        self.assertEqual(no_steps['curved_refinement_levels'], 0)
        self.assertNotIn('curved_refinement_steps', no_steps)

    def test_te_sector_tags_reflection_and_tm_refusal_are_preserved(self):
        from superfish_ng.config import Case
        for side in ('z_min', 'z_max'):
            for tag in ('electric_symmetry', 'magnetic_symmetry'):
                source, settings = fixture('rectangle')
                source = symmetry(source, side, tag)
                raw = source.case.to_dict(); raw['model']['polarization'] = 'te'
                source = replace(source, case=Case.from_dict(raw))
                for reflected in (False, True):
                    with self.subTest(side=side, tag=tag, reflected=reflected):
                        project = replace(source, reflect_full=reflected)
                        target = remesh_curved_project(project, generate_curved_remesh_plan(project, settings))
                        self.assertEqual(target.reflect_full, reflected)
                        self.assertEqual((target.case.z_min, target.case.z_max), (project.case.z_min, project.case.z_max))
                        self.assertEqual(set(space(target).boundary_tags), {'axis', 'pec', tag})
        source, settings = fixture('rectangle')
        with self.assertRaisesRegex(ValueError, 'TM'):
            generate_curved_remesh_plan(symmetry(source, 'z_min', 'magnetic_symmetry'), settings)
