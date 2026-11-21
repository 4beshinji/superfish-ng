# SPDX-License-Identifier: Apache-2.0
import unittest
from dataclasses import replace
import numpy as np
from scripts.hphi_mesh_reference import rectangular_holes
from superfish_ng.axis_connected_mesh import AxisConnectedMesh
from superfish_ng.coaxial import CoaxialCase
from superfish_ng.hphi_field_overlap import _scaled_mesh
from superfish_ng.hphi_geometry_mapping import HphiGeometryMapping, coaxial_dimension_mapping
from superfish_ng.meridional_mesh import MeridionalMesh


def transformed(mesh, function):
    data = mesh.to_dict()
    for key in ('outer_rz_m', 'points_rz_m'):
        data[key] = function(np.asarray(data[key])).tolist()
    data['holes_rz_m'] = [function(np.asarray(h)).tolist() for h in data['holes_rz_m']]
    return type(mesh).from_dict(data)


def integrated_measures(mapping):
    # Independent degree-one triangle rule, evaluated through the map.
    mesh = mapping.previous
    v = mesh.points_rz_m[mesh.triangles]
    area = ((v[:, 1, 0]-v[:, 0, 0])*(v[:, 2, 1]-v[:, 0, 1])
            -(v[:, 2, 0]-v[:, 0, 0])*(v[:, 1, 1]-v[:, 0, 1]))/2
    bary = np.tile([1/3]*3, (len(v), 1))
    radius = mapping.map_in_cells(list(range(len(v))), bary)[:, 0]
    weight = area*np.linalg.det(mapping.jacobians)
    return weight.sum(), np.dot(weight, 2*np.pi*radius)


class HphiGeometryMappingTests(unittest.TestCase):
    def test_coaxial_dimensions_independent_area_volume_and_inverse(self):
        a = CoaxialCase(.125, .25, .5)
        b = CoaxialCase(.25, .625, .75, nr=4, nz=6)
        mapping = coaxial_dimension_mapping(a, b)
        area, volume = integrated_measures(mapping)
        self.assertAlmostEqual(area, (.625-.25)*.75)
        self.assertAlmostEqual(volume, np.pi*(.625**2-.25**2)*.75)
        np.testing.assert_allclose(mapping.jacobians, np.tile(np.diag([3., 1.5]), (2, 1, 1)))
        np.testing.assert_allclose(mapping.inverse().jacobians @ mapping.jacobians, np.tile(np.eye(2), (2, 1, 1)), rtol=0, atol=4*np.finfo(float).eps)
        np.testing.assert_allclose(mapping.map_in_cells([0], [[.25, .25, .5]]), [[.53125, .375]])

    def test_uniform_scale_matches_h02_mesh_and_measure_laws(self):
        a = CoaxialCase(.125, .25, .5)
        b = replace(a, inner_radius_m=.25, outer_radius_m=.5, length_m=1.)
        mapping = coaxial_dimension_mapping(a, b)
        self.assertEqual(mapping.current.to_dict(), _scaled_mesh(mapping.previous, 2.).to_dict())
        for cls in (MeridionalMesh, AxisConnectedMesh):
            data = rectangular_holes(2, 2)
            # Dyadic grid avoids introducing undeclared rounded boundary bends.
            def dyadic(p):
                return np.column_stack((np.round((p[:, 0]-.025)/.0075)/64 + (0 if cls is AxisConnectedMesh else .125), np.round(p[:, 1]/.03)/32))
            data = {**data, 'outer_rz_m': dyadic(np.asarray(data['outer_rz_m'])),
                    'holes_rz_m': [dyadic(np.asarray(h)) for h in data['holes_rz_m']], 'points_rz_m': dyadic(data['points_rz_m'])}
            mesh = cls(**data)
            mapping = HphiGeometryMapping(mesh, _scaled_mesh(mesh, 2.))
            area, volume = integrated_measures(mapping)
            self.assertAlmostEqual(area, mesh.area_m2*4)
            self.assertAlmostEqual(volume, mesh.volume_m3*8)
            if cls is AxisConnectedMesh:
                np.testing.assert_array_equal(mapping.transport_axis_coordinates([0., .0625, .1875]), [0., .125, .375])
                with self.assertRaises(ValueError): mapping.transport_axis_coordinates([-.1])

    def test_nonuniform_piecewise_axis_and_hole_preserved(self):
        p = np.array([[0,0],[4,0],[4,4],[0,4],[1,1],[1,3],[3,3],[3,1]], dtype=float)/16
        cells = [[0,1,7],[0,7,4],[1,2,6],[1,6,7],[2,3,5],[2,5,6],[3,0,4],[3,4,5]]
        a = AxisConnectedMesh(p[:4], [p[4:]], p, cells)
        q = p.copy(); q[4:, 0] += 1/32
        b = AxisConnectedMesh(q[:4], [q[4:]], q, cells)
        mapping = HphiGeometryMapping(a, b)
        area, volume = integrated_measures(mapping)
        self.assertAlmostEqual(area, .25**2-.125**2)
        self.assertAlmostEqual(volume, np.pi*.25**2*.25 - np.pi*((.1875+1/32)**2-(.0625+1/32)**2)*.125)
        self.assertGreater(np.ptp(np.linalg.det(mapping.jacobians)), 0)
        np.testing.assert_array_equal(mapping.transport_axis_coordinates([0., .125, .25]), [0., .125, .25])
        with self.assertRaises(ValueError): transformed(a, lambda x: x+[1/32, 0])
        for change in ('hole', 'inverted', 'uncovered'):
            data = a.to_dict()
            if change == 'hole': data['holes_rz_m'] = []
            elif change == 'inverted': data['triangles'][0].reverse()
            else: data['triangles'].pop()
            with self.assertRaises(ValueError):
                HphiGeometryMapping(a, AxisConnectedMesh.from_dict(data))

    def test_rejects_implicit_correspondence_and_invalid_samples(self):
        mapping = coaxial_dimension_mapping(CoaxialCase(.125,.25,.5), CoaxialCase(.25,.5,1.))
        data = mapping.current.to_dict(); data['triangles'].reverse()
        with self.assertRaisesRegex(ValueError, 'triangles'):
            HphiGeometryMapping(mapping.previous, MeridionalMesh.from_dict(data))
        for cells, bary in (([True], [[1,0,0]]), ([-1], [[1,0,0]]), ([0], [[2,-1,0]]), ([0], [[0,0,0]]), ([0], [[True,0,0]])):
            with self.assertRaises(ValueError): mapping.map_in_cells(cells, bary)
        with self.assertRaises(ValueError): mapping.transport_axis_coordinates([0.])
        with self.assertRaises(ValueError): coaxial_dimension_mapping({}, {})
