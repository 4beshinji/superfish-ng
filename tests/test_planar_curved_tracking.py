# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import unittest
import numpy as np
from superfish_ng.planar_curved import PlanarCurvedCase, PlanarCurvedDomain
from superfish_ng.planar_curved_solver import solve_planar_curved, restore_planar_curved_solution
from superfish_ng.planar_curved_comparison import PlanarCurvedComparisonDomain
from test_planar_curved import curved_ellipse


class PlanarCurvedTrackingTests(unittest.TestCase):
    def test_original_te_tm_scale_and_signed_fields_share_ids(self):
        from superfish_ng.planar_curved_tracking import PlanarCurvedTrackingRequest, track_planar_curved_modes
        for polarization in ('te', 'tm'):
            base = curved_ellipse(16)
            a = solve_planar_curved(PlanarCurvedCase(base, polarization, modes=3, quadrature_order=16))
            scaled = PlanarCurvedDomain(2*base.points_xy_m, base.cell_nodes, base.boundary_nodes)
            b = solve_planar_curved(replace(a.case, domain=scaled))
            phases = np.sign(np.sum(a.coefficients*b.coefficients, axis=0))
            b = restore_planar_curved_solution(b.case, -b.coefficients*phases, b.frequencies_hz)
            before = (a.coefficients.tobytes(), b.coefficients.tobytes(), a.frequencies_hz.tobytes(), b.frequencies_hz.tobytes())
            request = PlanarCurvedTrackingRequest(PlanarCurvedComparisonDomain(base, scaled, 'declared_quadratic'))
            result = track_planar_curved_modes(a, b, request)
            self.assertEqual(result['status'], 'PASS', result['verification_reasons'])
            self.assertEqual(result['current_mode_ids'], ['mode-1', 'mode-2'])
            self.assertEqual([m['previous_phase_multiplier'] for m in result['matches']], [-1,-1])
            np.testing.assert_allclose(b.frequencies_hz*2, a.frequencies_hz, rtol=1e-11)
            self.assertEqual(before, (a.coefficients.tobytes(), b.coefficients.tobytes(), a.frequencies_hz.tobytes(), b.frequencies_hz.tobytes()))

    def test_symmetric_doublet_preserves_set_but_not_individual_ids(self):
        from superfish_ng.planar_curved_tracking import PlanarCurvedTrackingRequest, track_planar_curved_modes
        from superfish_ng.planar_curved_solver import restore_planar_curved_solution
        base = curved_ellipse(16, axes=(.02,.02), shift=(0.,0.))
        a = solve_planar_curved(PlanarCurvedCase(base, 'te', modes=3, quadrature_order=16))
        self.assertLess(abs(a.frequencies_hz[1]/a.frequencies_hz[0]-1), 1e-10)
        angle = .37
        rotation = np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
        c = a.coefficients.copy();c[:,:2] = c[:,:2]@rotation
        b = restore_planar_curved_solution(a.case, c, a.frequencies_hz)
        request = PlanarCurvedTrackingRequest(PlanarCurvedComparisonDomain(base, base))
        result = track_planar_curved_modes(a, b, request)
        self.assertEqual(result['status'], 'PASS', result['verification_reasons'])
        self.assertFalse(result['individual_ids_complete'])
        self.assertEqual(result['current_mode_ids'], [None,None])
        self.assertEqual(result['matches'][0]['previous_ids'], ['mode-1','mode-2'])
        self.assertEqual(result['matches'][0]['dimension'], 2)
        self.assertIsNone(result['matches'][0]['previous_phase_multiplier'])
        np.testing.assert_allclose(result['matches'][0]['principal_overlaps'], [1.,1.], rtol=0, atol=1e-10)

    def test_guard_crossing_clears_all_individual_ids_and_matches(self):
        from superfish_ng.planar_curved_tracking import PlanarCurvedTrackingRequest, track_planar_curved_modes
        base = curved_ellipse(16)
        a = solve_planar_curved(PlanarCurvedCase(base, 'te', modes=3, quadrature_order=16))
        request = PlanarCurvedTrackingRequest(PlanarCurvedComparisonDomain(base, base))
        request = replace(request, controls=replace(request.controls, relative_cluster_gap=.9))
        result = track_planar_curved_modes(a, a, request)
        self.assertEqual(result['status'], 'UNVERIFIED')
        self.assertEqual(result['current_mode_ids'], [None,None])
        self.assertTrue(any(result['guard_overlap']))
        self.assertTrue(any('upper guard' in why for why in result['verification_reasons']))
        self.assertTrue(all(m['status']=='UNVERIFIED' for m in result['matches']))

    def test_strict_request_roundtrip_and_owned_charts(self):
        import tempfile
        from pathlib import Path
        from copy import deepcopy
        from superfish_ng.planar_curved_tracking import PlanarCurvedTrackingRequest
        base = curved_ellipse(8)
        charts = [dict(base_cell=i, reference_vertices=[[[0,1],[0,1]],[[1,1],[0,1]],[[0,1],[1,1]]]) for i in range(8)]
        request = PlanarCurvedTrackingRequest(PlanarCurvedComparisonDomain(base, base), previous_cells=charts)
        charts[0]['base_cell'] = 999
        self.assertEqual(request.previous_cells[0]['base_cell'], 0)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'request.json';request.save(p)
            self.assertEqual(request.to_dict(), PlanarCurvedTrackingRequest.load(p).to_dict())
            with self.assertRaises(FileExistsError):request.save(p)
        for name,value in (('tracking_version',True),('transport','radial'),('previous_mode_count',True),
                           ('previous_mode_ids',['a','a']),('previous_cells',[{'base_cell':True,'reference_vertices':[]}]),('extra',0)):
            raw = request.to_dict();raw[name] = value
            with self.assertRaises(ValueError):PlanarCurvedTrackingRequest.from_dict(raw)
        for name,value in (('quadrature_order',29),('max_field_sample_points',True),('minimum_overlap',0),('extra',0)):
            raw = request.to_dict();raw['controls'][name] = value
            with self.assertRaises(ValueError):PlanarCurvedTrackingRequest.from_dict(raw)
        raw = request.to_dict();restored = PlanarCurvedTrackingRequest.from_dict(raw)
        raw['previous_cells'][0]['base_cell'] = 999
        self.assertEqual(request.to_dict(), restored.to_dict())

    def test_missing_guard_native_corruption_and_explicit_budget_stop(self):
        from superfish_ng.planar_curved_tracking import PlanarCurvedTrackingRequest, track_planar_curved_modes
        from superfish_ng.planar_curved_comparison import PlanarCurvedComparisonBudgetExceeded
        base = curved_ellipse(8)
        a = solve_planar_curved(PlanarCurvedCase(base, 'te', modes=3, quadrature_order=16))
        request = PlanarCurvedTrackingRequest(PlanarCurvedComparisonDomain(base, base))
        with self.assertRaisesRegex(ValueError, 'upper guard'):
            track_planar_curved_modes(a,a,replace(request,previous_mode_count=3,previous_mode_ids=['a','b','c']))
        for controls in ({'max_field_sample_points':1},{'max_enrichment_sample_points_per_side':1},
                         {'max_refined_triangles_per_side':1},{'max_dofs_per_side':1},{'max_pair_tests_per_comparison':1}):
            with self.subTest(controls=controls), self.assertRaises(PlanarCurvedComparisonBudgetExceeded) as caught:
                track_planar_curved_modes(a,a,replace(request,controls=replace(request.controls,**controls)))
            self.assertEqual(caught.exception.status, 'UNVERIFIED')
        with self.assertRaises(ValueError):track_planar_curved_modes(a,replace(a,coefficients=a.coefficients*1.001),request)

    def test_actual_elliptical_rank_exchange_tracks_reflection_parity_and_all_rf(self):
        from superfish_ng.planar_curved_tracking import PlanarCurvedTrackingRequest, track_planar_curved_modes
        from superfish_ng.planar_curved_solver import planar_curved_quantities
        axes = ((.020,.019),(.019,.020))
        sources = [solve_planar_curved(PlanarCurvedCase(curved_ellipse(16,axes=pair,shift=(0.,0.)),
            'te',modes=3,quadrature_order=16)) for pair in axes]
        angle = np.pi/7
        rotation = np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
        parity = []
        for solution in sources:
            points = solution.case.domain.points_xy_m
            reflected = points@rotation@np.diag([-1.,1.])@rotation.T
            distance = np.linalg.norm(reflected[:,None]-points[None,:],axis=2)
            permutation = np.argmin(distance,axis=1)
            self.assertLess(np.max(distance[np.arange(len(points)),permutation]), 1e-16)
            c = solution.coefficients
            signs = np.sum(c*c[permutation],axis=0)/np.sum(c*c,axis=0)
            np.testing.assert_allclose(abs(signs[:2]),[1.,1.],rtol=0,atol=1e-10)
            parity.append(np.sign(signs[:2]))
        self.assertEqual(parity[0].tolist(),[-1.,1.])
        self.assertEqual(parity[1].tolist(),[1.,-1.])
        before = [[planar_curved_quantities(s,i) for i in range(s.case.modes)] for s in sources]
        request = PlanarCurvedTrackingRequest(PlanarCurvedComparisonDomain(*(s.case.domain for s in sources),'declared_quadratic'),
            previous_mode_ids=['odd-x','even-x'])
        report = track_planar_curved_modes(*sources,request)
        self.assertEqual(report['status'],'PASS',report['verification_reasons'])
        self.assertEqual(report['current_mode_ids'],['even-x','odd-x'])
        self.assertEqual(before,[[planar_curved_quantities(s,i) for i in range(s.case.modes)] for s in sources])
        # A historical two-ID subspace cannot be split into invented individual
        # labels simply because the new finite frequencies are separated.
        grouped = replace(request,previous_mode_ids=None,previous_identity_groups=[dict(indices=[1,2],ids=['a','b'])])
        inherited = track_planar_curved_modes(*sources,grouped)
        self.assertEqual(inherited['status'],'PASS',inherited['verification_reasons'])
        self.assertEqual(inherited['current_mode_ids'],[None,None])
        self.assertEqual(inherited['matches'][0]['previous_ids'],['a','b'])

    def test_exact_frequency_covariance_cannot_override_e_h_transport_disagreement(self):
        from superfish_ng.planar_curved_tracking import PlanarCurvedTrackingRequest, track_planar_curved_modes
        base = curved_ellipse(16)
        a = solve_planar_curved(PlanarCurvedCase(base,'te',modes=3,quadrature_order=16))
        rotation = np.array([[0.,-1.],[1.,0.]])
        turned = PlanarCurvedDomain(base.points_xy_m@rotation.T,base.cell_nodes,base.boundary_nodes)
        b = solve_planar_curved(replace(a.case,domain=turned))
        np.testing.assert_allclose(b.frequencies_hz,a.frequencies_hz,rtol=1e-11)
        request = PlanarCurvedTrackingRequest(PlanarCurvedComparisonDomain(base,turned,'declared_quadratic'))
        result = track_planar_curved_modes(a,b,request)
        # Scalar Hz follows this exact rotation, whereas the declared fixed
        # Cartesian E components rotate by 90 degrees. No frame transform was
        # requested; exact frequencies and one passing family cannot assign ID.
        self.assertEqual(result['status'],'UNVERIFIED')
        self.assertEqual(result['current_mode_ids'],[None,None])
        self.assertTrue(any('electric' in why for why in result['verification_reasons']))
        mapping = result['physical_mapping']
        aa,ab,bb = map(np.asarray,mapping['electric_grams'])
        np.testing.assert_allclose(np.diag(ab)/np.sqrt(np.diag(aa)*np.diag(bb)),0.,rtol=0,atol=1e-10)
        np.testing.assert_allclose(np.diag(result['magnetic_overlap_matrix']),1.,rtol=0,atol=1e-10)

    def test_full_native_cell_permutation_uses_explicit_original_owner(self):
        from superfish_ng.planar_curved_tracking import PlanarCurvedTrackingRequest, track_planar_curved_modes
        base = curved_ellipse(16)
        a = solve_planar_curved(PlanarCurvedCase(base, 'tm', modes=3, quadrature_order=16))
        changed = PlanarCurvedDomain(base.points_xy_m,base.cell_nodes[::-1],base.boundary_nodes)
        b = solve_planar_curved(replace(a.case,domain=changed))
        charts = [dict(base_cell=i,reference_vertices=[[[0,1],[0,1]],[[1,1],[0,1]],[[0,1],[1,1]]]) for i in reversed(range(16))]
        request = PlanarCurvedTrackingRequest(PlanarCurvedComparisonDomain(base,base),current_cells=charts)
        result = track_planar_curved_modes(a,b,request)
        self.assertEqual(result['status'],'PASS',result['verification_reasons'])
        self.assertEqual(result['current_mode_ids'],['mode-1','mode-2'])


if __name__ == '__main__':unittest.main()
