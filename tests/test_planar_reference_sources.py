# SPDX-License-Identifier: Apache-2.0
"""Whole-domain copy and source-binding guards for reference preparation."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch as mock_patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from prepare_planar_superfish_comparison import prepare
from superfish_ng.planar import PlanarCase
from superfish_ng.planar_mesh import PlanarMesh
from superfish_ng.planar_polygon import PlanarPolygonCase
from superfish_ng.planar_curved import PlanarCurvedCase
from test_planar_curved import patch


class PlanarReferenceSourceTests(unittest.TestCase):
    def fixture(self, root):
        source = root / 'out' / 'source'; source.mkdir(parents=True)
        polygon = PlanarPolygonCase(PlanarMesh.create([[0., 0.], [.02, 0.], [0., .02]],
            [[0., 0.], [.02, 0.], [0., .02]], [[0, 1, 2]]), 'te', modes=1)
        curved = PlanarCurvedCase(patch(), 'tm', modes=1)
        receipt = source / 'historical.json'; receipt.write_text('{"scope":"source only; no reference PASS"}\n')
        def binding(path):
            return {'path': path.relative_to(root).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        rows=[]
        for identity, case in [('polygon', polygon), ('quadratic', curved)]:
            path = source / f'{identity}.json'
            # Deliberately noncanonical JSON bytes must survive copy.
            path.write_text(' \n' + json.dumps(case.to_dict(), separators=(',', ':')) + '\n\n')
            rows.append({'id': identity, 'feature_ids': ['P04', 'P09'],
                         'conditions': ['whole native input; not solver replay'],
                         'case': binding(path), 'evidence': [binding(receipt)]})
        catalog = root / 'catalog.json'
        data={'format':'superfish_ng_planar_reference_sources','schema_version':1,'cases':rows}
        catalog.write_text(json.dumps(data))
        return catalog, data

    def test_original_polygon_and_all_quadratic_mids_survive_without_solve(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); catalog, data=self.fixture(root)
            with mock_patch('superfish_ng.planar_solve.solve_planar_case', side_effect=AssertionError('no FEM in preparation')):
                report=prepare(root/'out'/'prepared', project_root=root, source_catalog=catalog)
            self.assertEqual(report['schema_version'], 2)
            self.assertEqual(report['historical_source_cases'], 2)
            self.assertEqual((report['new_ng_solves'], report['new_legacy_runs']), (0, 0))
            for row, result in zip(data['cases'], report['cases'][-2:]):
                copied=root/'out'/'prepared'/result['levels'][0]['path']/'ng-case.json'
                self.assertEqual(copied.read_bytes(), (root/row['case']['path']).read_bytes())
                self.assertEqual(result['ng_schema_version'], 2 if row['id']=='polygon' else 3)
                self.assertEqual(result['legacy_deck']['status'], 'UNVERIFIED')
                self.assertIsNone(result['legacy_deck']['path'])
                self.assertTrue(all(g['status']=='UNVERIFIED' for g in result['gates'].values()))
                self.assertTrue(all(g['status']=='UNVERIFIED' for g in result['acceptance_axes'].values()))
                self.assertIsNone(result['mode_correspondence']['ng_mode_index'])
                self.assertEqual(result['levels'][0]['ng_run']['expected_command'][6], 'solve-planar')
            self.assertIn('do not replace mids', report['cases'][-1]['geometry_equivalence']['reason'])

    def test_changed_case_or_receipt_rejected_before_output_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); catalog, data=self.fixture(root)
            for binding in (data['cases'][0]['case'], data['cases'][0]['evidence'][0]):
                path=root/binding['path']; before=path.read_bytes(); path.write_bytes(before+b' ')
                with self.assertRaisesRegex(ValueError, 'evidence changed'):
                    prepare(root/'out'/'must-not-exist', project_root=root, source_catalog=catalog)
                self.assertFalse((root/'out'/'must-not-exist').exists())
                path.write_bytes(before)

    def test_strict_catalog_duplicate_ids_unknown_physics_and_escape_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); catalog, data=self.fixture(root)
            with self.assertRaisesRegex(ValueError, 'cannot read UTF-8'):
                prepare(root/'out'/'must-not-exist', project_root=root, source_catalog=root/'missing.json')
            self.assertFalse((root/'out'/'must-not-exist').exists())
            bads=[]
            duplicate=deepcopy(data); duplicate['cases'].append(deepcopy(duplicate['cases'][0])); bads.append(duplicate)
            unknown=deepcopy(data); unknown['cases'][0]['promote_reference_pass']=True; bads.append(unknown)
            escaped=deepcopy(data); escaped['cases'][0]['case']['path']='../elsewhere.json'; bads.append(escaped)
            absolute=deepcopy(data); absolute['cases'][0]['case']['path']=str(root/'out'/'source'/'polygon.json'); bads.append(absolute)
            for bad in bads:
                catalog.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):
                    prepare(root/'out'/'must-not-exist', project_root=root, source_catalog=catalog)
                self.assertFalse((root/'out'/'must-not-exist').exists())
            original=root/data['cases'][0]['case']['path']
            model=json.loads(original.read_text()); model['model']['material']='dielectric'
            original.write_text(json.dumps(model)); data['cases'][0]['case']['sha256']=hashlib.sha256(original.read_bytes()).hexdigest()
            catalog.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'vacuum'):
                prepare(root/'out'/'must-not-exist', project_root=root, source_catalog=catalog)
            self.assertFalse((root/'out'/'must-not-exist').exists())

    def test_generated_rectangle_command_reaches_typed_cli_and_saved_si_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); out=root/'out'/'prepared'
            report=prepare(out, project_root=root)
            run=report['cases'][0]['levels'][0]['ng_run']
            # Use the selected locked Python in this unit; the public command uses uv.
            argv=run['expected_command'][4:]
            result=subprocess.run([sys.executable, *argv], cwd=root, capture_output=True, text=True,
                timeout=30, env=dict(os.environ, PYTHONPATH=str(ROOT/'src'), OPENBLAS_NUM_THREADS='1'))
            self.assertEqual(result.returncode, 0, result.stderr)
            saved=json.loads(result.stdout)
            q=saved['modes'][0]
            self.assertAlmostEqual(q['stored_energy_j_per_m'], 1., places=10)
            self.assertIsNone(q['r_over_q_accelerator_ohm'])
            self.assertIsNone(q['r_over_q_circuit_ohm'])
            self.assertIn('no finite accelerating path', q['accelerating_quantities_reason'])
            analytic=299792458/(2*.31)
            self.assertLess(abs(q['frequency_hz']/analytic-1), 1e-4)
            self.assertTrue((root/run['expected_command'][-1]/'manifest.json').is_file())


if __name__=='__main__':unittest.main()
