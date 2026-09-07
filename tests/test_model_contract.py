# SPDX-License-Identifier: Apache-2.0
"""Physics declarations must neither change a TM solve nor lose their meaning."""
import contextlib
import copy
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from superfish_ng import Case, solve
from superfish_ng.cli import main
from superfish_ng.io import save_run
from superfish_ng.project import Project
from superfish_ng.rf import quantities
from superfish_ng.saved import read_solution


def declared(case):
    data = case.to_dict()
    data.update(schema_version=3, model={
        'physics': 'rf_eigenmode', 'coordinates': 'axisymmetric',
        'polarization': 'tm', 'azimuthal_index': 0,
        'materials': [{'id': 'empty_space', 'type': 'vacuum'}],
        'regions': [{'id': 'domain', 'material': 'empty_space', 'domain': 'interior'}],
    })
    return data


class ModelContractTests(unittest.TestCase):
    def test_legacy_hashes_and_example_migration(self):
        from superfish_ng.model import upgrade_case
        cases = [Case(((0., .1), (.2, .1))),
                 Case(((0., .1), (.2, .1)), z_min='magnetic_symmetry', triangulation='crossed')]
        hashes = ['5f51598800c715c138ef8069fa213353ba0089249ed3feadb5088a897967228b',
                  'de9b5bf3050a72e82382e9af0495b986661b38face1652ac4f0467363f56e3f2']
        for case, digest in zip(cases, hashes):
            canonical = json.dumps(case.to_dict(), sort_keys=True, separators=(',', ':'), allow_nan=False)
            self.assertEqual(hashlib.sha256(canonical.encode()).hexdigest(), digest)
        for path in Path('examples').glob('*.json'):
            with self.subTest(path=path):
                old = Case.load(path)
                new = Case.from_dict(upgrade_case(old.to_dict()))
                self.assertEqual(replace(new, model=None), old)
                self.assertEqual(Case.from_dict(new.to_dict()), new)
                self.assertEqual(upgrade_case(new.to_dict()), new.to_dict())

    def test_same_fem_and_rf_with_explicit_model(self):
        for boundary in ['pec', 'electric_symmetry', 'magnetic_symmetry']:
            old = Case(((0., .1), (.2, .1)), nr=7, nz=8, modes=2, z_min=boundary)
            new = Case.from_dict(declared(old))
            a, b = solve(old), solve(new)
            np.testing.assert_array_equal(a.frequencies_hz, b.frequencies_hz)
            np.testing.assert_array_equal(a.u, b.u)
            for mode in range(old.modes):
                self.assertEqual(quantities(old, a, mode), quantities(new, b, mode))
            with tempfile.TemporaryDirectory() as tmp:
                save_run(new, b, Path(tmp)/'run')
                saved = read_solution(Path(tmp)/'run')
                self.assertEqual(saved.case, new)
                np.testing.assert_array_equal(saved.u, a.u)

    def test_unsupported_physics_and_nested_fields_rejected(self):
        base = declared(Case(((0., .1), (.2, .1))))
        for key, value in [('physics', 'electrostatic'), ('physics', 'unknown'),
                           ('coordinates', 'planar'), ('polarization', 'te'),
                           ('azimuthal_index', 1), ('azimuthal_index', True),
                           ('azimuthal_index', 0.0), ('future_option', 0)]:
            data = copy.deepcopy(base)
            data['model'][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                Case.from_dict(data)
        for mutation in [
            lambda m: m['materials'][0].update(type='dielectric'),
            lambda m: m['materials'][0].update(epsilon_r=4),
            lambda m: m['regions'][0].update(material='missing'),
            lambda m: m['regions'][0].update(domain='inner_conductor'),
            lambda m: m['regions'][0].update(source_current_a=1),
            lambda m: m['regions'].append(copy.deepcopy(m['regions'][0])),
            lambda m: m['materials'].clear(),
            lambda m: m.pop('physics'),
        ]:
            data = copy.deepcopy(base)
            mutation(data['model'])
            with self.assertRaises(ValueError):
                Case.from_dict(data)
        for version in [1, 2]:
            with self.assertRaisesRegex(ValueError, 'model'):
                Case.from_dict(dict(base, schema_version=version))
        missing = copy.deepcopy(base)
        del missing['model']
        with self.assertRaisesRegex(ValueError, 'model'):
            Case.from_dict(missing)

    def test_model_is_immutable_and_python_api_is_strict(self):
        from superfish_ng.model import Model
        from dataclasses import FrozenInstanceError
        case = Case.from_dict(declared(Case(((0., .1), (.2, .1)))))
        data = case.model.to_dict()
        data['materials'][0]['type'] = 'dielectric'
        self.assertEqual(case.model.to_dict()['materials'][0]['type'], 'vacuum')
        with self.assertRaises(FrozenInstanceError):
            case.model.polarization = 'te'
        with self.assertRaises(ValueError):
            Model(polarization='te')
        with self.assertRaises(ValueError):
            replace(case, model={})

    def test_project_study_reflection_and_external_mesh_preserve_model(self):
        from superfish_ng.mesh_input import mesh_to_dict
        from superfish_ng.studies import Study
        from superfish_ng.symmetry import reflect_solution
        base = Case.from_dict(declared(Case(((0., .1), (.1, .1)), nr=5, nz=6,
                                          modes=1, z_min='electric_symmetry')))
        sections = [{'geometry': {'type': 'pillbox', 'radius_m': .1, 'length_m': .1}, 'count': 1}]
        project = Project.from_sections(base, sections)
        self.assertEqual(Project.from_dict(project.to_dict()).case.model, base.model)
        study = Study(project, 'sweep', '/sections/0/count', [1, 2])
        for result in study.projects():
            self.assertEqual(result.case.model, base.model)
        solution = solve(base)
        external = solve(base, mesh_data=mesh_to_dict(solution.mesh))
        full, reflected = reflect_solution(base, external)
        self.assertEqual(full.model, base.model)
        with tempfile.TemporaryDirectory() as tmp:
            save_run(full, reflected, Path(tmp)/'run')
            self.assertEqual(read_solution(Path(tmp)/'run').case.model, base.model)

    def test_cli_migration_solve_capabilities_and_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source, migrated, out = folder/'old.json', folder/'v3.json', folder/'run'
            old = Case(((0., .1), (.2, .1)), nr=4, nz=5, modes=1)
            source.write_text(json.dumps(old.to_dict()))
            original = source.read_bytes()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(['migrate-case', str(source), '--out', str(migrated)]), 0)
                self.assertEqual(main(['migrate-case', str(source), '--out', str(migrated)]), 2)
                self.assertEqual(main(['solve', str(migrated), '--out', str(out)]), 0)
                invalid = declared(old)
                invalid['model']['polarization'] = 'te'
                migrated.write_text(json.dumps(invalid))
                self.assertEqual(main(['solve', str(migrated), '--out', str(folder/'bad')]), 2)
            self.assertEqual(source.read_bytes(), original)
            self.assertFalse((folder/'bad').exists())
            self.assertIsNotNone(read_solution(out).case.model)
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                self.assertEqual(main(['capabilities']), 0)
            capabilities = json.loads(captured.getvalue())
            self.assertEqual(capabilities['supported_models'][0]['polarization'], 'tm')
            self.assertEqual(capabilities['case_schema_versions'], [1, 2, 3])
            self.assertEqual(capabilities['element_orders'], [1, 2])
            self.assertEqual(capabilities['default_element_order'], 1)

    def test_duplicate_model_keys_fail_at_file_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'case.json'
            text = json.dumps(declared(Case(((0., .1), (.2, .1)))))
            path.write_text(text.replace('"polarization": "tm"', '"polarization": "tm", "polarization": "te"'))
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                Case.load(path)

    def test_migration_and_region_names_do_not_change_refinement_identity(self):
        from superfish_ng.studies import compare_refinement
        old = Case(((0., .1), (.2, .1)), nr=7, nz=8, modes=1)
        new = Case.from_dict(declared(old))
        with tempfile.TemporaryDirectory() as tmp:
            first, second = Path(tmp)/'first', Path(tmp)/'second'
            save_run(old, solve(old), first)
            save_run(new, solve(new), second)
            self.assertEqual(compare_refinement(first, second)['status'], 'PASS')
