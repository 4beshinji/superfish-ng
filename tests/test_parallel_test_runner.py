# SPDX-License-Identifier: Apache-2.0
"""Exercise real isolated workers, fixture semantics and failure/cancel handling."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest

RUNNER = Path(__file__).resolve().parents[1]/'scripts/run_tests.py'


class ParallelTestRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.tests = self.root/'tests'; self.tests.mkdir()

    def module(self, name, content):
        (self.tests/(name+'.py')).write_text(textwrap.dedent(content))

    def run_fixture(self, name, workers=2):
        out = self.root/name
        result = subprocess.run([sys.executable,str(RUNNER),'--start-directory',str(self.tests),
            '--workers',str(workers),'--out',str(out)],cwd=self.root,capture_output=True,text=True,timeout=40)
        report = json.loads((out/'report.json').read_text()) if (out/'report.json').exists() else None
        return result, report

    def test_success_skip_expected_failure_and_class_fixtures_match_serial(self):
        self.module('test_a','''
            import unittest
            class Tests(unittest.TestCase):
                count=0
                @classmethod
                def setUpClass(cls):cls.count+=1
                def test_a(self):self.assertEqual(self.count,1)
                def test_b(self):self.assertEqual(self.count,1)
                @unittest.skip('explicit fixture skip')
                def test_skip(self):pass
                @unittest.expectedFailure
                def test_expected(self):self.fail('known fixture failure')
        ''')
        self.module('test_b','''
            import os,unittest
            class Tests(unittest.TestCase):
                def test_threads(self):
                    for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
                        self.assertEqual(os.environ[name],'1')
        ''')
        (self.root/'support.py').write_text('TOKEN=17\n')
        with (self.tests/'test_b.py').open('a') as stream:
            stream.write('\nfrom support import TOKEN\nassert TOKEN == 17\n')
        results=[]
        for workers in (1,2):
            result,report=self.run_fixture(f'run-{workers}',workers)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(report['tests_run'],5)
            self.assertEqual(report['counts'],dict(failures=0,errors=0,skipped=1,expected_failures=1,unexpected_successes=0))
            results.append([row['result']['test_ids'] for row in report['records']])
        self.assertEqual(*results)
        env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
        serial=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(self.tests),'-v'],env=env,cwd=self.root,capture_output=True,text=True)
        self.assertEqual(serial.returncode,0,serial.stderr)
        self.assertIn('Ran 5 tests',serial.stderr)
        self.assertIn('OK (skipped=1, expected failures=1)',serial.stderr)

    def test_failures_subtest_errors_import_errors_and_unexpected_success_fail(self):
        self.module('test_a','''
            import unittest
            class Tests(unittest.TestCase):
                def test_failure(self):
                    with self.subTest(value=2):self.assertEqual(2,3)
                def test_error(self):raise RuntimeError('fixture error')
                @unittest.expectedFailure
                def test_unexpected(self):pass
        ''')
        self.module('test_b',"raise ImportError('fixture import failure')")
        result,report=self.run_fixture('failed')
        self.assertEqual(result.returncode,1)
        self.assertEqual(report['counts']['failures'],1)
        self.assertEqual(report['counts']['errors'],2)
        self.assertEqual(report['counts']['unexpected_successes'],1)
        self.assertEqual(report['tests_run'],4)
        self.assertIn('fixture import failure',(self.root/'failed/tests.log').read_text())

    def test_abrupt_worker_exit_is_not_a_pass_and_other_modules_finish(self):
        self.module('test_a','''
            import os,unittest
            class Tests(unittest.TestCase):
                def test_crash(self):os._exit(73)
        ''')
        self.module('test_b','''
            import unittest
            class Tests(unittest.TestCase):
                def test_ok(self):pass
        ''')
        result,report=self.run_fixture('crashed')
        self.assertEqual(result.returncode,1)
        self.assertEqual(report['records'][0]['exit_code'],73)
        self.assertIn('error',report['records'][0])
        self.assertEqual(report['records'][1]['result']['tests_run'],1)
        self.assertEqual(report['discovered_tests'],2)

    def test_workers_really_overlap_and_preserve_each_module_fixture(self):
        for index in range(2):
            self.module(f'test_{index}',f'''
                import os,time,unittest
                from pathlib import Path
                class Tests(unittest.TestCase):
                    def test_barrier(self):
                        root=Path({str(self.root)!r})
                        (root/'ready-{index}').write_text(str(os.getpid()))
                        deadline=time.monotonic()+15
                        while not (root/'ready-{1-index}').exists():
                            self.assertLess(time.monotonic(),deadline,'workers did not overlap')
                            time.sleep(.01)
            ''')
        result,report=self.run_fixture('overlap')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(report['tests_run'],2)
        self.assertNotEqual((self.root/'ready-0').read_text(),(self.root/'ready-1').read_text())

    @unittest.skipUnless(os.name=='posix','POSIX process-group interruption check')
    def test_interrupt_stops_workers_and_their_child_processes(self):
        self.module('test_wait',f'''
            import os,subprocess,sys,time,unittest
            from pathlib import Path
            class Tests(unittest.TestCase):
                def test_wait(self):
                    child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'])
                    Path({str(self.root/'pids')!r}).write_text(str(os.getpid())+' '+str(child.pid))
                    time.sleep(60)
        ''')
        process=subprocess.Popen([sys.executable,str(RUNNER),'--start-directory',str(self.tests),
            '--out',str(self.root/'interrupt')],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            deadline=time.monotonic()+15
            while not (self.root/'pids').exists():
                self.assertIsNone(process.poll());self.assertLess(time.monotonic(),deadline);time.sleep(.02)
            pids=list(map(int,(self.root/'pids').read_text().split()))
            process.send_signal(signal.SIGINT)
            stdout,stderr=process.communicate(timeout=10)
            self.assertEqual(process.returncode,130,stdout+stderr)
            for pid in pids:
                # An adopted zombie has exited and cannot consume CPU or retain handles.
                path=Path(f'/proc/{pid}/stat')
                if path.exists():self.assertEqual(path.read_text().split(') ',1)[1].split()[0],'Z')
                else:
                    with self.assertRaises(ProcessLookupError):os.kill(pid,0)
        finally:
            if process.poll() is None:process.kill()
            process.communicate()

    def test_empty_inventory_bad_worker_count_and_existing_output_are_rejected(self):
        result,report=self.run_fixture('empty')
        self.assertNotEqual(result.returncode,0);self.assertIsNone(report)
        self.assertIn('no tests discovered',result.stderr)
        self.module('test_a','import unittest\nclass Tests(unittest.TestCase):\n def test_ok(self):pass\n')
        result,_=self.run_fixture('bad-count',0)
        self.assertNotEqual(result.returncode,0);self.assertFalse((self.root/'bad-count').exists())
        marker=self.root/'existing';marker.mkdir();(marker/'mine').write_text('preserve')
        result,_=self.run_fixture('existing')
        self.assertNotEqual(result.returncode,0);self.assertEqual((marker/'mine').read_text(),'preserve')


if __name__=='__main__':unittest.main()
