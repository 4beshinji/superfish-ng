# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from test_meridional_overlap import fixture
from test_hphi_geometry_mapping import transformed
from superfish_ng.coaxial import CoaxialCase
from superfish_ng.hphi_geometry_mapping import HphiGeometryMapping, coaxial_dimension_mapping
from superfish_ng.hphi_mapped_overlap import mapped_hphi_overlay
from superfish_ng.meridional_mesh import MeridionalMesh
from superfish_ng.fem import triangle_quadrature


def moment(mesh, rp, zp):
    rectangles = [(mesh.outer_rz_m, 1), *((h, -1) for h in mesh.holes_rz_m)]
    return sum(sign*(p[:, 0].max()**(rp+1)-p[:, 0].min()**(rp+1))/(rp+1)
               *(p[:, 1].max()**(zp+1)-p[:, 1].min()**(zp+1))/(zp+1) for p, sign in rectangles)


def integrate(overlay, rp, zp, previous=False):
    vertices = overlay.previous_vertices_rz_m if previous else overlay.vertices_rz_m
    det = overlay.previous_determinants if previous else overlay.determinants
    total = 0.
    for bary, weight in triangle_quadrature(5):
        points = np.einsum('i,tij->tj', bary, vertices)
        total += np.dot(weight*det, points[:, 0]**rp*points[:, 1]**zp)
    return total


def renumber(mesh):
    data = mesh.to_dict()
    p = np.random.default_rng(8).permutation(len(mesh.points_rz_m))
    data['points_rz_m'] = mesh.points_rz_m[p].tolist()
    data['triangles'] = np.argsort(p)[mesh.triangles[::-1]][:, [1, 2, 0]].tolist()
    outer = mesh.outer_rz_m
    # Declare an existing boundary vertex, rather than inventing a midpoint
    # which need not be a node after a nonuniform map.
    subdivided = []
    for index, corner in enumerate(outer):
        subdivided.append(corner.tolist())
        nodes = mesh.boundary_edges[mesh.boundary_segments == index].ravel()
        choices = [mesh.points_rz_m[n] for n in nodes
                   if not np.array_equal(mesh.points_rz_m[n], corner)
                   and not np.array_equal(mesh.points_rz_m[n], outer[(index+1) % len(outer)])]
        if choices:
            subdivided.append(choices[0].tolist())
    data['outer_rz_m'] = subdivided
    data['holes_rz_m'] = data['holes_rz_m'][::-1]
    return type(mesh).from_dict(data)


