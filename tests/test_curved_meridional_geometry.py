# SPDX-License-Identifier: Apache-2.0
import copy
import unittest
import numpy as np
from scripts.curved_meridional_reference import fixture
from superfish_ng.curved_meridional_geometry import CurvedMeridionalGeometry
from superfish_ng.curved_space import check_curved_edges
from superfish_ng.meridional_mesh import MeridionalMesh

NODES=np.array(((0.,0.),(1.,0.),(0.,1.),(.5,0.),(.5,.5),(0.,.5)))


def single_triangle(points):
    base=MeridionalMesh(points[:3],[],points[:3],np.array([[0,1,2]]))
    # Canonical edge order is 01,02,12.
    return dict(base_mesh=base,edge_vertices=[[0,1],[0,2],[1,2]],edge_midpoints_rz_m=points[[3,5,4]])


class CurvedMeridionalGeometryTests(unittest.TestCase):
    def test_straight_limit_and_polynomial_shear_preserve_all_holes_and_moments(self):
        for axis in (False,True):
            for holes in (0,1,2):
                for shear in (0.,1.):
                    data,expected=fixture(axis,holes,shear=shear)
                    g=CurvedMeridionalGeometry(**data)
                    self.assertEqual(g.validation['euler_characteristic'],1-holes)
                    self.assertEqual(g.validation['boundary_components'],1+holes)
                    self.assertTrue(g.validation['exact_cell_boundary_moments_equal'])
                    self.assertAlmostEqual(g.area_m2/expected['area_m2'],1.,places=13)
                    self.assertAlmostEqual(g.volume_m3/expected['volume_m3'],1.,places=13)
                    self.assertEqual(g.to_dict(),CurvedMeridionalGeometry.from_dict(g.to_dict()).to_dict())
                    np.testing.assert_array_equal(g.points_rz_m[:len(g.base_mesh.points_rz_m)],g.base_mesh.points_rz_m)
                    if shear==0:
                        self.assertAlmostEqual(g.area_m2/g.base_mesh.area_m2,1.,places=13)
                    if holes:
                        with self.assertRaisesRegex(ValueError,'disk Euler'):
                            check_curved_edges(g.points_rz_m,g.cell_nodes,g.boundary_nodes)
                    with self.assertRaises(ValueError):g.points_rz_m[0,0]=9.

    def test_similarity_and_axial_translation(self):
        for axis in (False,True):
            data,_=fixture(axis,2,scale=1.,z_offset=-.25);a=CurvedMeridionalGeometry(**data)
            data,_=fixture(axis,2,scale=8.,z_offset=2.);b=CurvedMeridionalGeometry(**data)
            self.assertAlmostEqual(b.area_m2/a.area_m2,64.,places=12)
            self.assertAlmostEqual(b.volume_m3/a.volume_m3,512.,places=11)

    def test_positive_nodes_do_not_hide_negative_radius_or_fold(self):
        x,y=NODES.T
        points=np.column_stack(((x-.25)**2+y-.01,-x))
        self.assertTrue(np.all(points[:,0]>0))
        with self.assertRaisesRegex(ValueError,'radius between'):
            CurvedMeridionalGeometry(**single_triangle(points))
        points=np.column_stack(((x-.75)**2-y+2,(x-.75)*y-.01*x))
        self.assertTrue(np.all(2*(x-.75)**2+y-.01>0))
        with self.assertRaisesRegex(ValueError,'Jacobian'):
            CurvedMeridionalGeometry(**single_triangle(points))

    def test_axis_changes_boundary_contacts_and_global_edge_crossings_rejected(self):
        data,_=fixture(True,1);g=CurvedMeridionalGeometry(**data)
        bad=dict(data);bad['edge_midpoints_rz_m']=data['edge_midpoints_rz_m'].copy()
        axis_mid=int(g.boundary_nodes[g.boundary_tags=='axis'][0,2])-len(g.base_mesh.points_rz_m)
        bad['edge_midpoints_rz_m'][axis_mid,0]=1e-16
        with self.assertRaisesRegex(ValueError,'axis edges'):CurvedMeridionalGeometry(**bad)
        bad=dict(data);bad['edge_midpoints_rz_m']=data['edge_midpoints_rz_m'].copy()
        positive_mid=int(g.boundary_nodes[np.all(g.points_rz_m[g.boundary_nodes[:,:2],0]>0,axis=1)][0,2])
        bad['edge_midpoints_rz_m'][positive_mid-len(g.base_mesh.points_rz_m),0]=0.
        with self.assertRaises(ValueError):CurvedMeridionalGeometry(**bad)
        boundary=set(g.boundary_nodes[:,2]);interior=next(int(i) for i in g.cell_nodes[:,3:].flat if i not in boundary)
        points=g.points_rz_m.copy();points[interior]=[5.,5.]
        with self.assertRaises(ValueError):check_curved_edges(points,g.cell_nodes,g.boundary_nodes,hole_count=1)

    def test_strict_edges_types_schema_and_budgets(self):
        data,_=fixture();g=CurvedMeridionalGeometry(**data)
        for key,value in (('schema_version',True),('geometry','ellipse'),('physics','rf'),
                          ('max_boxes_per_pair',True),('max_boxes_per_pair',0),('edge_vertices',[[True,1]]),
                          ('edge_vertices',g.edge_vertices[::-1].tolist()),('edge_midpoints_rz_m',[])):
            raw=copy.deepcopy(g.to_dict());raw[key]=value
            with self.assertRaises(ValueError):CurvedMeridionalGeometry.from_dict(raw)
        raw=g.to_dict();raw['base_mesh']['extra']=1
        with self.assertRaises(ValueError):CurvedMeridionalGeometry.from_dict(raw)
        for count in (True,-1,1.0,0,2):
            with self.assertRaises(ValueError):check_curved_edges(g.points_rz_m,g.cell_nodes,g.boundary_nodes,hole_count=count)
