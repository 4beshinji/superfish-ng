# SPDX-License-Identifier: Apache-2.0
"""Curved TE deformation preserves N/A RF semantics through native tuning."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import tempfile,unittest
from superfish_ng import solve
from superfish_ng.model import Model
from superfish_ng.project import Project
from superfish_ng.tuning import _request,_project,execute_tune,replay_tune
from superfish_ng.te_saved import read_te_run
from superfish_ng.te import te_quantities
from test_curved_harmonic_tuning import harmonic_request


def te_curved_request():
 r=harmonic_request();p=Project.from_dict(r['project']);r['project']=replace(p,case=replace(p.case,model=Model(polarization='te'))).to_dict()
 return r

class TECurvedTuningTests(unittest.TestCase):
 def test_harmonic_native_restart_and_fixed_acceleration_na(self):
  r=te_curved_request();p=_project(r,.5,'search');r['target_hz']=float(solve(p.case,mesh_data=p.mesh_data).frequencies_hz[0])
  with tempfile.TemporaryDirectory() as tmp:
   first=execute_tune(r,Path(tmp)/'first',max_new_trials=2)
   final=execute_tune(r,Path(tmp)/'rest',checkpoint=first)
   self.assertEqual(final['status'],'TUNED');self.assertEqual(replay_tune(final),final)
   self.assertEqual(first['trial_sources_sha256'],final['trial_sources_sha256'][:2])
   for t,path in zip(final['trials'],final['trial_runs']):
    s=read_te_run(Path(path)/'solution');self.assertFalse(s.case.has_acceleration_overrides)
    self.assertIsNone(te_quantities(s)['r_over_q_accelerator_ohm'])
    if t['tracking']:self.assertEqual(t['tracking']['tracking']['physical_mapping']['field'],'Ephi_V_per_m')
   self.assertAlmostEqual(final['decision']['value'],.5)

 def test_expression_and_study_geometry_preserve_te_and_reject_acceleration_coordinates(self):
  from superfish_ng.curved_harmonic_tuning import shape_study
  from test_expression_tuning import c,op,X
  r=te_curved_request();p=Project.from_dict(r['project']);study=shape_study(r,p)
  for candidate in study.projects():
   self.assertEqual(candidate.case.model.polarization,'te');self.assertFalse(candidate.case.has_acceleration_overrides)
  bad=deepcopy(r);bad['rf_coordinates']='axis_fraction'
  with self.assertRaisesRegex(ValueError,'TE.*fixed'):_request(bad)
  r.update(schema_version=7,geometry_kind='curved_harmonic',parameter='x')
  r['bindings']=[dict(path='/case/geometry'+path,expression=op('add',c(v[0],'m'),op('mul',c(v[1],'m'),X))) for path,v in r.pop('geometry_coefficients').items()]
  _request(r)
  with tempfile.TemporaryDirectory() as tmp:
   d=execute_tune(r,Path(tmp)/'trial',max_new_trials=1);self.assertEqual(replay_tune(d),d)

 def test_te_shape_moments_match_independent_green_integrals(self):
  from scripts.validate_large_curved_mesh_selection import boundary_moments
  from test_curved_harmonic_deformation import space
  r=te_curved_request();base=boundary_moments(space(_project(r,0.,'search')))
  for x in [.5,1.]:
   p=_project(r,x,'search');m=boundary_moments(space(p));factor=1+x/8
   self.assertAlmostEqual(m['signed_area_m2']/base['signed_area_m2'],factor,places=12)
   self.assertAlmostEqual(m['signed_volume_m3']/base['signed_volume_m3'],factor**2,places=12)
   self.assertFalse(p.case.has_acceleration_overrides)
