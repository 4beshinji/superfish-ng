# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import unittest
import numpy as np
from superfish_ng.axis_hphi import AxisHphiCase, solve_axis_hphi
from superfish_ng.constants import C0
from scripts.validate_coaxial import radial_roots
from superfish_ng.coaxial import CoaxialCase, solve_coaxial, coaxial_quantities
from superfish_ng.hphi_mesh import HphiMeshCase, solve_hphi_mesh, hphi_mesh_quantities
from superfish_ng.hphi_geometry_mapping import HphiGeometryMapping, coaxial_dimension_mapping
from superfish_ng.hphi_field_overlap import _declared_mesh
from superfish_ng.hphi_tracking import HphiTrackingRequest, track_mapped_hphi_modes
from superfish_ng.hphi_tuning import _refine_mesh
from test_meridional_overlap import fixture
from test_hphi_geometry_mapping import transformed
from test_hphi_mapped_overlap import renumber


class HphiMappedTrackingTests(unittest.TestCase):
    def test_coaxial_dimensions_original_spectrum_rf_reverse_and_guard(self):
        a = solve_coaxial(CoaxialCase(.0625,.125,.5,nr=2,nz=8,modes=3,quadrature_order=12))
        b = solve_coaxial(CoaxialCase(.078125,.15625,.75,nr=3,nz=8,modes=3,quadrature_order=12))
        mapping = coaxial_dimension_mapping(a.case,b.case)
        q = HphiTrackingRequest(_refine_mesh(_declared_mesh(a)),_refine_mesh(_declared_mesh(b)))
        before = [(s.coefficients.copy(),s.frequencies_hz.copy(),[coaxial_quantities(s,i) for i in range(3)]) for s in (a,b)]
        report = track_mapped_hphi_modes(a,b,q,mapping)
        self.assertEqual(report['status'],'PASS',report['verification_reasons'])
        self.assertEqual(report['current_mode_ids'],['mode-1','mode-2'])
        self.assertEqual(report['physical_mapping']['previous_frequency_scale'],1.)
        self.assertEqual(report['request']['mapping'],mapping.to_dict())
        inverse = track_mapped_hphi_modes(b,a,replace(q,previous_comparison_mesh=q.current_comparison_mesh,
            current_comparison_mesh=q.previous_comparison_mesh),mapping.inverse())
        self.assertEqual(inverse['status'],'PASS',inverse['verification_reasons'])
        self.assertEqual(inverse['current_mode_ids'],['mode-1','mode-2'])
        failed = track_mapped_hphi_modes(a,b,replace(q,controls=replace(q.controls,relative_cluster_gap=.9)),mapping)
        self.assertEqual(failed['status'],'UNVERIFIED')
        self.assertTrue(any(failed['guard_overlap']))
        self.assertEqual(failed['current_mode_ids'],[None,None])
        for s,(coefficients,frequencies,rf) in zip((a,b),before):
            np.testing.assert_array_equal(s.coefficients,coefficients)
            np.testing.assert_array_equal(s.frequencies_hz,frequencies)
            self.assertEqual([coaxial_quantities(s,i) for i in range(3)],rf)
        with self.assertRaises(ValueError):track_mapped_hphi_modes(a,b,q,None)

    def test_piecewise_hole_motion_with_independent_numbering_and_id_set(self):
        control = fixture(1)
        def move(p):
            result = p.copy()
            result[:,0] += np.interp(p[:,0],np.arange(1,5)/32,[0,1/2048,1/2048,0])
            return result
        mapping = HphiGeometryMapping(control,transformed(control,move))
        a = solve_hphi_mesh(HphiMeshCase(fixture(2),modes=3,quadrature_order=12))
        b = solve_hphi_mesh(HphiMeshCase(renumber(transformed(fixture(2,opposite=True),move)),modes=3,quadrature_order=12))
        q = HphiTrackingRequest(_refine_mesh(a.case.mesh),_refine_mesh(b.case.mesh))
        before = [hphi_mesh_quantities(b,i) for i in range(3)]
        report = track_mapped_hphi_modes(a,b,q,mapping)
        self.assertEqual(report['status'],'PASS',report['verification_reasons'])
        self.assertEqual(report['current_mode_ids'],['mode-1','mode-2'])
        grouped = track_mapped_hphi_modes(a,b,replace(q,previous_mode_ids=None,
            previous_identity_groups=[dict(indices=[1,2],ids=['a','b'])]),mapping)
        self.assertEqual(grouped['status'],'PASS',grouped['verification_reasons'])
        self.assertFalse(grouped['individual_ids_complete'])
        self.assertEqual(grouped['current_mode_ids'],[None,None])
        self.assertEqual(grouped['matches'][0]['previous_ids'],['a','b'])
        self.assertEqual([hphi_mesh_quantities(b,i) for i in range(3)],before)
        inverse = track_mapped_hphi_modes(b,a,
            replace(q,previous_comparison_mesh=q.current_comparison_mesh,
                    current_comparison_mesh=q.previous_comparison_mesh),mapping.inverse())
        self.assertEqual(inverse['status'],'PASS',inverse['verification_reasons'])
        self.assertEqual(inverse['current_mode_ids'],['mode-1','mode-2'])
        # Same physical cavity, independent diagonals, boundary segmentation
        # and vertex/cell numbering: identity must survive representation.
        same = solve_hphi_mesh(HphiMeshCase(renumber(fixture(2,opposite=True)),
                                           modes=3,quadrature_order=12))
        identical_geometry = HphiGeometryMapping(control,control)
        equivalent = track_mapped_hphi_modes(a,same,
            HphiTrackingRequest(_refine_mesh(a.case.mesh),_refine_mesh(same.case.mesh)),
            identical_geometry)
        self.assertEqual(equivalent['status'],'PASS',equivalent['verification_reasons'])
        self.assertEqual(equivalent['current_mode_ids'],['mode-1','mode-2'])

    def test_axis_connected_nonuniform_map_tracks_original_regular_fields(self):
        control = fixture(1,axis=True)
        def move(p):
            result = p.copy()
            result[:,0] += np.interp(p[:,0],np.arange(4)/32,[0,1/2048,1/2048,0])
            return result
        mapping = HphiGeometryMapping(control,transformed(control,move))
        a = solve_axis_hphi(AxisHphiCase(fixture(2,axis=True),modes=3))
        b = solve_axis_hphi(AxisHphiCase(transformed(fixture(2,axis=True,opposite=True),move),modes=3))
        request = HphiTrackingRequest(_refine_mesh(a.case.mesh),_refine_mesh(b.case.mesh))
        result = track_mapped_hphi_modes(a,b,request,mapping)
        self.assertEqual(result['status'],'PASS',result['verification_reasons'])
        self.assertEqual(result['current_mode_ids'],['mode-1','mode-2'])

    def test_analytic_coaxial_degeneracy_preserves_only_an_id_set(self):
        solutions = []
        for a,b in ((.0625,.125),(.078125,.1640625)):
            kr = radial_roots(a,b,1)[0]
            length = np.pi/kr
            solution = solve_coaxial(CoaxialCase(a,b,length,nr=8,nz=8,modes=3,quadrature_order=12))
            np.testing.assert_allclose(solution.frequencies_hz[:2],C0*kr/(2*np.pi),rtol=1e-4)
            solutions.append(solution)
        a,b = solutions
        request = HphiTrackingRequest(_refine_mesh(_declared_mesh(a)),_refine_mesh(_declared_mesh(b)))
        report = track_mapped_hphi_modes(a,b,request,coaxial_dimension_mapping(a.case,b.case))
        self.assertEqual(report['status'],'PASS',report['verification_reasons'])
        self.assertFalse(report['individual_ids_complete'])
        self.assertEqual(report['current_mode_ids'],[None,None])
        self.assertEqual(report['matches'][0]['kind'],'SUBSPACE')
        self.assertEqual(report['matches'][0]['previous_ids'],['mode-1','mode-2'])
