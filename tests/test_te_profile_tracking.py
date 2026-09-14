# SPDX-License-Identifier: Apache-2.0
"""TE profile volume pullback and real Maxwell similarity."""
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch
import tempfile
from pathlib import Path
import unittest
import numpy as np
from superfish_ng import Case,solve
from superfish_ng.model import Model
from superfish_ng.profile_mode_tracking import track_profile_modes
from superfish_ng.io import save_run
from superfish_ng.saved_mode_tracking import build_saved_mode_tracking,replay_mode_tracking

CONTROLS=dict(mapping='normalized_profile',sample_order=8,minimum_overlap=.98,
 minimum_assignment_margin=.05,relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)

class TEProfileTrackingTests(unittest.TestCase):
    def test_variable_volume_factor_independent_integral(self):
        def fake(profile):
            return SimpleNamespace(case=Case(tuple(profile),modes=1,model=Model(polarization='te')),
                reflection_source_case=None,frequencies_hz=np.array([1.]))
        a=fake([(0.,1.),(1.,1.)]);b=fake([(0.,1.),(1.,2.)])
        sampler=SimpleNamespace(evaluate=lambda points,*a,**kw:dict(Ephi_V_per_m=points[:,0]))
        with patch('superfish_ng.te_profile_tracking.TEFieldSampler',return_value=sampler):
            report=track_profile_modes(a,b,['A'],**(CONTROLS|dict(sample_order=3,minimum_overlap=.1)))
        # Ephi=r: cross integral contains R^2, norm contains R^4.
        expected=(7/3)/np.sqrt(31/5)
        self.assertAlmostEqual(report['matches'][0]['minimum_principal_overlap'],expected,places=14)
        self.assertNotAlmostEqual(expected,1.5/np.sqrt(7/3),places=3)

    def test_real_scale_saved_replay_and_sector_guard(self):
        case=Case(((0.,.07),(.025,.055),(.065,.1),(.1,.08)),nr=10,nz=16,modes=2,
                  element_order=2,model=Model(polarization='te'))
        for end in ['pec','magnetic_symmetry','electric_symmetry']:
            with self.subTest(end=end),tempfile.TemporaryDirectory() as directory:
                a=solve(replace(case,z_max=end));b=solve(replace(a.case,profile=tuple((2*z,2*r) for z,r in case.profile)))
                np.testing.assert_allclose(a.frequencies_hz,2*b.frequencies_hz,rtol=2e-12)
                for order in [8,12]:
                    report=track_profile_modes(a,b,['A','B'],**(CONTROLS|dict(sample_order=order)))
                    self.assertEqual(report['status'],'PASS')
                    self.assertEqual(report['current_mode_ids'],['A','B'])
                    self.assertEqual(report['physical_mapping']['field'],'Ephi_V_per_m')
                    self.assertGreater(min(m['minimum_principal_overlap'] for m in report['matches']),1-1e-12)
                root=Path(directory)
                save_run(a.case,a,root/'a');save_run(b.case,b,root/'b')
                request=dict(schema_version=1,previous_run=str(root/'a'),current_run=str(root/'b'),previous_ids=['A','B'],controls=CONTROLS)
                saved=build_saved_mode_tracking(request);self.assertEqual(replay_mode_tracking(saved),saved)
                altered=replace(b,case=replace(b.case,z_max='electric_symmetry' if end!='electric_symmetry' else 'pec'))
                with self.assertRaisesRegex(ValueError,'matching ends'):track_profile_modes(a,altered,['A','B'],**CONTROLS)

    def test_reflected_profiles_both_sides_orders_and_parities(self):
        from superfish_ng.symmetry import reflect_solution
        for order in [1,2]:
            for side in ['z_min','z_max']:
                for tag in ['electric_symmetry','magnetic_symmetry']:
                    with self.subTest(order=order,side=side,tag=tag),tempfile.TemporaryDirectory() as directory:
                        case=Case(((0.,.07),(.04,.09),(.1,.08)),nr=8,nz=12,modes=1,
                                  element_order=order,model=Model(polarization='te'),**{side:tag})
                        a=solve(case);b=solve(replace(case,profile=tuple((2*z,2*r) for z,r in case.profile)))
                        _,ar=reflect_solution(a.case,a);_,br=reflect_solution(b.case,b)
                        report=track_profile_modes(ar,br,['A'],**CONTROLS)
                        self.assertEqual(report['status'],'PASS')
                        self.assertTrue(report['physical_mapping']['reflected_partial_spectrum'])
                        self.assertIn('source symmetry-sector',report['physical_mapping']['mode_index_scope'])
                        with self.assertRaisesRegex(ValueError,'mix ordinary'):track_profile_modes(a,br,['A'],**CONTROLS)
                        root=Path(directory);save_run(ar.case,ar,root/'a');save_run(br.case,br,root/'b')
                        saved=build_saved_mode_tracking(dict(schema_version=1,previous_run=str(root/'a'),current_run=str(root/'b'),previous_ids=['A'],controls=CONTROLS))
                        self.assertEqual(replay_mode_tracking(saved),saved)

    def test_collinear_knots_and_mixed_physics(self):
        case=Case(((0.,1.),(.25,1.25),(1.,2.)),modes=1,model=Model(polarization='te'))
        a=SimpleNamespace(case=case,reflection_source_case=None,frequencies_hz=np.array([1.]))
        b=SimpleNamespace(case=replace(case,profile=((0.,1.),(.6,1.6),(1.,2.))),reflection_source_case=None,frequencies_hz=np.array([1.]))
        sampler=SimpleNamespace(evaluate=lambda points,*a,**kw:dict(Ephi_V_per_m=points[:,0]))
        with patch('superfish_ng.te_profile_tracking.TEFieldSampler',return_value=sampler):
            report=track_profile_modes(a,b,['A'],**CONTROLS)
        self.assertEqual(report['physical_mapping']['reference_breakpoints_zeta'],[0.,.25,.6,1.])
        self.assertAlmostEqual(report['matches'][0]['minimum_principal_overlap'],1.,places=14)
        b.case=replace(case,model=Model())
        with self.assertRaisesRegex(ValueError,'mixed TE/TM'):track_profile_modes(a,b,['A'],**CONTROLS)
