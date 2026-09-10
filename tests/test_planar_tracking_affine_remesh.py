# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng.constants import C0
from superfish_ng.fem import triangle_quadrature
from superfish_ng.planar import solve_planar
from superfish_ng.planar_mesh import PlanarMesh
from superfish_ng.planar_polygon import PlanarPolygonCase
from superfish_ng.planar_saved import save_planar_run
from superfish_ng.planar_tracking import PlanarTrackingRequest, track_planar_modes
from superfish_ng.planar_tracking_affine_remesh import (
    PolygonAffineRemeshMapping, polygon_affine_remesh_overlay)
from superfish_ng.planar_tracking_fields import _electric_grams
from superfish_ng.planar_tracking_similarity_remesh import PolygonSimilarityRemeshMapping
from superfish_ng.planar_tracking_history import PlanarTrackingHistoryRequest
from superfish_ng.planar_tracking_history_saved import execute_planar_history, read_planar_history
from superfish_ng.planar_tracking_jobs import execute_planar_tracking, read_planar_tracking


def square(n, flipped=False, origin=0., width=1.):
    points=np.array([[origin+width*i/n,origin+width*j/n] for j in range(n+1) for i in range(n+1)])
    triangles=[]
    for j in range(n):
        for i in range(n):
            a=j*(n+1)+i;b=a+1;d=a+n+1;c=d+1
            triangles.extend([(a,b,d),(b,c,d)] if flipped else [(a,b,c),(a,c,d)])
    return PlanarMesh.create([[origin,origin],[origin+width,origin],[origin+width,origin+width],[origin,origin+width]],points,triangles)


def rectangle(nx, ny, width, height, flipped=False):
    points=np.array([[width*i/nx,height*j/ny] for j in range(ny+1) for i in range(nx+1)])
    triangles=[]
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i;b=a+1;d=a+nx+1;c=d+1
            triangles.extend([(a,b,d),(b,c,d)] if flipped else [(a,b,c),(a,c,d)])
    polygon=points[[0,nx,(nx+1)*(ny+1)-1,ny*(nx+1)]]
    return PlanarMesh.create(polygon,points,triangles)


def scalar_points(values, mapping, *, reverse=False):
    (a,b),(c,d)=mapping.linear_xy
    tx,ty=mapping.translation_xy_m
    x,y=values.T
    if mapping.inverse!=reverse:
        determinant=a*d-b*c
        return np.column_stack(((d*(x-tx)-b*(y-ty))/determinant,(-c*(x-tx)+a*(y-ty))/determinant))
    return np.column_stack((a*x+b*y+tx,c*x+d*y+ty))


def scalar_transform(mesh, mapping, *, reverse=False):
    polygon=scalar_points(mesh.polygon_xy_m,mapping,reverse=reverse)
    triangles=mesh.triangles
    if not mapping.orientation_preserving:
        polygon=polygon[::-1]
        triangles=triangles[:,[0,2,1]]
    return PlanarMesh.create(polygon,scalar_points(mesh.points_xy_m,mapping,reverse=reverse),triangles)


def polynomial_solution(base, functions):
    dofs=base.space.dof_points_xy_m
    return replace(base,coefficients=np.column_stack([f(dofs) for f in functions]))


def pullback(points, mapping):
    matrix, translation = mapping._effective(False)
    return (points-translation)@np.linalg.inv(matrix).T


def circle_reflection(angle):
    rotation=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
    return rotation@np.diag([-1.,1.])@rotation.T


