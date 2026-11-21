# SPDX-License-Identifier: Apache-2.0
"""Independent geometry/area-form invariants; no analytic eigenvalue injection."""
import copy
import json
import math
import unittest
import numpy as np
from scipy.integrate import quad
from scipy.linalg import eigh
from superfish_ng.planar_curved import PlanarCurvedDomain, PlanarCurvedCase
from superfish_ng.planar_curved_geometry import PlanarQuadraticTriangle
from superfish_ng.planar_curved_fem import mapped_planar_element_matrices, planar_curved_matrices
from superfish_ng.planar import planar_mesh_matrices
from superfish_ng.planar_mesh import PlanarMesh
from superfish_ng.project import parse_json

REFERENCE = np.array([[0, 0], [1, 0], [0, 1], [.5, 0], [.5, .5], [0, .5]], dtype=float)


def quadratic_nodes(vertices, triangles, cycle):
    vertices, triangles = np.array(vertices, dtype=float), np.array(triangles, dtype=int)
    edges = sorted({tuple(sorted((int(cell[i]), int(cell[j])))) for cell in triangles for i, j in ((0, 1), (1, 2), (2, 0))})
    lookup = {edge: len(vertices)+i for i, edge in enumerate(edges)}
    points = np.vstack([vertices, [vertices[list(edge)].mean(axis=0) for edge in edges]])
    cells = np.column_stack([triangles, [[lookup[tuple(sorted((int(cell[i]), int(cell[j]))))] for i, j in ((0, 1), (1, 2), (2, 0))] for cell in triangles]])
    boundary = np.array([[a, b, lookup[tuple(sorted((a, b)))]] for a, b in zip(cycle, cycle[1:]+cycle[:1])])
    return points, cells, boundary


def patch(length=.02, shift=(0., 0.)):
    x, y = REFERENCE.T
    return PlanarCurvedDomain(length*np.column_stack([x, y+.2*x*(1-x-y)])+shift,
                             [[0, 1, 2, 3, 4, 5]], [[0, 1, 3], [1, 2, 4], [2, 0, 5]])


def curved_ellipse(count, axes=(.02, .012), shift=(-.03, .01)):
    theta = 2*np.pi*np.arange(count)/count
    rotation = np.array([[np.cos(np.pi/7), -np.sin(np.pi/7)], [np.sin(np.pi/7), np.cos(np.pi/7)]])
    outer = (np.column_stack([np.cos(theta), np.sin(theta)])*axes)@rotation.T+shift
    points, cells, boundary = quadratic_nodes(np.vstack([shift, outer]),
        [[0, i+1, (i+1) % count+1] for i in range(count)], list(range(1, count+1)))
    for i, (_, _, mid) in enumerate(boundary):
        angle = 2*np.pi*(i+.5)/count
        points[mid] = (np.array([np.cos(angle), np.sin(angle)])*axes)@rotation.T+shift
    return PlanarCurvedDomain(points, cells, boundary)


