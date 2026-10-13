# SPDX-License-Identifier: Apache-2.0
"""Actual quadratic-domain tracking across an independently located TEM/TM crossing."""
import unittest
import numpy as np
from scripts.validate_coaxial import radial_roots
from superfish_ng.constants import C0,TAU
from superfish_ng.meridional_mesh import MeridionalMesh
from superfish_ng.curved_meridional_geometry import CurvedMeridionalGeometry
from superfish_ng.curved_hphi import CurvedHphiCase,solve_curved_hphi
from test_curved_hphi_tracking import request


from support.curved_hphi_geometry import coax


class CurvedHphiTrackingCrossingTests(unittest.TestCase):
    def test_genuinely_curved_rank_exchange_follows_fields(self):
        from superfish_ng.curved_hphi_tracking import track_curved_hphi_modes
        radial=C0*radial_roots(.0625,.125,1)[0]/TAU
        lengths=(.05859375,.0703125);solutions=[]
        self.assertGreater(C0/(2*lengths[0]),radial)
        self.assertLess(C0/(2*lengths[1]),radial)
        for length in lengths:
            # The exactly straight counterpart independently locates the crossing.
            straight=solve_curved_hphi(coax(length))
            np.testing.assert_allclose(straight.frequencies_hz[:2],sorted((radial,C0/(2*length))),rtol=1e-3)
            curved=solve_curved_hphi(coax(length,shear=1/16))
            self.assertGreater(np.max(abs(curved.case.geometry.points_rz_m[len(curved.case.geometry.base_mesh.points_rz_m):]-
                curved.case.geometry.base_mesh.points_rz_m[curved.case.geometry.edge_vertices].mean(axis=1))),0.)
            solutions.append(curved)
        a,b=solutions;report=track_curved_hphi_modes(a,b,request(a,b,'declared_quadratic'))
        self.assertEqual(report['status'],'PASS',report['verification_reasons'])
        self.assertEqual(report['current_mode_ids'],['mode-2','mode-1'])
        self.assertTrue(report['individual_ids_complete'])

    def test_analytic_degeneracy_in_quadratic_geometry_retains_id_set(self):
        from superfish_ng.curved_hphi_tracking import track_curved_hphi_modes
        kr=radial_roots(.0625,.125,1)[0]
        a=solve_curved_hphi(coax(np.pi/kr))
        np.testing.assert_allclose(a.frequencies_hz[:2],C0*kr/TAU,rtol=1e-3)
        report=track_curved_hphi_modes(a,a,request(a,a))
        self.assertEqual(report['status'],'PASS',report['verification_reasons'])
        self.assertFalse(report['individual_ids_complete'])
        self.assertEqual(report['current_mode_ids'],[None,None])
        self.assertEqual(report['matches'][0]['kind'],'SUBSPACE')
        self.assertEqual(report['matches'][0]['previous_ids'],['mode-1','mode-2'])
