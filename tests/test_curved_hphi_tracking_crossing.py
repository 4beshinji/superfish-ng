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


def coax(length,shear=0.,n=4):
    p=np.array([[.0625+.0625*i/n,length*j/n] for j in range(n+1) for i in range(n+1)])
    cells=[]
    for j in range(n):
        for i in range(n):
            a=j*(n+1)+i;b=a+1;d=a+n+1;c=d+1
            cells.extend(((a,b,c),(a,c,d)))
    cells=np.array(cells);edges=np.unique(np.sort(cells[:,[[0,1],[1,2],[2,0]]].reshape(-1,2),axis=1),axis=0)
    def mapped(points):
        q=points.copy();q[:,1]+=shear*q[:,0]**2;return q
    boundary=(list(range(n+1))+[j*(n+1)+n for j in range(1,n+1)]
              +[n*(n+1)+i for i in range(n-1,-1,-1)]+[j*(n+1) for j in range(n-1,0,-1)])
    loop=p[boundary]
    base=MeridionalMesh(mapped(loop),[],mapped(p),cells)
    return CurvedHphiCase(CurvedMeridionalGeometry(base,edges,mapped(p[edges].mean(axis=1))),modes=3)


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
