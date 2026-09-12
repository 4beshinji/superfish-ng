# SPDX-License-Identifier: Apache-2.0
import copy,unittest
import numpy as np
from test_magnetic_materials import partition as geometry
from superfish_ng.recoil_materials import LinearRecoilMaterial,OrientedMagneticRegion,PlanarRecoilPartition
from superfish_ng.constants import MU0


def partition(concave=False,scale=1.,angle=0.,shift=(0.,0.),uniform=False):
    c,s=np.cos(angle),np.sin(angle);base=geometry(concave,scale,[[c,-s],[s,c]],shift)
    materials=[LinearRecoilMaterial('first',(2.,5.),(.2,-.1)),LinearRecoilMaterial('second',(3.,11.),(.3,.05))]
    if uniform:
        regions=[OrientedMagneticRegion('all','first',list(range(len(base.mesh.triangles))),.3+angle)];materials=materials[:1]
    else:regions=[OrientedMagneticRegion(v.id,materials[i].id,v.cell_indices,(.3,-.4)[i]+angle) for i,v in enumerate(base.regions)]
    return PlanarRecoilPartition(base.mesh,materials,regions)


class RecoilMaterialTests(unittest.TestCase):
    def test_explicit_orientation_tensor_inverse_and_neutral_ownership(self):
        for concave in (False,True):
            p=partition(concave);self.assertEqual(p.to_dict(),PlanarRecoilPartition.from_dict(p.to_dict()).to_dict())
            self.assertNotIn('boundary',p.to_dict()['geometry']);self.assertFalse(hasattr(p,'mu_r'));self.assertFalse(hasattr(p,'epsilon_r'))
            for index,region in enumerate(p.regions):
                m=p.materials[index];c,s=np.cos(region.orientation_rad),np.sin(region.orientation_rad);rotation=np.array([[c,-s],[s,c]])
                expected=rotation@np.diag(m.mu_r_principal)@rotation.T;cells=list(region.cell_indices)
                np.testing.assert_allclose(p.mu_r_tensor[cells],np.broadcast_to(expected,(len(cells),2,2)),rtol=1e-14)
                np.testing.assert_allclose(p.remanent_b_t[cells],np.broadcast_to(rotation@np.array(m.remanent_b_local_t),(len(cells),2)),rtol=1e-14)
            np.testing.assert_allclose(np.einsum('tij,tjk->tik',p.reluctivity_tensor_m_per_h,MU0*p.mu_r_tensor),np.broadcast_to(np.eye(2),p.mu_r_tensor.shape),rtol=0.,atol=1e-14)
            for name in ('mu_r_tensor','reluctivity_tensor_m_per_h','remanent_b_t','remanent_h_a_per_m','cell_region_indices','interface_edges'):
                self.assertFalse(getattr(p,name).flags.writeable)
            self.assertTrue(np.all(p.interface_coefficient_jumps));self.assertAlmostEqual(p.region_area_m2.sum(),p.mesh.area_m2,places=14)

    def test_strict_constitutive_scope_coverage_and_finite_positive_tensors(self):
        raw=partition().to_dict()
        changes=[lambda d:d.update(schema_version=True),lambda d:d.update(coordinates='axisymmetric_rz'),lambda d:d.update(thickness_m=1.),
            lambda d:d['geometry'].update(boundary='pec'),lambda d:d['materials'][0].update(type='nonlinear'),lambda d:d['materials'][0].update(mu_r=2.),
            lambda d:d['materials'][0].update(magnetization_a_per_m=[1.,0.]),lambda d:d['materials'][0].pop('remanent_b_local_t'),
            lambda d:d['regions'][0].pop('orientation_rad'),lambda d:d['regions'][0].update(orientation_rad=True),
            lambda d:d['regions'][0]['cell_indices'].pop(),lambda d:d['regions'][0]['cell_indices'].append(10**100),
            lambda d:d['regions'][1]['cell_indices'].insert(0,d['regions'][0]['cell_indices'][0]),lambda d:d['materials'][1].update(id='first')]
        for change in changes:
            data=copy.deepcopy(raw);change(data)
            with self.assertRaises(ValueError):PlanarRecoilPartition.from_dict(data)
        for bad in (True,0.,-1.,float('nan'),float('inf'),1+0j,10**1000):
            with self.assertRaises(ValueError):LinearRecoilMaterial('bad',(bad,2.),(0.,0.))
        for bad in (True,float('nan'),float('inf'),1+0j,10**1000):
            with self.assertRaises(ValueError):LinearRecoilMaterial('bad',(1.,2.),(bad,0.))
        for principal in ([1e-323,1.],[1.,1e30]):
            data=copy.deepcopy(raw);data['materials'][0]['mu_r_principal']=principal
            with self.assertRaises(ValueError):PlanarRecoilPartition.from_dict(data)
