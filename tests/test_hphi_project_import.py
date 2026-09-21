# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from pathlib import Path
import tempfile,unittest
from superfish_ng.coaxial import CoaxialCase,solve_coaxial
from superfish_ng.hphi_native import save_hphi_run
from superfish_ng.hphi_project import HphiProject
from superfish_ng.jobs import JobManager


class HphiProjectImportTests(unittest.TestCase):
    def test_explicit_project_preserves_metadata_and_rejects_case_override(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);case=CoaxialCase(.01,.02,.04,nr=2,nz=3,modes=2)
            solution=solve_coaxial(case);source=root/'native';save_hphi_run(case,solution,source)
            manager=JobManager(root/'jobs');self.addCleanup(manager.close)
            project=HphiProject(case,'m');identifier=manager.import_hphi_result(source,project=project)
            owned=manager.directory(identifier)
            self.assertEqual(HphiProject.load(owned/'project.json'),project)
            for p in source.iterdir():self.assertEqual(p.read_bytes(),(owned/'solution'/p.name).read_bytes())
            before=len(manager.list())
            with self.assertRaises(ValueError):manager.import_hphi_result(source,project=HphiProject(replace(case,name='other')))
            with self.assertRaises(ValueError):manager.import_hphi_result(owned,project=project)
            with self.assertRaises(ValueError):manager.import_hphi_result(source,project=project.to_dict())
            self.assertEqual(len(manager.list()),before)