class PlanarAffineRemeshGeometryTests(unittest.TestCase):
    def test_strict_mapping_and_version_roundtrip(self):
        mapping=PolygonAffineRemeshMapping([[.9,.2],[-.1,1.1]],(.13,-.08),max_candidate_tests=99)
        self.assertEqual(PolygonAffineRemeshMapping.from_dict(mapping.to_dict()),mapping)
        self.assertTrue(mapping.orientation_preserving)
        for change in ({'linear_xy':[[1.,1.],[1.,1.]]},{'linear_xy':[[True,0.],[0.,1.]]},
                       {'linear_xy':[[float('nan'),0.],[0.,1.]]},{'linear_xy':[[1.,0.]]},
                       {'linear_xy':[[1.,0.],[0.,1.,2.]]},{'linear_xy':[[1.,0.],0.]},
                       {'translation_xy_m':[0.]},{'translation_xy_m':[0.,float('inf')]},
                       {'translation_xy_m':(0.,0.)},{'inverse':1},{'max_candidate_tests':0},
                       {'max_candidate_tests':True},{'max_candidate_tests':1.5},
                       {'shear':0.},{'name':'polygon_similarity_remesh'}):
            with self.assertRaises(ValueError):
                PolygonAffineRemeshMapping.from_dict({**mapping.to_dict(),**change})
        with self.assertRaises(ValueError):
            PolygonAffineRemeshMapping.from_dict({k:v for k,v in mapping.to_dict().items() if k!='linear_xy'})
        with self.assertRaises(ValueError):
            PolygonAffineRemeshMapping.from_dict({**mapping.to_dict(),'linear_xy':[[1.,0.],(0.,1.)]})
        self.assertTrue(PolygonAffineRemeshMapping([[-1.,0.],[0.,1.]]).determinant_sign()<0)
        request=PlanarTrackingRequest(1,1,['fundamental'],mapping=mapping).to_dict()
        self.assertEqual(request['tracking_version'],6)
        self.assertEqual(PlanarTrackingRequest.from_dict(request).to_dict(),request)
        old=PlanarTrackingRequest().to_dict()
        self.assertEqual(PlanarTrackingRequest.from_dict(old).to_dict(),old)
        with self.assertRaises(ValueError):
            PlanarTrackingRequest.from_dict({**request,'tracking_version':3})
        with self.assertRaises(ValueError):
            PlanarTrackingRequest.from_dict({**request,'tracking_version':7})
        composed=PlanarTrackingRequest(1,1,['fundamental'],
            mapping=PolygonSimilarityRemeshMapping(.7,.3,(0.,0.))).to_dict()
        with self.assertRaises(ValueError):
            PlanarTrackingRequest.from_dict({**composed,'tracking_version':6})

    def test_transformed_boundary_recognition_and_independent_interior(self):
        mappings=[PolygonAffineRemeshMapping([[1.3,0.],[0.,.7]],(.05,-.02)),
                  PolygonAffineRemeshMapping([[1.,.25],[0.,1.]],(0.,0.)),
                  PolygonAffineRemeshMapping([[-1.,0.],[0.,1.]],(1.2,0.)),
                  PolygonAffineRemeshMapping(circle_reflection(.6).tolist(),(0.,0.)),
                  PolygonAffineRemeshMapping([[.8,.3],[-.2,1.1]],(.1,-.07)),
                  PolygonAffineRemeshMapping([[-1.,.4],[.1,.9]],(.3,.2))]
        for mapping in mappings:
            a=square(5)
            b=mapping.transform_mesh(square(5,True))
            self.assertFalse(np.array_equal(a.triangles,b.triangles))
            overlay=polygon_affine_remesh_overlay(a,b,mapping)
            self.assertAlmostEqual(sum(overlay.reference_determinants)/(2*b.area_m2),1.,places=12)
            self.assertAlmostEqual(sum(overlay.reference_determinants)/(2*a.area_m2),
                                   abs(mapping.signed_determinant),places=12)
            transformed=mapping.transform_mesh(a)
            vertices=transformed.points_xy_m[transformed.triangles]
            determinant=np.linalg.det(np.stack((vertices[:,1]-vertices[:,0],vertices[:,2]-vertices[:,0]),axis=-1))
            self.assertTrue(np.all(determinant>0))
            np.testing.assert_allclose(np.bincount(overlay.previous_cells,weights=overlay.reference_determinants),
                                       determinant,rtol=1e-13,atol=1e-16)
            preimage=pullback(overlay.reference_vertices,mapping)
            restored=np.einsum('nij,njk->nik',overlay.previous_vertex_barycentric,
                               a.points_xy_m[a.triangles[overlay.previous_cells]])
            np.testing.assert_allclose(restored,preimage,rtol=1e-13,atol=1e-15)
            mapped=np.einsum('nij,njk->nik',overlay.current_vertex_barycentric,
                             b.points_xy_m[b.triangles[overlay.current_cells]])
            np.testing.assert_allclose(mapped,overlay.reference_vertices,rtol=1e-13,atol=1e-15)
            self.assertFalse(overlay.previous_vertex_barycentric.flags.writeable)
            scalar=scalar_transform(square(5,True),mapping)
            self.assertAlmostEqual(sum(polygon_affine_remesh_overlay(a,scalar,mapping).reference_determinants)/
                                   (2*a.area_m2),abs(mapping.signed_determinant),places=12)
            reverse=PolygonAffineRemeshMapping(mapping.linear_xy,mapping.translation_xy_m,inverse=True)
            inverse_current=reverse.transform_mesh(square(5,True))
            back=polygon_affine_remesh_overlay(a,inverse_current,reverse)
            self.assertAlmostEqual(sum(back.reference_determinants)/(2*inverse_current.area_m2),1.,places=12)
            self.assertAlmostEqual(sum(back.reference_determinants)/(2*a.area_m2),
                                   1/abs(mapping.signed_determinant),places=12)
            inverse_branch=mapping.transform_mesh(a,reverse=True)
            opposite=polygon_affine_remesh_overlay(inverse_branch,a,mapping)
            ratio=sum(opposite.reference_determinants)/(2*a.area_m2)
            determinant=abs(mapping.signed_determinant)
            self.assertTrue(any(abs(ratio-expected)<1e-12 for expected in (1.,1/determinant,determinant)))

    def test_moment_integrals_and_explicit_component_order(self):
        mapping=PolygonAffineRemeshMapping([[.4,.3],[.9,.2]],(.07,-.03))
        a=square(6)
        b=scalar_transform(square(6,True),mapping)
        overlay=polygon_affine_remesh_overlay(a,b,mapping)
        matrix=np.asarray(mapping.linear_xy,dtype=float)
        vertices=a.points_xy_m[a.triangles]
        determinant=np.linalg.det(np.stack((vertices[:,1]-vertices[:,0],
                                            vertices[:,2]-vertices[:,0]),axis=-1))
        direct=0.
        for bary,weight in triangle_quadrature(6):
            xy=np.einsum('j,tjk->tk',bary,vertices)
            transformed=xy@matrix.T+np.asarray(mapping.translation_xy_m)
            direct+=np.sum(weight*determinant*abs(mapping.signed_determinant)*
                           transformed[:,0]**2*transformed[:,1])
        integral=0.
        for bary,weight in triangle_quadrature(6):
            xy=np.einsum('j,njk->nk',bary,overlay.reference_vertices)
            integral+=np.sum(weight*overlay.reference_determinants*xy[:,0]**2*xy[:,1])
        self.assertAlmostEqual(integral,direct,places=9)

    def test_wrong_declaration_boundary_and_resource_bounds(self):
        mapping=PolygonAffineRemeshMapping([[1.,.25],[0.,1.]],(.03,-.02))
        a=square(3)
        b=mapping.transform_mesh(square(3,True))
        for wrong in (PolygonAffineRemeshMapping([[.9,.25],[0.,1.]],(.03,-.02)),
                      PolygonAffineRemeshMapping([[1.,.25],[0.,1.]],(0.,0.)),
                      PolygonAffineRemeshMapping([[-1.,.25],[0.,1.]],(.03,-.02))):
            with self.assertRaisesRegex(ValueError,'boundary cycle'):
                polygon_affine_remesh_overlay(a,b,wrong)
        with self.assertRaisesRegex(ValueError,'boundary cycle'):
            polygon_affine_remesh_overlay(a,mapping.transform_mesh(square(4,True)),mapping)
        changed=square(3,width=1.+8*np.spacing(1.))
        with self.assertRaisesRegex(ValueError,'boundary cycle'):
            polygon_affine_remesh_overlay(a,changed,PolygonAffineRemeshMapping([[1.,0.],[0.,1.]]))
        with self.assertRaisesRegex(ValueError,'input meshes'):
            polygon_affine_remesh_overlay(a,b,mapping,max_overlay_triangles=2)
        with self.assertRaisesRegex(ValueError,'max_candidate_tests'):
            polygon_affine_remesh_overlay(a,b,replace(mapping,max_candidate_tests=1))
        with self.assertRaises(ValueError):
            polygon_affine_remesh_overlay(a,b,'polygon_affine_remesh')


