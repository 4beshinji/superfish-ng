# SPDX-License-Identifier: Apache-2.0
import copy
from dataclasses import replace
from fractions import Fraction as F
import unittest
from superfish_ng.curved_hphi_rf_convergence import CurvedHphiRFConvergence
from superfish_ng.curved_hphi_tracking import CurvedHphiTrackingRequest
from test_curved_hphi_convergence import request
from test_curved_hphi_rf_design import declaration


class CurvedHphiRFChartSemanticsTests(unittest.TestCase):
    def test_exact_rational_representation_preserves_original_chart_roles(self):
        convergence=request(False,holes=0)
        base=declaration(convergence,[p.case.geometry for p in convergence.projects],convergence.native_cells)
        equivalent=copy.deepcopy(convergence.native_cells)
        for cells in equivalent:
            for cell in cells:
                for point in cell['reference_vertices']:
                    for coordinate in point:coordinate[0]*=2;coordinate[1]*=2
        for left,right in zip(convergence.native_cells,equivalent):
            for a,b in zip(left,right):
                self.assertEqual(a['base_cell'],b['base_cell'])
                self.assertTrue(all(F(*x)==F(*y) for p,q in zip(a['reference_vertices'],b['reference_vertices']) for x,y in zip(p,q)))
        changed=replace(convergence,native_cells=equivalent)
        self.assertEqual([p.to_dict() for p in changed.projects],[p.to_dict() for p in convergence.projects])
        rebuilt=CurvedHphiRFConvergence(changed,base.tracking_requests)
        self.assertEqual(rebuilt.mode_id,base.mode_id)
        self.assertEqual(rebuilt.convergence.native_cells,changed.native_cells)
        bad=base.tracking_requests[0].to_dict();bad['previous_cells'][0]['base_cell']=1
        altered=[CurvedHphiTrackingRequest.from_dict(bad),base.tracking_requests[1]]
        with self.assertRaisesRegex(ValueError,'retain each original native chart'):
            replace(base,tracking_requests=altered)