class PlanarCurvedGeometryTests(unittest.TestCase):
    def test_curved_patch_area_moments_gradients_and_actual_boundary_length(self):
        for length in (.01, .02):
            for shift in ((0., 0.), (-.03, .01)):
                with self.subTest(length=length, shift=shift):
                    domain = patch(length, shift)
                    mapping = domain.elements[0]
                    k, m = mapped_planar_element_matrices(mapping, quadrature_order=12)
                    area = length**2*(.5-.2/6)
                    one = np.ones(6)
                    x, y = (domain.points_xy_m-np.array(shift)).T
                    self.assertLess(abs(domain.area_m2/area-1), 1e-12)
                    self.assertLess(abs(one@m@one/area-1), 1e-12)
                    self.assertLess(abs(x@m@one/(length**3*(1/6-.2/12))-1), 1e-12)
                    self.assertLess(abs(y@m@one/(length**3*(1/6-.2**2/60))-1), 1e-12)
                    self.assertLess(np.linalg.norm(k@one)/np.linalg.norm(k), 1e-12)
                    np.testing.assert_allclose([[x@k@x, x@k@y], [y@k@x, y@k@y]], np.eye(2)*area, rtol=1e-12, atol=area*1e-12)
                    ref = np.array([[.2, .3], [0., 0.], [.5, 0.], [0., 1.]])
                    evaluated = mapping.evaluate(ref)
                    expected = length*np.column_stack([ref[:, 0], ref[:, 1]+.2*ref[:, 0]*(1-ref.sum(axis=1))])+shift
                    np.testing.assert_allclose(evaluated['points_xy_m'], expected, rtol=0, atol=1e-16)
                    for coefficient, gradient in ((x, [1., 0.]), (y, [0., 1.]), (one, [0., 0.])):
                        actual = np.einsum('qia,i->qa', evaluated['basis_gradients'], coefficient)
                        np.testing.assert_allclose(actual, np.tile(gradient, (len(ref), 1)), rtol=1e-12, atol=1e-12)
                    curved_arc = length*(math.sqrt(1+.2**2)/2+math.asinh(.2)/(2*.2))
                    perimeter = curved_arc+length*(1+math.sqrt(2))
                    self.assertLess(abs(domain.boundary_length_m()/perimeter-1), 1e-12)
                    edge = domain.boundary_evaluate(0, [0., .5, 1.])
                    np.testing.assert_allclose(edge['points_xy_m'], domain.points_xy_m[[0, 3, 1]], rtol=0, atol=1e-16)
                    np.testing.assert_allclose(np.linalg.norm(edge['outward_normal_xy'], axis=1), 1, atol=1e-14)
                    np.testing.assert_allclose(np.sum(edge['outward_normal_xy']*edge['tangent_xy'], axis=1), 0, atol=1e-14)
                    self.assertTrue(np.all(edge['outward_normal_xy'][:, 1] < 0))

    def test_whole_jacobian_rejects_internal_zero_despite_positive_samples(self):
        # Internal zero, and a stationary zero on each of the three edges.
        for center in ((.25, .25), (.5, 0.), (0., .5), (.5, .5)):
            x, y = (REFERENCE-np.array(center)).T
            nodes = np.column_stack([x*x-y*y, 2*x*y])
            self.assertTrue(np.all(4*np.sum((REFERENCE[:3]-center)**2, axis=1) > 0))
            with self.subTest(center=center), self.assertRaisesRegex(ValueError, 'whole reference triangle'):
                PlanarQuadraticTriangle(nodes)
        # A perturbation leaves all vertex determinants positive but makes
        # the internal minimum exactly -delta^2/4, at (.25-delta/4,.25).
        x, y = REFERENCE.T-.25
        delta = .125
        nodes = np.column_stack([x*x-y*y, 2*x*y+delta*REFERENCE[:, 1]])
        vertex_x, vertex_y = (REFERENCE[:3]-.25).T
        self.assertTrue(np.all(4*(vertex_x**2+vertex_y**2)+2*delta*vertex_x > 0))
        with self.assertRaisesRegex(ValueError, 'whole reference triangle'):
            PlanarQuadraticTriangle(nodes)
        flat = REFERENCE*np.array([1., 1e-14])
        with self.assertRaisesRegex(ValueError, 'Jacobian'):
            PlanarQuadraticTriangle(flat)
        with self.assertRaisesRegex(ValueError, 'resolution'):
            PlanarQuadraticTriangle(REFERENCE+[1e12, 1e12])
        for length in (1e-160, 1e155):
            with self.assertRaisesRegex(ValueError, 'scale'):
                PlanarQuadraticTriangle(REFERENCE*length)

    def test_all_edge_intersections_not_just_boundary_area_or_local_jacobians(self):
        # Twice-winding seven-point star: every straight fan cell has det>0,
        # disk topology and matching Green area; the global map still overlaps.
        theta = 4*np.pi*np.arange(7)/7
        vertices = np.vstack([[0., 0.], np.column_stack([np.cos(theta), np.sin(theta)])])
        points, cells, boundary = quadratic_nodes(vertices, [[0, i+1, (i+1) % 7+1] for i in range(7)], list(range(1, 8)))
        for cell in cells:
            self.assertGreater(PlanarQuadraticTriangle(points[cell]).determinant_lower_bound_m2, 0)
        with self.assertRaisesRegex(ValueError, 'intersection|contact|UNVERIFIED'):
            PlanarCurvedDomain(points, cells, boundary)

    def test_curved_ellipse_independent_area_and_line_integral(self):
        errors = []
        for count in (16, 32, 64):
            domain = curved_ellipse(count)
            a, b = .02, .012
            half_angle = np.pi/count
            exact_p2_area = count*a*b*np.sin(half_angle)*(4-np.cos(half_angle))/3
            self.assertLess(abs(domain.area_m2/exact_p2_area-1), 1e-12)
            # Independent analytic edge-coordinate derivative; do not call the
            # product evaluator, Green helper or its quadrature rule.
            perimeter = 0.
            for i in range(count):
                angles = 2*np.pi*np.array([i, i+1, i+.5])/count
                nodes = np.column_stack([a*np.cos(angles), b*np.sin(angles)])
                p, q, mid = nodes
                def speed(t):
                    return float(np.linalg.norm((4*t-1)*(q-p)+(4-8*t)*(mid-p)))
                perimeter += quad(speed, 0, 1, epsabs=1e-14, epsrel=1e-12)[0]
            self.assertLess(abs(domain.boundary_length_m()/perimeter-1), 1e-12)
            true_perimeter = 4*quad(lambda theta: math.hypot(a*math.sin(theta), b*math.cos(theta)), 0, np.pi/2, epsabs=1e-14)[0]
            errors.append((abs(domain.area_m2/(np.pi*a*b)-1), abs(perimeter/true_perimeter-1)))
        self.assertTrue(np.all(np.array(errors[1:]) < np.array(errors[:-1])))
        self.assertLess(max(errors[-1]), 1e-4)

    def test_strict_domain_topology_array_types_and_total_budget(self):
        base = patch().to_dict()
        invalid = []
        for key, value in [('domain_version', True), ('format', 'axisymmetric'), ('hole_count', 1)]:
            data = copy.deepcopy(base); data[key] = value; invalid.append(data)
        for value in (True, '0', float('nan'), float('inf')):
            data = copy.deepcopy(base); data['points_xy_m'][0][0] = value; invalid.append(data)
        for value in (True, 1., -1, 100, 2**70):
            data = copy.deepcopy(base); data['cell_nodes'][0][0] = value; invalid.append(data)
        data = copy.deepcopy(base); data['points_xy_m'].append([.3, .4]); invalid.append(data)
        data = copy.deepcopy(base); data['points_xy_m'][3] = data['points_xy_m'][0]; invalid.append(data)
        data = copy.deepcopy(base); data['cell_nodes'].append(data['cell_nodes'][0]); invalid.append(data)
        data = copy.deepcopy(base); data['boundary_nodes'] = data['boundary_nodes'][::-1]; invalid.append(data)
        data = copy.deepcopy(base); data['boundary_nodes'][0][2] = 4; invalid.append(data)
        data = copy.deepcopy(base); data['boundary_nodes'][0][0:2] = data['boundary_nodes'][0][1::-1]; invalid.append(data)
        for data in invalid:
            with self.subTest(data=data), self.assertRaises(ValueError):
                PlanarCurvedDomain.from_dict(data)
        with self.assertRaisesRegex(ValueError, 'exhausted after 1 checks'):
            PlanarCurvedDomain.from_dict(base, max_geometry_boxes=1)
        domain = PlanarCurvedDomain.from_dict(base, max_geometry_boxes=6)
        self.assertEqual(domain.geometry_diagnostics['boxes_checked'], 6)
        self.assertEqual(domain.to_dict(), base)
        for array in (domain.points_xy_m, domain.cell_nodes, domain.boundary_nodes, domain.boundary_cells):
            with self.assertRaises(ValueError):
                array.setflags(write=True)
        for reference in ([[.2, -.001]], [[.7, .4]], [[True, 0]], []):
            with self.assertRaises(ValueError):
                domain.elements[0].evaluate(reference)
        with self.assertRaises(ValueError):
            domain.boundary_evaluate(0, [-.01])
        with self.assertRaises(ValueError):
            domain.boundary_evaluate(True, [.5])
        for parameters in (None, [], [[.5]], [True], [float('inf')]):
            with self.assertRaises(ValueError):
                domain.boundary_evaluate(0, parameters)

    def test_shared_midpoint_orientation_disconnected_and_hole_rejected(self):
        points, cells, boundary = quadratic_nodes([[0, 0], [1, 0], [1, 1], [0, 1]], [[0, 1, 2], [0, 2, 3]], [0, 1, 2, 3])
        changed = cells.copy(); changed[1, 3] = changed[1, 4]
        with self.assertRaises(ValueError):
            PlanarCurvedDomain(points, changed, boundary)
        changed = cells.copy(); changed[1, 3] = len(points)
        with self.assertRaisesRegex(ValueError, 'nonconforming shared edge'):
            PlanarCurvedDomain(np.vstack([points, [.5, .6]]), changed, boundary)
        changed = cells.copy(); changed[1] = cells[1, [0, 2, 1, 5, 4, 3]]
        with self.assertRaisesRegex(ValueError, 'orientations must oppose'):
            PlanarCurvedDomain(points, changed, boundary)
        changed = np.vstack([cells, cells[0]])
        with self.assertRaisesRegex(ValueError, 'repeats a cell'):
            PlanarCurvedDomain(points, changed, boundary)
        d = patch()
        p = np.vstack([d.points_xy_m, d.points_xy_m+[.1, .1]])
        c = np.vstack([d.cell_nodes, d.cell_nodes+6])
        b = np.vstack([d.boundary_nodes, d.boundary_nodes+6])
        with self.assertRaisesRegex(ValueError, 'Euler|connected'):
            PlanarCurvedDomain(p, c, b)
        vertices = [[-2,-2],[2,-2],[2,2],[-2,2],[-1,-1],[1,-1],[1,1],[-1,1]]
        triangles = [[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]]
        p, c, b = quadratic_nodes(vertices, triangles, [0,1,2,3])
        with self.assertRaisesRegex(ValueError, 'holes are unsupported'):
            PlanarCurvedDomain(p, c, b)


