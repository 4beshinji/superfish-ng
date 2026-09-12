# SPDX-License-Identifier: Apache-2.0
import copy,unittest
import numpy as np
from scripts.curved_meridional_reference import fixture
from superfish_ng.axis_connected_mesh import AxisConnectedMesh
from superfish_ng.axis_recoil_materials import AxisRecoilPartition
from superfish_ng.recoil_materials import LinearRecoilMaterial,OrientedMagneticRegion
from superfish_ng.constants import MU0


def partition(holes=1,pattern=2,scale=1.,shift=0.):
    mesh=fixture(True,holes,scale=scale,shear=0.)[0]['base_mesh'];vertices=mesh.points_rz_m[mesh.triangles]
    labels=(np.zeros(len(vertices),dtype=int) if pattern==0 else
            (vertices[:,:,1].mean(axis=1)>=scale/16).astype(int) if pattern==1 else
            np.where(np.any(vertices[:,:,0]==0.,axis=1),0,1+np.arange(len(vertices))%2))
    t=np.array([0.,shift]);mesh=AxisConnectedMesh(mesh.outer_rz_m+t,[h+t for h in mesh.holes_rz_m],mesh.points_rz_m+t,mesh.triangles)
    principal=[(2.,5.),(3.,11.),(7.,4.)];remanent=[(0.,.1),(0.,-.04),(0.,.08)] if pattern!=2 else [(0.,.1),(.04,.1),(-.03,.08)]
    angles=[0.,0.,0.] if pattern!=2 else [0.,.3,-.6]
    materials=[LinearRecoilMaterial(f'm{i}',principal[i],remanent[i]) for i in range(int(labels.max())+1)]
    regions=[OrientedMagneticRegion(f'r{i}',m.id,np.flatnonzero(labels==i).tolist(),angles[i]) for i,m in enumerate(materials)]
    return AxisRecoilPartition(mesh,materials,regions)


class AxisRecoilMaterialTests(unittest.TestCase):
    def test_axis_regular_extension_and_oriented_off_axis_tensor_ownership(self):
        for holes in (0,1,2):
            p=partition(holes);self.assertEqual(p.to_dict(),AxisRecoilPartition.from_dict(p.to_dict()).to_dict())
            axis=np.any(p.mesh.points_rz_m[p.mesh.triangles,0]==0.,axis=1)
            np.testing.assert_array_equal(p.remanent_b_t[axis,0],0.)
            np.testing.assert_array_equal(p.mu_r_tensor[axis,0,1],0.)
            np.testing.assert_array_equal(p.azimuthal_mu_r,p.mu_r_tensor[:,0,0])
            self.assertTrue(np.any(p.mu_r_tensor[~axis,0,1]!=0.))
            inverse=np.einsum('tij,tjk->tik',p.reluctivity_tensor_m_per_h,MU0*p.mu_r_tensor)
            np.testing.assert_allclose(inverse,np.broadcast_to(np.eye(2),inverse.shape),rtol=1e-13,atol=1e-14)
            self.assertAlmostEqual(p.region_volume_m3.sum()/p.mesh.volume_m3,1.,places=13)
            self.assertTrue(np.any(p.interface_coefficient_jumps));self.assertEqual(p.region_axis_contact.tolist(),[True,False,False])
            for name in ('mu_r_tensor','reluctivity_tensor_m_per_h','remanent_b_t','remanent_h_a_per_m','azimuthal_mu_r','region_axis_contact','region_volume_m3'):
                self.assertFalse(getattr(p,name).flags.writeable)
            raw=p.to_dict();raw['materials'][0]['remanent_b_local_t'][1]=9.;self.assertEqual(p.materials[0].remanent_b_local_t[1],.1)

    def test_reject_singular_axis_material_and_unsupported_or_missing_physics(self):
        raw=partition().to_dict()
        changes=[lambda d:d['regions'][0].update(orientation_rad=.1),lambda d:d['regions'][0].update(orientation_rad=np.pi),
            lambda d:d['materials'][0].update(remanent_b_local_t=[1e-100,.1]),lambda d:d.pop('azimuthal_model'),
            lambda d:d.update(azimuthal_model='general_3d'),lambda d:d.update(schema_version=True),lambda d:d.update(coordinates='cartesian_xy'),
            lambda d:d['materials'][0].update(mu_r_phi=2.),lambda d:d['materials'][0].update(remanent_b_phi_t=0.),
            lambda d:d['materials'][0].update(type='nonlinear'),lambda d:d['regions'][0].pop('orientation_rad'),
            lambda d:d['regions'][0]['cell_indices'].pop(),lambda d:d['regions'][1]['cell_indices'].append(d['regions'][0]['cell_indices'][0]),
            lambda d:d['geometry'].update(type='curved_axis_connected')]
        for change in changes:
            data=copy.deepcopy(raw);change(data)
            with self.assertRaises(ValueError):AxisRecoilPartition.from_dict(data)
        for angle in (True,float('inf'),float('nan')):
            data=copy.deepcopy(raw);data['regions'][1]['orientation_rad']=angle
            with self.assertRaises(ValueError):AxisRecoilPartition.from_dict(data)
        off=fixture(False,1,shear=0.)[0]['base_mesh']
        with self.assertRaises(ValueError):AxisRecoilPartition(off,partition().materials,partition().regions)
