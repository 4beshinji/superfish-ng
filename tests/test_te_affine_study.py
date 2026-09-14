# SPDX-License-Identifier: Apache-2.0
"""Independent TE affine sweeps preserve native physics and Maxwell scaling."""
from copy import deepcopy
from pathlib import Path
import tempfile,unittest
import numpy as np
from superfish_ng.studies import Study,execute_study
from superfish_ng.jobs import read_job
from superfish_ng.te_saved import read_te_run
from superfish_ng.te import te_quantities
from test_curved_affine_study import affine_study_document


def te_affine_study():
 r=affine_study_document();r['project']['case']['model']['polarization']='te';r['rf_coordinates']='fixed'
 return r

class TEAffineStudyTests(unittest.TestCase):
 def test_real_sweep_keeps_independent_spectra_and_native_maxwell_laws(self):
  raw=te_affine_study();study=Study.from_dict(raw);self.assertEqual(study.to_dict(),raw)
  with tempfile.TemporaryDirectory() as tmp:
   folder=Path(tmp)/'study';report=execute_study(study,folder)
   self.assertEqual(report['numerical_status'],'UNVERIFIED');self.assertEqual(report['comparisons'],[])
   self.assertEqual(report['mode_tracking'],'not performed; independent spectra')
   self.assertEqual(read_job(folder)['status'],'complete')
   a,b=[read_te_run(folder/p['directory']/'solution') for p in report['points']]
   np.testing.assert_allclose(a.frequencies_hz,2*b.frequencies_hz,rtol=1e-10)
   np.testing.assert_allclose(a.coefficients_v_per_m2,2**2.5*b.coefficients_v_per_m2,rtol=1e-10,atol=1e-10)
   qa,qb=[te_quantities(s) for s in [a,b]]
   for key,factor in [('stored_energy_j',1),('geometry_factor_ohm',1),('q0',1/np.sqrt(2)),('wall_loss_w',2**1.5)]:
    self.assertLess(abs(qa[key]/(factor*qb[key])-1),1e-10)
   for s,q in zip([a,b],[qa,qb]):
    self.assertFalse(s.case.has_acceleration_overrides)
    self.assertIsNone(q['r_over_q_accelerator_ohm']);self.assertIsNone(q['r_over_q_circuit_ohm'])
   target=folder/report['points'][0]['directory']/'solution/axis_001.csv';target.write_text(target.read_text()+'\n')
   with self.assertRaises(ValueError):read_job(folder)

 def test_unsupported_coordinates_and_reflection_fail_at_study_construction(self):
  raw=te_affine_study()
  for changes,pattern in [({'rf_coordinates':'axial'},'TE.*fixed')]:
   with self.assertRaisesRegex(ValueError,pattern):Study.from_dict(dict(raw,**changes))
  reflected=deepcopy(raw);reflected['project']['reflect_full']=True
  with self.assertRaises(ValueError):Study.from_dict(reflected)
  overridden=deepcopy(raw);overridden['project']['case']['rf']['active_length_m']=.1
  with self.assertRaisesRegex(ValueError,'TE has no axial'):Study.from_dict(overridden)
