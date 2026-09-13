# SPDX-License-Identifier: Apache-2.0
import copy,json,unittest
import numpy as np
from scripts.planar_electrostatic_reference import rectangle
from superfish_ng.bh_curve import MonotoneBHCurve
from superfish_ng.magnetic_materials import MagneticRegion
from superfish_ng.planar_bh_materials import PlanarBHPartition


def partition(concave=False,scale=1.,angle=0.,shift=(0.,0.),uniform=False,h_scale=1.,linear=False):
    rotation=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
    mesh,local,_,height,_,_=rectangle(2,scale,concave,rotation,shift)
    labels=np.zeros(len(mesh.triangles),dtype=int) if uniform else (local[mesh.triangles][:,:,1].mean(axis=1)>=height/2).astype(int)
    b=np.array([0.,.25,.5,1.,4.]);tables=[400*b,1200*b] if linear else [np.array([0.,100.,250.,1500.,100000.]),np.array([0.,80.,500.,1800.,50000.])]
    materials=[MonotoneBHCurve(f'm{i}',tuple(b),tuple(tables[i]*h_scale),'Synthetic isotropic table; no measured material') for i in range(int(labels.max())+1)]
    regions=[MagneticRegion(f'r{i}',f'm{i}',np.flatnonzero(labels==i).tolist()) for i in range(len(materials))]
    return PlanarBHPartition(mesh,materials,regions),local


class PlanarBHMaterialTests(unittest.TestCase):
    def test_original_cell_materials_interfaces_provenance_and_strict_roundtrip(self):
        p,_=partition(concave=True);data=p.to_dict();self.assertEqual(PlanarBHPartition.from_dict(json.loads(json.dumps(data))).to_dict(),data)
        self.assertGreater(len(p.interface_edges),0);self.assertTrue(np.all(p.interface_material_definition_changes));self.assertAlmostEqual(sum(p.region_area_m2),p.mesh.area_m2,places=14)
        cells=np.array([len(p.mesh.triangles)-1,0,0]);b=np.array([[.3,.4],[0.,0.],[.3,.4]]);state=p.evaluate_cells(cells,b)
        for i,cell in enumerate(cells):
            expected=p.materials[p.cell_material_indices[cell]].evaluate_vectors(b[i])
            for name,value in expected.items():np.testing.assert_array_equal(state[name][i],value)
        with self.assertRaises(ValueError):p.cell_material_indices[0]=1
        with self.assertRaises(ValueError):state['h_a_per_m'][0,0]=1.
        raw=p.to_dict();raw['materials'][1]['b_t']=raw['materials'][0]['b_t'];raw['materials'][1]['h_a_per_m']=raw['materials'][0]['h_a_per_m'];same=PlanarBHPartition.from_dict(raw)
        self.assertFalse(np.any(same.interface_material_definition_changes));self.assertEqual(len(same.interface_edges),len(p.interface_edges))

    def test_invalid_ownership_physics_and_cell_queries_are_rejected(self):
        p,_=partition();data=p.to_dict()
        for kind in ('overlap','gap','unused','duplicate','orientation','geometry','coordinates','schema','range','curve'):
            bad=copy.deepcopy(data)
            if kind=='overlap':bad['regions'][1]['cell_indices'].append(bad['regions'][0]['cell_indices'][0])
            elif kind=='gap':bad['regions'][0]['cell_indices'].pop()
            elif kind=='unused':bad['materials'].append(dict(bad['materials'][0],id='unused'))
            elif kind=='duplicate':bad['materials'][1]['id']=bad['materials'][0]['id']
            elif kind=='orientation':bad['regions'][0]['orientation_rad']=.1
            elif kind=='geometry':bad['geometry']['type']='curved'
            elif kind=='coordinates':bad['coordinates']='axisymmetric_rz'
            elif kind=='schema':bad['schema_version']=True
            elif kind=='range':bad['regions'][0]['cell_indices'].append(100000)
            else:bad['materials'][0]['extrapolation']='vacuum_saturation'
            with self.subTest(kind=kind),self.assertRaises(ValueError):PlanarBHPartition.from_dict(bad)
        for indices,b in [([True],[[0.,0.]]),([0.],[[0.,0.]]),([-1],[[0.,0.]]),([len(p.mesh.triangles)],[[0.,0.]]),([],[]),([0],[[True,0.]]),([0],[[5.,0.]]),([0],[[0.,0.,0.]])]:
            with self.assertRaises(ValueError):p.evaluate_cells(indices,b)
