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
import test_axis_connected_mesh as geometry_tests
from superfish_ng.axis_connected_mesh import AxisConnectedMesh
from superfish_ng.axis_hphi import AxisHphiCase, AxisAccelerationPath, solve_axis_hphi
from superfish_ng.axis_hphi_saved import save_axis_hphi_run, read_axis_hphi_run, axis_hphi_result, export_axis_hphi_probe


class AxisHphiSavedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root = Path(self.temp.name)
        self.case = AxisHphiCase(AxisConnectedMesh(**geometry_tests.AxisConnectedMeshTests().data(1)),modes=2,
            acceleration=AxisAccelerationPath(0.,.18,1.,0.))

    def rehash(self,run):
        path=run/'manifest.json'; manifest=json.loads(path.read_text())
        manifest['files']={name:hashlib.sha256((run/name).read_bytes()).hexdigest() for name in manifest['files']}
        path.write_text(json.dumps(manifest))

    def test_actual_cli_native_and_probe_roundtrip(self):
        for order in (1,2):
            case=replace(self.case,element_order=order); path=self.root/f'case{order}.json';path.write_text(json.dumps(case.to_dict()))
            run=self.root/f'run{order}'
            done=subprocess.run([sys.executable,'-m','superfish_ng','solve-axis-hphi',str(path),'--out',str(run)],capture_output=True,text=True)
            self.assertEqual(done.returncode,0,done.stderr)
            solution=read_axis_hphi_run(run);self.assertEqual(json.loads(done.stdout),axis_hphi_result(solution))
            done=subprocess.run([sys.executable,'-m','superfish_ng','replay-axis-hphi',str(run)],capture_output=True,text=True)
            self.assertEqual(done.returncode,0,done.stderr)
            points=[[0.,0.],[0.,.09],[.1875,.06]];path=self.root/f'points{order}.json';path.write_text(json.dumps(points))
            out=self.root/f'probe{order}.json'
            done=subprocess.run([sys.executable,'-m','superfish_ng','probe-axis-hphi',str(run),'--points',str(path),'--mode','2','--out',str(out)],capture_output=True,text=True)
            self.assertEqual(done.returncode,0,done.stderr)
            probe=json.loads(out.read_text());self.assertEqual(len(probe['fields']),18)
            for key,value in solution.fields_at(points,1).items():np.testing.assert_array_equal(probe['fields'][key],value)
            self.assertIn('real + i*quadrature',probe['conventions']['phasor'])
            with self.assertRaises(FileExistsError):save_axis_hphi_run(case,solution,run)
            original=out.read_bytes()
            with self.assertRaises(FileExistsError):export_axis_hphi_probe(run,out,points)
            self.assertEqual(out.read_bytes(),original)
            with self.assertRaises(ValueError):export_axis_hphi_probe(run,self.root/'bad.json',[self.case.mesh.holes_rz_m[0].mean(axis=0)])
            self.assertFalse((self.root/'bad.json').exists())
            with self.assertRaises(ValueError):export_axis_hphi_probe(run,run/'probe.json',points)

    def test_rehashed_hole_boundary_and_metadata_tampering_rejected(self):
        run=self.root/'run';save_axis_hphi_run(self.case,solve_axis_hphi(self.case),run)
        path=run/'results.json';original=path.read_bytes()
        for key in ('topology','conventions','excluded_nullspace','modes'):
            data=json.loads(original);data[key]='changed';path.write_text(json.dumps(data));self.rehash(run)
            with self.assertRaisesRegex(ValueError,'replay'):read_axis_hphi_run(run)
        path.write_bytes(original)
        original_mesh=(run/'mesh.npz').read_bytes()
        for key in ('boundary_components','boundary_segments','axis_edges','axis_dofs'):
            with np.load(run/'mesh.npz') as archive:arrays={k:archive[k] for k in archive.files}
            arrays[key][:]=0;np.savez_compressed(run/'mesh.npz',**arrays);self.rehash(run)
            with self.assertRaisesRegex(ValueError,'boundary membership'):read_axis_hphi_run(run)
            (run/'mesh.npz').write_bytes(original_mesh)
        with np.load(run/'fields.npz') as archive:arrays={k:archive[k] for k in archive.files}
        arrays['coefficients'][:,0]+=100.;np.savez_compressed(run/'fields.npz',**arrays);self.rehash(run)
        with self.assertRaisesRegex(ValueError,'energy|static-nullspace'):read_axis_hphi_run(run)

    def test_lowest_spectrum_and_caller_boundary_changes_rejected_before_publication(self):
        full=solve_axis_hphi(replace(self.case,modes=3))
        forged=replace(full,case=self.case,coefficients=full.coefficients[:,1:],frequencies_hz=full.frequencies_hz[1:])
        with self.assertRaisesRegex(ValueError,'lowest positive'):save_axis_hphi_run(self.case,forged,self.root/'skipped')
        self.assertFalse((self.root/'skipped').exists())
        solution=solve_axis_hphi(self.case)
        object.__setattr__(solution.case.mesh,'boundary_components',np.zeros_like(solution.case.mesh.boundary_components))
        with self.assertRaisesRegex(ValueError,'boundary components'):save_axis_hphi_run(self.case,solution,self.root/'changed')
        self.assertFalse((self.root/'changed').exists())

    def test_partial_publication_has_no_completion_and_cannot_overwrite(self):
        solution=solve_axis_hphi(self.case);run=self.root/'failed'
        from os import link
        def fail(source,dest):
            if Path(dest).name=='manifest.json':raise OSError('interrupted publication')
            return link(source,dest)
        with patch('superfish_ng.axis_hphi_saved.os.link',side_effect=fail):
            with self.assertRaises(OSError):save_axis_hphi_run(self.case,solution,run)
        self.assertFalse((run/'manifest.json').exists())
        with self.assertRaisesRegex(ValueError,'completion manifest'):read_axis_hphi_run(run)
        original={p.name:p.read_bytes() for p in run.iterdir()}
        with self.assertRaises(FileExistsError):save_axis_hphi_run(self.case,solution,run)
        self.assertEqual({p.name:p.read_bytes() for p in run.iterdir()},original)
