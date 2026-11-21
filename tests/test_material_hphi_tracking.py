# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from pathlib import Path
import tempfile,unittest
import numpy as np
from superfish_ng.material_hphi import MaterialHphiCase,solve_material_hphi
from superfish_ng.material_hphi_tracking import MaterialHphiTrackingRequest,track_material_hphi_modes
from superfish_ng.hphi_geometry_mapping import HphiGeometryMapping
from test_material_hphi_comparison import request as compare
from scripts.material_hphi_reference import layered_partition,layered_reference


def setup(scale=1.):
    a=layered_partition(1,12);b=layered_partition(1,12,scale)
    left,right=[solve_material_hphi(MaterialHphiCase(p,modes=3)) for p in (a,b)]
    mapping='same_domain' if scale==1 else HphiGeometryMapping(a.mesh,b.mesh)
    request=MaterialHphiTrackingRequest(compare(a,b,mapping),compare(a,layered_partition(2,24)),compare(b,layered_partition(2,24,scale)))
    return left,right,request


class MaterialHphiTrackingTests(unittest.TestCase):
    def test_layered_tem_ids_phase_and_scale(self):
        a,b,q=setup(2.);before=a.coefficients.copy()
        result=track_material_hphi_modes(a,b,q)
        self.assertEqual(result['status'],'PASS',result['verification_reasons'])
        self.assertEqual(result['current_mode_ids'],['mode-1','mode-2'])
        np.testing.assert_allclose(a.frequencies_hz,[layered_reference(i)[0]['frequency_hz'] for i in range(1,4)],rtol=.002)
        np.testing.assert_allclose(b.frequencies_hz*2,a.frequencies_hz,rtol=1e-10)
        flipped=track_material_hphi_modes(a,replace(b,coefficients=-b.coefficients),q)
        self.assertEqual(flipped['status'],'PASS',flipped['verification_reasons'])
        for first,second in zip(result['matches'],flipped['matches']):self.assertEqual(first['previous_phase_multiplier'],-second['previous_phase_multiplier'])
        np.testing.assert_array_equal(a.coefficients,before)

    def test_guard_and_inherited_ambiguous_set(self):
        a,b,q=setup()
        result=track_material_hphi_modes(a,b,replace(q,controls=replace(q.controls,relative_cluster_gap=.9)))
        self.assertEqual(result['status'],'UNVERIFIED');self.assertTrue(any(result['guard_overlap']))
        self.assertEqual(result['current_mode_ids'],[None,None])
        grouped=replace(q,previous_mode_ids=None,previous_identity_groups=[dict(indices=[1,2],ids=['a','b'])])
        result=track_material_hphi_modes(a,b,grouped)
        self.assertEqual(result['status'],'PASS',result['verification_reasons']);self.assertFalse(result['individual_ids_complete'])
        self.assertEqual(result['current_mode_ids'],[None,None]);self.assertEqual(result['matches'][0]['previous_ids'],['a','b'])
        self.assertIsNone(result['matches'][0]['previous_phase_multiplier'])

    def test_numbering_ids_original_native_and_reverse(self):
        from test_material_hphi_comparison import partition
        from superfish_ng.rf_materials import RFMaterialPartition,LinearRFMaterial,RFMaterialRegion
        from superfish_ng.material_hphi_comparison import MaterialHphiComparison
        from superfish_ng.material_hphi_saved import save_material_hphi_run
        from superfish_ng.material_hphi_rf import material_hphi_quantities
        for axis in (False,True):
            a=partition(1,1,axis);fine=partition(2,1,axis)
            raw=a.mesh.to_dict();points=np.asarray(raw['points_rz_m']);triangles=np.asarray(raw['triangles'])
            raw['points_rz_m']=points[::-1].tolist();raw['triangles']=(len(points)-1-triangles[::-1]).tolist();count=len(triangles)
            b=RFMaterialPartition(type(a.mesh).from_dict(raw),[LinearRFMaterial('new-b',5.,7.),LinearRFMaterial('new-a',2.,3.)],
                [RFMaterialRegion('new-upper','new-b',sorted(count-1-i for i in a.regions[1].cell_indices)),
                 RFMaterialRegion('new-lower','new-a',sorted(count-1-i for i in a.regions[0].cell_indices))])
            mp=[dict(previous_id=x,current_id='new-'+x) for x in ('b','a')]
            rp=[dict(previous_id=x,current_id='new-'+x) for x in ('upper','lower')]
            reverse=lambda pairs:[dict(previous_id=p['current_id'],current_id=p['previous_id']) for p in pairs]
            ab=MaterialHphiComparison(a,b,'same_domain',mp,rp)
            ba=MaterialHphiComparison(b,a,'same_domain',reverse(mp),reverse(rp))
            bf=MaterialHphiComparison(b,fine,'same_domain',reverse(mp),reverse(rp))
            left,right=[solve_material_hphi(MaterialHphiCase(p,modes=3)) for p in (a,b)]
            q=MaterialHphiTrackingRequest(ab,compare(a,fine),bf)
            rf=[[material_hphi_quantities(s,i) for i in range(3)] for s in (left,right)]
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                for name,solution in (('left',left),('right',right)):save_material_hphi_run(solution.case,solution,root/name)
                files={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
                result=track_material_hphi_modes(left,right,q)
                back=track_material_hphi_modes(right,left,MaterialHphiTrackingRequest(ba,bf,compare(a,fine)))
                for r in (result,back):
                    self.assertEqual(r['status'],'PASS',r['verification_reasons']);self.assertEqual(r['current_mode_ids'],['mode-1','mode-2'])
                for name in ('electric_grams','magnetic_grams'):
                    np.testing.assert_allclose(result['physical_mapping'][name][1],np.asarray(back['physical_mapping'][name][1]).T,rtol=1e-9,atol=1e-9)
                self.assertEqual(files,{str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()})
            self.assertEqual(rf,[[material_hphi_quantities(s,i) for i in range(3)] for s in (left,right)])

    def test_strict_roundtrip_and_original_binding(self):
        a,b,q=setup()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'request.json';q.save(path)
            self.assertEqual(q.to_dict(),MaterialHphiTrackingRequest.load(path).to_dict())
            with self.assertRaises(FileExistsError):q.save(path)
        for name,value in (('tracking_version',True),('previous_mode_count',True),('previous_mode_ids',['a','a']),('max_sample_points',0),('extra',0)):
            data=q.to_dict();data[name]=value
            with self.assertRaises(ValueError):MaterialHphiTrackingRequest.from_dict(data)
        with self.assertRaisesRegex(ValueError,'guard mode'):
            track_material_hphi_modes(a,b,replace(q,previous_mode_count=3,previous_mode_ids=['a','b','c']))
        with self.assertRaises(ValueError):track_material_hphi_modes(a,b,replace(q,max_sample_points=1))
        with self.assertRaises(ValueError):track_material_hphi_modes(replace(a,coefficients=a.coefficients*1.01),b,q)
        wrong=replace(q,previous_resolution=compare(layered_partition(2,24),layered_partition(3,48)))
        with self.assertRaises(ValueError):track_material_hphi_modes(a,b,wrong)


if __name__=='__main__':unittest.main()
