# SPDX-License-Identifier: Apache-2.0
"""H08 coaxial-dimension and straight general affine mapping contract."""
from types import SimpleNamespace
import unittest
import numpy as np
from scripts.hphi_mesh_reference import rectangular_holes
from superfish_ng.axis_connected_mesh import AxisConnectedMesh
from superfish_ng.axis_hphi import AxisAccelerationPath
from superfish_ng.coaxial import CoaxialCase, _space
from superfish_ng.constants import TAU
from superfish_ng.hphi_field_overlap import _declared_mesh, _scaled_mesh
from superfish_ng.hphi_geometry_mapping import (
    HphiGeometryMapping,
    coaxial_dimension_mapping,
    hphi_geometry_overlay,
    map_axis_acceleration,
    map_axis_interval,
    map_mesh,
)
from superfish_ng.meridional_mesh import MeridionalMesh
import test_axis_connected_mesh as geometry_tests


def coaxial_mesh(a=.025, b=.05, length=.18, nr=3, nz=8):
    case = CoaxialCase(a, b, length, nr=nr, nz=nz, modes=3)
    return _declared_mesh(SimpleNamespace(case=case, space=_space(case)))


def integrals(mesh):
    """Independent area and rotation volume from the original triangles."""
    vertices = mesh.points_rz_m[mesh.triangles]
    determinants = np.abs(np.linalg.det(vertices[:, 1:]-vertices[:, :1]))/2
    area = float(determinants.sum())
    volume = float(TAU*np.sum(determinants*vertices[:, :, 0].mean(axis=1)))
    return area, volume


