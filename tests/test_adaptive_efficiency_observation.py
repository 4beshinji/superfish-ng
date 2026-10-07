# SPDX-License-Identifier: Apache-2.0
"""Argument/result identity, independent clock partition and binding restoration."""
import types
import unittest
from superfish_ng.adaptive_efficiency_observation import observe_selected_calls
from superfish_ng.adaptive_efficiency_timing import PhaseRecorder


class AdaptiveEfficiencyObservationTests(unittest.TestCase):
    def module(self, function):
        module = types.ModuleType('n06_observed_worker_fixture')
        module.call = function
        return module

    def test_nested_actual_calls_keep_objects_and_partition_independent_clock(self):
        values = iter([0., 1., 2., 5., 8., 10.])
        recorder = PhaseRecorder(clock=lambda: next(values), rss_reader=lambda: None)
        argument, result, keyword = object(), object(), object()
        calls = []
        inner = self.module(lambda arg, *, option: calls.append((arg, option)) or result)
        outer = self.module(lambda arg, *, option: inner.call(arg, option=option))
        original = (outer.call, inner.call)
        with observe_selected_calls(recorder, [(outer, 'call', 'solve_overhead'), (inner, 'call', 'assembly')]):
            returned = outer.call(argument, option=keyword)
        self.assertIs(returned, result)
        self.assertIs(calls[0][0], argument)
        self.assertIs(calls[0][1], keyword)
        self.assertIs(outer.call, original[0])
        self.assertIs(inner.call, original[1])
        costs = recorder.finish()
        self.assertEqual([p['inclusive_seconds'] for p in costs['phases']], [7., 3.])
        self.assertEqual([p['exclusive_seconds'] for p in costs['phases']], [4., 3.])
        self.assertEqual(costs['recorded_phase_seconds'], 7.)
        self.assertEqual(costs['unattributed_seconds'], 3.)

    def test_same_exception_object_reraised_and_binding_restored(self):
        error = RuntimeError('original solver failure')
        def fail():
            raise error
        module = self.module(fail)
        recorder = PhaseRecorder()
        with self.assertRaises(RuntimeError) as caught:
            with observe_selected_calls(recorder, [(module, 'call', 'eigensolve')]):
                module.call()
        self.assertIs(caught.exception, error)
        self.assertIs(module.call, fail)
        cost = recorder.finish()
        self.assertEqual(cost['status'], 'FAILED')
        self.assertEqual(cost['phases'][0]['exception_type'], 'RuntimeError')

    def test_alias_consistency_duplicate_and_invalid_last_row_fail_before_changes(self):
        original = lambda: None
        module = self.module(original)
        other = self.module(original)
        for extra in ((module, 'call', 'one'), (other, 'call', 'two'),
                      (other, 'missing', 'one'), (other, 'call', ' ')):
            with self.subTest(extra=extra[1:]), self.assertRaises(ValueError):
                with observe_selected_calls(PhaseRecorder(), [(module, 'call', 'one'), extra]):
                    self.fail('invalid observation must not enter')
            self.assertIs(module.call, original)
            self.assertIs(other.call, original)

    def test_nested_observer_rejected_and_foreign_replacement_not_overwritten(self):
        original, replacement = lambda: None, lambda: None
        module = self.module(original)
        recorder = PhaseRecorder()
        with self.assertRaisesRegex(ValueError, 'changed outside'):
            with observe_selected_calls(recorder, [(module, 'call', 'one')]):
                observed = module.call
                with self.assertRaisesRegex(ValueError, 'original callable'):
                    with observe_selected_calls(recorder, [(module, 'call', 'one')]):
                        self.fail('nested observation must not enter')
                self.assertIs(module.call, observed)
                module.call = replacement
        self.assertIs(module.call, replacement)

    def test_partial_install_failure_restores_prior_binding_and_reraises(self):
        original = lambda: None
        module = self.module(original)
        error = RuntimeError('binding installation failed')
        class RefusingModule(types.ModuleType):
            def __setattr__(self, name, value):
                if name == 'call' and hasattr(self, 'call'):
                    raise error
                super().__setattr__(name, value)
        refusing = RefusingModule('n06_refusing_fixture')
        refusing.call = lambda: None
        with self.assertRaises(RuntimeError) as caught:
            with observe_selected_calls(PhaseRecorder(), [(module, 'call', 'one'), (refusing, 'call', 'two')]):
                self.fail('partial install must not enter')
        self.assertIs(caught.exception, error)
        self.assertIs(module.call, original)


if __name__ == '__main__':
    unittest.main()
