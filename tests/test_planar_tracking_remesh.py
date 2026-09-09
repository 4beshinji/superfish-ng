# SPDX-License-Identifier: Apache-2.0
import unittest
from unittest.mock import patch
import numpy as np
from superfish_ng.planar_mesh import PlanarMesh
from superfish_ng.planar_refinement import refine_planar_mesh
from superfish_ng.planar_tracking_remesh import PolygonRemeshMapping, polygon_remesh_overlay, _candidate_pairs
from superfish_ng.fem import triangle_quadrature


def square(n, flipped=False, origin=0., width=1.):
    points=np.array([[origin+width*i/n, origin+width*j/n] for j in range(n+1) for i in range(n+1)])
    triangles=[]
    for j in range(n):
        for i in range(n):
            a=j*(n+1)+i; b=a+1; d=a+n+1; c=d+1
            triangles.extend([(a,b,d),(b,c,d)] if flipped else [(a,b,c),(a,c,d)])
    return PlanarMesh.create([[origin,origin],[origin+width,origin],[origin+width,origin+width],[origin,origin+width]],points,triangles)


class PlanarRemeshGeometryTests(unittest.TestCase):
    def test_strict_request_and_resource_bounds(self):
        mapping=PolygonRemeshMapping();self.assertEqual(PolygonRemeshMapping.from_dict(mapping.to_dict()),mapping)
        for value in (0,-1,True,1.5,float('inf')):
            with self.assertRaises(ValueError):PolygonRemeshMapping(value)
        for data in ({},dict(mapping.to_dict(),scale=1),dict(mapping.to_dict(),name='fit')):
            with self.assertRaises(ValueError):PolygonRemeshMapping.from_dict(data)
        a,b=square(2),square(3,True)
        with self.assertRaisesRegex(ValueError,'input meshes'):
            polygon_remesh_overlay(a,b,mapping,max_overlay_triangles=2)
        with self.assertRaisesRegex(ValueError,'max_candidate_tests'):
            polygon_remesh_overlay(a,b,PolygonRemeshMapping(1))
        with self.assertRaisesRegex(ValueError,'intersections exceed'):
            polygon_remesh_overlay(a,b,mapping,max_overlay_triangles=18)

    def test_per_element_area_moments_and_original_barycentric_maps(self):
        for n,m in ((2,3),(3,4),(4,2)):
            a,b=square(n),square(m,True)
            for previous,current in ((a,b),(b,a)):
                overlay=polygon_remesh_overlay(previous,current,PolygonRemeshMapping())
                for cells,bary,mesh in [(overlay.previous_cells,overlay.previous_vertex_barycentric,previous),(overlay.current_cells,overlay.current_vertex_barycentric,current)]:
                    vertices=mesh.points_xy_m[mesh.triangles]
                    det=np.linalg.det(np.stack((vertices[:,1]-vertices[:,0],vertices[:,2]-vertices[:,0]),axis=-1))
                    np.testing.assert_allclose(np.bincount(cells,weights=overlay.reference_determinants),det,rtol=1e-14,atol=1e-16)
                    mapped=np.einsum('nij,njk->nik',bary,vertices[cells]);np.testing.assert_allclose(mapped,overlay.reference_vertices,rtol=1e-14,atol=1e-16)
                    self.assertFalse(bary.flags.writeable)
                for px,py in ((0,0),(1,0),(0,1),(2,0),(1,1),(0,2),(2,2)):
                    integral=0.
                    for bary,weight in triangle_quadrature(5):
                        xy=np.einsum('j,njk->nk',bary,overlay.reference_vertices)
                        integral+=np.sum(weight*overlay.reference_determinants*xy[:,0]**px*xy[:,1]**py)
                    self.assertAlmostEqual(integral,1/((px+1)*(py+1)),places=13)

    def test_candidates_match_exhaustive_aabbs_and_missing_parts_fail(self):
        a,b=square(3),square(4,True)
        va=a.points_xy_m[a.triangles];vb=b.points_xy_m[b.triangles]
        expected={(i,j) for i,x in enumerate(va) for j,y in enumerate(vb) if np.all(x.min(0)<y.max(0)) and np.all(y.min(0)<x.max(0))}
        self.assertEqual(set(_candidate_pairs(a,b,10000)),expected)
        with patch('superfish_ng.planar_tracking_remesh._candidate_pairs',return_value=iter(())):
            with self.assertRaisesRegex(ValueError,'every original element'):
                polygon_remesh_overlay(a,b,PolygonRemeshMapping())

    def test_numbering_boundary_subdivision_and_concave_domain(self):
        a=square(3);permutation=np.arange(len(a.points_xy_m))[::-1];inverse=np.argsort(permutation)
        polygon=np.array([[1.,0.],[1.,1.],[0.,1.],[0.,1/3],[0.,0.]])
        b=PlanarMesh.create(polygon,a.points_xy_m[permutation],inverse[a.triangles[::-1]])
        overlay=polygon_remesh_overlay(a,b,PolygonRemeshMapping());self.assertAlmostEqual(sum(overlay.reference_determinants)/2,1.)
        points=np.array([[0.,0.],[2.,0.],[2.,1.],[1.,1.],[1.,2.],[0.,2.]])
        a=PlanarMesh.create(points,points,[[0,1,3],[1,2,3],[0,3,5],[3,4,5]])
        b=refine_planar_mesh(refine_planar_mesh(a));overlay=polygon_remesh_overlay(a,b,PolygonRemeshMapping())
        self.assertAlmostEqual(sum(overlay.reference_determinants)/2,3.)

    def test_small_domain_change_at_large_origin_is_not_absorbed(self):
        a=square(2,origin=1e6,width=.125);b=square(2,True,origin=1e6,width=.125+8*np.spacing(1e6))
        with self.assertRaisesRegex(ValueError,'exactly the same physical polygon'):
            polygon_remesh_overlay(a,b,PolygonRemeshMapping())
        for origin,width in ((1e6,.125),(0.,1e-6),(0.,1e3)):
            a,b=square(2,origin=origin,width=width),square(3,True,origin=origin,width=width)
            overlay=polygon_remesh_overlay(a,b,PolygonRemeshMapping());self.assertAlmostEqual(sum(overlay.reference_determinants)/(2*width**2),1.,places=12)

