# SPDX-License-Identifier: Apache-2.0
"""TE source-sector identities survive affine workflows and native restart."""
from dataclasses import replace
from pathlib import Path
import tempfile,unittest
import numpy as np
from superfish_ng import solve
from superfish_ng.project import Project
from superfish_ng.studies import Study,execute_study
from superfish_ng.study_mode_tracking import build_study_mode_tracking,replay_study_mode_tracking
from superfish_ng.tuning import execute_tune,replay_tune,_request
from superfish_ng.te_saved import read_te_run
from superfish_ng.te import te_quantities
from test_te_curved_symmetry_tracking import sector,CONTROLS


def symmetry_study(side='z_max',tag='magnetic_symmetry',reflected=True):
 return dict(study_version=2,project=Project(sector(side,tag,1),reflect_full=reflected).to_dict(),
  kind='curved_affine_sweep',parameter='scale',parameter_unit='1',values=[1.,2.],
  affine_coefficients=dict(radial_scale=[0.,1.],axial_scale=[0.,1.],axial_shear=[0.]),rf_coordinates='fixed')


def symmetry_tune(reflected=True):
 raw=symmetry_study(reflected=reflected);p=Project.from_dict(raw['project']);p=replace(p,case=replace(p.case,curved_refinement_levels=2));f=float(solve(p.case).frequencies_hz[0])
 return dict(schema_version=4,project=p.to_dict(),parameter='scale',parameter_unit='1',
  affine_coefficients=raw['affine_coefficients'],rf_coordinates='fixed',bounds=[1.,1.2],target_hz=f,
  frequency_tolerance_hz=1.,parameter_tolerance=1e-8,max_trials=8,initial_ids=['sector-1'],mode_id='sector-1',
  controls=dict(CONTROLS,mapping='affine_remesh'),refinement_scale=2,mesh_frequency_tolerance_hz=1e6)

class TESymmetryAffineWorkflowTests(unittest.TestCase):
 def test_study_all_sectors_native_scale_and_completed_tracking(self):
  with tempfile.TemporaryDirectory() as tmp:
   for side in ('z_min','z_max'):
    for tag in ('electric_symmetry','magnetic_symmetry'):
     for reflected in (False,True):
      with self.subTest(side=side,tag=tag,reflected=reflected):
       folder=Path(tmp)/f'{side}-{tag}-{reflected}'
       study=Study.from_dict(symmetry_study(side,tag,reflected));report=execute_study(study,folder)
       a,b=[read_te_run(folder/p['directory']/'solution') for p in report['points']]
       np.testing.assert_allclose(a.frequencies_hz,2*b.frequencies_hz,rtol=1e-10)
       np.testing.assert_allclose(a.coefficients_v_per_m2,2**2.5*b.coefficients_v_per_m2,rtol=1e-10,atol=1e-9)
       qa,qb=map(te_quantities,(a,b))
       for key,factor in [('stored_energy_j',1),('geometry_factor_ohm',1),('q0',1/np.sqrt(2)),('wall_loss_w',2**1.5)]:
        self.assertLess(abs(qa[key]/(factor*qb[key])-1),1e-10)
       self.assertIsNone(qa['r_over_q_accelerator_ohm']);self.assertIsNone(qb['r_over_q_circuit_ohm'])
       track=build_study_mode_tracking(dict(schema_version=1,study_run=str(folder),initial_ids=['sector-1'],step_controls=[dict(CONTROLS,mapping='affine_remesh')]))
       self.assertEqual(replay_study_mode_tracking(track),track)
       pair=track['history']['steps'][0];self.assertEqual(pair['status'],'PASS')
       metadata=pair['tracking']['physical_mapping']['symmetry_sector']
       self.assertEqual(metadata['reflected'],reflected);self.assertIn('not full-spectrum',metadata['mode_indices'])

 def test_tune_direct_and_reflected_restart_and_refinement(self):
  with tempfile.TemporaryDirectory() as tmp:
   for reflected in (False,True):
    r=symmetry_tune(reflected);root=Path(tmp)/str(reflected)
    first=execute_tune(r,root/'first',max_new_trials=1)
    final=execute_tune(r,root/'rest',checkpoint=first)
    self.assertEqual(final['status'],'REFINEMENT_FAILED');self.assertEqual(replay_tune(final),final)
    self.assertFalse(final['decision']['refined_target_met'])
    self.assertTrue(final['decision']['mesh_difference_met'])
    self.assertEqual(first['trial_sources_sha256'],final['trial_sources_sha256'][:1])
    self.assertEqual(final['trials'][-1]['phase'],'refinement')
    for t in final['trials']:
     if t['tracking']:
      metadata=t['tracking']['tracking']['physical_mapping']['symmetry_sector']
      self.assertEqual(metadata['reflected'],reflected)

 def test_tune_one_mhz_operating_request_completes_for_direct_and_reflected(self):
  with tempfile.TemporaryDirectory() as tmp:
   for reflected in (False,True):
    r=symmetry_tune(reflected)
    # Separate operating requirement; the one-Hz refusal above is retained.
    r['frequency_tolerance_hz']=1e6
    root=Path(tmp)/str(reflected)
    first=execute_tune(r,root/'first',max_new_trials=1)
    final=execute_tune(r,root/'rest',checkpoint=first)
    self.assertEqual(final['status'],'TUNED',final['decision'])
    self.assertEqual(replay_tune(final),final)
    self.assertEqual(first['trial_sources_sha256'],final['trial_sources_sha256'][:1])
    self.assertTrue(final['decision']['refined_target_met'])
    self.assertTrue(final['decision']['mesh_difference_met'])
    self.assertEqual(final['trials'][-1]['phase'],'refinement')

 def test_nonzero_shear_law_rejected_even_if_sampled_endpoints_are_zero(self):
  raw=symmetry_study();raw['affine_coefficients']['axial_shear']=[2.,-3.,1.]
  with self.assertRaisesRegex(ValueError,'zero axial shear'):Study.from_dict(raw)
  request=symmetry_tune();request['affine_coefficients']['axial_shear']=[1.2,-2.2,1.]
  with self.assertRaisesRegex(ValueError,'zero axial shear'):_request(request)