class PlanarAffineRemeshIntegrationTests(unittest.TestCase):
    functions=[lambda p:p[:,0]+.3*p[:,1],lambda p:.2+p[:,0]**2-.5*p[:,0]*p[:,1],
               lambda p:-.1*p[:,1]**2+.4*p[:,0]]

    def _polynomial_pair(self, mapping, pol):
        base=solve_planar(PlanarPolygonCase(square(4),pol,2,3))
        current_base=solve_planar(PlanarPolygonCase(mapping.transform_mesh(square(4,True)),pol,2,3))
        previous=polynomial_solution(base,self.functions)
        current=polynomial_solution(current_base,
            [lambda points,f=f,mapping=mapping:f(pullback(points,mapping)) for f in self.functions])
        return previous,current

    def test_pointwise_adjugate_transport_on_polynomial_fields(self):
        mappings=[PolygonAffineRemeshMapping([[1.,.3],[0.,1.]],(0.,0.)),
                  PolygonAffineRemeshMapping(circle_reflection(.6).tolist(),(0.,0.)),
                  PolygonAffineRemeshMapping([[.8,.3],[-.2,1.1]],(.1,-.07)),
                  PolygonAffineRemeshMapping([[.8,.3],[-.2,1.1]],(.1,-.07),inverse=True)]
        for mapping in mappings:
            for pol in ('te','tm'):
                previous,current=self._polynomial_pair(mapping,pol)
                overlay=polygon_affine_remesh_overlay(previous.case.mesh,current.case.mesh,mapping)
                cells=len(overlay.previous_cells)
                components=('Ez_real_V_per_m',) if pol=='tm' else ('Ex_quadrature_V_per_m','Ey_quadrature_V_per_m')
                def fields(solution,side):
                    indices=np.repeat(overlay.previous_cells if side=='previous' else overlay.current_cells,3)
                    barycentric=(overlay.previous_vertex_barycentric if side=='previous'
                                 else overlay.current_vertex_barycentric).reshape(-1,3)
                    return [[solution.fields_in_cells(indices,barycentric,mode)[key].reshape(cells,3)
                             for key in components] for mode in range(3)]
                old,new=fields(previous,'previous'),fields(current,'current')
                if pol=='tm':
                    for mode in range(3):
                        np.testing.assert_allclose(new[mode][0],old[mode][0],rtol=1e-11,atol=1e-14)
                else:
                    transport=mapping.current_to_previous_linear
                    omega_old=2*np.pi*previous.frequencies_hz[:3]
                    omega_new=2*np.pi*current.frequencies_hz[:3]
                    for mode in range(3):
                        vector=np.stack([new[mode][0],new[mode][1]])
                        transported=np.einsum('ij,jnm->inm',transport,vector)*omega_new[mode]
                        expected=np.stack([old[mode][0],old[mode][1]])*omega_old[mode]
                        scale=max(np.max(np.abs(expected)),1e-300)
                        np.testing.assert_allclose(transported/scale,expected/scale,rtol=1e-11,atol=1e-13)
                    plain=_electric_grams(previous,current,overlay,5)
                    transported=_electric_grams(previous,current,overlay,5,
                                                current_to_previous_rotation=transport)
                    plain_overlap=np.abs(plain[1][0,0])/np.sqrt(plain[0][0,0]*plain[2][0,0])
                    fixed_overlap=np.abs(transported[1][0,0])/np.sqrt(transported[0][0,0]*transported[2][0,0])
                    self.assertLess(plain_overlap,fixed_overlap-1e-3)
                    self.assertAlmostEqual(fixed_overlap,1.,places=9)
                if pol=='tm':
                    grams=_electric_grams(previous,current,overlay,5)
                    np.testing.assert_allclose(grams[1],grams[0],rtol=1e-11,atol=1e-14)

    def test_reflection_frequencies_and_real_fem_correspondence(self):
        width,height=.31,.20
        mapping=PolygonAffineRemeshMapping(circle_reflection(.6).tolist(),(0.,0.))
        for pol in ('te','tm'):
            previous=solve_planar(PlanarPolygonCase(rectangle(16,12,width,height),pol,2,7))
            current=solve_planar(PlanarPolygonCase(mapping.transform_mesh(rectangle(16,12,width,height,True)),pol,2,7))
            np.testing.assert_allclose(current.frequencies_hz,previous.frequencies_hz,rtol=1e-12)
            result=track_planar_modes(previous,current,
                PlanarTrackingRequest(4,4,[f'mode-{i}' for i in range(4)],mapping=mapping))
            self.assertEqual(result['result_version'],6)
            self.assertEqual(result['status'],'PASS')
            self.assertTrue(result['individual_ids_complete'])
            self.assertEqual(result['current_mode_ids'],[f'mode-{i}' for i in range(4)])
            mapping_document=result['physical_mapping']
            self.assertEqual(mapping_document['name'],'polygon_affine_remesh')
            self.assertEqual(mapping_document['declaration'],mapping.to_dict())
            np.testing.assert_allclose(mapping_document['current_to_previous_linear'],
                                       mapping.current_to_previous_linear)
            self.assertEqual(mapping_document['orientation'],'reversed; polygon order and triangle vertex order normalized to positive orientation')
            self.assertAlmostEqual(mapping_document['signed_determinant'],-1.,places=12)

    def test_anisotropic_rectangle_frequency_law_and_tracking(self):
        width,height=.31,.20
        stretch=PolygonAffineRemeshMapping([[1.3,0.],[0.,.8]],(.02,-.01))
        for pol in ('te','tm'):
            previous=solve_planar(PlanarPolygonCase(rectangle(16,12,width,height),pol,2,7))
            current=solve_planar(PlanarPolygonCase(
                stretch.transform_mesh(rectangle(16,12,width,height,True)),pol,2,7))
            analytic_old=self._analytic_frequencies(pol,width,height)
            analytic_new=self._analytic_frequencies(pol,width*1.3,height*.8)
            for frequencies,reference in ((previous.frequencies_hz,analytic_old),
                                          (current.frequencies_hz,analytic_new)):
                errors=[min(abs(value/exact-1.) for exact in reference) for value in frequencies[:5]]
                self.assertLess(max(errors),5e-4)
                self.assertEqual(len({int(np.argmin([abs(value/exact-1.) for exact in reference]))
                                      for value in frequencies[:5]}),5)
        previous=solve_planar(PlanarPolygonCase(rectangle(16,12,width,height),'te',2,7))
        current=solve_planar(PlanarPolygonCase(stretch.transform_mesh(rectangle(16,12,width,height,True)),'te',2,7))
        result=track_planar_modes(previous,current,
            PlanarTrackingRequest(4,4,[f'mode-{i}' for i in range(4)],mapping=stretch))
        self.assertEqual(result['status'],'PASS')
        self.assertTrue(result['individual_ids_complete'])
        self.assertNotEqual([match['current_indices'] for match in result['matches']],[[1],[2],[3],[4]])

    @staticmethod
    def _analytic_frequencies(pol,width,height):
        values=[]
        for m in range(0,6):
            for n in range(0,6):
                if pol=='te' and (m,n)==(0,0):continue
                if pol=='tm' and (m==0 or n==0):continue
                values.append(C0/2*np.sqrt((m/width)**2+(n/height)**2))
        return sorted(values)

    def test_degenerate_subspaces_and_guard_are_preserved(self):
        mapping=PolygonAffineRemeshMapping([[-1.,0.],[0.,1.]],(1.2,0.))
        for pol,count in (('te',2),('tm',3)):
            case=PlanarPolygonCase(square(6),pol,2,count+1)
            previous=solve_planar(case)
            current=solve_planar(replace(case,mesh=mapping.transform_mesh(square(6,True))))
            ids=[f'mode-{i}' for i in range(count)]
            result=track_planar_modes(previous,current,
                PlanarTrackingRequest(count,count,ids,mapping=mapping))
            self.assertEqual(result['status'],'PASS')
            cut=track_planar_modes(previous,current,
                PlanarTrackingRequest(count-1,count-1,ids[:-1],mapping=mapping))
            self.assertEqual(cut['status'],'UNVERIFIED')
            self.assertTrue(any(cut['guard_overlap']))
        case=PlanarPolygonCase(square(6),'te',2,3)
        previous=solve_planar(case)
        current=solve_planar(replace(case,mesh=mapping.transform_mesh(square(6,True))))
        result=track_planar_modes(previous,current,
            PlanarTrackingRequest(2,2,['mode-1','mode-2'],mapping=mapping))
        self.assertEqual(result['status'],'PASS')
        self.assertTrue(any(match['dimension']==2 and match['kind']=='SUBSPACE'
                            for match in result['matches']))

    def test_saved_worker_and_composed_affine_history_chain(self):
        base=square(6)
        first=PolygonAffineRemeshMapping([[1.,.3],[0.,1.]],(.02,-.01))
        second=PolygonAffineRemeshMapping([[-1.1,0.],[0.,.9]],(.35,.05))
        case=PlanarPolygonCase(base,'tm',2,2)
        a=solve_planar(case)
        b=solve_planar(replace(case,mesh=first.transform_mesh(square(6,True))))
        c=solve_planar(replace(case,mesh=second.transform_mesh(first.transform_mesh(square(6)))))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,solution in [('a',a),('b',b),('c',c)]:
                save_planar_run(solution.case,solution,root/name)
            for name,left,right,mapping in [('ab','a','b',first),('bc','b','c',second)]:
                execute_planar_tracking(root/left,root/right,
                    PlanarTrackingRequest(1,1,['fundamental'],mapping=mapping),root/name)
                self.assertEqual(read_planar_tracking(root/name)['status'],'PASS')
            result=execute_planar_history([root/'ab',root/'bc'],
                                          PlanarTrackingHistoryRequest(2),root/'history')
            self.assertEqual(result['status'],'PASS')
            self.assertEqual(result['current_mode_ids'],['fundamental'])
            self.assertTrue(result['can_extend'])
            self.assertEqual(result['steps'][0]['request']['tracking_version'],6)
            self.assertEqual(result['steps'][1]['request']['mapping'],second.to_dict())
            self.assertEqual(read_planar_history(root/'history'),result)
            target=root/'ab'/'tracking.json'
            data=json.loads(target.read_text())
            data['mapping']['linear_xy'][0][1]+=1.
            target.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                read_planar_tracking(root/'ab')


if __name__=='__main__':
    unittest.main()
