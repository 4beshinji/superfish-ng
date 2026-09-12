# SPDX-License-Identifier: Apache-2.0
import copy,unittest
import numpy as np
from scripts.curved_meridional_reference import fixture
from superfish_ng.dielectrics import LinearDielectric,DielectricRegion,AxisymmetricDielectricPartition


def partition(axis=False,holes=1,scale=1.,uniform=None):
    mesh=fixture(axis,holes,scale=scale,shear=0.)[0]['base_mesh']
    labels=mesh.points_rz_m[mesh.triangles][:,:,1].mean(axis=1)>=scale/16
    materials=[LinearDielectric('lower',2.),LinearDielectric('upper',5.)] if uniform is None else [LinearDielectric('single',uniform)]
    regions=([DielectricRegion('bottom','lower',np.flatnonzero(~labels).tolist()),DielectricRegion('top','upper',np.flatnonzero(labels).tolist())]
             if uniform is None else [DielectricRegion('all','single',list(range(len(mesh.triangles))))])
    return AxisymmetricDielectricPartition(mesh,materials,regions)


class DielectricTests(unittest.TestCase):
    def test_explicit_coverage_measures_and_interfaces_without_rf_parameters(self):
        for axis in (False,True):
            for holes in (0,1,2):
                p=partition(axis,holes);self.assertEqual(p.to_dict(),AxisymmetricDielectricPartition.from_dict(p.to_dict()).to_dict())
                self.assertFalse(hasattr(p,'mu_r'));self.assertFalse(hasattr(p.materials[0],'mu_r'))
                self.assertAlmostEqual(p.region_volume_m3.sum()/p.mesh.volume_m3,1.,places=13)
                self.assertGreater(len(p.interface_cells),0)
                for edge,cells in zip(p.interface_edges,p.interface_cells):
                    self.assertEqual(set(edge),set(p.mesh.triangles[cells[0]])&set(p.mesh.triangles[cells[1]]))
                    self.assertEqual({p.epsilon_r[c] for c in cells},{2.,5.})
                for name in ('epsilon_r','cell_region_indices','interface_edges','region_volume_m3'):
                    self.assertFalse(getattr(p,name).flags.writeable)
                data=p.to_dict();data['materials'][0]['epsilon_r']=20.;self.assertEqual(p.materials[0].epsilon_r,2.)

    def test_no_implicit_vacuum_and_reject_unsupported_physics(self):
        raw=partition().to_dict()
        changes=[lambda d:d.update(coordinates='planar_xy'),lambda d:d.update(schema_version=True),
            lambda d:d.update(phasor='peak'),lambda d:d['materials'][0].update(mu_r=1.),
            lambda d:d['materials'][0].update(conductivity_s_per_m=0.),lambda d:d['materials'][0].update(type='nonlinear'),
            lambda d:d['regions'][0]['cell_indices'].pop(),lambda d:d['regions'][0]['cell_indices'].append(10**100),
            lambda d:d['regions'][1]['cell_indices'].insert(0,d['regions'][0]['cell_indices'][0]),
            lambda d:d['regions'][0].update(material='missing'),lambda d:d['materials'][1].update(id='lower'),
            lambda d:d['mesh'].update(format='superfish_ng_curved_meridional_geometry')]
        for change in changes:
            data=copy.deepcopy(raw);change(data)
            with self.assertRaises(ValueError):AxisymmetricDielectricPartition.from_dict(data)
        for value in (0.,-1.,True,float('inf'),float('nan'),1+1j,[1,2],10**1000):
            with self.assertRaises(ValueError):LinearDielectric('invalid',value)
