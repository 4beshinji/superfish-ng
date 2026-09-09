# SPDX-License-Identifier: Apache-2.0
"""Independent geometry and polynomial pullback invariants for polygon tracking."""
import unittest
import numpy as np
from superfish_ng.planar_mesh import PlanarMesh
from superfish_ng.planar_refinement import refine_planar_mesh
from superfish_ng.planar_tracking_polygon import PolygonScaleMapping, polygon_scale_overlay
from superfish_ng.fem import triangle_quadrature


def mesh():
    points = np.array([[0., 0.], [2., 0.], [2., 1.], [1., 1.], [1., 2.], [0., 2.]])*.13 + [-.2, .1]
    return PlanarMesh.create(points, points, [[0, 1, 3], [1, 2, 3], [0, 3, 5], [3, 4, 5]])


def scaled(m, scale):
    return PlanarMesh.create(m.polygon_xy_m*scale, m.points_xy_m*scale, m.triangles)


class PolygonTrackingGeometryTests(unittest.TestCase):
    def test_scale_refinement_geometry_area_and_quadratic_pullback(self):
        for scale in (.37, 1., 2.):
            for reverse in (False, True):
                for levels in (0, 1, 2):
                    original = mesh(); finer = original
                    for _ in range(levels):
                        finer = refine_planar_mesh(finer)
                    previous, current = (finer, scaled(original, scale)) if reverse else (original, scaled(finer, scale))
                    mapping = PolygonScaleMapping(scale, levels if reverse else 0, 0 if reverse else levels)
                    overlay = polygon_scale_overlay(previous, current, mapping)
                    self.assertAlmostEqual(overlay.reference_determinants.sum()/2, previous.area_m2, places=14)
                    self.assertFalse(overlay.reference_vertices.flags.writeable)
                    for quadrature, _ in triangle_quadrature(5):
                        coords = []
                        for m, cells, bary, factor in ((previous, overlay.previous_cells, overlay.previous_vertex_barycentric, 1.), (current, overlay.current_cells, overlay.current_vertex_barycentric, scale)):
                            parent_bary = np.einsum('j,njk->nk', quadrature, bary)
                            vertices = m.points_xy_m[m.triangles[cells]]/factor
                            points = np.einsum('ni,nij->nj', parent_bary, vertices)
                            coords.append(points)
                            # Reproduce a quadratic with original P2 nodal values, not display interpolation.
                            nodes = np.concatenate((vertices, (vertices[:, [0,1,2]]+vertices[:, [1,2,0]])/2), axis=1)
                            x, y = nodes[:,:,0], nodes[:,:,1]; values = 1+2*x-3*y+x*x+4*x*y-2*y*y
                            l = parent_bary; basis = np.column_stack((l*(2*l-1), 4*l[:,0]*l[:,1], 4*l[:,1]*l[:,2], 4*l[:,2]*l[:,0]))
                            x,y = points.T
                            np.testing.assert_allclose(np.sum(basis*values,axis=1),1+2*x-3*y+x*x+4*x*y-2*y*y,rtol=2e-14,atol=2e-14)
                        np.testing.assert_allclose(coords[0],coords[1],rtol=2e-14,atol=2e-14)

    def test_same_connectivity_is_not_same_geometry(self):
        previous = mesh(); current = scaled(previous, 2.)
        points=current.points_xy_m.copy(); points[:,0]*=1.01
        wrong=PlanarMesh.create(points,points,current.triangles)
        with self.assertRaisesRegex(ValueError,'coordinates'):
            polygon_scale_overlay(previous,wrong,PolygonScaleMapping(2.))
        shifted=PlanarMesh.create(current.polygon_xy_m+[.001,0],current.points_xy_m+[.001,0],current.triangles)
        with self.assertRaisesRegex(ValueError,'coordinates'):
            polygon_scale_overlay(previous,shifted,PolygonScaleMapping(2.))
        renumbered=PlanarMesh.create(current.polygon_xy_m,current.points_xy_m,current.triangles[::-1])
        with self.assertRaisesRegex(ValueError,'numbering'):
            polygon_scale_overlay(previous,renumbered,PolygonScaleMapping(2.))

    def test_large_origin_offset_cannot_hide_area_change(self):
        points=np.array([[0.,0.],[.01,0.],[.01,.01]])+1e6
        previous=PlanarMesh.create(points,points,[[0,1,2]])
        changed=points.copy();changed[1:,0]+=8*np.spacing(1e6)
        current=PlanarMesh.create(changed,changed,[[0,1,2]])
        self.assertGreater(abs(current.area_m2/previous.area_m2-1),1e-8)
        with self.assertRaisesRegex(ValueError,'local mesh precision'):
            polygon_scale_overlay(previous,current,PolygonScaleMapping(1.))
        identity=polygon_scale_overlay(previous,previous,PolygonScaleMapping(1.))
        self.assertAlmostEqual(identity.reference_determinants.sum()/(2*previous.area_m2),1.,places=14)

    def test_scale_before_or_after_refinement_has_same_declared_domain(self):
        points=np.array([[0.,0.],[.2,0.],[.2,.1],[.1,.1],[.1,.2],[0.,.2]])
        base=PlanarMesh.create(points,points,[[0,1,3],[1,2,3],[0,3,5],[3,4,5]])
        for _ in range(3):base=refine_planar_mesh(base)
        first=refine_planar_mesh(scaled(base,.37))
        second=scaled(refine_planar_mesh(base),.37)
        self.assertFalse(np.array_equal(first.points_xy_m,second.points_xy_m))
        for current in (first,second):
            forward=polygon_scale_overlay(base,current,PolygonScaleMapping(.37,current_refinements=1))
            reverse=polygon_scale_overlay(current,base,PolygonScaleMapping(1/.37,previous_refinements=1))
            self.assertAlmostEqual(forward.reference_determinants.sum()/(2*base.area_m2),1.,places=13)
            self.assertAlmostEqual(reverse.reference_determinants.sum()/(2*current.area_m2),1.,places=13)

    def test_strict_declaration_and_budget(self):
        for scale in (True, 0, -1, float('nan'), float('inf'), '2'):
            with self.assertRaises(ValueError):PolygonScaleMapping(scale)
        for count in (True,-1,1.5,9):
            with self.assertRaises(ValueError):PolygonScaleMapping(2.,current_refinements=count)
        with self.assertRaises(ValueError):PolygonScaleMapping(2.,1,1)
        doc=PolygonScaleMapping(2.,current_refinements=2).to_dict()
        self.assertEqual(doc,PolygonScaleMapping.from_dict(doc).to_dict())
        with self.assertRaises(ValueError):PolygonScaleMapping.from_dict({**doc,'translation':[0,0]})
        with self.assertRaisesRegex(ValueError,'count'):
            polygon_scale_overlay(mesh(),scaled(mesh(),2.),PolygonScaleMapping(2.,current_refinements=1))
        with self.assertRaisesRegex(ValueError,'max_overlay'):
            polygon_scale_overlay(mesh(),scaled(mesh(),2.),PolygonScaleMapping(2.),max_overlay_triangles=3)
