# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng import Case, solve
from superfish_ng.cli import main
from superfish_ng.project import Project
from superfish_ng.saved import read_solution


class ElementOrderTests(unittest.TestCase):
    def test_strict_schema_default_and_project_roundtrip(self):
        old=Case(((0.,.1),(.2,.1)),nr=4,nz=6,modes=1)
        self.assertNotIn('element_order',old.to_dict()['solver'])
        self.assertEqual(old.to_dict()['schema_version'],1)
        for value in [True,False,0,3,2.,'2',None]:
            with self.assertRaisesRegex(ValueError,'element_order'):
                replace(old,element_order=value)
        case=replace(old,element_order=2)
        data=case.to_dict()
        self.assertEqual(data['schema_version'],3)
        self.assertEqual(Case.from_dict(data),case)
        project=Project.from_dict({'project_version':1,'case':data})
        self.assertEqual(project.case.element_order,2)
        data['schema_version']=1
        data.pop('model')
        with self.assertRaisesRegex(ValueError,'element_order'):
            Case.from_dict(data)

    def test_cli_solve_save_read_and_reexecute_preserve_p2(self):
        case=Case(((0.,.1),(.2,.1)),nr=4,nz=6,modes=2,element_order=2)
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            root=Path(tmp)
            source=root/'case.json'
            source.write_text(json.dumps(case.to_dict()))
            self.assertEqual(main(['solve',str(source),'--out',str(root/'run')]),0)
            saved=read_solution(root/'run')
            self.assertEqual(saved.case.element_order,2)
            self.assertEqual(saved.element_order,2)
            repeated=solve(saved.case)
            np.testing.assert_array_equal(repeated.frequencies_hz,saved.frequencies_hz)
            np.testing.assert_array_equal(repeated.u,saved.u)

    def test_imported_job_rerun_retains_quadratic_order(self):
        from superfish_ng.jobs import execute_project, JobManager
        from superfish_ng.io import save_run
        case=Case(((0.,.1),(.2,.1)),nr=4,nz=6,modes=2,element_order=2)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            save_run(case,solve(case),root/'source')
            manager=JobManager(root/'history')
            try:
                identifier=manager.import_result(root/'source')
                directory=manager.directory(identifier)
                project=Project.load(directory/'project.json')
                self.assertEqual(project.case.element_order,2)
                execute_project(project,root/'rerun')
                imported=read_solution(directory/'solution')
                repeated=read_solution(root/'rerun'/'solution')
                np.testing.assert_array_equal(imported.u,repeated.u)
                self.assertEqual(imported.results['modes'],repeated.results['modes'])
            finally:
                manager.close()
