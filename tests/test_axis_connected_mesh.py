# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from scripts.hphi_mesh_reference import rectangular_holes
from superfish_ng.axis_connected_mesh import AxisConnectedMesh
from superfish_ng.meridional_mesh import MeridionalMesh


class AxisConnectedMeshTests(unittest.TestCase):
    def data(self,holes=1):
        data=rectangular_holes(2,holes)
        def mapped(points):
            p=np.asarray(points).copy();p[:,0]=np.round((p[:,0]-.025)/(.075/(10 if holes==2 else 6)))/32;return p
        return dict(outer_rz_m=mapped(data['outer_rz_m']),holes_rz_m=[mapped(h) for h in data['holes_rz_m']],points_rz_m=mapped(data['points_rz_m']),triangles=data['triangles'])
    def test_axis_is_one_regular_boundary_and_not_a_loss_surface(self):
        for holes in (0,1,2):
            data=self.data(holes);mesh=AxisConnectedMesh(**data)
            self.assertEqual(mesh.euler_characteristic,1-holes);self.assertEqual(mesh.axis_interval_m,(0.,.18))
            self.assertEqual(len(mesh.axis_edges),6);self.assertEqual(len(mesh.axis_nodes),7)
            self.assertTrue(np.all(mesh.points_rz_m[mesh.axis_nodes,0]==0))
            self.assertEqual(mesh.boundary_tags[mesh.axis_edges].tolist(),['axis']*6)
            self.assertEqual(np.count_nonzero(mesh.surface_area_m2_by_segment==0),1)
            self.assertEqual(mesh.to_dict(),AxisConnectedMesh.from_dict(mesh.to_dict()).to_dict())
            with self.assertRaises(ValueError):MeridionalMesh(**data)
    def test_absent_axis_negative_radius_and_axis_touching_hole_rejected(self):
        data=rectangular_holes(2)
        with self.assertRaises(ValueError):AxisConnectedMesh(**data)
        data=self.data();data['points_rz_m']=data['points_rz_m'].copy();data['points_rz_m'][0,0]=-1e-10
        with self.assertRaises(ValueError):AxisConnectedMesh(**data)
        data=self.data();data['holes_rz_m'][0][0,0]=0.
        with self.assertRaises(ValueError):AxisConnectedMesh(**data)
        good=AxisConnectedMesh(**self.data()).to_dict()
        for key,value in (('boundary','all_pec'),('schema_version',True),('format','superfish_ng_meridional_mesh'),('extra',0)):
            raw=dict(good);raw[key]=value
            with self.assertRaises(ValueError):AxisConnectedMesh.from_dict(raw)
