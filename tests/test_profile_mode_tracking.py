# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import tempfile
import unittest
import numpy as np
from superfish_ng import Case,solve
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution
from superfish_ng.profile_mode_tracking import track_profile_modes
from superfish_ng.mode_tracking import track_cylindrical_modes
from superfish_ng.saved_mode_tracking import save_mode_tracking,read_mode_tracking
from superfish_ng.mode_tracking_history import start_mode_history,extend_mode_history

CONTROLS=dict(minimum_overlap=.98,minimum_assignment_margin=.05,relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)

class ProfileMapMeasureTests(unittest.TestCase):
    def fake(self,profile):return SimpleNamespace(case=Case(tuple(profile),modes=1),frequencies_hz=np.array([1.]))

    def test_variable_volume_factor_matches_independent_polynomial_integral(self):
        a=self.fake([(0.,1.),(1.,1.)]);b=self.fake([(0.,1.),(1.,2.)])
        sampler=SimpleNamespace(evaluate=lambda points,*a,**kw:dict(Hphi_A_per_m=points[:,0]))
        with patch('superfish_ng.profile_mode_tracking.FieldSampler.from_solution',return_value=sampler):
            report=track_profile_modes(a,b,['A'],mapping='normalized_profile',sample_order=3,**dict(CONTROLS,minimum_overlap=.1))
        expected=(7/3)/np.sqrt(31/5)
        self.assertAlmostEqual(report['matches'][0]['minimum_principal_overlap'],expected,places=14)
        self.assertNotAlmostEqual(expected,1.5/np.sqrt(7/3),places=3)

    def test_common_knots_and_redundant_collinear_breakpoint_invariance(self):
        a=self.fake([(0.,1.),(.25,1.25),(1.,2.)]);b=self.fake([(0.,1.),(.6,1.6),(1.,2.)])
        sampler=SimpleNamespace(evaluate=lambda points,*a,**kw:dict(Hphi_A_per_m=points[:,0]))
        with patch('superfish_ng.profile_mode_tracking.FieldSampler.from_solution',return_value=sampler):
            report=track_profile_modes(a,b,['A'],mapping='normalized_profile',sample_order=3,**CONTROLS)
        self.assertEqual(report['physical_mapping']['reference_breakpoints_zeta'],[0.,.25,.6,1.])
        self.assertAlmostEqual(sum(report['physical_mapping']['reference_weights']),.5,places=14)
        self.assertAlmostEqual(report['matches'][0]['minimum_principal_overlap'],1.,places=14)

    def test_unsupported_geometry_symmetry_and_controls_rejected(self):
        a=self.fake([(0.,1.),(1.,1.)])
        for changes in [dict(z_max='magnetic_symmetry'),dict(geometry_type='stepped_profile')]:
            b=SimpleNamespace(case=replace(a.case,**changes),frequencies_hz=a.frequencies_hz)
            with self.assertRaisesRegex(ValueError,'closed PEC'):track_profile_modes(a,b,['A'],mapping='normalized_profile',sample_order=3,**CONTROLS)
        for order in [True,1,257]:
            with self.assertRaisesRegex(ValueError,'sample_order'):track_profile_modes(a,a,['A'],mapping='normalized_profile',sample_order=order,**CONTROLS)

class ProfileMapFEMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup);cls.root=Path(cls.tmp.name)
        cls.case=Case(((0.,.07),(.025,.055),(.065,.1),(.1,.08)),nr=10,nz=16,modes=3,element_order=2)
        cls.base=solve(cls.case);cls.scaled_case=replace(cls.case,profile=tuple((2*z,2*r) for z,r in cls.case.profile));cls.scaled=solve(cls.scaled_case)
        save_run(cls.case,cls.base,cls.root/'a');save_run(cls.scaled_case,cls.scaled,cls.root/'b')
        cls.base=read_solution(cls.root/'a');cls.scaled=read_solution(cls.root/'b')

    def test_maxwell_similarity_and_sample_order_stability(self):
        np.testing.assert_allclose(self.base.frequencies_hz,2*self.scaled.frequencies_hz,rtol=2e-12)
        for order in [8,12]:
            report=track_profile_modes(self.base,self.scaled,['A','B','C'],mapping='normalized_profile',sample_order=order,**CONTROLS)
            self.assertEqual(report['status'],'PASS');self.assertEqual(report['current_mode_ids'],['A','B','C'])
            self.assertGreater(min(m['minimum_principal_overlap'] for m in report['matches']),1-1e-12)

    def test_saved_profile_mapping_and_history(self):
        controls=dict(CONTROLS,mapping='normalized_profile',sample_order=8)
        request=dict(schema_version=1,previous_run='a',current_run='b',previous_ids=['A','B','C'],controls=controls)
        path=self.root/'tracking.json';report=save_mode_tracking(request,path,base_directory=self.root)
        self.assertEqual(read_mode_tracking(path),report)
        history=extend_mode_history(start_mode_history(report),dict(current_run='a',controls=controls),base_directory=self.root)
        self.assertEqual(history['status'],'PASS');self.assertEqual(history['current_mode_ids'],['A','B','C'])

    def test_cylinder_mapping_agrees_in_constant_radius_limit(self):
        saved=[]
        for i,length in enumerate((.055,.075)):
            case=Case(((0.,.1),(length,.1)),nr=8,nz=8,modes=3,element_order=2)
            path=self.root/f'cylinder-{i}';save_run(case,solve(case),path);saved.append(read_solution(path))
        a,b=saved
        old=track_cylindrical_modes(a,b,['A','B','C'],mapping='normalized_cylinder',sample_order=12,**CONTROLS)
        new=track_profile_modes(a,b,['A','B','C'],mapping='normalized_profile',sample_order=12,**CONTROLS)
        self.assertEqual(old['current_mode_ids'],new['current_mode_ids'])
        np.testing.assert_allclose(old['overlap_matrix'],new['overlap_matrix'],atol=2e-14,rtol=0)
