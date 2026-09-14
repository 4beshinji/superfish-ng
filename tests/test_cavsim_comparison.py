# SPDX-License-Identifier: Apache-2.0
"""A01 comparison gates must not certify the wrong physical problem."""
from copy import deepcopy
import math
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from compare_cavsim2d import check_domain,candidate_quantities,comparison_passes,ng_run


class CavsimComparisonTests(unittest.TestCase):
    def test_native_comparison_uses_real_p2_fields_and_si_geometry(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=ng_run(Path(tmp)/'native',(.1,.1),.08,4,np.array([[.025,.017],[.05,.037]]))
            self.assertEqual(np.asarray(result['field_values']).shape,(2,3))
            self.assertTrue(np.isfinite(result['field_values']).all())
            self.assertAlmostEqual(result['quantities']['stored_energy_j'],1.,places=12)
            self.assertAlmostEqual(result['volume_m3'],math.pi*.0008,places=14)
            self.assertGreater(result['dofs'],len(result['field_values']))

    def test_closed_cylinder_invariants_reject_pmc_aperture(self):
        check_domain(dict(AXI=.08,PEC=.28),.008,math.pi*.0008,(.1,.1),.08)
        with self.assertRaisesRegex(ValueError,'only AXI and PEC'):
            check_domain(dict(AXI=.08,PEC=.24,PMC=.04),.008,math.pi*.0008,(.1,.1),.08)
        with self.assertRaisesRegex(ValueError,'volume'):
            check_domain(dict(AXI=.08,PEC=.28),.008,math.pi*.0009,(.1,.1),.08)

    def test_named_rq_uses_peak_energy_formula_and_checks_raw_column(self):
        q={'freq [MHz]':1000.,'Vacc [MV]':2.,'U [J]':3.,'R/Q [Ohm]':4e12/(2*math.pi*1e9*3),
           'G [Ohm]':200.,'Epk/Eacc []':2.,'Bpk/Eacc [mT/MV/m]':4.}
        result=candidate_quantities(q)
        self.assertEqual(result['frequency_hz'],1e9)
        self.assertAlmostEqual(result['r_over_q_accelerator_ohm'],2*result['r_over_q_circuit_ohm'])
        with self.assertRaisesRegex(ValueError,'R/Q'):
            candidate_quantities(dict(q,**{'R/Q [Ohm]':q['R/Q [Ohm]']/2}))

    def test_agreement_cannot_replace_each_convergence_or_physical_check(self):
        q=dict(frequency_hz=1e9,r_over_q_accelerator_ohm=100.,geometry_factor_ohm=200.)
        row=dict(ng={'quantities':q},candidate={'quantities':dict(q)},physical_checks_passed=True,
                 field_relative_l2=dict(E=0.,Hphi=0.))
        rows=[deepcopy(row) for _ in range(3)]
        self.assertTrue(comparison_passes(rows))
        for solver in ('ng','candidate'):
            changed=deepcopy(rows);changed[-2][solver]['quantities']['r_over_q_accelerator_ohm']=90.
            self.assertFalse(comparison_passes(changed))
        changed=deepcopy(rows);changed[-1]['physical_checks_passed']=False
        self.assertFalse(comparison_passes(changed))
        for value in (.1,float('nan')):
            changed=deepcopy(rows);changed[-1]['field_relative_l2']['E']=value
            self.assertFalse(comparison_passes(changed))


if __name__=='__main__':unittest.main()
