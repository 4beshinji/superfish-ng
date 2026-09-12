# SPDX-License-Identifier: Apache-2.0
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from scripts.hphi_mesh_reference import rectangular_holes
from superfish_ng.meridional_mesh import MeridionalMesh
from superfish_ng.hphi_mesh import HphiMeshCase, solve_hphi_mesh
from superfish_ng.hphi_mesh_saved import save_hphi_mesh_run, read_hphi_mesh_run, hphi_mesh_result, export_hphi_mesh_probe


class HphiMeshSavedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root = Path(self.temp.name)
        self.case = HphiMeshCase(MeridionalMesh(**rectangular_holes(1)),modes=2)

    def rehash(self,run):
        path=run/'manifest.json'; manifest=json.loads(path.read_text())
        manifest['files']={name:hashlib.sha256((run/name).read_bytes()).hexdigest() for name in manifest['files']}
        path.write_text(json.dumps(manifest))

    def test_actual_cli_native_and_probe_roundtrip(self):
        for order in (1,2):
            case=replace(self.case,element_order=order); path=self.root/f'case{order}.json';path.write_text(json.dumps(case.to_dict()))
            run=self.root/f'run{order}'
            done=subprocess.run([sys.executable,'-m','superfish_ng','solve-hphi-mesh',str(path),'--out',str(run)],capture_output=True,text=True)
            self.assertEqual(done.returncode,0,done.stderr)
            solution=read_hphi_mesh_run(run);self.assertEqual(json.loads(done.stdout),hphi_mesh_result(solution))
            done=subprocess.run([sys.executable,'-m','superfish_ng','replay-hphi-mesh',str(run)],capture_output=True,text=True)
            self.assertEqual(done.returncode,0,done.stderr)
            points=[[.025,0.],[.035,.09],[.075,.06]];path=self.root/f'points{order}.json';path.write_text(json.dumps(points))
            out=self.root/f'probe{order}.json'
            done=subprocess.run([sys.executable,'-m','superfish_ng','probe-hphi-mesh',str(run),'--points',str(path),'--mode','2','--out',str(out)],capture_output=True,text=True)
            self.assertEqual(done.returncode,0,done.stderr)
            probe=json.loads(out.read_text());self.assertEqual(len(probe['fields']),18)
            for key,value in solution.fields_at(points,1).items():np.testing.assert_array_equal(probe['fields'][key],value)
            self.assertIn('real + i*quadrature',probe['conventions']['phasor'])
            with self.assertRaises(FileExistsError):save_hphi_mesh_run(case,solution,run)
            original=out.read_bytes()
            with self.assertRaises(FileExistsError):export_hphi_mesh_probe(run,out,points)
            self.assertEqual(out.read_bytes(),original)
            with self.assertRaises(ValueError):export_hphi_mesh_probe(run,self.root/'bad.json',[[.06,.09]])
            self.assertFalse((self.root/'bad.json').exists())
            with self.assertRaises(ValueError):export_hphi_mesh_probe(run,run/'probe.json',points)

    def test_rehashed_hole_boundary_and_metadata_tampering_rejected(self):
        run=self.root/'run';save_hphi_mesh_run(self.case,solve_hphi_mesh(self.case),run)
        path=run/'results.json';original=path.read_bytes()
        for key in ('topology','conventions','excluded_nullspace','modes'):
            data=json.loads(original);data[key]='changed';path.write_text(json.dumps(data));self.rehash(run)
            with self.assertRaisesRegex(ValueError,'replay'):read_hphi_mesh_run(run)
        path.write_bytes(original)
        original_mesh=(run/'mesh.npz').read_bytes()
        for key in ('boundary_components','boundary_segments'):
            with np.load(run/'mesh.npz') as archive:arrays={k:archive[k] for k in archive.files}
            arrays[key][:]=0;np.savez_compressed(run/'mesh.npz',**arrays);self.rehash(run)
            with self.assertRaisesRegex(ValueError,'boundary membership'):read_hphi_mesh_run(run)
            (run/'mesh.npz').write_bytes(original_mesh)
        with np.load(run/'fields.npz') as archive:arrays={k:archive[k] for k in archive.files}
        arrays['coefficients'][:,0]+=100.;np.savez_compressed(run/'fields.npz',**arrays);self.rehash(run)
        with self.assertRaisesRegex(ValueError,'energy|static-nullspace'):read_hphi_mesh_run(run)

    def test_lowest_spectrum_and_caller_boundary_changes_rejected_before_publication(self):
        full=solve_hphi_mesh(replace(self.case,modes=3))
        forged=replace(full,case=self.case,coefficients=full.coefficients[:,1:],frequencies_hz=full.frequencies_hz[1:])
        with self.assertRaisesRegex(ValueError,'lowest positive'):save_hphi_mesh_run(self.case,forged,self.root/'skipped')
        self.assertFalse((self.root/'skipped').exists())
        solution=solve_hphi_mesh(self.case)
        object.__setattr__(solution.case.mesh,'boundary_components',np.zeros_like(solution.case.mesh.boundary_components))
        with self.assertRaisesRegex(ValueError,'boundary components'):save_hphi_mesh_run(self.case,solution,self.root/'changed')
        self.assertFalse((self.root/'changed').exists())

    def test_partial_publication_has_no_completion_and_cannot_overwrite(self):
        solution=solve_hphi_mesh(self.case);run=self.root/'failed'
        from os import link
        def fail(source,dest):
            if Path(dest).name=='manifest.json':raise OSError('interrupted publication')
            return link(source,dest)
        with patch('superfish_ng.hphi_mesh_saved.os.link',side_effect=fail):
            with self.assertRaises(OSError):save_hphi_mesh_run(self.case,solution,run)
        self.assertFalse((run/'manifest.json').exists())
        with self.assertRaisesRegex(ValueError,'completion manifest'):read_hphi_mesh_run(run)
        original={p.name:p.read_bytes() for p in run.iterdir()}
        with self.assertRaises(FileExistsError):save_hphi_mesh_run(self.case,solution,run)
        self.assertEqual({p.name:p.read_bytes() for p in run.iterdir()},original)
