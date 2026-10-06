# SPDX-License-Identifier: Apache-2.0
"""Curve-native replay must preserve the original physical solution."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from superfish_ng.planar_curved import PlanarCurvedCase
from superfish_ng.planar_curved_solver import solve_planar_curved
from test_planar_curved import curved_ellipse


class PlanarCurvedSavedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        domain = curved_ellipse(16)
        cls.solutions = {pol: solve_planar_curved(PlanarCurvedCase(domain, pol, modes=4))
                         for pol in ('te', 'tm')}

    def rehash(self, folder, name):
        path = folder/'manifest.json'
        data = json.loads(path.read_text())
        data['files'][name] = hashlib.sha256((folder/name).read_bytes()).hexdigest()
        path.write_text(json.dumps(data))

    def assert_bytes_equal(self, first, second):
        self.assertEqual(first.dtype, second.dtype)
        self.assertEqual(first.shape, second.shape)
        self.assertEqual(first.tobytes(), second.tobytes())

    def test_full_physical_roundtrip(self):
        from superfish_ng.planar_curved_saved import (save_planar_curved_run,
            read_planar_curved_run, planar_curved_result)
        cells = [0, 3, 7, 15]
        refs = [[.2, .3], [.3, .1], [.1, .4], [.3, .3]]
        with tempfile.TemporaryDirectory() as temporary:
            for pol, original in self.solutions.items():
                with self.subTest(polarization=pol):
                    folder = Path(temporary)/pol
                    result = save_planar_curved_run(original.case, original, folder)
                    before = {p.name: p.read_bytes() for p in folder.iterdir()}
                    restored = read_planar_curved_run(folder)
                    self.assertEqual(result, planar_curved_result(original))
                    self.assertEqual(result, planar_curved_result(restored))
                    self.assertEqual(original.case, restored.case)
                    for name in ('coefficients', 'frequencies_hz', 'free_dofs'):
                        self.assert_bytes_equal(getattr(original, name), getattr(restored, name))
                    for name in ('points_xy_m', 'cell_nodes', 'boundary_nodes',
                                 'boundary_cells', 'boundary_local_edges', 'free_dofs'):
                        self.assert_bytes_equal(getattr(original.space, name), getattr(restored.space, name))
                    first = original.all_fields_at_reference(cells, refs)
                    second = restored.all_fields_at_reference(cells, refs)
                    self.assertEqual(len(first), 12)
                    for name in first:
                        self.assert_bytes_equal(first[name], second[name])
                    self.assertEqual(before, {p.name: p.read_bytes() for p in folder.iterdir()})
                    self.assertEqual(json.loads((folder/'manifest.json').read_text())['schema_version'], 3)
                    self.assertEqual(set(before), {'case.json', 'mesh.npz', 'fields.npz', 'results.json', 'manifest.json'})
                    self.assertFalse(restored.coefficients.flags.writeable)
                    for mode in result['modes']:
                        for name in ('r_over_q_accelerator_ohm', 'r_over_q_circuit_ohm', 'vacc_v', 'eacc_v_per_m'):
                            self.assertIsNone(mode[name])
                        self.assertTrue(mode['accelerating_quantities_reason'])
                    with self.assertRaises(FileExistsError):
                        save_planar_curved_run(original.case, original, folder)

    def test_signed_zero_coefficients_are_not_recreated(self):
        from superfish_ng.planar_curved_saved import save_planar_curved_run, read_planar_curved_run
        original = self.solutions['tm']
        coefficients = original.coefficients.copy()
        coefficients[coefficients == 0.] = -0.
        solution = replace(original, coefficients=coefficients)
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)/'native'
            save_planar_curved_run(solution.case, solution, folder)
            restored = read_planar_curved_run(folder)
            self.assert_bytes_equal(coefficients, restored.coefficients)
            self.assertTrue(np.signbit(restored.coefficients[coefficients == 0.]).all())

    def test_rehashed_geometry_mesh_rf_and_schema_changes_are_rejected(self):
        from superfish_ng.planar_curved_saved import save_planar_curved_run, read_planar_curved_run
        original = self.solutions['tm']
        with tempfile.TemporaryDirectory() as temporary:
            for kind in ('geometry', 'mesh', 'rf', 'rf_reason', 'schema'):
                folder = Path(temporary)/kind
                save_planar_curved_run(original.case, original, folder)
                name = 'mesh.npz' if kind == 'mesh' else 'case.json' if kind == 'geometry' else 'manifest.json' if kind == 'schema' else 'results.json'
                if kind == 'mesh':
                    with np.load(folder/name, allow_pickle=False) as archive:
                        arrays = {key: archive[key] for key in archive.files}
                    arrays['points_xy_m'][0, 0] += .0001
                    np.savez_compressed(folder/name, **arrays)
                else:
                    data = json.loads((folder/name).read_text())
                    if kind == 'geometry':
                        # A valid translated curved domain, not malformed input.
                        for point in data['geometry']['domain']['points_xy_m']:
                            point[0] += .001
                    elif kind == 'rf':
                        data['modes'][0]['wall_loss_w_per_m'] *= 1.01
                    elif kind == 'rf_reason':
                        data['modes'][0]['accelerating_quantities_reason'] = ''
                    else:
                        data['schema_version'] = 2
                    (folder/name).write_text(json.dumps(data))
                if name != 'manifest.json':
                    self.rehash(folder, name)
                with self.subTest(kind=kind), self.assertRaises(ValueError):
                    read_planar_curved_run(folder)

    def test_rehashed_physical_counterexamples_are_rejected(self):
        from superfish_ng.planar_curved_saved import save_planar_curved_run, read_planar_curved_run
        with tempfile.TemporaryDirectory() as temporary:
            for kind, pol, message in (
                    ('normalization', 'te', 'normalization/orthogonality'),
                    ('pec', 'tm', 'PEC coefficients'),
                    ('frequency', 'tm', 'FEM residual'),
                    ('lowest_band', 'tm', 'lowest positive modes'),
                    ('dtype', 'te', 'float64')):
                original = self.solutions[pol]
                folder = Path(temporary)/kind
                save_planar_curved_run(original.case, original, folder)
                coefficients = original.coefficients.copy()
                frequencies = original.frequencies_hz.copy()
                if kind == 'normalization':
                    coefficients *= 2
                elif kind == 'pec':
                    coefficients[original.space.boundary_nodes[0, 0], 0] = 1.
                elif kind == 'frequency':
                    frequencies[0] *= 1.01
                elif kind == 'lowest_band':
                    coefficients, frequencies = coefficients[:, 1:], frequencies[1:]
                    data = original.case.to_dict()
                    data['modes'] = 3
                    (folder/'case.json').write_text(json.dumps(data))
                    self.rehash(folder, 'case.json')
                else:
                    coefficients = coefficients.astype(np.float32)
                np.savez_compressed(folder/'fields.npz', coefficients=coefficients, frequencies_hz=frequencies)
                self.rehash(folder, 'fields.npz')
                with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, message):
                    read_planar_curved_run(folder)

    def test_invalid_save_creates_no_output(self):
        from superfish_ng.planar_curved_saved import save_planar_curved_run
        original = self.solutions['te']
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)/'invalid'
            bad = replace(original, coefficients=original.coefficients*2)
            with self.assertRaisesRegex(ValueError, 'normalization/orthogonality'):
                save_planar_curved_run(original.case, bad, folder)
            self.assertFalse(folder.exists())

    def test_source_change_during_replay_is_rejected(self):
        import superfish_ng.planar_curved_saved as saved
        original = self.solutions['te']
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)/'native'
            saved.save_planar_curved_run(original.case, original, folder)
            restore = saved.restore_planar_curved_solution

            def changed(*args, **kwargs):
                solution = restore(*args, **kwargs)
                with (folder/'case.json').open('a') as stream:
                    stream.write('\n')
                return solution

            with patch.object(saved, 'restore_planar_curved_solution', changed):
                with self.assertRaisesRegex(ValueError, 'changed during verification'):
                    saved.read_planar_curved_run(folder)

    def test_completion_regular_files_and_archive_integrity(self):
        from superfish_ng.planar_curved_saved import save_planar_curved_run, read_planar_curved_run
        from zipfile import ZipFile
        import io
        original = self.solutions['te']
        with tempfile.TemporaryDirectory() as temporary:
            for kind in ('missing', 'extra', 'symlink', 'directory_symlink', 'corrupt', 'duplicate'):
                folder = Path(temporary)/kind
                save_planar_curved_run(original.case, original, folder)
                if kind == 'missing':
                    (folder/'manifest.json').unlink()
                elif kind == 'extra':
                    (folder/'extra.json').write_text('{}')
                elif kind == 'symlink':
                    target = Path(temporary)/'case-copy.json'
                    target.write_bytes((folder/'case.json').read_bytes())
                    (folder/'case.json').unlink()
                    (folder/'case.json').symlink_to(target)
                elif kind == 'directory_symlink':
                    link = Path(temporary)/'linked-native'
                    link.symlink_to(folder, target_is_directory=True)
                    folder = link
                else:
                    if kind == 'corrupt':
                        (folder/'fields.npz').write_bytes(b'invalid archive')
                    else:
                        array = io.BytesIO()
                        np.save(array, original.coefficients, allow_pickle=False)
                        with ZipFile(folder/'fields.npz', 'w') as archive:
                            archive.writestr('coefficients.npy', array.getvalue())
                            # Duplicate members must fail before physical replay.
                            import warnings
                            with warnings.catch_warnings():
                                warnings.simplefilter('ignore', UserWarning)
                                archive.writestr('coefficients.npy', array.getvalue())
                    self.rehash(folder, 'fields.npz')
                with self.subTest(kind=kind), self.assertRaises(ValueError):
                    read_planar_curved_run(folder)
