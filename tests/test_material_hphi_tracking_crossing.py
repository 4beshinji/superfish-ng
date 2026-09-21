# SPDX-License-Identifier: Apache-2.0
"""Independent TEM/Bessel crossings in a uniform nonvacuum material."""
import unittest
import numpy as np
from scripts.validate_coaxial import radial_roots
from superfish_ng.constants import C0,TAU
from superfish_ng.material_hphi import MaterialHphiCase,solve_material_hphi
from superfish_ng.material_hphi_tracking import MaterialHphiTrackingRequest,track_material_hphi_modes
from superfish_ng.rf_materials import RFMaterialPartition,LinearRFMaterial,RFMaterialRegion
from superfish_ng.hphi_geometry_mapping import HphiGeometryMapping
from test_curved_hphi_tracking_crossing import coax
from test_material_hphi_comparison import request


def material(length,n=4):
    mesh=coax(length,n=n).geometry.base_mesh
    return RFMaterialPartition(mesh,[LinearRFMaterial('dielectric',4.,9.)],
        [RFMaterialRegion('all','dielectric',list(range(len(mesh.triangles))))])


def tracking(a,b,mapping='same_domain'):
    lengths=[s.case.partition.mesh.outer_rz_m[:,1].max() for s in (a,b)]
    return MaterialHphiTrackingRequest(request(a.case.partition,b.case.partition,mapping),
        request(a.case.partition,material(lengths[0],8)),request(b.case.partition,material(lengths[1],8)))


class MaterialHphiTrackingCrossingTests(unittest.TestCase):
    def test_actual_rank_exchange_matches_fields_in_both_directions(self):
        radial=C0*radial_roots(.0625,.125,1)[0]/TAU/6
        lengths=(.05859375,.0703125);solutions=[]
        self.assertGreater(C0/(12*lengths[0]),radial);self.assertLess(C0/(12*lengths[1]),radial)
        for length in lengths:
            s=solve_material_hphi(MaterialHphiCase(material(length),modes=3))
            np.testing.assert_allclose(s.frequencies_hz[:2],sorted((radial,C0/(12*length))),rtol=1e-3)
            solutions.append(s)
        a,b=solutions;mapping=HphiGeometryMapping(a.case.partition.mesh,b.case.partition.mesh)
        for x,y,m in ((a,b,mapping),(b,a,mapping.inverse())):
            report=track_material_hphi_modes(x,y,tracking(x,y,m))
            self.assertEqual(report['status'],'PASS',report['verification_reasons'])
            self.assertEqual(report['current_mode_ids'],['mode-2','mode-1']);self.assertTrue(report['individual_ids_complete'])

    def test_analytic_degeneracy_keeps_only_a_subspace_identity(self):
        kr=radial_roots(.0625,.125,1)[0]
        s=solve_material_hphi(MaterialHphiCase(material(np.pi/kr),modes=3))
        np.testing.assert_allclose(s.frequencies_hz[:2],C0*kr/(6*TAU),rtol=1e-3)
        report=track_material_hphi_modes(s,s,tracking(s,s))
        self.assertEqual(report['status'],'PASS',report['verification_reasons'])
        self.assertEqual(report['current_mode_ids'],[None,None]);self.assertFalse(report['individual_ids_complete'])
        self.assertEqual(report['matches'][0]['kind'],'SUBSPACE')
        self.assertEqual(report['matches'][0]['previous_ids'],['mode-1','mode-2'])
        self.assertIsNone(report['matches'][0]['previous_phase_multiplier'])


if __name__=='__main__':unittest.main()
