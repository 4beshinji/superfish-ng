# SPDX-License-Identifier: Apache-2.0
"""Matching TE cylinder sectors retain physical IDs and complete native replay."""
from pathlib import Path
from dataclasses import replace
from copy import deepcopy
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from scipy.special import jn_zeros
from superfish_ng import Case,solve
from superfish_ng.model import Model
from superfish_ng.io import save_run
from superfish_ng.symmetry import reflect_solution
from superfish_ng.mode_tracking import track_cylindrical_modes,tracked_frequency_hz
from superfish_ng.saved_mode_tracking import build_saved_mode_tracking,replay_mode_tracking
from test_te_mode_tracking import CONTROLS


class TESectorTrackingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name);cls.data={};roots=jn_zeros(1,4)
        for tag,offset,delta in [('magnetic_symmetry',1,8),('electric_symmetry',2,12)]:
            aspect=np.pi*np.sqrt(delta/(roots[1]**2-roots[0]**2))/2
            for stage,factor,count in [('a',.97,4),('b',1.03,4),('cross',1.,4),('short',1.03,2)]:
                ratio=float(aspect*factor)
                case=Case(((0.,.1),(.1*ratio,.1)),nr=24,nz=36,modes=count,element_order=2,
                          normalization_j=.5,z_max=tag,model=Model(polarization='te'))
                half=solve(case);full,reflected=reflect_solution(case,half)
                spectrum=sorted((np.hypot(root,p*np.pi/(2*ratio)),n,p) for n,root in enumerate(roots,1) for p in range(offset,14,2))[:count]
                labels=[f'r{n}p{p}' for _,n,p in spectrum]
                for domain,solution in [('half',half),('full',reflected)]:
                    path=cls.root/f'{tag}-{stage}-{domain}';save_run(solution.case,solution,path)
                    cls.data[tag,stage,domain]=(solution,path,labels)

    def test_crossing_ids_and_actual_input_field_scaling(self):
        for tag in ('magnetic_symmetry','electric_symmetry'):
            for domain in ('half','full'):
                a,_,ids=self.data[tag,'a',domain];b,_,expected=self.data[tag,'b',domain]
                result=track_cylindrical_modes(a,b,ids,**CONTROLS)
                self.assertEqual(result['status'],'PASS');self.assertEqual(result['current_mode_ids'],expected)
                self.assertEqual(result['physical_mapping']['boundary_conditions'],['pec',tag])
                self.assertEqual(result['physical_mapping']['reflected_partial_spectrum'],domain=='full')
                self.assertIn('not full-spectrum',result['physical_mapping']['mode_index_scope'])
                for i,identifier in enumerate(expected):self.assertEqual(tracked_frequency_hz(result,identifier),b.frequencies_hz[i])
                altered=track_cylindrical_modes(replace(a,coefficients_v_per_m2=a.coefficients_v_per_m2*[1,-2,3,-4]),replace(b,coefficients_v_per_m2=b.coefficients_v_per_m2*[-.5,1,2,3]),ids,**CONTROLS)
                self.assertEqual(altered['current_mode_ids'],expected)

    def test_degenerate_ids_remain_a_set_and_band_exit_abstains(self):
        for tag in ('magnetic_symmetry','electric_symmetry'):
            for domain in ('half','full'):
                cross,_,ids=self.data[tag,'cross',domain];short,_,_=self.data[tag,'short',domain]
                result=track_cylindrical_modes(cross,cross,ids,**CONTROLS)
                group=next(m for m in result['matches'] if m['dimension']==2)
                for identifier in group['previous_ids']:
                    with self.assertRaisesRegex(ValueError,'subspace'):tracked_frequency_hz(result,identifier)
                result=track_cylindrical_modes(cross,short,ids,**CONTROLS)
                self.assertEqual(result['status'],'UNVERIFIED')
                with self.assertRaisesRegex(ValueError,'UNVERIFIED'):tracked_frequency_hz(result,ids[0])

    def test_saved_sector_metadata_and_source_fields_replay(self):
        for tag in ('magnetic_symmetry','electric_symmetry'):
            for domain in ('half','full'):
                _,a,ids=self.data[tag,'a',domain];_,b,_=self.data[tag,'b',domain]
                request=dict(schema_version=1,previous_run=str(a),current_run=str(b),previous_ids=ids,controls=CONTROLS)
                result=build_saved_mode_tracking(request);self.assertEqual(replay_mode_tracking(result),result)
                if domain=='full':self.assertTrue(all('source_fields.npz' in s['sha256'] for s in result['sources']))
                altered=deepcopy(result);altered['tracking']['physical_mapping']['boundary_conditions']=['pec','pec']
                with self.assertRaisesRegex(ValueError,'replay'):replay_mode_tracking(altered)

    def test_changed_reflection_source_during_tracking_rejected(self):
        _,a,ids=self.data['magnetic_symmetry','a','full'];_,b,_=self.data['magnetic_symmetry','b','full']
        target=a/'source_fields.npz';original=target.read_bytes()
        def changed(*args,**kwargs):
            result=track_cylindrical_modes(*args,**kwargs);target.write_bytes(original+b'changed after sampling');return result
        try:
            with patch('superfish_ng.saved_mode_tracking.track_cylindrical_modes',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'source changed'):
                    build_saved_mode_tracking(dict(schema_version=1,previous_run=str(a),current_run=str(b),previous_ids=ids,controls=CONTROLS))
        finally:target.write_bytes(original)

    def test_boundary_and_representation_mismatches_rejected(self):
        a,_,ids=self.data['magnetic_symmetry','a','half'];b,_,_=self.data['electric_symmetry','b','half'];full,_,_=self.data['magnetic_symmetry','a','full']
        with self.assertRaisesRegex(ValueError,'matching ends'):track_cylindrical_modes(a,b,ids,**CONTROLS)
        with self.assertRaisesRegex(ValueError,'mix ordinary and reflected'):track_cylindrical_modes(a,full,ids,**CONTROLS)
        two=replace(a,case=replace(a.case,z_min='magnetic_symmetry'))
        with self.assertRaisesRegex(ValueError,'at most one'):track_cylindrical_modes(two,two,ids,**CONTROLS)
        forged=replace(full,reflection_source_case=replace(a.case,z_max='pec'))
        with self.assertRaisesRegex(ValueError,'source symmetry'):track_cylindrical_modes(forged,forged,ids,**CONTROLS)

    def test_closed_pec_mapping_contract_is_unchanged_and_curved_is_rejected(self):
        from test_curved_reflection import half_case
        source,_,_=self.data['magnetic_symmetry','a','half']
        closed=solve(replace(source.case,z_max='pec',modes=1,nr=8,nz=12))
        mapping=track_cylindrical_modes(closed,closed,['mode'],**CONTROLS)['physical_mapping']
        self.assertNotIn('boundary_conditions',mapping)
        self.assertNotIn('reflected_partial_spectrum',mapping)
        self.assertEqual(mapping['scope'],'closed PEC TE cylinders only; real peak Ephi pointwise pullback; quadrature accuracy must be checked separately')
        case=replace(half_case('z_max','magnetic_symmetry'),model=Model(polarization='te'))
        curved=solve(case);_,reflected=reflect_solution(case,curved)
        for solution in (curved,reflected):
            with self.assertRaisesRegex(ValueError,'straight constant-radius'):
                track_cylindrical_modes(solution,solution,['mode'],**CONTROLS)
