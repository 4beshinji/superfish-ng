# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng.fem import triangle_quadrature
from superfish_ng.planar import planar_quantities, solve_planar
from superfish_ng.planar_mesh import PlanarMesh
from superfish_ng.planar_polygon import PlanarPolygonCase
from superfish_ng.planar_saved import save_planar_run
from superfish_ng.planar_tracking import PlanarTrackingRequest, track_planar_modes
from superfish_ng.planar_tracking_fields import _electric_grams
from superfish_ng.planar_tracking_history import PlanarTrackingHistoryRequest
from superfish_ng.planar_tracking_history_saved import execute_planar_history, read_planar_history
from superfish_ng.planar_tracking_jobs import execute_planar_tracking, read_planar_tracking
from superfish_ng.planar_tracking_similarity_remesh import (
    PolygonSimilarityRemeshMapping, polygon_similarity_remesh_overlay)


def square(n, flipped=False, origin=0., width=1.):
    points=np.array([[origin+width*i/n,origin+width*j/n] for j in range(n+1) for i in range(n+1)])
    triangles=[]
    for j in range(n):
        for i in range(n):
            a=j*(n+1)+i;b=a+1;d=a+n+1;c=d+1
            triangles.extend([(a,b,d),(b,c,d)] if flipped else [(a,b,c),(a,c,d)])
    return PlanarMesh.create([[origin,origin],[origin+width,origin],[origin+width,origin+width],[origin,origin+width]],points,triangles)


def scalar_transform(mesh, mapping, *, reverse=False):
    inverse=reverse!=mapping.inverse
    c,sine=np.cos(mapping.rotation_radians),np.sin(mapping.rotation_radians)
    tx,ty=mapping.translation_xy_m
    def points(values):
        x,y=values.T
        if inverse:
            x,y=x-tx,y-ty
            return np.column_stack(((c*x+sine*y)/mapping.scale,(-sine*x+c*y)/mapping.scale))
        return np.column_stack((mapping.scale*(c*x-sine*y)+tx,mapping.scale*(sine*x+c*y)+ty))
    return PlanarMesh.create(points(mesh.polygon_xy_m),points(mesh.points_xy_m),mesh.triangles)


