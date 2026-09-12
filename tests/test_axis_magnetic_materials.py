# SPDX-License-Identifier: Apache-2.0
import copy,unittest
import numpy as np
from scripts.curved_meridional_reference import fixture
from superfish_ng.magnetic_materials import LinearMagneticMaterial,MagneticRegion
from superfish_ng.axis_magnetic_materials import AxisMagneticPartition


def partition(axis=True,holes=1,scale=1.,uniform=None):
    mesh=fixture(axis,holes,scale=scale,shear=0.)[0]['base_mesh']
    labels=mesh.points_rz_m[mesh.triangles][:,:,1].mean(axis=1)>=scale/16
    materials=[LinearMagneticMaterial('lower',2.),LinearMagneticMaterial('upper',5.)] if uniform is None else [LinearMagneticMaterial('single',uniform)]
    regions=([MagneticRegion('bottom','lower',np.flatnonzero(~labels).tolist()),MagneticRegion('top','upper',np.flatnonzero(labels).tolist())]
             if uniform is None else [MagneticRegion('all','single',list(range(len(mesh.triangles))))])
    return AxisMagneticPartition(mesh,materials,regions)


class AxisMagneticMaterialTests(unittest.TestCase):
    def test_explicit_coverage_measures_and_interfaces_without_rf_parameters(self):
        for axis in (True,):
            for holes in (0,1,2):
                p=partition(axis,holes);self.assertEqual(p.to_dict(),AxisMagneticPartition.from_dict(p.to_dict()).to_dict())
                self.assertNotIn('boundary',p.to_dict()['geometry']);self.assertNotIn('mesh',p.to_dict())
                self.assertFalse(hasattr(p,'epsilon_r'));self.assertFalse(hasattr(p.materials[0],'epsilon_r'));self.assertTrue(np.all(p.reluctivity_m_per_h>0))
                self.assertAlmostEqual(p.region_volume_m3.sum()/p.mesh.volume_m3,1.,places=13)
                self.assertGreater(len(p.interface_cells),0)
                for edge,cells in zip(p.interface_edges,p.interface_cells):
                    self.assertEqual(set(edge),set(p.mesh.triangles[cells[0]])&set(p.mesh.triangles[cells[1]]))
                    self.assertEqual({p.mu_r[c] for c in cells},{2.,5.})
                for name in ('mu_r','cell_region_indices','interface_edges','region_volume_m3'):
                    self.assertFalse(getattr(p,name).flags.writeable)
                data=p.to_dict();data['materials'][0]['mu_r']=20.;self.assertEqual(p.materials[0].mu_r,2.)

    def test_no_implicit_vacuum_and_reject_unsupported_physics(self):
        raw=partition().to_dict()
        changes=[lambda d:d.update(coordinates='planar_xy'),lambda d:d.update(schema_version=True),
            lambda d:d.update(phasor='peak'),lambda d:d['materials'][0].update(epsilon_r=1.),
            lambda d:d['materials'][0].update(conductivity_s_per_m=0.),lambda d:d['materials'][0].update(type='nonlinear'),
            lambda d:d['regions'][0]['cell_indices'].pop(),lambda d:d['regions'][0]['cell_indices'].append(10**100),
            lambda d:d['regions'][1]['cell_indices'].insert(0,d['regions'][0]['cell_indices'][0]),
            lambda d:d['regions'][0].update(material='missing'),lambda d:d['materials'][1].update(id='lower'),
            lambda d:d['geometry'].update(type='curved_axis_connected')]
        for change in changes:
            data=copy.deepcopy(raw);change(data)
            with self.assertRaises(ValueError):AxisMagneticPartition.from_dict(data)
        with self.assertRaises(ValueError):partition(axis=False)
        data=copy.deepcopy(raw);data['materials'][0]['mu_r']=1e-323
        with self.assertRaises(ValueError):AxisMagneticPartition.from_dict(data)
        for value in (0.,-1.,True,float('inf'),float('nan'),1+1j,[1,2],10**1000):
            with self.assertRaises(ValueError):LinearMagneticMaterial('invalid',value)
