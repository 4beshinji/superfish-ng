# SPDX-License-Identifier: Apache-2.0
import copy,unittest
import numpy as np
from scripts.validate_off_axis_bh_forms import partition
from scripts.curved_meridional_reference import fixture
from superfish_ng.off_axis_bh_materials import OffAxisBHPartition


class OffAxisBHMaterialTests(unittest.TestCase):
    def test_original_ownership_tables_volumes_and_immutable_state(self):
        for holes in (0,1,2):
            p=partition(holes);self.assertEqual(OffAxisBHPartition.from_dict(p.to_dict()).to_dict(),p.to_dict())
            self.assertAlmostEqual(p.region_volume_m3.sum()/p.mesh.volume_m3,1.,places=13);self.assertTrue(np.any(p.interface_material_definition_changes))
            state=p.evaluate_cells([0,1,0],[[0.,.75],[0.,-.75],[0.,0.]])
            np.testing.assert_array_equal(state['h_a_per_m'][:,0],0.);self.assertGreater(state['h_a_per_m'][0,1],0.);self.assertLess(state['h_a_per_m'][1,1],0.);np.testing.assert_array_equal(state['h_a_per_m'][2],0.)
            for name in ('cell_material_indices','cell_region_indices','region_volume_m3','interface_material_definition_changes'):self.assertFalse(getattr(p,name).flags.writeable)
            for value in state.values():self.assertFalse(value.flags.writeable)
            raw=p.to_dict();raw['materials'][0]['b_t'][1]=9.;self.assertEqual(p.materials[0].b_t[1],.25)

    def test_reject_missing_azimuthal_model_unsupported_geometry_material_and_cell_types(self):
        p=partition();raw=p.to_dict()
        changes=[lambda d:d.pop('azimuthal_model'),lambda d:d.update(azimuthal_model='general_3d'),lambda d:d.update(schema_version=True),
            lambda d:d.update(coordinates='cartesian_xy'),lambda d:d['materials'][0].update(mu_r=2.),lambda d:d['materials'][0].update(remanent_b_t=[0.,1.]),
            lambda d:d['regions'][0].update(orientation_rad=0.),lambda d:d['regions'][0]['cell_indices'].pop(),lambda d:d['regions'][1]['cell_indices'].append(d['regions'][0]['cell_indices'][0]),
            lambda d:d['geometry'].update(type='curved_off_axis')]
        for change in changes:
            data=copy.deepcopy(raw);change(data)
            with self.assertRaises(ValueError):OffAxisBHPartition.from_dict(data)
        with self.assertRaises(ValueError):OffAxisBHPartition(fixture(True,1,shear=0.)[0]['base_mesh'],p.materials,p.regions)
        for cells,b in [([True],[[0.,1.]]),([0.],[[0.,1.]]),([-1],[[0.,1.]]),([0],[[False,1.]]),([0],[[1+0j,1.]]),([0],[[0.,4.01]])]:
            with self.assertRaises(ValueError):p.evaluate_cells(cells,b)
