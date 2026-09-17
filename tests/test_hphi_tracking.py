# SPDX-License-Identifier: Apache-2.0
import copy,tempfile,unittest
from dataclasses import replace
from pathlib import Path
import numpy as np
from superfish_ng.axis_hphi import AxisHphiCase,solve_axis_hphi
from superfish_ng.coaxial import CoaxialCase,solve_coaxial
from superfish_ng.hphi_mesh import HphiMeshCase,solve_hphi_mesh
from superfish_ng.hphi_field_overlap import _declared_mesh
from superfish_ng.hphi_geometry_mapping import HphiGeometryMapping,coaxial_dimension_mapping,map_mesh
from superfish_ng.hphi_tracking import HphiTrackingRequest,HphiTrackingControls,track_hphi_modes,track_hphi_mapped_modes
from superfish_ng.hphi_tuning import _refine_mesh
from test_meridional_overlap import fixture
from test_hphi_mass_projection import declared


def pair(axis=True):
    solutions=[]
    for n in (2,3):
        mesh=declared(n,0,axis,17+n)
        solutions.append(solve_axis_hphi(AxisHphiCase(mesh,modes=3)) if axis else solve_hphi_mesh(HphiMeshCase(mesh,modes=3,quadrature_order=12)))
    return solutions,HphiTrackingRequest(declared(4,0,axis,29),declared(6,0,axis,31))


