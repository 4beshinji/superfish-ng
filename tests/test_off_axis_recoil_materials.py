# SPDX-License-Identifier: Apache-2.0
import copy,unittest
import numpy as np
from scripts.curved_meridional_reference import fixture
from superfish_ng.meridional_mesh import MeridionalMesh
from superfish_ng.off_axis_recoil_materials import OffAxisRecoilPartition
from superfish_ng.recoil_materials import LinearRecoilMaterial,OrientedMagneticRegion
from superfish_ng.constants import MU0


def partition(holes=1,pattern=2,scale=1.,shift=0.):
    mesh=fixture(False,holes,scale=scale,shear=0.)[0]['base_mesh'];vertices=mesh.points_rz_m[mesh.triangles]
    labels=(np.zeros(len(vertices),dtype=int) if pattern==0 else (vertices[:,:,1].mean(axis=1)>=scale/16).astype(int) if pattern==1 else np.arange(len(vertices))%3)
    t=np.array([0.,shift]);mesh=MeridionalMesh(mesh.outer_rz_m+t,[h+t for h in mesh.holes_rz_m],mesh.points_rz_m+t,mesh.triangles)
    principal=[(2.,5.),(3.,11.),(7.,4.)];remanent=[(0.,.1),(.04,-.1),(-.03,.08)];angles=[0.,.3,-.6]
    materials=[LinearRecoilMaterial(f'm{i}',principal[i],remanent[i]) for i in range(int(labels.max())+1)]
    regions=[OrientedMagneticRegion(f'r{i}',m.id,np.flatnonzero(labels==i).tolist(),angles[i]) for i,m in enumerate(materials)]
    return OffAxisRecoilPartition(mesh,materials,regions)


class OffAxisRecoilMaterialTests(unittest.TestCase):
    def test_positive_radius_rotated_tensor_and_remanence_ownership(self):
        for holes in (0,1,2):
            p=partition(holes);self.assertEqual(p.to_dict(),OffAxisRecoilPartition.from_dict(p.to_dict()).to_dict())
            self.assertTrue(np.all(p.mesh.points_rz_m[:,0]>0.));self.assertFalse(hasattr(p,'region_axis_contact'))
            self.assertTrue(np.any(p.mu_r_tensor[:,0,1]!=0.));self.assertTrue(np.any(p.remanent_b_t[:,0]!=0.))
            inverse=np.einsum('tij,tjk->tik',p.reluctivity_tensor_m_per_h,MU0*p.mu_r_tensor)
            np.testing.assert_allclose(inverse,np.broadcast_to(np.eye(2),inverse.shape),rtol=1e-13,atol=1e-14)
            np.testing.assert_array_equal(p.azimuthal_mu_r,p.mu_r_tensor[:,0,0]);self.assertAlmostEqual(p.region_volume_m3.sum()/p.mesh.volume_m3,1.,places=13)
            self.assertTrue(np.any(p.interface_coefficient_jumps))
            for name in ('mu_r_tensor','reluctivity_tensor_m_per_h','remanent_b_t','remanent_h_a_per_m','azimuthal_mu_r','region_volume_m3'):
                self.assertFalse(getattr(p,name).flags.writeable)
            raw=p.to_dict();raw['regions'][0]['orientation_rad']=.7;raw['materials'][0]['remanent_b_local_t']=[.1,.2]
            changed=OffAxisRecoilPartition.from_dict(raw);self.assertGreater(abs(changed.mu_r_tensor[0,0,1]),0.)
            self.assertEqual(p.regions[0].orientation_rad,0.)

    def test_reject_axis_geometry_missing_coverage_and_unsupported_physics(self):
        raw=partition().to_dict()
        for change in (lambda d:d.pop('azimuthal_model'),lambda d:d.update(azimuthal_model='general_3d'),lambda d:d.update(schema_version=True),
            lambda d:d.update(coordinates='cartesian_xy'),lambda d:d['materials'][0].update(mu_r_phi=1.),
            lambda d:d['materials'][0].update(remanent_b_phi_t=0.),lambda d:d['materials'][0].update(type='nonlinear'),
            lambda d:d['regions'][0].pop('orientation_rad'),lambda d:d['regions'][0]['cell_indices'].pop(),
            lambda d:d['regions'][1]['cell_indices'].append(d['regions'][0]['cell_indices'][0]),lambda d:d['geometry'].update(type='curved_meridional')):
            data=copy.deepcopy(raw);change(data)
            with self.assertRaises(ValueError):OffAxisRecoilPartition.from_dict(data)
        for angle in (True,float('inf'),float('nan')):
            data=copy.deepcopy(raw);data['regions'][0]['orientation_rad']=angle
            with self.assertRaises(ValueError):OffAxisRecoilPartition.from_dict(data)
        p=partition();axis=fixture(True,1,shear=0.)[0]['base_mesh']
        with self.assertRaises(ValueError):OffAxisRecoilPartition(axis,p.materials,p.regions)
