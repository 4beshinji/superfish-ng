# SPDX-License-Identifier: Apache-2.0
"""Same analytical curve does not imply the same represented P2 domain."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from superfish_ng.adaptive_efficiency_domain import verify_efficiency_saved_domain
from superfish_ng.adaptive_efficiency_plan import build_adaptive_efficiency_plan
from superfish_ng.config import Case
from superfish_ng.curved_same_domain_tracking import compare_quadratic_space_boundaries
from superfish_ng.curved_space import case_curved_space
from superfish_ng.io import save_run
from superfish_ng.marked_refinement import refine_marked_cells
from superfish_ng.mesh import make_mesh
from superfish_ng.mesh_input import mesh_from_dict,mesh_to_dict
from superfish_ng.saved import read_solution
from superfish_ng.solver import solve


class AdaptiveEfficiencyDomainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=build_adaptive_efficiency_plan()

    def test_actual_curved_initial_and_uniform_full_case_source_boundary_and_changed_source_rejection(self):
        request=self.plan['cases'][1]['request'];case=Case.from_dict(request['case'])
        with tempfile.TemporaryDirectory() as tmp:
            for level in (0,1):
                current=replace(case,curved_refinement_levels=level)
                solution=solve(current)
                run=Path(tmp)/f'curved-{level}'
                save_run(current,solution,run)
                report=verify_efficiency_saved_domain(request,run)
                self.assertEqual(report['status'],'DOMAIN_VERIFIED')
                self.assertEqual(report['base_case'],case.to_dict())
                self.assertTrue(report['initial_source_mesh_exact_match'])
                self.assertGreater(report['boundary']['common_interval_count'],0)
                self.assertTrue(report['native_sources_unchanged'])
                self.assertIsNone(report['physical_error_bound'])
                self.assertEqual(report['individual_mode_identity_status'],'NOT_CHECKED')
                saved=read_solution(run)
                np.testing.assert_array_equal(saved.u,solution.u)
                changed=deepcopy(request)
                source=mesh_to_dict(make_mesh(case));source['triangles'].reverse()
                mesh_from_dict(case,source)  # Valid same boundary, different original source bytes/order.
                changed['initial_mesh']=source
                with self.assertRaisesRegex(ValueError,'initial source mesh'):
                    verify_efficiency_saved_domain(changed,run)

    def test_actual_affine_full_case_whole_tagged_boundary_both_uniform_levels(self):
        request=self.plan['cases'][0]['request'];case=Case.from_dict(request['case'])
        initial=make_mesh(case)
        refined=refine_marked_cells(case,initial,list(range(len(initial.triangles))),
                                   max_triangles=1000,minimum_angle_deg=5.).mesh
        with tempfile.TemporaryDirectory() as tmp:
            for level,mesh in enumerate((initial,refined)):
                solution=solve(case,mesh_data=mesh_to_dict(mesh))
                run=Path(tmp)/f'affine-{level}'
                save_run(case,solution,run)
                report=verify_efficiency_saved_domain(request,run)
                self.assertEqual(report['status'],'DOMAIN_VERIFIED')
                self.assertEqual(report['native_mesh_exact_initial_match'],level==0)
                self.assertGreater(report['boundary']['roundoff_tolerance_m'],0)
                self.assertEqual(report['individual_mode_identity_status'],'NOT_CHECKED')
                np.testing.assert_array_equal(read_solution(run).u,solution.u)

    def test_same_analytic_curves_changed_chords_fail_independent_p2_boundary_and_complete_case(self):
        request=self.plan['cases'][1]['request'];case=Case.from_dict(request['case'])
        finer=replace(case,contour=None,curve_chord_tolerance_m=case.curve_chord_tolerance_m/4)
        original=case_curved_space(case,make_mesh(case))
        changed=case_curved_space(finer,make_mesh(finer))
        self.assertEqual(case.curved_contour,finer.curved_contour)
        with self.assertRaisesRegex(ValueError,'quadratic boundary differs'):
            compare_quadratic_space_boundaries(case,original,finer,changed)
        solution=solve(finer)
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp)/'different-p2'
            save_run(finer,solution,run)
            read_solution(run)  # Valid native solve, independent of the N05 original Case.
            with self.assertRaisesRegex(ValueError,'complete original Case'):
                verify_efficiency_saved_domain(request,run)

    def test_unsupported_physics_and_linked_inputs_fail_before_native_reader(self):
        request=deepcopy(self.plan['cases'][0]['request'])
        request['case']['model']['polarization']='te'
        with patch('superfish_ng.adaptive_efficiency_domain.read_solution') as reader:
            with self.assertRaisesRegex(ValueError,'closed vacuum.*TM P2'):
                verify_efficiency_saved_domain(request,'missing')
            reader.assert_not_called()
        with tempfile.TemporaryDirectory() as tmp:
            actual=Path(tmp)/'actual';actual.mkdir()
            link=Path(tmp)/'linked';link.symlink_to(actual,target_is_directory=True)
            with patch('superfish_ng.adaptive_efficiency_domain.read_solution') as reader:
                with self.assertRaisesRegex(ValueError,'symlink'):
                    verify_efficiency_saved_domain(self.plan['cases'][0]['request'],link)
                reader.assert_not_called()

    def test_late_native_csv_mutation_detected_without_returning_domain_pass(self):
        request=self.plan['cases'][0]['request'];case=Case.from_dict(request['case'])
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp)/'late'
            save_run(case,solve(case),run)
            def late_read(path):
                result=read_solution(path)
                with (run/'axis_001.csv').open('a') as stream:stream.write('0,0\n')
                return result
            with patch('superfish_ng.adaptive_efficiency_domain.read_solution',side_effect=late_read):
                with self.assertRaisesRegex(ValueError,'native sources changed'):
                    verify_efficiency_saved_domain(request,run)


if __name__=='__main__':
    unittest.main()
