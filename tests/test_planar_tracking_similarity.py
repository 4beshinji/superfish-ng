# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng.planar_mesh import PlanarMesh
from superfish_ng.planar_polygon import PlanarPolygonCase
from superfish_ng.planar_refinement import refine_planar_mesh
from superfish_ng.planar_tracking_similarity import PolygonSimilarityMapping,polygon_similarity_overlay
from superfish_ng.planar_tracking import PlanarTrackingRequest,track_planar_modes
from superfish_ng.planar_tracking_fields import _electric_grams
from superfish_ng.planar import solve_planar,planar_quantities
from superfish_ng.planar_saved import save_planar_run
from superfish_ng.planar_tracking_jobs import execute_planar_tracking,read_planar_tracking
from superfish_ng.planar_tracking_history import PlanarTrackingHistoryRequest
from superfish_ng.planar_tracking_history_saved import read_planar_history
from superfish_ng.jobs import JobManager


def triangle(levels=0):
    points=np.array([[0.,0.],[.2,0.],[.2,.2]])
    mesh=PlanarMesh.create(points,points,[[0,1,2]])
    for _ in range(levels):mesh=refine_planar_mesh(mesh)
    return mesh


class PlanarSimilarityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mapping=PolygonSimilarityMapping(2.,np.pi/2,(.13,-.08))
        mesh=triangle(3);cls.pairs={}
        for pol in ('te','tm'):
            for order in (1,2):
                case=PlanarPolygonCase(mesh,pol,order,3)
                cls.pairs[pol,order]=(solve_planar(case),solve_planar(replace(case,mesh=cls.mapping.transform_mesh(mesh),normalization_j_per_m=3.)))

    def test_strict_mapping_and_version_roundtrip(self):
        doc=self.mapping.to_dict();self.assertEqual(PolygonSimilarityMapping.from_dict(doc).to_dict(),doc)
        for change in ({'scale':True},{'scale':-1},{'rotation_radians':float('nan')},{'translation_xy_m':[0,float('inf')]},{'translation_xy_m':(0,0)},{'inverse':1},{'shear':0},{'previous_refinements':1,'current_refinements':1},{'current_refinements':9}):
            with self.assertRaises(ValueError):PolygonSimilarityMapping.from_dict({**doc,**change})
        request=PlanarTrackingRequest(1,1,['fundamental'],mapping=self.mapping).to_dict();self.assertEqual(request['tracking_version'],3)
        self.assertEqual(PlanarTrackingRequest.from_dict(request).to_dict(),request)
        for version in (1,2,True,4):
            with self.assertRaises(ValueError):PlanarTrackingRequest.from_dict({**request,'tracking_version':version})
        old=PlanarTrackingRequest().to_dict();self.assertEqual(PlanarTrackingRequest.from_dict(old).to_dict(),old)

    def test_nested_original_coordinates_and_area_in_both_directions(self):
        mesh=triangle(1)
        for scale in (.37,2.):
            for angle in (np.pi/2,.371):
                for level in (0,1,2):
                    mapping=PolygonSimilarityMapping(scale,angle,(.13,-.08),current_refinements=level);current=mapping.transform_mesh(mesh)
                    for _ in range(level):current=refine_planar_mesh(current)
                    for a,b,m in ((mesh,current,mapping),(current,mesh,replace(mapping,inverse=True,previous_refinements=level,current_refinements=0))):
                        part=polygon_similarity_overlay(a,b,m)
                        self.assertAlmostEqual(sum(part.reference_determinants)/(2*a.area_m2),1.,places=13)
                        bary=np.array([.2,.3,.5]);points=[]
                        for geometry,cells,vertices in ((a,part.previous_cells,part.previous_vertex_barycentric),(b,part.current_cells,part.current_vertex_barycentric)):
                            local=np.einsum('j,njk->nk',bary,vertices);points.append(np.einsum('ni,nij->nj',local,geometry.points_xy_m[geometry.triangles[cells]]))
                        expected=(points[0]-m.translation_xy_m)@m.rotation/m.scale if m.inverse else m.scale*(points[0]@m.rotation.T)+m.translation_xy_m
                        np.testing.assert_allclose(points[1],expected,rtol=1e-13,atol=1e-14)
                        self.assertFalse(part.reference_vertices.flags.writeable)

    def test_wrong_domain_and_large_origin_are_rejected(self):
        mesh=triangle();current=self.mapping.transform_mesh(mesh);points=current.points_xy_m.copy();points[1,0]+=.0001
        with self.assertRaisesRegex(ValueError,'coordinates'):polygon_similarity_overlay(mesh,PlanarMesh.create(points,points,current.triangles),self.mapping)
        with self.assertRaisesRegex(ValueError,'max_overlay'):polygon_similarity_overlay(mesh,current,self.mapping,max_overlay_triangles=0)
        with self.assertRaisesRegex(ValueError,'count'):polygon_similarity_overlay(mesh,current,replace(self.mapping,current_refinements=1))
        points=np.array([[1e6,1e6],[1e6+.01,1e6],[1e6+.01,1e6+.01]]);a=PlanarMesh.create(points,points,[[0,1,2]]);changed=points.copy();changed[1:,0]+=8*np.spacing(1e6);b=PlanarMesh.create(changed,changed,[[0,1,2]])
        with self.assertRaisesRegex(ValueError,'local mesh precision'):polygon_similarity_overlay(a,b,PolygonSimilarityMapping(1.,0.,(0.,0.)))

    def test_vector_rotation_frequency_and_rf_similarity(self):
        for (pol,order),(a,b) in self.pairs.items():
            np.testing.assert_allclose(b.frequencies_hz,a.frequencies_hz/2,rtol=1e-11)
            part=polygon_similarity_overlay(a.case.mesh,b.case.mesh,self.mapping)
            plain=_electric_grams(a,b,part,5);rotated=_electric_grams(a,b,part,5,current_to_previous_rotation=self.mapping.current_to_previous_rotation)
            normalizer=np.sqrt(rotated[0][0,0]*rotated[2][0,0]);self.assertAlmostEqual(abs(rotated[1][0,0])/normalizer,1.,places=11)
            if pol=='te':self.assertLess(abs(plain[1][0,0])/normalizer,1e-11)
            qa,qb=planar_quantities(a),planar_quantities(b)
            self.assertAlmostEqual(qb['geometry_factor_ohm']/qa['geometry_factor_ohm'],1.,places=10)
            self.assertAlmostEqual(qb['q0']/qa['q0'],np.sqrt(2),places=10)
            self.assertAlmostEqual(qb['wall_loss_w_per_m']/qa['wall_loss_w_per_m'],3/2**1.5,places=10)

    def test_complete_correspondence_and_rotation_invariant_resolution(self):
        for a,b in self.pairs.values():
            for previous,current,mapping in ((a,b,self.mapping),(b,a,replace(self.mapping,inverse=True))):
                result=track_planar_modes(previous,current,PlanarTrackingRequest(1,1,['fundamental'],mapping=mapping))
                self.assertEqual(result['status'],'PASS');self.assertEqual(result['result_version'],3);self.assertEqual(result['current_mode_ids'],['fundamental'])
                x,y=result['spectral_resolution'];self.assertEqual(x['shift_geometry'],'inverse_polygon_area')
                np.testing.assert_allclose(x['relative_inverse_residual'],y['relative_inverse_residual'],rtol=1e-7,atol=1e-11)

    def test_saved_worker_and_history_preserve_forward_inverse_declarations(self):
        a,b=self.pairs['te',2]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);save_planar_run(a.case,a,root/'previous');save_planar_run(b.case,b,root/'current')
            request=PlanarTrackingRequest(1,1,['fundamental'],mapping=self.mapping)
            result=execute_planar_tracking(root/'previous',root/'current',request,root/'forward');self.assertEqual(result,read_planar_tracking(root/'forward'))
            execute_planar_tracking(root/'current',root/'previous',replace(request,mapping=replace(self.mapping,inverse=True)),root/'reverse')
            manager=JobManager(root/'workspace')
            try:
                identifier=manager.start_planar_history([root/'forward',root/'reverse'],PlanarTrackingHistoryRequest(2))
                self.assertEqual(manager.processes[identifier].wait(timeout=120),0)
                history=read_planar_history(manager.directory(identifier));self.assertTrue(history['can_extend']);self.assertEqual(history['current_mode_ids'],['fundamental'])
            finally:manager.close()

    def test_degenerate_electric_subspaces_and_guard_are_preserved(self):
        points=np.array([[0.,0.],[.2,0.],[.2,.2],[0.,.2]])
        mesh=PlanarMesh.create(points,points,[[0,1,2],[0,2,3]])
        for _ in range(3):mesh=refine_planar_mesh(mesh)
        mapping=PolygonSimilarityMapping(.37,.371,(.13,-.08))
        for pol,count in (('te',2),('tm',3)):
            case=PlanarPolygonCase(mesh,pol,2,4);a=solve_planar(case);b=solve_planar(replace(case,mesh=mapping.transform_mesh(mesh)))
            ids=[f'mode-{i}' for i in range(count)]
            result=track_planar_modes(a,b,PlanarTrackingRequest(count,count,ids,mapping=mapping))
            self.assertEqual(result['status'],'PASS');self.assertFalse(result['individual_ids_complete'])
            self.assertTrue(any(match['dimension']==2 and match['kind']=='SUBSPACE' for match in result['matches']))
            cut=track_planar_modes(a,b,PlanarTrackingRequest(count-1,count-1,ids[:-1],mapping=mapping))
            self.assertEqual(cut['status'],'UNVERIFIED');self.assertTrue(any(cut['guard_overlap']))

    def test_scalar_and_matrix_arithmetic_are_verified_without_widening_tolerance(self):
        # Separate multiplies/adds used in browser-produced JSON can differ
        # from a BLAS matrix product by one coordinate ulp.
        mesh=triangle(3);mapping=PolygonSimilarityMapping(.37,.371,(.13,-.08),current_refinements=1)
        c,sine=np.cos(.371),np.sin(.371)
        def points(values):
            x,y=values.T
            return np.column_stack((.37*(c*x-sine*y)+.13,.37*(sine*x+c*y)-.08))
        transformed=PlanarMesh.create(points(mesh.polygon_xy_m),points(mesh.points_xy_m),mesh.triangles)
        matrix=mapping.transform_mesh(mesh)
        self.assertFalse(np.array_equal(matrix.points_xy_m,transformed.points_xy_m))
        for current in (refine_planar_mesh(transformed),PlanarMesh.create(points(refine_planar_mesh(mesh).polygon_xy_m),points(refine_planar_mesh(mesh).points_xy_m),refine_planar_mesh(mesh).triangles)):
            forward=polygon_similarity_overlay(mesh,current,mapping)
            backward=polygon_similarity_overlay(current,mesh,replace(mapping,inverse=True,previous_refinements=1,current_refinements=0))
            self.assertAlmostEqual(sum(forward.reference_determinants)/(2*mesh.area_m2),1.,places=13)
            self.assertAlmostEqual(sum(backward.reference_determinants)/(2*current.area_m2),1.,places=13)

    def test_composed_transform_history_retains_native_chain_and_physical_laws(self):
        from superfish_ng.planar_tracking_history_saved import execute_planar_history
        a=self.pairs['te',2][0]
        first=PolygonSimilarityMapping(.37,.371,(.13,-.08))
        second=PolygonSimilarityMapping(1.7,-.217,(-.02,.11))
        b=solve_planar(replace(a.case,mesh=first.transform_mesh(a.case.mesh),normalization_j_per_m=2.))
        c=solve_planar(replace(b.case,mesh=second.transform_mesh(b.case.mesh),normalization_j_per_m=3.))
        np.testing.assert_allclose(c.frequencies_hz,a.frequencies_hz/(first.scale*second.scale),rtol=1e-10)
        # Original barycentric coordinates compose without replacing either FEM field.
        part=polygon_similarity_overlay(a.case.mesh,a.case.mesh,PolygonSimilarityMapping(1.,0.,(0.,0.)))
        rotation=(second.rotation@first.rotation).T
        aa,ab,bb=_electric_grams(a,c,part,5,current_to_previous_rotation=rotation)
        np.testing.assert_allclose(abs(np.diag(ab))/np.sqrt(np.diag(aa)*np.diag(bb)),1.,rtol=1e-10)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,solution in [('a',a),('b',b),('c',c)]:save_planar_run(solution.case,solution,root/name)
            for name,left,right,mapping in [('ab','a','b',first),('bc','b','c',second)]:
                execute_planar_tracking(root/left,root/right,PlanarTrackingRequest(1,1,['fundamental'],mapping=mapping),root/name)
            result=execute_planar_history([root/'ab',root/'bc'],PlanarTrackingHistoryRequest(2),root/'history')
            self.assertEqual(result['status'],'PASS');self.assertEqual(result['current_mode_ids'],['fundamental'])
            self.assertEqual(result['steps'][0]['request']['mapping'],first.to_dict())
            self.assertEqual(result['steps'][1]['request']['mapping'],second.to_dict())
