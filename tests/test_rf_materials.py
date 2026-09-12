# SPDX-License-Identifier: Apache-2.0
import copy,unittest
import numpy as np
from scripts.curved_meridional_reference import fixture
from superfish_ng.rf_materials import LinearRFMaterial,RFMaterialRegion,RFMaterialPartition


def partition(axis=False,holes=1,uniform=None):
    mesh=fixture(axis,holes,shear=0.)[0]['base_mesh']
    labels=mesh.points_rz_m[mesh.triangles][:,:,1].mean(axis=1)>=1/16
    materials=[LinearRFMaterial('low',2.,3.),LinearRFMaterial('high',5.,7.)] if uniform is None else [LinearRFMaterial('low',*uniform)]
    regions=([RFMaterialRegion('bottom','low',np.flatnonzero(~labels).tolist()),RFMaterialRegion('top','high',np.flatnonzero(labels).tolist())]
             if uniform is None else [RFMaterialRegion('all','low',list(range(len(mesh.triangles))))])
    return RFMaterialPartition(mesh,materials,regions)


class RFMaterialTests(unittest.TestCase):
    def test_total_cell_partition_interfaces_and_region_measures(self):
        for axis in (False,True):
            for holes in (0,1,2):
                p=partition(axis,holes);restored=RFMaterialPartition.from_dict(p.to_dict());self.assertEqual(p.to_dict(),restored.to_dict())
                self.assertAlmostEqual(sum(p.region_area_m2)/p.mesh.area_m2,1.,places=13)
                self.assertAlmostEqual(sum(p.region_volume_m3)/p.mesh.volume_m3,1.,places=13)
                self.assertGreater(len(p.interface_edges),0)
                for edge,cells,regions in zip(p.interface_edges,p.interface_cells,p.interface_region_indices):
                    self.assertEqual(set(edge),set(p.mesh.triangles[cells[0]])&set(p.mesh.triangles[cells[1]]))
                    np.testing.assert_array_equal(regions,p.cell_region_indices[cells]);self.assertNotEqual(*regions)
                    self.assertNotEqual(p.epsilon_r[cells[0]],p.epsilon_r[cells[1]])
                np.testing.assert_array_equal(p.boundary_region_indices,p.cell_region_indices[p.mesh.boundary_cells])
                for name in ('epsilon_r','mu_r','interface_cells','interface_edges','region_volume_m3'):
                    self.assertFalse(getattr(p,name).flags.writeable)
                raw=p.to_dict();raw['materials'][0]['epsilon_r']=9.;self.assertEqual(p.materials[0].epsilon_r,2.)

    def test_strict_materials_ids_cell_coverage_and_unsupported_models(self):
        p=partition();raw=p.to_dict()
        changes=[lambda d:d.update(schema_version=True),lambda d:d.update(loss_tangent=.01),
            lambda d:d['materials'][0].update(type='dispersive'),lambda d:d['materials'][0].update(epsilon_r=True),
            lambda d:d['materials'][0].update(epsilon_r=-1.),lambda d:d['materials'][0].update(mu_r=0.),
            lambda d:d['materials'][0].update(conductivity_s_per_m=1.),lambda d:d['materials'][0].update(epsilon_r=[1,2,3]),
            lambda d:d['materials'][1].update(id='low'),lambda d:d['regions'][1].update(id='bottom'),
            lambda d:d['regions'][0].update(material='missing'),lambda d:d['regions'][0]['cell_indices'].pop(),
            lambda d:d['regions'][0]['cell_indices'].append(10**100),lambda d:d['regions'][0]['cell_indices'].__setitem__(0,True),
            lambda d:d['regions'][1]['cell_indices'].insert(0,d['regions'][0]['cell_indices'][0]),
            lambda d:d['regions'][0]['cell_indices'].reverse(),lambda d:d['mesh'].update(format='superfish_ng_curved_meridional_geometry')]
        for change in changes:
            value=copy.deepcopy(raw);change(value)
            with self.assertRaises(ValueError):RFMaterialPartition.from_dict(value)
        for value in (0.,-1.,True,float('inf'),float('nan'),1+1j,[1,2]):
            with self.assertRaises(ValueError):LinearRFMaterial('test',value,1.)
        with self.assertRaises(ValueError):RFMaterialPartition(p.mesh,p.materials[:1],p.regions)
        with self.assertRaises(ValueError):RFMaterialPartition(p.mesh,[*p.materials,LinearRFMaterial('unused',1,1)],p.regions)
