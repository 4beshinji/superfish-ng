# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from scripts.hphi_mesh_reference import rectangular_holes
from superfish_ng.axis_connected_mesh import AxisConnectedMesh
from superfish_ng.meridional_mesh import MeridionalMesh
from superfish_ng.meridional_overlap import meridional_overlay
from superfish_ng.fem import triangle_quadrature


def fixture(n,holes=1,axis=False,opposite=False,sloped=False):
    data=rectangular_holes(n,holes);strips=5 if holes==2 else 3
    def mapped(points):
        points=np.asarray(points);r=np.round((points[:,0]-.025)/.075*(strips*n))/(32*n)
        z=np.round(points[:,1]/.18*(3*n))/(32*n)
        if not axis:r+=1/32
        if sloped:r+=z/2
        return np.column_stack((r,z))
    for key in ('outer_rz_m','points_rz_m'):data[key]=mapped(data[key])
    data['holes_rz_m']=[mapped(h) for h in data['holes_rz_m']]
    if opposite:
        # The fixture emits pairs [a,b,c], [a,c,d]; use the other diagonal.
        pairs=data['triangles'].reshape(-1,2,3);a,b,c,d=pairs[:,0,0],pairs[:,0,1],pairs[:,0,2],pairs[:,1,2]
        data['triangles']=np.stack((np.column_stack((a,b,d)),np.column_stack((b,c,d))),axis=1).reshape(-1,3)
    return (AxisConnectedMesh if axis else MeridionalMesh)(**data)


class MeridionalOverlayTests(unittest.TestCase):
    def test_concave_partial_axis_and_hole(self):
        for axis in (False,True):
            meshes=[]
            offset=0. if axis else 1/32
            for n in (1,2):
                points=np.array([(i/(32*n)+offset,j/(32*n)) for j in range(8*n+1) for i in range(8*n+1)])
                triangles=[]
                for j in range(8*n):
                    for i in range(8*n):
                        if j>=4*n and i<4*n or 2*n<=i<3*n and n<=j<2*n:continue
                        a=j*(8*n+1)+i;b=a+1;d=a+8*n+1;c=d+1
                        triangles.extend(((a,b,c),(a,c,d)) if n==1 else ((a,b,d),(b,c,d)))
                used=np.unique(triangles);mapping=np.full(len(points),-1,dtype=int);mapping[used]=np.arange(len(used))
                outer=np.array([[0,0],[8,0],[8,8],[4,8],[4,4],[0,4]])/32;outer[:,0]+=offset
                hole=np.array([[2,1],[2,2],[3,2],[3,1]])/32;hole[:,0]+=offset
                meshes.append((AxisConnectedMesh if axis else MeridionalMesh)(outer,[hole],points[used],mapping[np.array(triangles)]))
            overlay=meridional_overlay(*meshes)
            self.assertAlmostEqual(overlay.determinants.sum()/2,(64-16-1)/32**2,delta=1e-14)
            volume=sum(np.dot(weight*overlay.determinants,np.einsum('tij,i->tj',overlay.vertices_rz_m,bary)[:,0]) for bary,weight in triangle_quadrature(4))
            exact=((offset+8/32)**2-offset**2)/2*(8/32)-((offset+4/32)**2-offset**2)/2*(4/32)-((offset+3/32)**2-(offset+2/32)**2)/2/32
            self.assertAlmostEqual(volume/exact,1.,delta=1e-12)
            if axis:self.assertEqual(meshes[0].axis_interval_m,(0.,.125))

    def test_exact_vacuum_coverage_and_independent_rectangular_moments(self):
        for axis in (False,True):
            for holes in (0,1,2):
                previous,current=fixture(1,holes,axis),fixture(2,holes,axis,True)
                overlay=meridional_overlay(previous,current)
                rectangles=[(*previous.outer_rz_m[0],*previous.outer_rz_m[2],1.)]
                rectangles += [(h[0,0],h[0,1],h[2,0],h[2,1],-1.) for h in previous.holes_rz_m]
                for rp,zp in ((0,0),(1,0),(3,0),(1,2),(3,2)):
                    exact=sum(sign*(b**(rp+1)-a**(rp+1))/(rp+1)*(d**(zp+1)-c**(zp+1))/(zp+1) for a,c,b,d,sign in rectangles)
                    value=0.
                    for bary,weight in triangle_quadrature(5):
                        rz=np.einsum('tij,i->tj',overlay.vertices_rz_m,bary)
                        value+=np.dot(weight*overlay.determinants,rz[:,0]**rp*rz[:,1]**zp)
                    self.assertAlmostEqual(value/exact,1.,delta=1e-12)
                for mesh,cells,bary in ((previous,overlay.previous_cells,overlay.previous_vertex_barycentric),(current,overlay.current_cells,overlay.current_vertex_barycentric)):
                    vertices=mesh.points_rz_m[mesh.triangles[cells]]
                    np.testing.assert_allclose(np.einsum('tij,tjk->tik',bary,vertices),overlay.vertices_rz_m,rtol=1e-14,atol=1e-16)
                self.assertFalse(overlay.vertices_rz_m.flags.writeable)

    def test_sloped_domain_relabeling_and_independent_boundary_subdivision(self):
        previous,current=fixture(1,2,sloped=True),fixture(2,2,opposite=True,sloped=True)
        raw=current.to_dict();raw['outer_rz_m']=raw['outer_rz_m'][1:]+raw['outer_rz_m'][:1]
        raw['holes_rz_m']=raw['holes_rz_m'][::-1]
        points=np.asarray(raw['points_rz_m']);permutation=np.random.default_rng(7).permutation(len(points));inverse=np.argsort(permutation)
        raw['points_rz_m']=points[permutation].tolist();raw['triangles']=inverse[np.asarray(raw['triangles'])[::-1]][:,[1,2,0]].tolist()
        # Split declared contour edges as well as the actual boundary mesh.
        outer=np.asarray(raw['outer_rz_m']);raw['outer_rz_m']=np.stack((outer,(outer+np.roll(outer,-1,axis=0))/2),axis=1).reshape(-1,2).tolist()
        current=MeridionalMesh.from_dict(raw);overlap=meridional_overlay(previous,current)
        self.assertAlmostEqual(overlap.determinants.sum()/2/previous.area_m2,1.,delta=1e-12)
        self.assertEqual(set(overlap.previous_cells),set(range(len(previous.triangles))))
        self.assertEqual(set(overlap.current_cells),set(range(len(current.triangles))))

    def test_different_vacuum_and_resource_limits_rejected(self):
        one,two=fixture(1,1),fixture(1,2)
        for other in (two,fixture(1,0)):
            with self.assertRaisesRegex(ValueError,'same.*vacuum'):meridional_overlay(one,other)
        raw=one.to_dict()
        for name in ('outer_rz_m','points_rz_m'):
            for point in raw[name]:point[0]+=2**-40
        for hole in raw['holes_rz_m']:
            for point in hole:point[0]+=2**-40
        changed=MeridionalMesh.from_dict(raw)
        with self.assertRaisesRegex(ValueError,'same.*vacuum'):meridional_overlay(one,changed)
        for kwargs in ({'max_candidate_tests':1},{'max_overlay_triangles':1},{'max_candidate_tests':True}):
            with self.assertRaises(ValueError):meridional_overlay(one,one,**kwargs)
        with self.assertRaises(ValueError):meridional_overlay(one.to_dict(),one)


if __name__=='__main__':unittest.main()
