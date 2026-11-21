# SPDX-License-Identifier: Apache-2.0
"""A timeout cannot authorize replay; a complete terminal prefix is required."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from superfish_ng.jobs import _implementation_hashes
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from recover_planar_curved_shapes import prefix_preflight


class PlanarCurvedShapeRecoveryTests(unittest.TestCase):
    def fixture(self, root):
        folder = root/'prefix'
        folder.mkdir()
        names = ('validate_planar_curved_shapes.py', 'planar_curved_mesh_reference.py',
            'planar_curved_shape_reference.py', 'planar_curved_vector_reference.py',
            'validate_planar_curved_independent.py', 'validate_planar_curved_convergence.py',
            'validate_planar_curved_fem.py', 'validate_planar_curved_rf.py')
        paths = [Path(__file__).resolve().parents[1]/'scripts'/name for name in names]
        (folder/'validator-hashes.json').write_text(json.dumps({str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}))
        (folder/'implementation-before.json').write_text(json.dumps(_implementation_hashes()))
        rows = [dict(label='A-L1', patterns=['uniform']),
                dict(label='A-L2', patterns=['uniform']*2),
                dict(label='B-L1', patterns=['bisection'])]
        # These metadata-only fixtures are never accepted as physical solutions.
        for row in rows:
            trial = folder/row['label']
            trial.mkdir()
            for name in ('case.json', 'fem-fields.npz', 'patterns.json', 'regenerated-parent-charts.npz'):
                (trial/name).write_text('metadata fixture; no FEM solution')
        (folder/'progress.json').write_text(json.dumps(rows))
        audit = root/'terminal.json'
        observation = dict(terminal=True, observed_exit_code=143, original_evidence=str(folder))
        audit.write_text(json.dumps(observation))
        return folder, audit, rows, observation

    def test_complete_terminal_metadata_preflight_preserves_original_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            folder, audit, rows, _ = self.fixture(Path(directory))
            restored_rows, hashes, observation = prefix_preflight(folder, audit)
            self.assertEqual(restored_rows, rows)
            self.assertEqual(observation['observed_exit_code'], 143)
            self.assertEqual(len(hashes), 15)
            self.assertEqual(hashes, prefix_preflight(folder, audit)[1])

    def test_timeout_success_wrong_directory_or_complete_report_cannot_authorize_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            folder, audit, _, observation = self.fixture(Path(directory))
            for changes in (dict(terminal=False), dict(observed_exit_code=0),
                            dict(observed_exit_code=True), dict(original_evidence=str(folder.parent))):
                audit.write_text(json.dumps(observation|changes))
                with self.assertRaises(ValueError):
                    prefix_preflight(folder, audit)
            audit.write_text(json.dumps(observation))
            (folder/'report.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'completed reports'):
                prefix_preflight(folder, audit)

    def test_incomplete_nonlocal_out_of_order_or_missing_native_prefix_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            folder, audit, rows, _ = self.fixture(Path(directory))
            nonlocal_rows = copy.deepcopy(rows)
            nonlocal_rows[0]['label'] = '../outside'
            for changed in (rows[1:], [rows[0], rows[2], rows[1]], nonlocal_rows, rows+rows[:1]):
                (folder/'progress.json').write_text(json.dumps(changed))
                with self.assertRaises(ValueError):
                    prefix_preflight(folder, audit)
            (folder/'progress.json').write_text(json.dumps(rows))
            (folder/'B-L1/fem-fields.npz').unlink()
            with self.assertRaisesRegex(ValueError, 'complete recorded artifact'):
                prefix_preflight(folder, audit)

    def test_changed_product_or_incomplete_validator_hashes_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            folder, audit, _, _ = self.fixture(Path(directory))
            (folder/'implementation-before.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'production hashes'):
                prefix_preflight(folder, audit)
            (folder/'implementation-before.json').write_text(json.dumps(_implementation_hashes()))
            (folder/'validator-hashes.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'complete original validator'):
                prefix_preflight(folder, audit)


if __name__ == '__main__':
    unittest.main()
