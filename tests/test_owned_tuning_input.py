# SPDX-License-Identifier: Apache-2.0
"""Select all three owned tuning input formats without running a FEM trial."""
from contextlib import ExitStack
from copy import deepcopy
import unittest
from unittest.mock import patch

from support.hphi_tuning_fixtures import straight_worker_request
from support.curved_hphi_tuning_fixtures import curved_tune_request
from support.material_hphi_tuning_fixtures import material_tune_request


class OwnedTuningInputTests(unittest.TestCase):
    def check_format(self, adapter, request_factory):
        # Preflight must not turn a metadata check into a trial or a solve.
        with ExitStack() as stack:
            for binding in ('superfish_ng.hphi_tuning.solve_hphi',
                            'superfish_ng.curved_hphi_tuning.solve_curved_hphi',
                            'superfish_ng.material_hphi_tuning.solve_material_hphi'):
                stack.enter_context(patch(binding, side_effect=AssertionError('input validation solved a FEM')))
            request = request_factory()
            data = dict(request=request, max_new_trials=1, checkpoint=None)
            original = deepcopy(data)
            self.assertEqual(adapter._input(data), data)
            self.assertEqual(data, original)
            for value in (0, -1, True, 1.5, float('nan')):
                with self.subTest(max_new_trials=value):
                    with self.assertRaises(ValueError):
                        adapter._input(dict(data, max_new_trials=value))
            for change in (dict(schema_version=True), dict(target_hz=float('nan')), dict(extra=1)):
                with self.subTest(request_change=change):
                    with self.assertRaises(ValueError):
                        adapter._input(dict(data, request=dict(request, **change)))
            for foreign in (straight_worker_request, curved_tune_request, material_tune_request):
                if foreign is request_factory:
                    continue
                with self.subTest(foreign_format=foreign.__name__):
                    with self.assertRaises(ValueError):
                        adapter._input(dict(data, request=foreign()))
            with self.assertRaises(ValueError):
                adapter._input(dict(data, unknown=1))
            self.assertEqual(data, original)

    def test_straight_format_preflight_without_fem(self):
        from superfish_ng import hphi_tuning_jobs
        self.check_format(hphi_tuning_jobs, straight_worker_request)

    def test_curved_format_preflight_without_fem(self):
        from superfish_ng import curved_hphi_tuning_jobs
        self.check_format(curved_hphi_tuning_jobs, curved_tune_request)

    def test_material_format_preflight_without_fem(self):
        from superfish_ng import material_hphi_tuning_jobs
        self.check_format(material_hphi_tuning_jobs, material_tune_request)
