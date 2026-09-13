# SPDX-License-Identifier: Apache-2.0
import contextlib
import copy
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from test_static_field_project import cases, solve_and_result, axis_electric, planar_electric, axis_magnetic, planar_bh, axis_bh, off_axis_bh
from superfish_ng import static_field_study as static
from superfish_ng.static_field_project import StaticFieldProject
from superfish_ng.cli import main
from superfish_ng.model import capabilities
from superfish_ng.nonlinear_magnetic import MagneticNewtonControls


def centers(case):
    mesh = case.partition.mesh
    points = mesh.points_xy_m if 'planar' in case.to_dict()['format'] else mesh.points_rz_m
    return points[mesh.triangles].mean(axis=1)


def expected_case(case, parameter, value):
    data = copy.deepcopy(case.to_dict())
    if parameter == 'uniform_scale':
        def coordinates(item):
            if isinstance(item, dict):
                for name, child in item.items():
                    if name in ('polygon_xy_m', 'points_xy_m', 'outer_rz_m', 'points_rz_m'):
                        item[name] = (np.asarray(child) * value).tolist()
                    elif name == 'holes_rz_m':
                        item[name] = [(np.asarray(hole) * value).tolist() for hole in child]
                    else: coordinates(child)
        coordinates(data['partition'])
    else:
        for name in ('charge_density_c_per_m3', 'current_density_z_a_per_m2', 'current_density_phi_a_per_m2'):
            if name in data: data[name] = {region: density * value for region, density in data[name].items()}
        for boundary in data['boundaries']:
            for name in set(boundary) - {'id', 'kind', 'edge_indices'}: boundary[name] *= value
        for material in data['partition']['materials']:
            if 'remanent_b_local_t' in material:
                material['remanent_b_local_t'] = [component * value for component in material['remanent_b_local_t']]
    return data


