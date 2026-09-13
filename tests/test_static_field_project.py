# SPDX-License-Identifier: Apache-2.0
import contextlib
import copy
from dataclasses import replace
import importlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.electrostatic_reference import parallel_plate as axis_electric
from scripts.planar_electrostatic_reference import parallel_plate as planar_electric
from scripts.planar_magnetostatic_reference import layered_gap as planar_magnetic
from scripts.axis_magnetostatic_reference import cylinder_current as axis_magnetic
from scripts.off_axis_magnetostatic_reference import annular_current as off_axis_magnetic
from scripts.planar_recoil_reference import uniform_remanence as planar_recoil
from scripts.axis_recoil_reference import interface_patch as axis_recoil
from scripts.off_axis_recoil_reference import interface_patch as off_axis_recoil
from scripts.planar_bh_reference import uniform_field as planar_bh
from scripts.axis_bh_reference import uniform_field as axis_bh
from scripts.off_axis_bh_reference import radial_field as off_axis_bh
from superfish_ng import static_field_project as static
from superfish_ng.cli import main
from superfish_ng.config import Case
from superfish_ng.project import Project
from superfish_ng.planar import PlanarCase
from superfish_ng.planar_project import PlanarProject
from superfish_ng.coaxial import CoaxialCase
from superfish_ng.hphi_project import HphiProject
from superfish_ng.model import capabilities
from superfish_ng.nonlinear_magnetic import MagneticNewtonControls


def cases():
    for order in (1, 2):
        for factory in (axis_electric, planar_electric, planar_magnetic, axis_magnetic,
                        off_axis_magnetic, planar_recoil, axis_recoil, off_axis_recoil):
            yield factory(order=order, n=2)[0]
    for factory in (planar_bh, axis_bh, off_axis_bh):
        yield factory(n=2)[0]


def solve_and_result(case):
    module = importlib.import_module(type(case).__module__)
    name = module.__name__.rsplit('.', 1)[-1]
    solver = getattr(module, 'solve_axisymmetric_electrostatic' if name == 'electrostatic' else 'solve_' + name)
    saved = importlib.import_module(module.__name__ + '_saved')
    solution = solver(case)
    return solution, getattr(saved, name + '_result')(solution)