class PlanarCurvedFormTests(unittest.TestCase):
    def test_straight_rectangle_and_reentrant_L_limit_K_M_and_constraints(self):
        fixtures = [([[0,0],[1,0],[1,1],[0,1]], [[0,1,2],[0,2,3]], [0,1,2,3], 1., 4.),
                    ([[-1,-1],[1,-1],[1,0],[0,0],[0,1],[-1,1]], [[0,1,3],[1,2,3],[0,3,5],[3,4,5]], [0,1,2,3,4,5], 3., 8.)]
        for vertices, triangles, cycle, area, perimeter in fixtures:
            for length in (.01, .02):
                p = np.array(vertices)*length+[-.03, -.02]
                mesh = PlanarMesh.create(p[cycle], p, triangles)
                points, cells, boundary = quadratic_nodes(p, triangles, cycle)
                domain = PlanarCurvedDomain(points, cells, boundary)
                self.assertLess(abs(domain.area_m2/(area*length**2)-1), 1e-12)
                self.assertLess(abs(domain.boundary_length_m()/(perimeter*length)-1), 1e-12)
                for polarization in ('te', 'tm'):
                    with self.subTest(vertices=vertices, length=length, polarization=polarization):
                        old, expected_k, expected_m, expected_free = planar_mesh_matrices(mesh, 2, polarization)
                        space, k, m, free = planar_curved_matrices(PlanarCurvedCase(domain, polarization, modes=1))
                        np.testing.assert_array_equal(space.points_xy_m, old.dof_points_xy_m)
                        for actual, expected in ((k, expected_k), (m, expected_m)):
                            self.assertLess(np.linalg.norm((actual-expected).toarray())/np.linalg.norm(expected.toarray()), 1e-12)
                        np.testing.assert_array_equal(free, expected_free)
                        eigenvalues = eigh(k[free][:, free].toarray(), m[free][:, free].toarray(), eigvals_only=True)
                        if polarization == 'te':
                            self.assertLess(abs(eigenvalues[0]/eigenvalues[-1]), 1e-12)
                            self.assertGreater(eigenvalues[1]/eigenvalues[-1], 1e-5)
                            self.assertLess(np.linalg.norm(k@np.ones(len(free)))/np.linalg.norm(k.toarray()), 1e-12)
                        else:
                            self.assertGreater(eigenvalues[0], 0)

    def test_curved_matrices_scale_rotation_translation_and_quadrature(self):
        domain = curved_ellipse(16)
        _, k, m, free = planar_curved_matrices(PlanarCurvedCase(domain, modes=3))
        angle = .43
        rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
        changed = PlanarCurvedDomain(2*domain.points_xy_m@rotation.T+[.2,-.3], domain.cell_nodes, domain.boundary_nodes)
        _, kk, mm, ff = planar_curved_matrices(PlanarCurvedCase(changed, modes=3))
        np.testing.assert_array_equal(free, ff)
        self.assertLess(np.linalg.norm((k-kk).toarray())/np.linalg.norm(k.toarray()), 1e-12)
        self.assertLess(np.linalg.norm((m-mm/4).toarray())/np.linalg.norm(m.toarray()), 1e-12)
        _, fine_k, fine_m, _ = planar_curved_matrices(PlanarCurvedCase(domain, modes=3, quadrature_order=12))
        self.assertLess(np.linalg.norm((k-fine_k).toarray())/np.linalg.norm(fine_k.toarray()), 1e-10)
        self.assertLess(np.linalg.norm((m-fine_m).toarray())/np.linalg.norm(fine_m.toarray()), 1e-12)

    def test_strict_case_roundtrip_and_unsupported_physics_before_assembly(self):
        case = PlanarCurvedCase(patch(), modes=1)
        base = case.to_dict()
        self.assertEqual(PlanarCurvedCase.from_dict(parse_json(json.dumps(base))), case)
        changes = [('model','coordinates','cylindrical'),('model','material','dielectric'),
            ('model','boundary','open'),('model','propagation_constant_per_m',.1),
            ('model','propagation_constant_per_m',True),('model','polarization','tem'),
            ('model','symmetry','magnetic'),('mesh','element_order',1),('mesh','element_order',True),
            ('geometry','type','circle'),('geometry','hole_count',1),('numerics','quadrature_order',True),
            ('numerics','quadrature_order',3),('numerics','wall_quadrature_order',33),
            ('numerics','max_geometry_boxes',0),('numerics','max_geometry_boxes',100000001),
            ('rf','stored_energy_j_per_m',0),('rf','conductivity_s_per_m',float('inf'))]
        for section, key, value in changes:
            data = copy.deepcopy(base); data[section][key] = value
            with self.subTest(section=section, key=key, value=value), self.assertRaises(ValueError):
                PlanarCurvedCase.from_dict(data)
        with self.assertRaisesRegex(ValueError, 'Duplicate|duplicate'):
            parse_json(json.dumps(base).replace('"modes": 1', '"modes": 1, "modes": 2'))
        for invalid in (True, 0, 3, 33, 4.5):
            with self.assertRaises(ValueError):
                mapped_planar_element_matrices(case.domain.elements[0], quadrature_order=invalid)
        with self.assertRaisesRegex(ValueError, 'positive FEM degrees'):
            planar_curved_matrices(PlanarCurvedCase(patch(), 'tm', modes=1))
        with self.assertRaisesRegex(ValueError, 'positive FEM degrees'):
            planar_curved_matrices(PlanarCurvedCase(patch(), modes=6))


if __name__ == '__main__':
    unittest.main()
