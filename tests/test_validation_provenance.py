# SPDX-License-Identifier: Apache-2.0
"""Controller-only fixtures: actual child processes, no numerical acceptance."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('rf_validator',ROOT/'scripts/validate.py')
validator=importlib.util.module_from_spec(spec);spec.loader.exec_module(validator)


class ValidationProvenanceTests(unittest.TestCase):
    def run_fixture(self, *, mutation=None, skip=False, child_code=0, numerical_error=None):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ('src','tests','scripts','examples'):(root/name).mkdir()
            target=root/'src/input.py';target.write_text('ORIGINAL=1\n')
            for name in ('pillbox.json','shaped_cell.json'):
                (root/'examples'/name).write_bytes((ROOT/'examples'/name).read_bytes())
            child='from pathlib import Path\nimport sys\nprint("fixture-child-log")\n'
            if mutation=='changed':child+='Path("src/input.py").write_text("CHANGED=2\\n")\n'
            elif mutation=='added':child+='Path("src/new.py").write_text("ADDED=3\\n")\n'
            elif mutation=='deleted':child+='Path("src/input.py").unlink()\n'
            child+=f'sys.exit({child_code})\n'
            original_run=subprocess.run;calls=[]
            def child_run(command,**kwargs):
                calls.append(command)
                return original_run([sys.executable,'-c',child if len(calls)==1 else 'print("second-child")'],
                                    cwd=root,capture_output=True,text=True)
            frequencies=[x[0] for x in validator.pillbox_spectrum(.1,.2,6)]
            argv=['validate.py','--out',str(root/'output'),'--test-workers','1']+(['--skip-tests'] if skip else [])
            patches=[patch.object(validator,'ROOT',root),patch.object(sys,'argv',argv),
                     patch.object(validator.subprocess,'run',side_effect=child_run),
                     patch.object(validator,'solve',side_effect=numerical_error,return_value=SimpleNamespace(frequencies_hz=frequencies,mesh=SimpleNamespace(points=[None]))),
                     patch.object(validator,'save_run'),patch.object(validator,'quantities',return_value={'fixture':'not a FEM result'})]
            from contextlib import ExitStack
            with ExitStack() as stack:
                for context in patches:stack.enter_context(context)
                if numerical_error is None:code=validator.main()
                else:
                    with self.assertRaises(RuntimeError) as caught:validator.main()
                    self.assertIs(caught.exception,numerical_error);code=None
            out=root/'output'
            report=json.loads((out/'validation.json').read_text()) if (out/'validation.json').exists() else None
            audit=json.loads((out/'source-audit.json').read_text()) if (out/'source-audit.json').exists() else None
            logs={p.name:p.read_text() for p in out.glob('*.log')}
            return code,report,audit,logs,len(calls)

    def test_unchanged_full_scope_records_both_source_snapshots(self):
        code,report,audit,_,_=self.run_fixture()
        self.assertEqual(code,0);self.assertTrue(report['passed'])
        self.assertIsNotNone(audit);self.assertEqual(audit['status'],'UNCHANGED')
        self.assertEqual(audit['before'],audit['after']);self.assertEqual(report['source_sha256'],audit['after'])
        self.assertEqual(report['source_audit'],audit)

    def test_actual_child_content_addition_and_deletion_fail_acceptance(self):
        for mutation in ('changed','added','deleted'):
            code,report,audit,_,_=self.run_fixture(mutation=mutation)
            with self.subTest(mutation=mutation):
                self.assertNotEqual(code,0);self.assertFalse(report['passed'])
                self.assertEqual(audit['status'],'CHANGED')
                expected='src/new.py' if mutation=='added' else 'src/input.py'
                self.assertEqual(audit[mutation],[expected])

    def test_child_failure_keeps_log_exit_code_and_source_audit(self):
        code,report,audit,logs,calls=self.run_fixture(child_code=7)
        self.assertEqual(code,7);self.assertIsNotNone(report);self.assertFalse(report['passed'])
        self.assertEqual(audit['status'],'UNCHANGED');self.assertEqual(calls,1)
        self.assertIn('fixture-child-log',logs['tests.log']);self.assertEqual(report['tests']['status'],'FAIL')

    def test_skip_tests_remains_seed_only_with_audited_sources(self):
        code,report,audit,logs,calls=self.run_fixture(skip=True)
        self.assertEqual(code,0);self.assertEqual(report['scope'],'seed-numerics')
        self.assertEqual(report['tests']['status'],'NOT_RUN');self.assertEqual(calls,1)
        self.assertIn('unittest suite (--skip-tests)',report['not_performed'])
        self.assertNotIn('tests.log',logs);self.assertEqual(audit['status'],'UNCHANGED')

    def test_numerical_exception_retains_original_error_and_final_audit(self):
        error=RuntimeError('fixture numerical interruption')
        _,report,audit,_,_=self.run_fixture(numerical_error=error)
        self.assertIsNotNone(report);self.assertFalse(report['passed'])
        self.assertEqual(report['error_type'],'RuntimeError');self.assertEqual(audit['status'],'UNCHANGED')


if __name__=='__main__':unittest.main()
