# SPDX-License-Identifier: Apache-2.0
import copy,unittest
import numpy as np
from superfish_ng.planar_mesh import PlanarMesh
from superfish_ng.planar_dielectrics import PlanarDielectricPartition,LinearDielectric,DielectricRegion


def partition(concave=False,scale=1.,rotation=None,shift=(0.,0.)):
    polygon=(np.array([[-1.,-1.],[1.,-1.],[1.,0.],[0.,0.],[0.,1.],[-1.,1.]]) if concave else np.array([[-1.,-1.],[1.,-1.],[1.,1.],[-1.,1.]]))
    coordinates=[(i,j) for j in range(3) for i in range(3) if not (concave and i==j==2)]
    lookup={point:index for index,point in enumerate(coordinates)};points=np.asarray(coordinates,dtype=float)-1;cells=[]
    for j in range(2):
        for i in range(2):
            if concave and i==j==1:continue
            a,b,c,d=[lookup[point] for point in ((i,j),(i+1,j),(i+1,j+1),(i,j+1))];cells.extend(((a,b,c),(a,c,d)))
    cells=np.asarray(cells)
    labels=points[cells][:,:,1].mean(axis=1)>=0;rotation=np.eye(2) if rotation is None else np.asarray(rotation)
    mesh=PlanarMesh.create(polygon@rotation.T*scale/32+shift,points@rotation.T*scale/32+shift,cells)
    return PlanarDielectricPartition(mesh,[LinearDielectric('lower',2.),LinearDielectric('upper',5.)],
        [DielectricRegion('bottom','lower',np.flatnonzero(~labels).tolist()),DielectricRegion('top','upper',np.flatnonzero(labels).tolist())])


class PlanarDielectricTests(unittest.TestCase):
    def test_areas_interfaces_and_neutral_geometry_across_coordinate_origin(self):
        for concave in (False,True):
            p=partition(concave);self.assertEqual(p.to_dict(),PlanarDielectricPartition.from_dict(p.to_dict()).to_dict())
            np.testing.assert_allclose(p.region_area_m2,np.array([2.,1. if concave else 2.])/32**2,rtol=1e-13,atol=0.)
            self.assertNotIn('boundary',p.to_dict()['geometry']);self.assertNotIn('mu_r',p.to_dict()['materials'][0]);self.assertFalse(hasattr(p,'region_volume_m3'))
            self.assertLess(p.mesh.points_xy_m.min(),0.);self.assertGreater(len(p.interface_edges),0)
            for edge,cells in zip(p.interface_edges,p.interface_cells):self.assertEqual(set(edge),set(p.mesh.triangles[cells[0]])&set(p.mesh.triangles[cells[1]]))
            for name in ('epsilon_r','cell_region_indices','region_area_m2','interface_edges'):self.assertFalse(getattr(p,name).flags.writeable)

    def test_strict_partition_without_implicit_boundary_material_or_thickness(self):
        raw=partition().to_dict()
        changes=[lambda d:d.update(coordinates='axisymmetric_rz'),lambda d:d.update(thickness_m=1.),lambda d:d.update(schema_version=True),
            lambda d:d['geometry'].update(boundary='pec'),lambda d:d['geometry'].update(holes=[]),lambda d:d['geometry'].update(type='curved'),
            lambda d:d['materials'][0].update(mu_r=1.),lambda d:d['materials'][0].update(epsilon_r=-1.),
            lambda d:d['regions'][0]['cell_indices'].pop(),lambda d:d['regions'][0]['cell_indices'].append(10**100),
            lambda d:d['regions'][1]['cell_indices'].insert(0,d['regions'][0]['cell_indices'][0]),
            lambda d:d['materials'][1].update(id='lower'),lambda d:d['regions'][0].update(material='missing')]
        for change in changes:
            data=copy.deepcopy(raw);change(data)
            with self.assertRaises(ValueError):PlanarDielectricPartition.from_dict(data)
