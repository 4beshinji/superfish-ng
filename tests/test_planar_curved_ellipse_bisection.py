# SPDX-License-Identifier: Apache-2.0
"""Failed map evidence cannot silently authorize repeating completed FEMs."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from superfish_ng.jobs import _implementation_hashes
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from extend_planar_curved_ellipse_bisection import previous_ellipse
from extend_planar_curved_shapes import artifact_hashes


class PlanarCurvedEllipseBisectionTests(unittest.TestCase):
    def fixture(self, root):
        folder, failure = root/'original', root/'uniform-failure'
        folder.mkdir(); failure.mkdir()
        names = ('planar_curved_mesh_reference.py', 'planar_curved_shape_reference.py',
            'planar_curved_vector_reference.py', 'validate_planar_curved_shapes.py',
            'validate_planar_curved_independent.py', 'validate_planar_curved_convergence.py',
            'validate_planar_curved_fem.py', 'validate_planar_curved_rf.py')
        paths = [Path(__file__).resolve().parents[1]/'scripts'/name for name in names]
        code = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        (folder/'validator-hashes.json').write_text(json.dumps(code))
        extended = Path(__file__).resolve().parents[1]/'scripts/extend_planar_curved_shapes.py'
        (failure/'validator-hashes.json').write_text(json.dumps(code|{str(extended): hashlib.sha256(extended.read_bytes()).hexdigest()}))
        before = _implementation_hashes()
        for p in (folder/'implementation-before.json', folder/'implementation-after.json', failure/'implementation-before.json'):
            p.write_text(json.dumps(before))
        rows = [dict(label=f'A-L{i}', patterns=['uniform']*i, passed=i==4) for i in range(1, 5)]
        rows += [dict(label=f'B-L{i}', patterns=['bisection']+['uniform']*(i-1), passed=False) for i in (3, 4)]
        # Metadata preflight only; these placeholder native files cannot pass
        # the later physical restoration or be treated as real eigenmodes.
        for row in rows:
            trial = folder/row['label']; trial.mkdir()
            for name in ('case.json','fem-fields.npz','patterns.json','regenerated-parent-charts.npz'):
                (trial/name).write_text('metadata fixture')
        report = dict(passed=False, shape='ellipse', polarization='tm', scale=1,
            initial_angular_segments=16, records=rows, new_FEM_solves=6, accepted_A='A-L4', accepted_B=None,
            scope='one synthetic noncircle, fixed original P2 domain; finite A/B and last-two f/E/H/full RF')
        (folder/'report.json').write_text(json.dumps(report))
        (folder/'progress.json').write_text(json.dumps(rows))
        (failure/'previous-report.json').write_text(json.dumps(report))
        (failure/'progress.json').write_text('[]')
        (failure/'failed-evidence.json').write_text(json.dumps(dict(error='UNVERIFIED: cumulative original-map roundoff exceeds local resolution')))
        audit = root/'termination.json'
        observation = dict(terminal=True, observed_exit_code=1, original_evidence=str(failure))
        audit.write_text(json.dumps(observation))
        return folder, failure, audit, report, observation

    def test_exact_terminal_failed_prefix_is_read_only_and_preserves_two_artifact_sets(self):
        with tempfile.TemporaryDirectory() as directory:
            folder, failure, audit, report, _ = self.fixture(Path(directory))
            prior = artifact_hashes(folder), artifact_hashes(failure)
            accepted, original, old, failed, _ = previous_ellipse(folder, failure, audit)
            self.assertEqual(accepted, report)
            self.assertEqual((old, failed), prior)
            self.assertEqual((artifact_hashes(folder), artifact_hashes(failure)), prior)
            self.assertEqual(len(original.cell_nodes), 112)

    def test_timeout_success_wrong_case_completed_trial_or_partial_code_cannot_authorize_continuation(self):
        with tempfile.TemporaryDirectory() as directory:
            folder, failure, audit, report, observation = self.fixture(Path(directory))
            for changes in (dict(terminal=False), dict(observed_exit_code=0), dict(original_evidence=str(folder))):
                audit.write_text(json.dumps(observation|changes))
                with self.assertRaises(ValueError):
                    previous_ellipse(folder, failure, audit)
            audit.write_text(json.dumps(observation))
            changed = copy.deepcopy(report); changed['scale']=2
            (failure/'previous-report.json').write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError,'exact original physical report'):
                previous_ellipse(folder, failure, audit)
            (failure/'previous-report.json').write_text(json.dumps(report))
            (failure/'progress.json').write_text('[{}]')
            with self.assertRaisesRegex(ValueError,'no completed'):
                previous_ellipse(folder, failure, audit)
            (failure/'progress.json').write_text('[]')
            (failure/'validator-hashes.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'complete original validator'):
                previous_ellipse(folder, failure, audit)


if __name__=='__main__':
    unittest.main()
