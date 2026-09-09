# SPDX-License-Identifier: Apache-2.0
"""TE refinement must independently assess frequency, both fields and RF."""
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from scipy.special import jn_zeros
from superfish_ng import Case, solve
from superfish_ng.model import Model
from superfish_ng.io import save_run
from superfish_ng.studies import compare_refinement
from superfish_ng import te_convergence


class TEConvergenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name);cls.cases={}
        for order in (1,2):
            for n in (8,16):
                case=Case(((0.,.1),(.2,.1)),nr=n,nz=3*n//2,modes=2,
                          element_order=order,model=Model(polarization='te'))
                name=f'p{order}-n{n}';cls.cases[name]=case
                save_run(case,solve(case),cls.root/name)

    def test_identical_native_fields_have_zero_changes(self):
        result=compare_refinement(self.root/'p2-n8',self.root/'p2-n8')
        self.assertEqual(result['status'],'PASS')
        for mode in result['modes']:
            self.assertLess(mode['electric_relative_l2'],1e-7)
            self.assertLess(mode['magnetic_relative_l2'],1e-7)
            self.assertTrue(all(v==0 for v in mode['relative_changes'].values()))
            self.assertNotIn('r_over_q_accelerator_ohm',mode['relative_changes'])

    def test_coarse_refinement_does_not_hide_magnetic_or_rf_changes(self):
        result=compare_refinement(self.root/'p1-n8',self.root/'p1-n16')
        self.assertNotEqual(result['status'],'PASS')
        self.assertTrue(any(not m['gates']['magnetic_field'] for m in result['modes']))
        self.assertTrue(any(not m['gates']['rf'] for m in result['modes']))
        self.assertIn('orders 3 and 5',result['sampling'])

    def test_normalization_change_is_not_mesh_convergence(self):
        case=replace(self.cases['p2-n8'],normalization_j=4.)
        target=self.root/'different-energy';save_run(case,solve(case),target)
        with self.assertRaisesRegex(ValueError,'identical physical cases'):
            compare_refinement(self.root/'p2-n8',target)

    def test_near_degenerate_pair_remains_unverified_even_against_itself(self):
        roots=jn_zeros(1,2);ratio=float(np.pi*np.sqrt(8/(roots[1]**2-roots[0]**2)))
        case=Case(((0.,.1),(.1*ratio,.1)),nr=20,nz=30,modes=4,
                  element_order=2,model=Model(polarization='te'))
        path=self.root/'cluster';save_run(case,solve(case),path)
        result=compare_refinement(path,path)
        self.assertEqual(result['status'],'UNVERIFIED')
        self.assertEqual([m['status'] for m in result['modes'][-2:]],['UNVERIFIED','UNVERIFIED'])

    def test_mutation_during_comparison_is_rejected(self):
        path=self.root/'p2-n8';target=path/'axis_001.csv';original=target.read_bytes()
        integrate=te_convergence._integrals
        def changed(*args):
            result=integrate(*args);target.write_bytes(original+b'\n');return result
        try:
            with patch.object(te_convergence,'_integrals',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'source changed during comparison'):
                    compare_refinement(path,path)
        finally:target.write_bytes(original)

    def test_sign_choices_do_not_change_refinement_diagnostics(self):
        from superfish_ng.te_saved import read_te_run
        source=self.root/'p2-n8';solution=read_te_run(source)
        flipped=replace(solution,coefficients_v_per_m2=-solution.coefficients_v_per_m2)
        path=self.root/'flipped';save_run(solution.case,flipped,path)
        result=compare_refinement(source,path)
        self.assertEqual(result['status'],'PASS')
        self.assertTrue(all(m['magnetic_relative_l2']<1e-7 for m in result['modes']))

    def test_mesh_study_uses_te_electric_magnetic_and_rf_comparisons(self):
        from superfish_ng.studies import Study,execute_study
        from superfish_ng.project import Project
        case=replace(self.cases['p2-n16'],modes=1)
        result=execute_study(Study(Project(case),'mesh_convergence','mesh_scale',[1,2]),self.root/'study')
        self.assertEqual(result['comparisons'][0]['physics'],'axisymmetric_m0_te')
        self.assertEqual(result['numerical_status'],'PASS')
        self.assertEqual(set(result['comparisons'][0]['modes'][0]['gates']),
                         {'frequency','electric_field','magnetic_field','rf'})

    def test_fixed_curved_study_preserves_source_geometry(self):
        from superfish_ng.studies import Study,execute_study
        from superfish_ng.project import Project
        from test_te_curved import sphere
        case=replace(sphere(),modes=1)
        result=execute_study(Study(Project(case),'fixed_geometry_convergence',
                                  '/case/mesh/curved_refinement_levels',[0,1]),self.root/'curved-study')
        self.assertEqual(result['comparisons'][0]['physics'],'axisymmetric_m0_te')
        self.assertIn('without curve reprojection',result['geometry_refinement'])
        self.assertIsNone(result['points'][0]['modes'][0]['r_over_q_accelerator_ohm'])

    def test_mixed_polarizations_are_rejected(self):
        case=replace(self.cases['p2-n8'],model=Model(polarization='tm'))
        target=self.root/'tm';save_run(case,solve(case),target)
        with self.assertRaisesRegex(ValueError,'mixed TE/TM'):
            compare_refinement(self.root/'p2-n8',target)

    def test_magnetic_symmetry_has_its_own_valid_refinement(self):
        from superfish_ng.studies import Study,execute_study
        from superfish_ng.project import Project
        case=replace(self.cases['p2-n16'],profile=((0.,.1),(.1,.1)),modes=1,
                     z_max='magnetic_symmetry',normalization_j=.5)
        report=execute_study(Study(Project(case),'mesh_convergence','mesh_scale',[1,2]),self.root/'magnetic-half')
        self.assertEqual(report['numerical_status'],'PASS')
        self.assertEqual(report['comparisons'][0]['physics'],'axisymmetric_m0_te')
