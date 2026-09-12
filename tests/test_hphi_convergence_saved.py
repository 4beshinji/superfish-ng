# SPDX-License-Identifier: Apache-2.0
import hashlib,json,shutil,tempfile,unittest
from pathlib import Path
from superfish_ng.hphi_convergence_saved import execute_hphi_convergence,read_hphi_convergence
from test_hphi_convergence import request


class HphiConvergenceSavedTests(unittest.TestCase):
    def test_native_replay_no_overwrite_and_rehashed_decision_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);run=root/'run';report=execute_hphi_convergence(request(),run)
            before={str(p.relative_to(run)):p.read_bytes() for p in run.rglob('*') if p.is_file()}
            self.assertEqual(read_hphi_convergence(run),report)
            self.assertEqual(before,{str(p.relative_to(run)):p.read_bytes() for p in run.rglob('*') if p.is_file()})
            with self.assertRaises(FileExistsError):execute_hphi_convergence(request(),run)
            result=run/'convergence-results.json';raw=json.loads(result.read_text());raw['status']='FORGED';result.write_text(json.dumps(raw))
            manifest=run/'manifest.json';raw=json.loads(manifest.read_text());raw['files']['convergence-results.json']=hashlib.sha256(result.read_bytes()).hexdigest();manifest.write_text(json.dumps(raw))
            with self.assertRaisesRegex(ValueError,'replay'):read_hphi_convergence(run)

    def test_missing_or_linked_level_cannot_complete(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);run=root/'run';execute_hphi_convergence(request(False,order=1),run)
            source=run/'level-0001';moved=root/'moved';source.rename(moved);source.symlink_to(moved,target_is_directory=True)
            with self.assertRaises(ValueError):read_hphi_convergence(run)
            source.unlink()
            with self.assertRaises(ValueError):read_hphi_convergence(run)


if __name__=='__main__':unittest.main()
