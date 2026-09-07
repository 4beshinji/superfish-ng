# SPDX-License-Identifier: Apache-2.0
import math
import unittest
import numpy as np
from superfish_ng import Case
from superfish_ng.contour import Contour
from superfish_ng.contour_mesh import triangulate_contour, refine_contour, contour_mesh_quality, improve_contour_angles
from superfish_ng.contour_mesh import smooth_contour_interior
from superfish_ng.contour_mesh import quality_contour_mesh


class InitialContourMeshTests(unittest.TestCase):
    def check_moments(self, contour, area, volume):
        mesh = triangulate_contour(Case((), contour=contour))
        p = mesh.points[mesh.triangles]
        u, v = p[:, 1]-p[:, 0], p[:, 2]-p[:, 0]
        areas = (u[:, 0]*v[:, 1]-u[:, 1]*v[:, 0])/2
        self.assertTrue(np.all(areas > 0))
        self.assertAlmostEqual(areas.sum()/area, 1, places=13)
        self.assertAlmostEqual(np.sum(2*math.pi*areas*p[:, :, 0].mean(axis=1))/volume,
                               1, places=13)
        self.assertEqual(len(mesh.triangles), len(contour.vertices_zr_m)-2)
        np.testing.assert_array_equal(mesh.points[:, ::-1], contour.vertices_zr_m)
        self.assertEqual(tuple(mesh.boundary_tags), contour.edge_tags)
        return mesh

    def test_reentrant_partition_independent_rectangles_and_scale(self):
        vertices = ((0,0),(3,0),(3,2),(1,2),(1,1),(2,1),(2,.5),(0,.5))
        for scale in (1e-6, 1., 1e6):
            contour = Contour(tuple((z*scale,r*scale) for z,r in vertices),
                              ('axis',)+('pec',)*7)
            mesh = self.check_moments(contour, 4*scale**2, 7.5*math.pi*scale**3)
            again = triangulate_contour(Case((), contour=contour))
            np.testing.assert_array_equal(mesh.triangles, again.triangles)
            # Interior of the explicit radial gap cannot be covered.
            for triangle in mesh.points[mesh.triangles]/scale:
                for weights in ((.2,.3,.5),(.6,.2,.2), (1/3,)*3):
                    r,z = np.asarray(weights) @ triangle
                    self.assertFalse(1 < z < 2 and .5 < r < 1)

    def test_collinear_axis_and_mixed_end_tags_survive(self):
        contour = Contour(((0,0),(1,0),(2,0),(2,1),(1,1),(0,1),(0,.5)),
                          ('axis','axis','pec','pec','pec','pec','magnetic_symmetry'))
        mesh = self.check_moments(contour, 2., 2*math.pi)
        np.testing.assert_array_equal(mesh.points[mesh.axis_nodes, 1], [0,1,2])

    def test_cone_and_narrow_reentrant_channel(self):
        self.check_moments(Contour(((0,0),(3,0),(0,2)), ('axis','pec','pec')),
                           3., 4*math.pi)
        width = 1e-5
        contour = Contour(((0,0),(3,0),(3,2),(1,2),(1,1),(2,1),
                           (2,width),(0,width)), ('axis',)+('pec',)*7)
        # Separate rectangles: lower channel, right riser, upper left arm.
        self.check_moments(contour, 3+2*width, math.pi*(7+2*width**2))

    def test_profile_requires_explicit_conversion(self):
        with self.assertRaisesRegex(ValueError, 'contour Case'):
            triangulate_contour(Case(((0,.1),(.2,.1))))

    def test_refinement_preserves_partition_and_local_tag_sizes(self):
        contour = Contour(((0,0),(3,0),(3,2),(1,2),(1,1),(2,1),(2,.5),(0,.5),(0,.25)),
                          ('axis',)+('pec',)*7+('magnetic_symmetry',))
        case = Case((), contour=contour, boundary_max_edge_m=.2,
                    corner_max_edge_m=.08, corner_radius_m=.12)
        initial = triangulate_contour(case)
        mesh = refine_contour(case, initial, .5)
        p = mesh.points[mesh.triangles]
        u,v = p[:,1]-p[:,0], p[:,2]-p[:,0]
        areas = (u[:,0]*v[:,1]-u[:,1]*v[:,0])/2
        self.assertAlmostEqual(areas.sum(),4,places=13)
        self.assertAlmostEqual(np.sum(2*math.pi*areas*p[:,:,0].mean(axis=1)),7.5*math.pi,places=12)
        edges = np.unique(np.sort(mesh.triangles[:,[[0,1],[1,2],[2,0]]].reshape(-1,2),axis=1),axis=0)
        ends = mesh.points[edges]
        delta = ends[:,1]-ends[:,0]
        length = np.linalg.norm(delta,axis=1)
        self.assertLessEqual(length.max(),.5*(1+1e-12))
        boundary = mesh.points[mesh.boundary_edges[mesh.boundary_tags!='axis']]
        self.assertLessEqual(np.linalg.norm(boundary[:,1]-boundary[:,0],axis=1).max(),.2*(1+1e-12))
        # Independently check the reentrant corner's ball/segment intersection.
        corner = np.array([1.,2.])
        fraction = np.clip(np.sum((corner-ends[:,0])*delta,axis=1)/length**2,0,1)
        distances = np.linalg.norm(ends[:,0]+fraction[:,None]*delta-corner,axis=1)
        self.assertLessEqual(length[distances<=.12*(1+1e-12)].max(),.08*(1+1e-12))
        magnetic = mesh.points[mesh.boundary_edges[mesh.boundary_tags=='magnetic_symmetry']]
        self.assertTrue(np.all(magnetic[:,:,1]==0))
        self.assertAlmostEqual(np.abs(magnetic[:,1,0]-magnetic[:,0,0]).sum(),.25)
        again = refine_contour(case,initial,.5)
        for name in ('points','triangles','boundary_edges','boundary_tags'):
            np.testing.assert_array_equal(getattr(mesh,name),getattr(again,name))
        quality = contour_mesh_quality(mesh)
        self.assertGreater(quality['min_angle_deg'],0)
        self.assertGreater(quality['min_quality'],0)
        self.assertLessEqual(quality['median_quality'],1+1e-14)

    def test_refinement_limits_and_strict_controls(self):
        case = Case((),contour=Contour(((0,0),(3,0),(0,2)),('axis','pec','pec')))
        mesh = triangulate_contour(case)
        for size in (0,-1,True,float('nan'),float('inf'),'1'):
            with self.subTest(size=size),self.assertRaisesRegex(ValueError,'max_edge_m'):
                refine_contour(case,mesh,size)
        with self.assertRaisesRegex(ValueError,'max_triangles'):
            refine_contour(case,mesh,.01,max_triangles=5)
        with self.assertRaisesRegex(ValueError,'max_passes'):
            refine_contour(case,mesh,.01,max_passes=1)
        for kwargs in ({'max_triangles':True},{'max_passes':0}):
            with self.assertRaises(ValueError):refine_contour(case,mesh,1.,**kwargs)

    def test_quality_known_right_triangle(self):
        case = Case((),contour=Contour(((0,0),(1,0),(0,1)),('axis','pec','pec')))
        quality = contour_mesh_quality(triangulate_contour(case))
        self.assertAlmostEqual(quality['min_angle_deg'],45)
        self.assertAlmostEqual(quality['min_quality'],math.sqrt(3)/2)
        self.assertAlmostEqual(quality['max_edge_m'],math.sqrt(2))

    def test_internal_flips_preserve_boundary_and_improve_quality(self):
        contour = Contour(((0,0),(3,0),(3,2),(1,2),(1,1),(2,1),(2,.5),(0,.5),(0,.25)),
                          ('axis',)+('pec',)*7+('magnetic_symmetry',))
        case = Case((),contour=contour,corner_max_edge_m=.1,corner_radius_m=.12)
        original = refine_contour(case,triangulate_contour(case),.25)
        improved = improve_contour_angles(case,original)
        old,new = contour_mesh_quality(original),contour_mesh_quality(improved)
        self.assertGreater(new['median_quality'],old['median_quality'])
        self.assertGreaterEqual(new['min_angle_deg'],old['min_angle_deg']-1e-12)
        self.assertLessEqual(new['max_edge_m'],old['max_edge_m']*(1+1e-12))
        for name in ('points','boundary_edges','boundary_tags','axis_nodes'):
            np.testing.assert_array_equal(getattr(original,name),getattr(improved,name))
        # Geometrical first moment is independent of the internal diagonal.
        p = improved.points[improved.triangles]
        u,v = p[:,1]-p[:,0],p[:,2]-p[:,0]
        areas = (u[:,0]*v[:,1]-u[:,1]*v[:,0])/2
        self.assertAlmostEqual(areas.sum(),4.,places=13)
        self.assertAlmostEqual(np.sum(2*math.pi*areas*p[:,:,0].mean(axis=1)),7.5*math.pi,places=12)
        # No new local-size violation, and a second improvement is a fixed point.
        refined = refine_contour(case,improved,.25)
        np.testing.assert_array_equal(refined.triangles,improved.triangles)
        again = improve_contour_angles(case,improved)
        np.testing.assert_array_equal(again.triangles,improved.triangles)
        repeated = improve_contour_angles(case,original)
        np.testing.assert_array_equal(repeated.triangles,improved.triangles)
        with self.assertRaisesRegex(ValueError,'max_sweeps'):
            improve_contour_angles(case,original,max_sweeps=True)

    def test_smoothing_preserves_boundary_moments_and_local_sizes(self):
        contour = Contour(((0,0),(3,0),(3,2),(1,2),(1,1),(2,1),(2,.5),(0,.5),(0,.25)),
                          ('axis',)+('pec',)*7+('magnetic_symmetry',))
        case = Case((),contour=contour,corner_max_edge_m=.1,corner_radius_m=.12)
        original = improve_contour_angles(case,refine_contour(case,triangulate_contour(case),.25))
        moved = smooth_contour_interior(case,original,.25)
        old,new = contour_mesh_quality(original),contour_mesh_quality(moved)
        self.assertGreater(new['min_quality'],old['min_quality'])
        self.assertLessEqual(new['max_edge_m'],.25*(1+1e-12))
        for name in ('triangles','boundary_edges','boundary_tags','axis_nodes'):
            np.testing.assert_array_equal(getattr(original,name),getattr(moved,name))
        np.testing.assert_array_equal(original.points[original.boundary_edges],moved.points[moved.boundary_edges])
        p = moved.points[moved.triangles]
        u,v = p[:,1]-p[:,0],p[:,2]-p[:,0]
        areas = (u[:,0]*v[:,1]-u[:,1]*v[:,0])/2
        self.assertTrue(np.all(areas>0))
        self.assertAlmostEqual(areas.sum(),4.,places=13)
        self.assertAlmostEqual(np.sum(2*math.pi*areas*p[:,:,0].mean(axis=1)),7.5*math.pi,places=12)
        refined = refine_contour(case,moved,.25)
        np.testing.assert_array_equal(refined.points,moved.points)
        repeated = smooth_contour_interior(case,original,.25)
        np.testing.assert_array_equal(repeated.points,moved.points)
        with self.assertRaisesRegex(ValueError,'refine it first'):
            smooth_contour_interior(case,original,.1)
        for size in (False,0,float('nan')):
            with self.assertRaisesRegex(ValueError,'max_edge_m'):
                smooth_contour_interior(case,original,size)
        with self.assertRaisesRegex(ValueError,'sweeps'):
            smooth_contour_interior(case,original,.25,sweeps=True)

    def test_quality_insertion_narrow_channel_and_rejection(self):
        width = .05
        contour = Contour(((0,0),(3,0),(3,2),(1,2),(1,1),(2,1),(2,width),(0,width)),
                          ('axis',)+('pec',)*7)
        case = Case((),contour=contour)
        mesh = quality_contour_mesh(case,.25,max_triangles=4000,max_rounds=8)
        quality = contour_mesh_quality(mesh)
        self.assertGreaterEqual(quality['min_angle_deg'],10.)
        self.assertLessEqual(quality['max_edge_m'],.25*(1+1e-12))
        p = mesh.points[mesh.triangles]
        u,v = p[:,1]-p[:,0],p[:,2]-p[:,0]
        areas = (u[:,0]*v[:,1]-u[:,1]*v[:,0])/2
        self.assertAlmostEqual(areas.sum(),3+2*width,places=12)
        self.assertAlmostEqual(np.sum(2*math.pi*areas*p[:,:,0].mean(axis=1)),math.pi*(7+2*width**2),places=11)
        self.assertGreater(len(mesh.boundary_edges),len(contour.edge_tags))
        with self.assertRaisesRegex(ValueError,'quality unmet'):
            quality_contour_mesh(case,.25,max_triangles=4000,max_rounds=1)
        with self.assertRaisesRegex(ValueError,'max_triangles'):
            quality_contour_mesh(case,.25,max_triangles=500,max_rounds=8)
        for angle in (0,60,True,float('nan')):
            with self.assertRaisesRegex(ValueError,'min_angle_deg'):
                quality_contour_mesh(case,.25,min_angle_deg=angle)