class HphiGeometryMappingTests(unittest.TestCase):
    def test_coaxial_dimension_analytic_and_independent_integrals(self):
        previous = coaxial_mesh()
        target = (.03, .09, .3)
        mapping = coaxial_dimension_mapping(.025, .05, .18, *target)
        mapped = map_mesh(previous, mapping)
        inner, outer, length = target
        self.assertAlmostEqual(mapped.area_m2, (outer-inner)*length, places=14)
        self.assertAlmostEqual(mapped.volume_m3, np.pi*(outer**2-inner**2)*length, places=13)
        area, volume = integrals(mapped)
        self.assertAlmostEqual(area, mapped.area_m2, places=13)
        self.assertAlmostEqual(volume, mapped.volume_m3, places=12)
        # Rotation volume scales non-similarly: annular second moment, not s**3.
        self.assertAlmostEqual(mapped.volume_m3/previous.volume_m3,
            ((outer**2-inner**2)*length)/((.05**2-.025**2)*.18), places=13)
        np.testing.assert_allclose(mapped.outer_rz_m,
            np.array([[inner, 0.], [outer, 0.], [outer, length], [inner, length]]), rtol=0, atol=1e-15)
        self.assertGreater(mapping.signed_determinant, 0.)

    def test_uniform_scale_matches_h02_path_and_overlay(self):
        previous = coaxial_mesh()
        for scale in (1., 2., .5):
            mapping = HphiGeometryMapping(((scale, 0.), (0., scale)))
            mapped = map_mesh(previous, mapping)
            reference = _scaled_mesh(previous, scale)
            np.testing.assert_array_equal(mapped.points_rz_m, reference.points_rz_m)
            np.testing.assert_array_equal(mapped.outer_rz_m, reference.outer_rz_m)
            overlay = hphi_geometry_overlay(previous, reference, mapping)
            self.assertAlmostEqual(overlay.determinants.sum()/2, reference.area_m2, places=13)
            self.assertEqual(mapping.signed_determinant, scale**2)

    def test_inverse_declaration_round_trips_exactly(self):
        previous = coaxial_mesh(nr=2, nz=4)
        linear, translation = ((2., 0.), (0., 3.)), (.01, -.02)
        forward = HphiGeometryMapping(linear, translation)
        mapped = map_mesh(previous, forward)
        backward = HphiGeometryMapping(linear, translation, inverse=True)
        restored = map_mesh(mapped, backward)
        np.testing.assert_allclose(restored.points_rz_m, previous.points_rz_m, rtol=1e-14, atol=1e-16)
        self.assertEqual(backward.effective_exact()[0]*forward.effective_exact()[0], 1)

    def test_hole_disappearance_and_uncovered_domain_rejected(self):
        data = rectangular_holes(2, 1)
        previous = MeridionalMesh(**data)
        with self.assertRaisesRegex(ValueError, 'r > 0'):
            map_mesh(previous, HphiGeometryMapping(((1., 0.), (0., 1.)), (-.03, 0.)))
        mapping = HphiGeometryMapping(((2., 0.), (0., 3.)))
        mapped = map_mesh(previous, mapping)
        with self.assertRaisesRegex(ValueError, 'same exact vacuum'):
            hphi_geometry_overlay(previous, mapped, HphiGeometryMapping(((2., 0.), (0., 2.5))))
        shifted = map_mesh(mapped, HphiGeometryMapping(((1., 0.), (0., 1.)), (2.**-40, 0.)))
        with self.assertRaises(ValueError):
            hphi_geometry_overlay(previous, shifted, mapping)
        for args in ((.025, .05, .18, .10, .09, .3), (.025, .05, .18, 0., .09, .3),
                     (.025, .05, .18, .03, .09, 0.)):
            with self.assertRaises(ValueError):
                coaxial_dimension_mapping(*args)

    def test_inversion_degeneracy_and_axis_movement_rejected(self):
        for linear in (((-1., 0.), (0., 1.)), ((1., 0.), (0., 0.)), ((1., 1.), (1., 1.))):
            with self.assertRaises(ValueError):
                HphiGeometryMapping(linear)
        for bad in (True, 'x', float('nan')):
            with self.assertRaises(ValueError):
                HphiGeometryMapping(((1., 0.), (bad, 1.)))
        with self.assertRaises(ValueError):
            HphiGeometryMapping(((1., 0.), (0., 1.)), (0., 0.), inverse='no')
        mesh = AxisConnectedMesh(**geometry_tests.AxisConnectedMeshTests().data(0))
        for linear, translation in ((((1., 0.), (0., 1.)), (.01, 0.)),
                                    (((1., .5), (0., 1.)), (0., 0.)),
                                    (((1., 0.), (0., 1.)), (0., 2.**-60))):
            with self.assertRaisesRegex(ValueError, 'axis'):
                map_mesh(mesh, HphiGeometryMapping(linear, translation))

    def test_axis_interval_and_acceleration_policy(self):
        mesh = AxisConnectedMesh(**geometry_tests.AxisConnectedMeshTests().data(0))
        mapping = HphiGeometryMapping(((2., 0.), (0., 1.5)), (0., 0.))
        mapped = map_mesh(mesh, mapping)
        interval = map_axis_interval(mapping, mesh.axis_interval_m)
        self.assertEqual(interval, (0., .27))
        self.assertEqual(mapped.axis_interval_m, interval)
        path = AxisAccelerationPath(0., .18, .6, .01)
        transformed = map_axis_acceleration(mapping, path)
        self.assertEqual(transformed.beta, .6)
        self.assertEqual((transformed.z_start_m, transformed.z_end_m, transformed.phase_origin_m), (0., .27, .015))
        shifted = HphiGeometryMapping(((1., 0.), (0., 1.)), (0., .1))
        with self.assertRaisesRegex(ValueError, 'axis interval'):
            map_axis_interval(shifted, mesh.axis_interval_m)
        with self.assertRaisesRegex(ValueError, 'axis'):
            map_axis_interval(HphiGeometryMapping(((1., .5), (0., 1.))), mesh.axis_interval_m)

    def test_strict_mapping_document_and_fields(self):
        mapping = HphiGeometryMapping(((1., 0.), (0., 2.)), (.001, .002))
        self.assertEqual(HphiGeometryMapping.from_dict(mapping.to_dict()), mapping)
        self.assertGreater(mapping.max_candidate_tests, 0)
        for change in ({'name': 'other'}, {'linear_rz': [[1., 0.]]}, {'linear_rz': 'x'},
                       {'translation_rz_m': [1.]}, {'inverse': 1}, {'max_candidate_tests': True},
                       {'max_candidate_tests': 0}, {'extra': 1}):
            with self.assertRaises(ValueError):
                HphiGeometryMapping.from_dict({**mapping.to_dict(), **change})
        with self.assertRaises(ValueError):
            map_mesh(coaxial_mesh(), object())
        with self.assertRaises(ValueError):
            hphi_geometry_overlay(coaxial_mesh(), coaxial_mesh(), mapping.to_dict())


if __name__ == '__main__':
    unittest.main()
