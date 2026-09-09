# SPDX-License-Identifier: Apache-2.0
import copy
import unittest
import numpy as np
from superfish_ng.planar_mesh import PlanarMesh, _orient, _check_edges


class PlanarMeshTests(unittest.TestCase):
    def rectangle(self,nx=4,ny=3):
        x,y=np.meshgrid(np.linspace(0,2,nx+1),np.linspace(0,1,ny+1))
        p=np.column_stack((x.ravel(),y.ravel()));cells=[]
        for j in range(ny):
            for i in range(nx):
                a=j*(nx+1)+i;b=a+nx+1
                cells.extend(((a,a+1,b+1),(a,b+1,b)))
        return np.array([[0.,0.],[2.,0.],[2.,1.],[0.,1.]]),p,np.array(cells)

    def test_area_boundary_and_rigid_transform(self):
        polygon,points,cells=self.rectangle()
        for angle in (0.,.317,1.731):
            r=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
            for scale in (1e-6,1.,1e6):
                shift=np.array([-3.,7.])*scale
                mesh=PlanarMesh.create(polygon@r.T*scale+shift,points@r.T*scale+shift,cells)
                self.assertAlmostEqual(mesh.area_m2/(2*scale**2),1.,places=13)
                perimeter=np.linalg.norm(np.diff(mesh.points_xy_m[mesh.boundary_edges],axis=1)[:,0],axis=1).sum()
                self.assertAlmostEqual(perimeter/(6*scale),1.,places=13)
                np.testing.assert_array_equal(mesh.points_xy_m[mesh.triangles[mesh.boundary_cells[:,None],mesh.boundary_local_vertices]],mesh.points_xy_m[mesh.boundary_edges])
                self.assertFalse(mesh.points_xy_m.flags.writeable)
                self.assertEqual(PlanarMesh.from_dict(mesh.to_dict()).to_dict(),mesh.to_dict())

    def test_concave_polygon_and_thin_triangle(self):
        polygon=np.array([[0.,0.],[2.,0.],[2.,1.],[1.,1.],[1.,2.],[0.,2.]])
        mesh=PlanarMesh.create(polygon,polygon,[[0,1,3],[1,2,3],[0,3,5],[3,4,5]])
        self.assertAlmostEqual(mesh.area_m2,3.)
        thin=np.array([[0.,0.],[1.,0.],[.3,1e-12]])
        self.assertAlmostEqual(PlanarMesh.create(thin,thin,[[0,1,2]]).area_m2/5e-13,1.)

    def test_strict_schema_and_numeric_types(self):
        mesh=PlanarMesh.create(*self.rectangle());data=mesh.to_dict()
        for key,value in [('coordinates','rz'),('boundary','magnetic'),('schema_version',True),('extra',1)]:
            bad=copy.deepcopy(data);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):PlanarMesh.from_dict(bad)
        for key,value in [('points_xy_m',True),('points_xy_m','0'),('points_xy_m',float('nan')),('triangles',0.)]:
            bad=copy.deepcopy(data);bad[key][0][0]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):PlanarMesh.from_dict(bad)

    def test_degenerate_duplicate_and_unused_data(self):
        polygon,points,cells=self.rectangle()
        cases=[(polygon,np.vstack((points,[[.1,.2]])),cells),(polygon,np.vstack((points,points[:1])),cells),(polygon,points,np.vstack((cells,cells[:1]))),(polygon,points,cells[:,::-1]),(polygon[::-1],points,cells)]
        for args in cases:
            with self.subTest(),self.assertRaises(ValueError):PlanarMesh.create(*args)

    def test_hole_and_disconnected_mesh_rejected(self):
        p=np.array([[0.,0.],[3.,0.],[3.,3.],[0.,3.],[1.,1.],[2.,1.],[2.,2.],[1.,2.]])
        cells=[]
        for i in range(4):
            j=(i+1)%4;cells.extend(((i,j,j+4),(i,j+4,i+4)))
        with self.assertRaisesRegex(ValueError,'disk without holes'):PlanarMesh.create(p[:4],p,cells)
        p=np.array([[0.,0.],[1.,0.],[0.,1.],[2.,0.],[3.,0.],[2.,1.]])
        with self.assertRaisesRegex(ValueError,'edge-connected'):PlanarMesh.create([[0.,0.],[3.,0.],[3.,1.],[0.,1.]],p,[[0,1,2],[3,4,5]])

    def test_declared_boundary_mismatch_not_just_area(self):
        polygon,points,cells=self.rectangle()
        # Same area: shift the declaration while leaving the mesh untouched.
        with self.assertRaises(ValueError):PlanarMesh.create(polygon+[.1,0],points,cells)
        polygon=np.array([[0.,0.],[2.,0.],[2.,1.],[1.,.5],[0.,1.]])
        points=np.vstack((polygon,[[1.,1.]]))
        # Declared reentrant corner is internal in a different-area triangulation.
        with self.assertRaises(ValueError):PlanarMesh.create(polygon,points,[[0,1,3],[1,2,3],[2,5,3],[5,4,3],[4,0,3]])

    def test_edge_crossing_overlap_and_t_junction(self):
        for points,edges in [([[0,0],[1,1],[0,1],[1,0]],[[0,1],[2,3]]),([[0,0],[1,0],[.5,0],[.5,1]],[[0,1],[2,3]]),([[0,0],[1,0],[.5,0]],[[0,1],[0,2]])]:
            with self.subTest(points=points),self.assertRaises(ValueError):_check_edges(np.asarray(points,float),np.asarray(edges),'test')
        _check_edges(np.array([[0.,0.],[1.,0.],[-1.,0.]]),np.array([[0,1],[0,2]]),'allowed straight subdivision')
        polygon=np.array([[0.,0.],[2.,2.],[0.,2.],[2.,0.]])
        with self.assertRaisesRegex(ValueError,'intersect'):PlanarMesh.create(polygon,polygon,[[0,3,1],[0,1,2]])

    def test_polygon_mass_moments_and_linear_gradient_patch(self):
        from superfish_ng.planar import planar_mesh_matrices
        polygon=np.array([[0.,0.],[2.,0.],[2.,1.],[1.,1.],[1.,2.],[0.,2.]])
        mesh=PlanarMesh.create(polygon,polygon,[[0,1,3],[1,2,3],[0,3,5],[3,4,5]])
        for order in (1,2):
            for polarization in ('te','tm'):
                space,k,m,free=planar_mesh_matrices(mesh,order,polarization)
                x,y=space.dof_points_xy_m.T;one=np.ones(len(x))
                for actual,expected in ((one@(m@one),3.),(one@(m@x),2.5),(one@(m@y),2.5),(x@(m@x),3.),(y@(m@y),3.),(x@(m@y),1.75),(x@(k@x),3.),(y@(k@y),3.),(x@(k@y),0.)):
                    self.assertAlmostEqual(actual,expected,places=12)
                np.testing.assert_allclose(k@one,0,atol=2e-14)
                expected=np.setdiff1d(np.arange(len(x)),space.boundary_dofs) if polarization=='tm' else np.arange(len(x))
                np.testing.assert_array_equal(free,expected)

    def test_rectangle_assembly_preserves_matrices(self):
        from superfish_ng.planar import PlanarCase,planar_matrices,planar_mesh_matrices
        polygon,points,cells=self.rectangle()
        mesh=PlanarMesh.create(polygon,points,cells)
        for order in (1,2):
            for polarization in ('te','tm'):
                old=planar_matrices(PlanarCase(2.,1.,polarization,nx=4,ny=3,element_order=order))
                new=planar_mesh_matrices(mesh,order,polarization)
                for a,b in zip(old[1:3],new[1:3]):
                    np.testing.assert_array_equal(a.toarray(),b.toarray())
                np.testing.assert_array_equal(old[3],new[3])

    def test_negative_triangle_hidden_by_roundoff_is_rejected(self):
        points=[[6.524466935423302,-8.763061292528544],[-8.140160146755433,9.263634334794698],[1.0838902879349916,-2.0751572147916213]]
        # Normalizing these actual binary64 coordinates gives a positive
        # determinant in float64, but their exact oriented area is negative.
        with self.assertRaises(ValueError):PlanarMesh.create(points,points,[[0,1,2]])

    def test_exact_orientation_near_cancellation(self):
        a=np.array([0.,0.]);b=np.array([1.,1.]);c=np.array([2.,np.nextafter(2.,3.)])
        self.assertEqual(_orient(a,b,c),1)
        self.assertEqual(_orient(a,c,b),-1)
        self.assertEqual(_orient(a,b,2*b),0)


if __name__=='__main__':unittest.main()