class HphiTrackingTests(unittest.TestCase):
    def test_strict_complete_request_and_identity_partition_roundtrip(self):
        q=HphiTrackingRequest(declared(2),declared(2))
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'request.json';q.save(path);self.assertEqual(HphiTrackingRequest.load(path).to_dict(),q.to_dict())
            with self.assertRaises(FileExistsError):q.save(path)
        for name,value in (('tracking_version',True),('mapping','nearest_frequency'),('previous_mode_count',True),('previous_mode_ids',['same','same']),('extra',0)):
            raw=q.to_dict();raw[name]=value
            with self.assertRaises(ValueError):HphiTrackingRequest.from_dict(raw)
        for name in q.controls.__dataclass_fields__:
            raw=q.to_dict();raw['controls'][name]=True
            with self.assertRaises(ValueError):HphiTrackingRequest.from_dict(raw)
        groups=[dict(indices=[1,2],ids=['a','b'])]
        grouped=replace(q,previous_mode_ids=None,previous_identity_groups=groups);groups[0]['ids'][0]='changed'
        self.assertEqual(grouped.previous_identity_groups[0]['ids'],['a','b'])

    def test_both_original_fields_track_independent_meshes_and_coefficient_phase(self):
        for axis in (False,True):
            (a,b),q=pair(axis);before=a.coefficients.copy(),b.coefficients.copy()
            report=track_hphi_modes(a,b,q);self.assertEqual(report['status'],'PASS')
            self.assertEqual(report['current_mode_ids'],['mode-1','mode-2'])
            self.assertTrue(report['individual_ids_complete'])
            flipped=copy.deepcopy(b);flipped.coefficients*=-1
            other=track_hphi_modes(a,flipped,q);self.assertEqual(other['status'],'PASS')
            self.assertEqual(other['current_mode_ids'],report['current_mode_ids'])
            self.assertEqual([m['previous_phase_multiplier'] for m in report['matches']],[-m['previous_phase_multiplier'] for m in other['matches']])
            np.testing.assert_array_equal(a.coefficients,before[0]);np.testing.assert_array_equal(b.coefficients,before[1])

    def test_prior_subspace_remains_an_id_set_after_frequency_separation(self):
        (a,b),q=pair();q=replace(q,previous_mode_ids=None,previous_identity_groups=[dict(indices=[1,2],ids=['a','b'])])
        report=track_hphi_modes(a,b,q);self.assertEqual(report['status'],'PASS')
        self.assertFalse(report['individual_ids_complete']);self.assertEqual(report['current_mode_ids'],[None,None])
        self.assertEqual(report['matches'][0]['kind'],'SUBSPACE');self.assertEqual(report['matches'][0]['previous_ids'],['a','b'])
        self.assertIsNone(report['matches'][0]['previous_phase_multiplier'])

    @staticmethod
    def mapping_request(previous,current,ids):
        return HphiTrackingRequest(_refine_mesh(_declared_mesh(previous)),_refine_mesh(_declared_mesh(current)),
            previous_mode_count=len(ids),current_mode_count=len(ids),previous_mode_ids=ids,
            controls=HphiTrackingControls())

    def test_declared_mapping_coaxial_growth_forward_reverse_and_identity_partition(self):
        previous=solve_coaxial(CoaxialCase(.025,.05,.18,nr=4,nz=8,modes=3,quadrature_order=12))
        current=solve_coaxial(CoaxialCase(.03,.09,.30,nr=4,nz=8,modes=3,quadrature_order=12))
        mapping=coaxial_dimension_mapping(.025,.05,.18,.03,.09,.30)
        forward=track_hphi_mapped_modes(previous,current,self.mapping_request(previous,current,['a','b']),mapping)
        self.assertEqual(forward['status'],'PASS');self.assertTrue(forward['individual_ids_complete'])
        self.assertEqual(forward['current_mode_ids'],['a','b'])
        self.assertEqual(forward['physical_mapping']['name'],'declared_affine')
        self.assertEqual(forward['physical_mapping']['mapping'],mapping.to_dict())
        reverse=track_hphi_mapped_modes(current,previous,self.mapping_request(current,previous,['a','b']),
            HphiGeometryMapping.from_dict({**mapping.to_dict(),'inverse':True}))
        self.assertEqual(reverse['status'],'PASS');self.assertEqual(reverse['current_mode_ids'],['a','b'])
        # The same physical shape with an independent interior mesh is an exact identity map.
        a=solve_hphi_mesh(HphiMeshCase(declared(1,1,False),modes=3,quadrature_order=12))
        b=solve_hphi_mesh(HphiMeshCase(declared(2,1,False,19),modes=3,quadrature_order=12))
        identity=HphiGeometryMapping(((1.,0.),(0.,1.)))
        same=track_hphi_mapped_modes(a,b,self.mapping_request(a,b,['a','b']),identity)
        self.assertEqual(same['status'],'PASS');self.assertEqual(same['current_mode_ids'],['a','b'])

    def test_declared_mapping_axis_stretch_and_geometry_refusal(self):
        mesh=fixture(2,1,True,False)
        previous=solve_axis_hphi(AxisHphiCase(mesh,modes=3))
        mapping=HphiGeometryMapping(((1.,0.),(0.,1.5)))
        current=solve_axis_hphi(AxisHphiCase(map_mesh(mesh,mapping),modes=3))
        report=track_hphi_mapped_modes(previous,current,self.mapping_request(previous,current,['a','b']),mapping)
        self.assertEqual(report['status'],'PASS');self.assertEqual(report['current_mode_ids'],['a','b'])
        with self.assertRaises(ValueError):
            track_hphi_mapped_modes(previous,current,self.mapping_request(previous,current,['a','b']),
                HphiGeometryMapping(((2.,0.),(0.,2.))))
        with self.assertRaises(ValueError):
            track_hphi_mapped_modes(previous,current,self.mapping_request(previous,current,['a','b']),mapping.to_dict())

    def test_guard_and_assignment_failures_clear_current_ids(self):
        (a,b),q=pair()
        with self.assertRaisesRegex(ValueError,'guard mode'):
            track_hphi_modes(a,b,replace(q,previous_mode_count=3,previous_mode_ids=['a','b','c']))
        controls=replace(q.controls,minimum_overlap=1.)
        unresolved=track_hphi_modes(a,b,replace(q,controls=controls));self.assertEqual(unresolved['status'],'UNVERIFIED')
        self.assertEqual(unresolved['current_mode_ids'],[None,None])
        controls=replace(q.controls,relative_cluster_gap=.9)
        guarded=track_hphi_modes(a,b,replace(q,controls=controls));self.assertEqual(guarded['status'],'UNVERIFIED')
        self.assertTrue(any(guarded['guard_overlap']));self.assertEqual(guarded['current_mode_ids'],[None,None])
        changed=copy.deepcopy(a);changed.coefficients[:,0]*=1.01
        with self.assertRaises(ValueError):track_hphi_modes(changed,b,q)


if __name__=='__main__':unittest.main()
