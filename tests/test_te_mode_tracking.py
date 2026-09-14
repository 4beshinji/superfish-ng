# SPDX-License-Identifier: Apache-2.0
"""Real TE crossings, degenerate subspaces and complete native replay."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from scipy.special import jn_zeros
from superfish_ng import Case,solve
from superfish_ng.model import Model
from superfish_ng.io import save_run
from superfish_ng.mode_tracking import track_cylindrical_modes,tracked_frequency_hz
from superfish_ng.saved_mode_tracking import build_saved_mode_tracking,replay_mode_tracking

CONTROLS=dict(mapping='normalized_cylinder',sample_order=24,minimum_overlap=.98,
              minimum_assignment_margin=.05,relative_cluster_gap=.001,minimum_relative_singular_value=1e-8)


class TEModeTrackingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup);cls.root=Path(cls.tmp.name)
        roots=jn_zeros(1,3);ratio=np.pi*np.sqrt(8/(roots[1]**2-roots[0]**2))
        cls.solutions=[];cls.labels=[]
        for name,factor in [('a',.97),('b',1.03),('cross',1.)]:
            case=Case(((0.,.1),(.1*ratio*factor,.1)),nr=24,nz=36,element_order=2,modes=6,model=Model(polarization='te'))
            solution=solve(case);cls.solutions.append(solution);save_run(case,solution,cls.root/name)
            spectrum=sorted((np.hypot(chi,n*np.pi/(ratio*factor)),p,n) for p,chi in enumerate(roots,1) for n in range(1,7))[:6]
            cls.labels.append([f'r{p}z{n}' for _,p,n in spectrum])

    def request(self):
        return dict(schema_version=1,previous_run=str(self.root/'a'),current_run=str(self.root/'b'),previous_ids=self.labels[0],controls=CONTROLS.copy())

    def test_real_crossing_ids_and_electric_mapping(self):
        result=track_cylindrical_modes(*self.solutions[:2],self.labels[0],**CONTROLS)
        self.assertEqual(result['status'],'PASS');self.assertEqual(result['current_mode_ids'],self.labels[1])
        self.assertNotEqual(self.labels[0][2:4],self.labels[1][2:4])
        self.assertEqual(result['physical_mapping']['field'],'Ephi_V_per_m')
        for i,name in enumerate(self.labels[1]):self.assertEqual(tracked_frequency_hz(result,name),self.solutions[1].frequencies_hz[i])

    def test_degeneracy_only_identifies_subspace_and_exit_is_unverified(self):
        cross=self.solutions[2];result=track_cylindrical_modes(cross,cross,self.labels[2],**CONTROLS)
        self.assertEqual(result['status'],'PASS');group=next(m for m in result['matches'] if m['dimension']==2)
        for name in group['previous_ids']:
            with self.assertRaisesRegex(ValueError,'subspace'):tracked_frequency_hz(result,name)
        short=solve(replace(self.solutions[1].case,modes=2))
        result=track_cylindrical_modes(self.solutions[0],short,self.labels[0],**CONTROLS)
        self.assertEqual(result['status'],'UNVERIFIED')
        with self.assertRaisesRegex(ValueError,'UNVERIFIED'):tracked_frequency_hz(result,self.labels[0][0])

    def test_saved_replay_covers_all_te_files_and_rejects_tampering(self):
        result=build_saved_mode_tracking(self.request());self.assertEqual(replay_mode_tracking(result),result)
        for source in result['sources']:
            self.assertIn('te_complete.json',source['sha256']);self.assertIn('axis_006.csv',source['sha256']);self.assertIn('mode_006.vtk',source['sha256'])
        altered=deepcopy(result);altered['tracking']['physical_mapping']['field']='Hphi_A_per_m'
        with self.assertRaisesRegex(ValueError,'replay'):replay_mode_tracking(altered)
        target=self.root/'a'/'axis_001.csv';original=target.read_bytes()
        try:
            target.write_bytes(original+b'\n')
            with self.assertRaises(ValueError):build_saved_mode_tracking(self.request())
        finally:target.write_bytes(original)

    def test_mixed_physics_and_unsupported_mapping_rejected(self):
        from superfish_ng.saved import read_solution
        case=replace(self.solutions[0].case,model=Model(),modes=2)
        save_run(case,solve(case),self.root/'tm')
        tm=read_solution(self.root/'tm')
        with self.assertRaisesRegex(ValueError,'mixed TE/TM'):track_cylindrical_modes(self.solutions[0],tm,self.labels[0],**CONTROLS)
        request=self.request();request['controls']['mapping']='same_domain'
        with self.assertRaisesRegex(ValueError,'normalized_cylinder'):build_saved_mode_tracking(request)
        with self.assertRaisesRegex(ValueError,'sample_order'):track_cylindrical_modes(*self.solutions[:2],self.labels[0],**(CONTROLS|dict(sample_order=True)))

    def test_csv_change_during_tracking_rejected(self):
        target=self.root/'a'/'axis_001.csv';original=target.read_bytes()
        def changed(*args,**kwargs):
            result=track_cylindrical_modes(*args,**kwargs);target.write_bytes(original+b'\n');return result
        try:
            with patch('superfish_ng.saved_mode_tracking.track_cylindrical_modes',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'source changed'):build_saved_mode_tracking(self.request())
        finally:target.write_bytes(original)