class PlanarSimilarityRemeshGeometryTests(unittest.TestCase):
    def test_strict_mapping_and_version_roundtrip(self):
        mapping=PolygonSimilarityRemeshMapping(.37,.371,(.13,-.08),max_candidate_tests=99)
        self.assertEqual(PolygonSimilarityRemeshMapping.from_dict(mapping.to_dict()),mapping)
        for change in ({'scale':True},{'scale':-1},{'rotation_radians':float('nan')},
                       {'translation_xy_m':[0,float('inf')]},{'translation_xy_m':(0,0)},
                       {'inverse':1},{'max_candidate_tests':0},{'max_candidate_tests':True},
                       {'max_candidate_tests':1.5},{'shear':0},{'name':'polygon_similarity'}):
            with self.assertRaises(ValueError):
                PolygonSimilarityRemeshMapping.from_dict({**mapping.to_dict(),**change})
        with self.assertRaises(ValueError):
            PolygonSimilarityRemeshMapping.from_dict({k:v for k,v in mapping.to_dict().items() if k!='scale'})
        request=PlanarTrackingRequest(1,1,['fundamental'],mapping=mapping).to_dict()
        self.assertEqual(request['tracking_version'],5)
        self.assertEqual(PlanarTrackingRequest.from_dict(request).to_dict(),request)
        old=PlanarTrackingRequest().to_dict()
        self.assertEqual(PlanarTrackingRequest.from_dict(old).to_dict(),old)
        with self.assertRaises(ValueError):
            PlanarTrackingRequest.from_dict({**request,'tracking_version':4})
        with self.assertRaises(ValueError):
            PlanarTrackingRequest.from_dict({**request,'tracking_version':6})

    def test_transformed_boundary_recognition_and_independent_interior(self):
        mapping=PolygonSimilarityRemeshMapping(.37,.371,(.13,-.08))
        for n in (2,3,4):
            a=square(n);b=mapping.transform_mesh(square(n,True))
            self.assertFalse(np.array_equal(a.triangles,b.triangles))
            overlay=polygon_similarity_remesh_overlay(a,b,mapping)
            self.assertAlmostEqual(sum(overlay.reference_determinants)/(2*b.area_m2),1.,places=12)
            self.assertAlmostEqual(sum(overlay.reference_determinants)/(2*a.area_m2),mapping.scale**2,places=12)
            transformed=mapping.transform_mesh(a)
            vertices=transformed.points_xy_m[transformed.triangles]
            determinant=np.linalg.det(np.stack((vertices[:,1]-vertices[:,0],vertices[:,2]-vertices[:,0]),axis=-1))
            np.testing.assert_allclose(np.bincount(overlay.previous_cells,weights=overlay.reference_determinants),determinant,rtol=1e-13,atol=1e-16)
            for cells,bary,mesh in ((overlay.previous_cells,overlay.previous_vertex_barycentric,transformed),
                                    (overlay.current_cells,overlay.current_vertex_barycentric,b)):
                mapped=np.einsum('nij,njk->nik',bary,mesh.points_xy_m[mesh.triangles[cells]])
                np.testing.assert_allclose(mapped,overlay.reference_vertices,rtol=1e-13,atol=1e-15)
                self.assertFalse(bary.flags.writeable)
            reverse=polygon_similarity_remesh_overlay(b,a,replace(mapping,inverse=True))
            self.assertAlmostEqual(sum(reverse.reference_determinants)/(2*b.area_m2),1.,places=12)
            self.assertAlmostEqual(sum(reverse.reference_determinants)/(2*a.area_m2),mapping.scale**2,places=12)

    def test_explicit_component_order_and_moment_integrals(self):
        mapping=PolygonSimilarityRemeshMapping(.37,.371,(.13,-.08))
        a=square(6)
        self.assertFalse(np.array_equal(mapping.transform_mesh(a).points_xy_m,scalar_transform(a,mapping).points_xy_m))
        overlay=polygon_similarity_remesh_overlay(a,scalar_transform(square(6,True),mapping),mapping)
        self.assertAlmostEqual(sum(overlay.reference_determinants)/(2*a.area_m2),mapping.scale**2,places=12)
        scaled=PolygonSimilarityRemeshMapping(1.3,0.,(0.,0.))
        b=scalar_transform(square(6,True),scaled)
        overlay=polygon_similarity_remesh_overlay(a,b,scaled)
        for px,py in ((0,0),(1,0),(0,1),(2,1)):
            integral=0.
            for bary,weight in triangle_quadrature(5):
                xy=np.einsum('j,njk->nk',bary,overlay.reference_vertices)
                integral+=np.sum(weight*overlay.reference_determinants*xy[:,0]**px*xy[:,1]**py)
            self.assertAlmostEqual(integral,scaled.scale**(px+py+2)/((px+1)*(py+1)),places=11)

    def test_wrong_declaration_boundary_and_resource_bounds(self):
        mapping=PolygonSimilarityRemeshMapping(.37,.371,(.13,-.08))
        a=square(3);b=mapping.transform_mesh(square(3,True))
        for wrong in (replace(mapping,scale=.38),replace(mapping,rotation_radians=0.),
                      replace(mapping,translation_xy_m=(0.,0.))):
            with self.assertRaisesRegex(ValueError,'boundary cycle'):
                polygon_similarity_remesh_overlay(a,b,wrong)
        with self.assertRaisesRegex(ValueError,'boundary cycle'):
            polygon_similarity_remesh_overlay(a,mapping.transform_mesh(square(4,True)),mapping)
        changed=square(3,width=1.+8*np.spacing(1.))
        with self.assertRaisesRegex(ValueError,'boundary cycle'):
            polygon_similarity_remesh_overlay(a,changed,PolygonSimilarityRemeshMapping(1.,0.,(0.,0.)))
        with self.assertRaisesRegex(ValueError,'input meshes'):
            polygon_similarity_remesh_overlay(a,b,mapping,max_overlay_triangles=2)
        with self.assertRaisesRegex(ValueError,'max_candidate_tests'):
            polygon_similarity_remesh_overlay(a,b,replace(mapping,max_candidate_tests=1))


class PlanarSimilarityRemeshIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mapping=PolygonSimilarityRemeshMapping(2.,np.pi/2,(.13,-.08))
        cls.independent=PolygonSimilarityRemeshMapping(.37,.371,(.13,-.08))
        mesh=square(6);cls.concurrent={};cls.independent_pairs={}
        for pol,count in (('te',2),('tm',3)):
            for order in (1,2):
                case=PlanarPolygonCase(mesh,pol,order,count+1)
                cls.concurrent[pol,order]=(solve_planar(case),
                    solve_planar(replace(case,mesh=cls.mapping.transform_mesh(square(6)))))
                cls.independent_pairs[pol,order]=(solve_planar(case),
                    solve_planar(replace(case,mesh=cls.independent.transform_mesh(square(6,True)))))

    def test_frequency_rotation_and_rf_similarity_laws(self):
        for (pol,order),(a,b) in self.concurrent.items():
            np.testing.assert_allclose(b.frequencies_hz,a.frequencies_hz/2,rtol=1e-11)
            part=polygon_similarity_remesh_overlay(a.case.mesh,b.case.mesh,self.mapping)
            plain=_electric_grams(a,b,part,5)
            rotated=_electric_grams(a,b,part,5,current_to_previous_rotation=self.mapping.current_to_previous_rotation)
            normalizer=np.sqrt(rotated[0][0,0]*rotated[2][0,0])
            self.assertAlmostEqual(abs(rotated[1][0,0])/normalizer,1.,places=11)
            if pol=='te':
                self.assertLess(abs(plain[1][0,0])/normalizer,1e-9)
            qa,qb=planar_quantities(a),planar_quantities(b)
            self.assertAlmostEqual(qb['geometry_factor_ohm']/qa['geometry_factor_ohm'],1.,places=10)
            self.assertAlmostEqual(qb['q0']/qa['q0'],np.sqrt(2),places=10)
            self.assertAlmostEqual(qb['wall_loss_w_per_m']/qa['wall_loss_w_per_m'],1/2**1.5,places=10)

    def test_independent_interior_mesh_tracks_rotation_and_guard(self):
        for (pol,order),(a,b) in self.independent_pairs.items():
            count=a.case.modes-1
            ids=[f'mode-{i}' for i in range(count)]
            request=PlanarTrackingRequest(count,count,ids,mapping=self.independent)
            result=track_planar_modes(a,b,request)
            self.assertEqual(result['result_version'],5)
            self.assertEqual(result['status'],'PASS')
            mapping=result['physical_mapping']
            self.assertEqual(mapping['name'],'polygon_similarity_remesh')
            self.assertEqual(mapping['declaration'],self.independent.to_dict())
            np.testing.assert_allclose(mapping['current_to_previous_rotation'],self.independent.current_to_previous_rotation)
            self.assertIn('exact common frame',mapping['reference_measure'])
            reverse=track_planar_modes(b,a,PlanarTrackingRequest(count,count,ids,mapping=replace(self.independent,inverse=True)))
            self.assertEqual(reverse['status'],'PASS')
            cut=track_planar_modes(a,b,PlanarTrackingRequest(count-1,count-1,ids[:-1],mapping=self.independent))
            self.assertEqual(cut['status'],'UNVERIFIED')
            self.assertTrue(any(cut['guard_overlap']))

    def test_degenerate_electric_subspaces_and_guard_are_preserved(self):
        for pol,count in (('te',2),('tm',3)):
            case=PlanarPolygonCase(square(6),pol,2,count+1)
            a=solve_planar(case)
            b=solve_planar(replace(case,mesh=self.independent.transform_mesh(square(6,True))))
            ids=[f'mode-{i}' for i in range(count)]
            result=track_planar_modes(a,b,PlanarTrackingRequest(count,count,ids,mapping=self.independent))
            self.assertEqual(result['status'],'PASS')
            cut=track_planar_modes(a,b,PlanarTrackingRequest(count-1,count-1,ids[:-1],mapping=self.independent))
            self.assertEqual(cut['status'],'UNVERIFIED')
            self.assertTrue(any(cut['guard_overlap']))
        case=PlanarPolygonCase(square(6),'te',2,3)
        a=solve_planar(case)
        b=solve_planar(replace(case,mesh=self.independent.transform_mesh(square(6,True))))
        result=track_planar_modes(a,b,PlanarTrackingRequest(2,2,['mode-1','mode-2'],mapping=self.independent))
        self.assertEqual(result['status'],'PASS')
        self.assertTrue(any(match['dimension']==2 and match['kind']=='SUBSPACE' for match in result['matches']))

    def test_saved_worker_and_composed_remeshed_history_chain(self):
        base=square(6)
        first=PolygonSimilarityRemeshMapping(.37,.371,(.13,-.08))
        second=PolygonSimilarityRemeshMapping(1.7,-.217,(-.02,.11))
        case=PlanarPolygonCase(base,'tm',2,2)
        a=solve_planar(case)
        b=solve_planar(replace(case,mesh=first.transform_mesh(square(6,True))))
        c=solve_planar(replace(case,mesh=second.transform_mesh(first.transform_mesh(square(6,False)))))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,solution in [('a',a),('b',b),('c',c)]:
                save_planar_run(solution.case,solution,root/name)
            for name,left,right,mapping in [('ab','a','b',first),('bc','b','c',second)]:
                execute_planar_tracking(root/left,root/right,PlanarTrackingRequest(1,1,['fundamental'],mapping=mapping),root/name)
                self.assertEqual(read_planar_tracking(root/name)['status'],'PASS')
            result=execute_planar_history([root/'ab',root/'bc'],PlanarTrackingHistoryRequest(2),root/'history')
            self.assertEqual(result['status'],'PASS')
            self.assertEqual(result['current_mode_ids'],['fundamental'])
            self.assertTrue(result['can_extend'])
            self.assertEqual(result['steps'][0]['request']['mapping'],first.to_dict())
            self.assertEqual(result['steps'][1]['request']['mapping'],second.to_dict())
            self.assertEqual(read_planar_history(root/'history'),result)
            target=root/'ab'/'tracking.json'
            data=json.loads(target.read_text())
            data['mapping']['max_candidate_tests']=1
            target.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                read_planar_tracking(root/'ab')


if __name__=='__main__':
    unittest.main()