class StaticFieldProjectTests(unittest.TestCase):
    def test_all_eleven_case_formats_and_orders_roundtrip_without_display_unit_scaling(self):
        formats = set()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index, case in enumerate(cases()):
                original = case.to_dict(); formats.add(original['format'])
                for unit in ('m', 'mm'):
                    project = static.StaticFieldProject(case, unit)
                    path = root / f'{index}-{unit}.json'; project.save(path)
                    loaded = static.StaticFieldProject.load(path)
                    self.assertEqual(loaded, project)
                    self.assertEqual(loaded.case.to_dict(), original)
                    self.assertEqual(loaded.display_length_unit, unit)
                    self.assertEqual(static.load_static_document(project.dumps()).to_dict(), project.to_dict())
                    self.assertEqual(static.StaticFieldProject.from_dict(original).case.to_dict(), original)
                    changed = loaded.to_dict(); changed['case']['name'] = 'edited copy'
                    self.assertEqual(loaded.case.to_dict(), original)
                self.assertEqual(case.to_dict(), original)
        self.assertEqual(formats, {row['case_format'] for row in static.static_case_families()})
        self.assertEqual(len(formats), 11)

    def test_wrapped_inputs_produce_identical_real_fem_fields_and_all_static_quantities(self):
        for case in cases():
            original = case.to_dict()
            _, before = solve_and_result(case)
            project = static.load_static_document(static.StaticFieldProject(case, 'm').dumps())
            _, after = solve_and_result(project.case)
            self.assertEqual(before, after)
            self.assertEqual(project.case.to_dict(), original)

    def test_unknown_physics_fields_versions_types_and_duplicate_keys_reject(self):
        case = axis_electric(n=2)[0]; project = static.StaticFieldProject(case).to_dict()
        for key, value in (('project_version', True), ('project_version', 2), ('format', 'superfish_ng_project'),
                           ('display_length_unit', 'cm'), ('display_length_unit', ['m']), ('extra', 1)):
            changed = copy.deepcopy(project); changed[key] = value
            with self.assertRaises(ValueError): static.StaticFieldProject.from_dict(changed)
        for key, value in (('physics', 'rf_eigenmode'), ('format', []), ('schema_version', True), ('extra', 1)):
            changed = copy.deepcopy(project); changed['case'][key] = value
            with self.assertRaises(ValueError): static.StaticFieldProject.from_dict(changed)
        changed = copy.deepcopy(project); changed['case']['partition']['extra'] = 1
        with self.assertRaises(ValueError): static.StaticFieldProject.from_dict(changed)
        for text in ('{"format":"one","format":"two"}', json.dumps(project).replace('"project_version": 1', '"project_version": 1, "project_version": 1')):
            with self.assertRaisesRegex(ValueError, 'duplicate'): static.load_static_document(text)
        for value in (None, [], 1, True):
            with self.assertRaises(ValueError): static.StaticFieldProject.from_dict(value)

    def test_bh_initial_coefficients_iteration_controls_and_material_provenance_are_preserved(self):
        for factory, initial, field in ((planar_bh, 'initial_az_relative_to_reference_wb_per_m', 'az_relative_to_reference_wb_per_m'),
                                        (axis_bh, 'initial_aphi_over_r_t', 'aphi_over_r_t'),
                                        (off_axis_bh, 'initial_psi_relative_to_reference_wb', 'psi_relative_to_reference_wb')):
            case = factory(n=2)[0]; solution, _ = solve_and_result(case)
            seeded = replace(case, controls=MagneticNewtonControls(max_iterations=1), **{initial:getattr(solution, field).tolist()})
            original = seeded.to_dict()
            project = static.load_static_document(static.StaticFieldProject(seeded, 'm').dumps())
            self.assertEqual(project.case.to_dict(), original)
            self.assertEqual(project.case.controls.max_iterations, 1)
            self.assertEqual(getattr(project.case, initial), getattr(seeded, initial))
            self.assertEqual(project.case.partition.to_dict(), seeded.partition.to_dict())

    def test_exclusive_complete_publication_and_changed_project_leave_no_partial_output(self):
        project = static.StaticFieldProject(planar_recoil(n=2)[0])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); target = root / 'project.json'; project.save(target); before = target.read_bytes()
            with self.assertRaises(FileExistsError): project.save(target)
            self.assertEqual(target.read_bytes(), before)
            with patch.object(static.os, 'link', side_effect=OSError('interrupted publication')):
                with self.assertRaises(OSError): project.save(root / 'partial.json')
            self.assertFalse((root / 'partial.json').exists()); self.assertFalse(list(root.glob('.static-project-*')))
            original = static.os.fsync
            def changed(descriptor):
                original(descriptor); object.__setattr__(project, 'display_length_unit', 'm')
            with patch.object(static.os, 'fsync', side_effect=changed):
                with self.assertRaisesRegex(ValueError, 'changed during'): project.save(root / 'changed.json')
            self.assertFalse((root / 'changed.json').exists())
            self.assertFalse(list(root.glob('.static-project-*')))

    def test_cli_matches_project_bytes_and_keeps_existing_rf_projects_separate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index, case in enumerate(cases()):
                source = root / f'{index}-case.json'; source.write_text(json.dumps(case.to_dict()))
                before = source.read_bytes()
                for unit in ('m', 'mm'):
                    output = root / f'{index}-{unit}.json'; stdout, stderr = io.StringIO(), io.StringIO()
                    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                        code = main(['normalize-static-project', str(source), '--out', str(output), '--display-length-unit', unit])
                    self.assertEqual(code, 0, stderr.getvalue())
                    expected = static.StaticFieldProject(case, unit).dumps()
                    self.assertEqual(stdout.getvalue(), expected); self.assertEqual(output.read_bytes(), expected.encode())
                self.assertEqual(source.read_bytes(), before)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(['normalize-static-project', str(source), '--out', str(output)]), 2)
            projects = [Project(Case(profile=((0., .1), (.12, .1)), nr=2, nz=2, modes=1)),
                        PlanarProject(PlanarCase(.1, .2, nx=2, ny=2, modes=1)),
                        HphiProject(CoaxialCase(.025, .05, .12, nr=2, nz=2, modes=1))]
            for project in projects:
                self.assertEqual(type(project).from_dict(project.to_dict()).to_dict(), project.to_dict())
                with self.assertRaises(ValueError): static.StaticFieldProject.from_dict(project.to_dict())
                with self.assertRaises(ValueError): static.StaticFieldProject(project.case)
            inventory = capabilities()['static_field_project']
            self.assertEqual(len(inventory['case_families']), 11)
            self.assertEqual(inventory['display_length_units'], ['m', 'mm'])
            self.assertFalse(inventory['solve']); self.assertFalse(inventory['gui'])


if __name__ == '__main__':
    unittest.main()