class StaticFieldStudyTests(unittest.TestCase):
    def test_linear_excitation_scales_original_fields_and_quadratic_integrals(self):
        checked = 0
        for case in cases():
            if '_bh_case' in case.to_dict()['format']: continue
            source, result = solve_and_result(case); probe = source.probe_at(centers(case))['fields']
            for factor, project in zip((-2., 0., 2.), static.StaticFieldStudy(StaticFieldProject(case), 'excitation_scale', (-2., 0., 2.)).projects()):
                solution, current = solve_and_result(project.case)
                actual = solution.probe_at(centers(project.case))['fields']
                self.assertEqual(set(actual), set(probe))
                for name, values in probe.items():
                    scale = max(np.max(np.abs(values)), 1e-30)
                    np.testing.assert_allclose(actual[name], np.asarray(values) * factor, rtol=2e-11, atol=2e-12 * scale, err_msg=type(case).__name__ + '/' + name)
                quantities = result['quantities']
                names = [name for name in quantities if name in ('energy_j', 'energy_j_per_m', 'b_quadratic_j', 'b_quadratic_j_per_m', 'remanence_coupling_j', 'remanence_coupling_j_per_m', 'constitutive_potential_b0_j', 'constitutive_potential_b0_j_per_m', 'constitutive_potential_h0_j', 'constitutive_potential_h0_j_per_m')]
                self.assertTrue(names)
                for name in names:
                    expected = quantities[name] * factor**2
                    self.assertAlmostEqual(current['quantities'][name], expected, delta=2e-11 * max(abs(expected), abs(quantities[name]), 1e-30))
                checked += 1
        self.assertEqual(checked, 48)

    def test_fixed_voltage_geometry_scaling_preserves_potential_and_dimension_laws(self):
        for order in (1, 2):
            for factory, energy, exponent in ((axis_electric, 'energy_j', 1), (planar_electric, 'energy_j_per_m', 0)):
                case, analytic = factory(order=order, n=2); solution, original = solve_and_result(case)
                before = solution.probe_at(centers(case))['fields']
                axes = 'xy' if factory is planar_electric else 'rz'
                groups = [('potential_V',), tuple('E' + axis + '_V_per_m' for axis in axes), tuple('D' + axis + '_C_per_m2' for axis in axes)]
                exact = analytic['fields'](centers(case))
                self.assertEqual(set(before), {name for group in groups for name in group})
                for factor, project in zip((.5, 2.), static.StaticFieldStudy(StaticFieldProject(case), 'uniform_scale', (.5, 2.)).projects()):
                    current, result = solve_and_result(project.case); after = current.probe_at(centers(project.case))['fields']
                    for group, analytical in zip(groups, exact):
                        values = np.column_stack([before[name] for name in group])
                        actual = np.column_stack([after[name] for name in group])
                        analytical = np.asarray(analytical).reshape(values.shape)
                        # A vector has one physical scale, including its analytically zero component.
                        scale = max(np.max(np.abs(analytical)), 1e-30)
                        multiplier = 1. if group[0] == 'potential_V' else 1. / factor
                        np.testing.assert_allclose(values, analytical, rtol=2e-11, atol=2e-12 * scale)
                        np.testing.assert_allclose(actual, analytical * multiplier, rtol=2e-11, atol=2e-12 * scale)
                        np.testing.assert_allclose(actual, values * multiplier, rtol=2e-11, atol=2e-12 * scale)
                    self.assertAlmostEqual(result['quantities'][energy], original['quantities'][energy] * factor**exponent, delta=2e-11 * original['quantities'][energy])

    def test_all_formats_complete_derived_cases_and_owned_roundtrips(self):
        formats = set()
        for case in cases():
            formats.add(case.to_dict()['format']); original = case.to_dict()
            for parameter, values in (('uniform_scale', (.5, 2.)), ('excitation_scale', (-2., 0., 2.))):
                for unit in ('m', 'mm'):
                    study = static.StaticFieldStudy(StaticFieldProject(case, unit), parameter, values)
                    self.assertEqual(static.load_static_study_document(study.dumps()), study)
                    for value, project in zip(values, study.projects()):
                        self.assertEqual(project.case.to_dict(), expected_case(case, parameter, value))
                        self.assertEqual(project.display_length_unit, unit)
                    changed = study.to_dict(); changed['project']['case']['name'] = 'external mutation'
                    self.assertEqual(study.project.case.to_dict(), original)
            self.assertEqual(case.to_dict(), original)
        self.assertEqual(len(formats), 11)
        # The axis-connected prescribed Aphi/r boundary is distinct from fixed Az and psi.
        case = axis_magnetic(n=2)[0]; boundary_type = type(case.boundaries[0])
        edges = sorted(edge for b in case.boundaries if b.kind != 'axis_regularity' for edge in b.edge_indices)
        fixed = replace(case, boundaries=(case.boundaries[0], boundary_type('fixed', 'fixed_aphi_over_r', edges, .125)))
        for value, project in zip((-2., 0.), static.StaticFieldStudy(StaticFieldProject(fixed), 'excitation_scale', (-2., 0.)).projects()):
            self.assertEqual(project.case.to_dict(), expected_case(fixed, 'excitation_scale', value))

    def test_bh_initial_values_controls_and_provenance_are_not_adjusted(self):
        for factory, initial, field in ((planar_bh, 'initial_az_relative_to_reference_wb_per_m', 'az_relative_to_reference_wb_per_m'), (axis_bh, 'initial_aphi_over_r_t', 'aphi_over_r_t'), (off_axis_bh, 'initial_psi_relative_to_reference_wb', 'psi_relative_to_reference_wb')):
            case = factory(n=2)[0]; solution, _ = solve_and_result(case)
            seeded = replace(case, controls=MagneticNewtonControls(max_iterations=1), **{initial: getattr(solution, field).tolist()})
            for project in static.StaticFieldStudy(StaticFieldProject(seeded), 'uniform_scale', (.5, 2.)).projects():
                self.assertEqual(getattr(project.case, initial), getattr(seeded, initial))
                self.assertEqual(project.case.controls, seeded.controls)
                self.assertEqual(project.case.partition.to_dict()['materials'], seeded.partition.to_dict()['materials'])
            if factory is off_axis_bh:
                with self.assertRaisesRegex(ValueError, 'initial|boundary'):
                    static.StaticFieldStudy(StaticFieldProject(seeded), 'excitation_scale', (1., 2.))

    def test_holes_and_nonzero_volume_sources_keep_topology_and_excitation_laws(self):
        from scripts.electrostatic_reference import manufactured_quadratic
        from scripts.off_axis_magnetostatic_reference import annular_current
        fixtures = [manufactured_quadratic(n=1, holes=2, axis=axis, amplitude=100., offset=-.125)[0] for axis in (False, True)]
        fixtures += [factory(n=1, holes=2, current_density=-2e5, outer_h=300., shift=-.25)[0] for factory in (axis_magnetic, annular_current)]
        for case in fixtures:
            original, _ = solve_and_result(case); fields = original.probe_at(centers(case))['fields']
            for parameter, values in (('uniform_scale', (.5, 2.)), ('excitation_scale', (-2., 0., 2.))):
                for value, project in zip(values, static.StaticFieldStudy(StaticFieldProject(case), parameter, values).projects()):
                    self.assertEqual(project.case.to_dict(), expected_case(case, parameter, value))
                    if parameter == 'excitation_scale':
                        current, _ = solve_and_result(project.case)
                        for name, data in fields.items():
                            np.testing.assert_allclose(current.probe_at(centers(project.case))['fields'][name], np.asarray(data) * value, rtol=2e-11, atol=2e-12 * max(np.max(np.abs(data)), 1e-30))

    def test_strict_values_unknown_fields_and_invalid_derived_cases_reject(self):
        project = StaticFieldProject(axis_electric(n=2)[0])
        for parameter, values in [('uniform_scale', (-1, 2)), ('uniform_scale', (0, 1)), ('excitation_scale', (1, True)), ('excitation_scale', (1, float('inf'))), ('excitation_scale', (1, float('nan'))), ('excitation_scale', (1, 10**1000)), ('unknown', (1, 2)), ([], (1, 2)), ('uniform_scale', (1,)), ('uniform_scale', '12')]:
            with self.assertRaises(ValueError): static.StaticFieldStudy(project, parameter, values)
        source = static.StaticFieldStudy(project, 'excitation_scale', (-2, 0, 2)).to_dict()
        for key, value in [('format', 'superfish_ng_study'), ('study_version', True), ('study_version', 2), ('kind', 'tracking'), ('values', None), ('extra', 1)]:
            changed = copy.deepcopy(source); changed[key] = value
            with self.assertRaises(ValueError): static.StaticFieldStudy.from_dict(changed)
        with self.assertRaisesRegex(ValueError, 'duplicate'): static.load_static_study_document(json.dumps(source).replace('"study_version": 1', '"study_version": 1, "study_version": 1'))
        for value in (None, [], 1, True, project.to_dict()):
            with self.assertRaises(ValueError): static.StaticFieldStudy.from_dict(value)
        with self.assertRaises(ValueError): static.StaticFieldStudy(project, 'uniform_scale', (1., 1e308))

    def test_exclusive_publication_cli_bytes_and_capabilities(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index, case in enumerate(cases()):
                study = static.StaticFieldStudy(StaticFieldProject(case), 'excitation_scale', (-2., 0., 2.))
                source = root / f'{index}.json'; study.save(source); self.assertEqual(static.StaticFieldStudy.load(source), study)
                with self.assertRaises(FileExistsError): study.save(source)
                target = root / f'{index}-cli.json'; stdout, stderr = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr): status = main(['normalize-static-study', str(source), '--out', str(target)])
                self.assertEqual(status, 0, stderr.getvalue()); self.assertEqual(target.read_bytes(), source.read_bytes()); self.assertEqual(stdout.getvalue(), study.dumps())
            before = source.read_bytes()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()): self.assertEqual(main(['normalize-static-study', str(source), '--out', str(source)]), 2)
            self.assertEqual(source.read_bytes(), before)
            with patch.object(static.os, 'link', side_effect=OSError('interrupted publication')):
                with self.assertRaises(OSError): study.save(root / 'partial.json')
            self.assertFalse((root / 'partial.json').exists()); self.assertFalse(list(root.glob('.static-study-*')))
            original = static.os.fsync
            def changed(descriptor):
                original(descriptor); object.__setattr__(study, 'values', (1., 2.))
            with patch.object(static.os, 'fsync', side_effect=changed):
                with self.assertRaisesRegex(ValueError, 'changed during'): study.save(root / 'changed.json')
            self.assertFalse((root / 'changed.json').exists())
        inventory = capabilities()['static_field_study']; self.assertEqual(inventory['parameters'], ['uniform_scale', 'excitation_scale']); self.assertFalse(inventory['gui']); self.assertEqual(inventory['commands'], ['normalize-static-study'])
