# SPDX-License-Identifier: Apache-2.0
"""Independent clock partitions; no FEM or synthetic solver timings."""
import unittest
from concurrent.futures import ThreadPoolExecutor
from superfish_ng.adaptive_efficiency_timing import PhaseRecorder


class Clock:
    def __init__(self): self.value = 100.0
    def __call__(self): return self.value
    def advance(self, seconds): self.value += seconds


class EfficiencyTimingTests(unittest.TestCase):
    def test_nested_partition_counts_each_observed_second_once(self):
        clock = Clock(); recorder = PhaseRecorder(clock=clock, rss_reader=lambda: 12345)
        clock.advance(2)
        with recorder.phase('execution'):
            clock.advance(1)
            with recorder.phase('assembly'): clock.advance(3)
            clock.advance(2)
            with recorder.phase('eigensolve'): clock.advance(5)
            clock.advance(1)
        clock.advance(4)
        result = recorder.finish()
        self.assertEqual(result['wall_seconds'], 18)
        self.assertEqual(result['recorded_phase_seconds'], 12)
        self.assertEqual(result['unattributed_seconds'], 6)
        self.assertEqual([p['inclusive_seconds'] for p in result['phases']], [12, 3, 5])
        self.assertEqual([p['exclusive_seconds'] for p in result['phases']], [4, 3, 5])
        self.assertEqual(sum(p['exclusive_seconds'] for p in result['phases']) + result['unattributed_seconds'], 18)
        self.assertEqual([p['parent_index'] for p in result['phases']], [None, 0, 0])
        self.assertEqual(result['peak_rss_bytes'], 12345)
        self.assertEqual(result['status'], 'COMPLETE')

    def test_real_failure_and_interrupt_preserve_observed_cost(self):
        for exception in (RuntimeError('solver failed'), KeyboardInterrupt()):
            with self.subTest(exception=type(exception).__name__):
                clock = Clock(); recorder = PhaseRecorder(clock=clock, rss_reader=lambda: None)
                with self.assertRaises(type(exception)):
                    with recorder.phase('solve'):
                        clock.advance(7); raise exception
                result = recorder.finish()
                self.assertEqual(result['status'], 'FAILED')
                self.assertEqual(result['phases'][0]['inclusive_seconds'], 7)
                self.assertEqual(result['phases'][0]['exception_type'], type(exception).__name__)
                self.assertIsNone(result['peak_rss_bytes'])
                self.assertEqual(result['memory_status'], 'UNKNOWN')

    def test_incomplete_phase_never_becomes_success_or_zero_cost(self):
        clock = Clock(); recorder = PhaseRecorder(clock=clock, rss_reader=lambda: 10)
        context = recorder.phase('unfinished'); context.__enter__(); clock.advance(5)
        try:
            result = recorder.snapshot()
            self.assertEqual(result['status'], 'INCOMPLETE')
            self.assertEqual(result['wall_seconds'], 5)
            self.assertIsNone(result['recorded_phase_seconds'])
            self.assertIsNone(result['phases'][0]['inclusive_seconds'])
            with self.assertRaisesRegex(ValueError, 'open phase'): recorder.finish()
        finally: context.__exit__(None, None, None)
        self.assertEqual(recorder.finish()['status'], 'COMPLETE')

    def test_broken_clock_is_unknown_and_original_failure_is_not_masked(self):
        clock = Clock(); recorder = PhaseRecorder(clock=clock, rss_reader=lambda: 10)
        with self.assertRaisesRegex(RuntimeError, 'original failure'):
            with recorder.phase('solve'):
                clock.value = 99; raise RuntimeError('original failure')
        clock.value = 101
        result = recorder.finish()
        self.assertEqual(result['status'], 'TIMING_UNVERIFIED')
        self.assertIsNone(result['wall_seconds'])
        self.assertIsNone(result['phases'][0]['inclusive_seconds'])
        self.assertEqual(result['phases'][0]['exception_type'], 'RuntimeError')
        self.assertTrue(result['timing_errors'])

    def test_nonfinite_clock_and_invalid_memory_do_not_fabricate_measurements(self):
        for invalid in (None, True, -1, '12', 3.5):
            with self.subTest(memory=invalid):
                recorder = PhaseRecorder(clock=Clock(), rss_reader=lambda: invalid)
                result = recorder.finish(); self.assertIsNone(result['peak_rss_bytes'])
                self.assertEqual(result['memory_status'], 'UNKNOWN')
        for invalid in (True, float('nan'), float('inf')):
            with self.subTest(clock=invalid), self.assertRaisesRegex(ValueError, 'clock'):
                PhaseRecorder(clock=lambda: invalid)

    def test_finished_summary_is_stable_copied_and_rejects_new_phases(self):
        clock = Clock(); recorder = PhaseRecorder(clock=clock, rss_reader=lambda: 10)
        with recorder.phase('save'): clock.advance(2)
        first = recorder.finish(); clock.advance(100)
        self.assertEqual(recorder.finish(), first)
        first['phases'][0]['name'] = 'forged'; first['wall_seconds'] = 0
        self.assertEqual(recorder.snapshot()['phases'][0]['name'], 'save')
        self.assertEqual(recorder.snapshot()['wall_seconds'], 2)
        with self.assertRaisesRegex(ValueError, 'finished'):
            with recorder.phase('late'): pass

    def test_foreign_thread_cannot_be_misattributed_as_a_nested_phase(self):
        clock = Clock(); recorder = PhaseRecorder(clock=clock, rss_reader=lambda: 10)
        def foreign():
            for operation in (recorder.snapshot, recorder.finish):
                with self.assertRaisesRegex(ValueError, 'original thread'): operation()
            with self.assertRaisesRegex(ValueError, 'original thread'):
                with recorder.phase('foreign'): pass
        with recorder.phase('original'):
            with ThreadPoolExecutor(max_workers=1) as pool: pool.submit(foreign).result()
            clock.advance(2)
        result = recorder.finish()
        self.assertEqual([p['name'] for p in result['phases']], ['original'])
        self.assertEqual(result['wall_seconds'], 2)


if __name__ == '__main__': unittest.main()