if __name__=='__main__':unittest.main()

class PlanarRemeshIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from superfish_ng.planar import solve_planar
        from superfish_ng.planar_polygon import PlanarPolygonCase
        cls.solutions={}
        for pol in ('te','tm'):
            count=2 if pol=='te' else 3
            cls.solutions[pol]=[solve_planar(PlanarPolygonCase(square(6,flip),pol,2,count+1)) for flip in (False,True)]

    def test_request_result_subspaces_and_guard(self):
        from superfish_ng.planar_tracking import PlanarTrackingRequest,track_planar_modes
        for pol,solutions in self.solutions.items():
            count=2 if pol=='te' else 3
            request=PlanarTrackingRequest(count,count,[f'mode-{i}' for i in range(count)],mapping=PolygonRemeshMapping())
            self.assertEqual(request.to_dict()['tracking_version'],4)
            self.assertEqual(PlanarTrackingRequest.from_dict(request.to_dict()),request)
            result=track_planar_modes(*solutions,request)
            self.assertEqual(result['result_version'],4);self.assertEqual(result['status'],'PASS')
            self.assertFalse(result['individual_ids_complete'])
            self.assertTrue(any(m['dimension']==2 for m in result['matches']))
            cut=track_planar_modes(*solutions,PlanarTrackingRequest(count-1,count-1,[f'mode-{i}' for i in range(count-1)],mapping=PolygonRemeshMapping()))
            self.assertEqual(cut['status'],'UNVERIFIED');self.assertTrue(any(cut['guard_overlap']))

    def test_saved_real_worker_and_owned_history(self):
        from pathlib import Path
        import tempfile,json
        from superfish_ng.planar_saved import save_planar_run
        from superfish_ng.planar_tracking import PlanarTrackingRequest
        from superfish_ng.planar_tracking_jobs import read_planar_tracking
        from superfish_ng.planar_tracking_history import PlanarTrackingHistoryRequest
        from superfish_ng.planar_tracking_history_saved import read_planar_history
        from superfish_ng.jobs import JobManager
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);paths=[]
            for index,solution in enumerate(self.solutions['tm']):
                path=root/f'native-{index}';save_planar_run(solution.case,solution,path);paths.append(path)
            request=PlanarTrackingRequest(1,1,['fundamental'],mapping=PolygonRemeshMapping())
            manager=JobManager(root/'workspace')
            try:
                pairs=[]
                for a,b in (paths,paths[::-1]):
                    identifier=manager.start_planar_tracking(a,b,request);self.assertEqual(manager.processes[identifier].wait(timeout=60),0)
                    directory=manager.directory(identifier);self.assertEqual(read_planar_tracking(directory)['status'],'PASS');pairs.append(directory)
                identifier=manager.start_planar_history(pairs,PlanarTrackingHistoryRequest(2));self.assertEqual(manager.processes[identifier].wait(timeout=60),0)
                result=read_planar_history(manager.directory(identifier));self.assertTrue(result['can_extend']);self.assertEqual(result['current_mode_ids'],['fundamental'])
                target=pairs[0]/'tracking.json';data=json.loads(target.read_text());data['mapping']['max_candidate_tests']=1;target.write_text(json.dumps(data))
                with self.assertRaises(ValueError):read_planar_tracking(pairs[0])
            finally:manager.close()
