# SPDX-License-Identifier: Apache-2.0
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
from superfish_ng.coaxial import CoaxialCase,solve_coaxial
from superfish_ng.coaxial_saved import save_coaxial_run,read_coaxial_run,coaxial_result,export_coaxial_probe


class CoaxialSavedTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.case=CoaxialCase(.025,.05,.18,nr=3,nz=8,modes=2)

    def rehash(self,run):
        path=run/'manifest.json';manifest=json.loads(path.read_text())
        manifest['files']={n:hashlib.sha256((run/n).read_bytes()).hexdigest() for n in manifest['files']}
        path.write_text(json.dumps(manifest))

    def test_native_all_fields_and_actual_cli_roundtrip(self):
        for order in (1,2):
            case=replace(self.case,element_order=order)
            run=self.root/f'p{order}'
            case_path=self.root/f'case{order}.json';case_path.write_text(json.dumps(case.to_dict()))
            command=[sys.executable,'-m','superfish_ng','solve-coaxial',str(case_path),'--out',str(run)]
            done=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(done.returncode,0,done.stderr)
            saved=read_coaxial_run(run)
            self.assertEqual(json.loads(done.stdout),coaxial_result(saved))
            done=subprocess.run([sys.executable,'-m','superfish_ng','replay-coaxial',str(run)],capture_output=True,text=True)
            self.assertEqual(done.returncode,0,done.stderr)
            points=[[.025,0],[.04,.09],[.05,.18]]
            path=self.root/f'points{order}.json';path.write_text(json.dumps(points))
            out=self.root/f'probe{order}.json'
            done=subprocess.run([sys.executable,'-m','superfish_ng','probe-coaxial',str(run),'--points',str(path),
                                 '--out',str(out),'--mode','2'],capture_output=True,text=True)
            self.assertEqual(done.returncode,0,done.stderr)
            report=json.loads(out.read_text());actual=saved.fields_at(points,1)
            for key,value in actual.items():np.testing.assert_array_equal(report['fields'][key],value)
            self.assertEqual(len(report['fields']),18)
            self.assertIn('real + i*quadrature',report['conventions']['phasor'])
            with self.assertRaises(FileExistsError):save_coaxial_run(case,saved,run)
            with self.assertRaises(ValueError):export_coaxial_probe(run,self.root/'bad.json',[[0,.09]])
            self.assertFalse((self.root/'bad.json').exists())
            original=out.read_bytes()
            with self.assertRaises(FileExistsError):export_coaxial_probe(run,out,points)
            self.assertEqual(out.read_bytes(),original)
            with self.assertRaises(ValueError):export_coaxial_probe(run,run/'probe.json',points)

    def test_rehashed_metadata_and_static_contamination_are_rejected(self):
        run=self.root/'run';save_coaxial_run(self.case,solve_coaxial(self.case),run)
        result_path=run/'results.json';original=result_path.read_text()
        for key in ('excluded_nullspace','conventions','modes','matrix_quadrature'):
            data=json.loads(original);data[key]='changed';result_path.write_text(json.dumps(data));self.rehash(run)
            with self.assertRaisesRegex(ValueError,'replay'):read_coaxial_run(run)
        result_path.write_text(original)
        with np.load(run/'fields.npz') as archive:fields={key:archive[key] for key in archive.files}
        fields['coefficients'][:,0]+=100
        np.savez_compressed(run/'fields.npz',**fields);self.rehash(run)
        with self.assertRaisesRegex(ValueError,'static-nullspace|energy'):read_coaxial_run(run)

    def test_valid_higher_eigenpairs_cannot_impersonate_lowest_positive_spectrum(self):
        full=solve_coaxial(replace(self.case,modes=3))
        forged=replace(full,case=self.case,coefficients=full.coefficients[:,1:],frequencies_hz=full.frequencies_hz[1:])
        with self.assertRaisesRegex(ValueError,'lowest positive'):
            save_coaxial_run(self.case,forged,self.root/'skipped')
        self.assertFalse((self.root/'skipped').exists())

    def test_failed_publication_has_no_completion_and_preserves_existing_output(self):
        solution=solve_coaxial(self.case);run=self.root/'failed'
        from os import link
        def fault(source,destination):
            if Path(destination).name=='manifest.json':raise OSError('publication interrupted')
            return link(source,destination)
        with patch('superfish_ng.coaxial_saved.os.link',side_effect=fault):
            with self.assertRaisesRegex(OSError,'publication interrupted'):save_coaxial_run(self.case,solution,run)
        self.assertFalse((run/'manifest.json').exists())
        with self.assertRaisesRegex(ValueError,'completion manifest'):read_coaxial_run(run)
        before={p.name:p.read_bytes() for p in run.iterdir()}
        with self.assertRaises(FileExistsError):save_coaxial_run(self.case,solution,run)
        self.assertEqual(before,{p.name:p.read_bytes() for p in run.iterdir()})


if __name__=='__main__':unittest.main()