class HphiMappedOverlayTests(unittest.TestCase):
    def assert_moments_and_parents(self, previous, current, overlay):
        for old, mesh in ((True, previous), (False, current)):
            for rp, zp in ((0, 0), (1, 0), (3, 0), (1, 2), (3, 2)):
                self.assertAlmostEqual(integrate(overlay, rp, zp, old)/moment(mesh, rp, zp), 1., delta=2e-13)
            cells = overlay.previous_cells if old else overlay.current_cells
            bary = overlay.previous_vertex_barycentric if old else overlay.current_vertex_barycentric
            expected = overlay.previous_vertices_rz_m if old else overlay.vertices_rz_m
            actual = np.einsum('tij,tjk->tik', bary, mesh.points_rz_m[mesh.triangles[cells]])
            np.testing.assert_allclose(actual, expected, rtol=0, atol=3e-16)
            self.assertEqual(set(cells), set(range(len(mesh.triangles))))
        self.assertFalse(overlay.previous_determinants.flags.writeable)
        self.assertFalse(overlay.vertices_rz_m.flags.writeable)

    def test_piecewise_hole_shift_independent_meshes_and_inverse(self):
        for axis in (False, True):
            control = fixture(1, axis=axis)
            start = 0 if axis else 1/32
            def move(points):
                result = points.copy()
                result[:, 0] += np.interp(points[:, 0], start+np.arange(4)/32, [0, 1/128, 1/128, 0])
                return result
            mapping = HphiGeometryMapping(control, transformed(control, move))
            previous = fixture(2, axis=axis, opposite=True)
            current = renumber(transformed(fixture(2, axis=axis), move))
            overlay = mapped_hphi_overlay(previous, current, mapping)
            self.assert_moments_and_parents(previous, current, overlay)
            inverse = mapped_hphi_overlay(current, previous, mapping.inverse())
            self.assert_moments_and_parents(current, previous, inverse)
            ratios = overlay.determinants/overlay.previous_determinants
            np.testing.assert_allclose(ratios, np.linalg.det(mapping.jacobians)[overlay.mapping_cells], rtol=2e-14)
            self.assertGreater(np.ptp(ratios), .4)

    def test_two_holes_scaling_with_independent_boundary_and_numbering(self):
        control = fixture(1, holes=2)
        mapping = HphiGeometryMapping(control, transformed(control, lambda p: 2*p))
        previous = fixture(2, holes=2, opposite=True)
        current = renumber(transformed(fixture(1, holes=2), lambda p: 2*p))
        overlay = mapped_hphi_overlay(previous, current, mapping)
        self.assert_moments_and_parents(previous, current, overlay)
        np.testing.assert_allclose(overlay.vertices_rz_m, 2*overlay.previous_vertices_rz_m, rtol=0, atol=0)
        np.testing.assert_allclose(overlay.determinants, 4*overlay.previous_determinants, rtol=0, atol=0)
        self.assertAlmostEqual(integrate(overlay, 1, 0)/integrate(overlay, 1, 0, True), 8.)

    def test_non_dyadic_exact_mapping_and_affine_scalar_integral(self):
        mapping = coaxial_dimension_mapping(CoaxialCase(.025,.1,.18), CoaxialCase(.04,.13,.21))
        def crossed(mesh, weight):
            p = mesh.points_rz_m
            center = p[0]+weight*(p[2]-p[0])
            return MeridionalMesh(p, [], np.vstack((p, center)), [[0,1,4],[1,2,4],[2,3,4],[3,0,4]])
        previous = crossed(mapping.previous, .37)
        current = crossed(mapping.current, .61)
        overlay = mapped_hphi_overlay(previous, current, mapping)
        self.assert_moments_and_parents(previous, current, overlay)
        # Integrate the product r_old * z_new over the new physical volume.
        a,b,l = .025,.1,.18
        c,d,h = .04,.13,.21
        radial_scale = (d-c)/(b-a)
        expected = 2*np.pi*h*h/2*(a*(d*d-c*c)/2 + ((d**3-c**3)/3-c*(d*d-c*c)/2)/radial_scale)
        actual = 0.
        for bary, weight in triangle_quadrature(5):
            old = np.einsum('i,tij->tj', bary, overlay.previous_vertices_rz_m)
            new = np.einsum('i,tij->tj', bary, overlay.vertices_rz_m)
            actual += np.dot(weight*overlay.determinants, 2*np.pi*new[:,0]*old[:,0]*new[:,1])
        self.assertAlmostEqual(actual/expected, 1., delta=2e-13)

    def test_domain_type_and_limits_rejected(self):
        a,b = fixture(1),fixture(2)
        mapping = HphiGeometryMapping(a,a)
        for args in ((a,fixture(1,holes=0),mapping), (fixture(1,axis=True),b,mapping), (a,b,None)):
            with self.assertRaises(ValueError): mapped_hphi_overlay(*args)
        for kwargs in ({'max_candidate_tests':True}, {'max_candidate_tests':2}, {'max_overlay_triangles':1},
                       {'max_overlay_triangles':len(b.triangles)}):
            # Opposite diagonals split existing cells further than either input.
            with self.assertRaises(ValueError): mapped_hphi_overlay(fixture(2,opposite=True),b,mapping,**kwargs)
