# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from pathlib import Path
import tempfile,unittest
import numpy as np
from test_curved_hphi_field_overlap import case
from superfish_ng.curved_hphi import solve_curved_hphi
from superfish_ng.curved_hphi_refinement import refine_curved_hphi_geometry
from superfish_ng.curved_hphi_comparison import CurvedHphiComparisonDomain


def request(a,b,mapping='same_vacuum'):
    from superfish_ng.curved_hphi_tracking import CurvedHphiTrackingRequest
    x,y=(refine_curved_hphi_geometry(s.case.geometry) for s in (a,b))
    domain=CurvedHphiComparisonDomain(a.case.geometry,b.case.geometry,mapping,restriction_policy='binary64_roundoff')
    return CurvedHphiTrackingRequest(domain,x.geometry,y.geometry,
        previous_comparison_cells=x.native_cells,current_comparison_cells=y.native_cells)


class CurvedHphiTrackingTests(unittest.TestCase):
    def test_same_native_fields_phase_and_guard(self):
        for axis in (False,True):
            a=solve_curved_hphi(case(axis,n=2));before=a.coefficients.copy()
            from superfish_ng.curved_hphi_tracking import track_curved_hphi_modes
            q=request(a,a);report=track_curved_hphi_modes(a,a,q)
            self.assertEqual(report['status'],'PASS',report['verification_reasons'])
            self.assertEqual(report['current_mode_ids'],['mode-1','mode-2'])
            flipped=replace(a,coefficients=-a.coefficients)
            other=track_curved_hphi_modes(a,flipped,q)
            self.assertEqual(other['status'],'PASS',other['verification_reasons'])
            self.assertEqual([m['previous_phase_multiplier'] for m in other['matches']],[-1,-1])
            guarded=track_curved_hphi_modes(a,a,replace(q,controls=replace(q.controls,relative_cluster_gap=.9)))
            self.assertEqual(guarded['status'],'UNVERIFIED')
            self.assertTrue(any(guarded['guard_overlap']))
            self.assertEqual(guarded['current_mode_ids'],[None,None])
            np.testing.assert_array_equal(a.coefficients,before)

    def test_strict_request_roundtrip_and_owned_declarations(self):
        from superfish_ng.curved_hphi_tracking import CurvedHphiTrackingRequest
        a=solve_curved_hphi(case());q=request(a,a)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'request.json';q.save(p)
            self.assertEqual(q.to_dict(),CurvedHphiTrackingRequest.load(p).to_dict())
            with self.assertRaises(FileExistsError):q.save(p)
        for name,value in (('tracking_version',True),('previous_mode_count',True),('previous_mode_ids',['a','a']),
                           ('max_sample_points',0),('extra',0),('previous_cells',[{'base_cell':True,'reference_vertices':[]}])):
            raw=q.to_dict();raw[name]=value
            with self.assertRaises(ValueError):CurvedHphiTrackingRequest.from_dict(raw)
        raw=q.to_dict();restored=CurvedHphiTrackingRequest.from_dict(raw)
        raw['previous_comparison_cells'][0]['base_cell']=999
        self.assertEqual(q.to_dict(),restored.to_dict())

    def test_declared_scale_and_inherited_subspace(self):
        from superfish_ng.curved_hphi_tracking import track_curved_hphi_modes
        a=solve_curved_hphi(case(n=2));b=solve_curved_hphi(case(n=2,scale=2.))
        np.testing.assert_allclose(b.frequencies_hz,a.frequencies_hz/2,rtol=1e-9)
        q=request(a,b,'declared_quadratic');report=track_curved_hphi_modes(a,b,q)
        self.assertEqual(report['status'],'PASS',report['verification_reasons'])
        self.assertEqual(report['current_mode_ids'],['mode-1','mode-2'])
        grouped=replace(q,previous_mode_ids=None,previous_identity_groups=[dict(indices=[1,2],ids=['a','b'])])
        result=track_curved_hphi_modes(a,b,grouped)
        self.assertEqual(result['status'],'PASS',result['verification_reasons'])
        self.assertFalse(result['individual_ids_complete'])
        self.assertEqual(result['current_mode_ids'],[None,None])
        self.assertEqual(result['matches'][0]['previous_ids'],['a','b'])
        self.assertIsNone(result['matches'][0]['previous_phase_multiplier'])

    def test_missing_guard_budget_and_modified_original_refused(self):
        from superfish_ng.curved_hphi_tracking import track_curved_hphi_modes
        a=solve_curved_hphi(case());q=request(a,a)
        with self.assertRaisesRegex(ValueError,'guard mode'):
            track_curved_hphi_modes(a,a,replace(q,previous_mode_count=3,previous_mode_ids=['a','b','c']))
        with self.assertRaises(ValueError):track_curved_hphi_modes(a,a,replace(q,max_sample_points=1))
        with self.assertRaises(ValueError):track_curved_hphi_modes(replace(a,coefficients=a.coefficients*1.01),a,q)

    def test_explicit_original_chart_preserves_native_cell_numbering(self):
        from superfish_ng.curved_hphi_tracking import track_curved_hphi_modes
        from superfish_ng.curved_meridional_geometry import CurvedMeridionalGeometry
        a=solve_curved_hphi(case(n=2));q=request(a,a)
        raw=a.case.geometry.to_dict()
        raw['base_mesh']['triangles']=raw['base_mesh']['triangles'][::-1]
        b=solve_curved_hphi(replace(a.case,geometry=CurvedMeridionalGeometry.from_dict(raw)))
        cells=[dict(base_cell=i,reference_vertices=[[[0,1],[0,1]],[[1,1],[0,1]],[[0,1],[1,1]]])
               for i in reversed(range(len(a.case.geometry.cell_nodes)))]
        result=track_curved_hphi_modes(a,b,replace(q,current_cells=cells))
        self.assertEqual(result['status'],'PASS',result['verification_reasons'])
        self.assertEqual(result['current_mode_ids'],['mode-1','mode-2'])
        np.testing.assert_allclose(a.frequencies_hz,b.frequencies_hz,rtol=1e-10)
