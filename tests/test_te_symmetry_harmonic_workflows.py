# SPDX-License-Identifier: Apache-2.0
"""Non-affine TE sector workflows preserve physical volume and native restart."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import tempfile,unittest
import numpy as np
from superfish_ng import solve
from superfish_ng.project import Project
from superfish_ng.studies import Study,execute_study
from superfish_ng.tuning import execute_tune,replay_tune,_project
from superfish_ng.te_saved import read_te_run
from superfish_ng.te import te_quantities
from test_te_symmetry_piecewise_tracking import half_fixture
from test_curved_harmonic_study import controls
from test_curved_harmonic_deformation import space
from test_expression_tuning import c,op,X


def symmetry_harmonic_study(reflected=True,tag='magnetic_symmetry',levels=1):
 cases,maps,_=half_fixture(tag=tag)
 return dict(study_version=3,kind='curved_harmonic_sweep',project=Project(replace(cases[0],curved_refinement_levels=levels),reflect_full=reflected,mesh_data=maps[0]['source_mesh']).to_dict(),parameter='bulge',parameter_unit='1',values=[0.,.5,1.],rf_coordinates='fixed',minimum_corner_angle_deg=1.,geometry_coefficients={'/curves/2/end_zr_m/1':[.08,.0064],'/curves/3/start_zr_m/1':[.08,.0064]})


def symmetry_harmonic_request(expression=False,reflected=True):
 study=symmetry_harmonic_study(reflected,levels=2);p=Project.from_dict(study['project'])
 r=dict(schema_version=5,project=p.to_dict(),parameter='bulge',parameter_unit='1',geometry_coefficients=study['geometry_coefficients'],rf_coordinates='fixed',minimum_corner_angle_deg=1.,bounds=[0.,.25],target_hz=float(solve(p.case,mesh_data=p.mesh_data).frequencies_hz[0]),frequency_tolerance_hz=1e6,parameter_tolerance=1e-8,max_trials=8,initial_ids=['TE'],mode_id='TE',controls=controls(),refinement_scale=2,mesh_frequency_tolerance_hz=1e6)
 if expression:
  r.update(schema_version=7,parameter='x',geometry_kind='curved_harmonic')
  expr=op('add',c(.08,'m'),op('mul',c(.0064,'m'),op('sub',op('exp',X),c(1))))
  r['bindings']=[dict(path='/case/geometry'+p,expression=deepcopy(expr)) for p in r.pop('geometry_coefficients')]
 return r

class TESymmetryHarmonicWorkflowTests(unittest.TestCase):
 def test_polynomial_projects_match_independent_volume_all_sectors(self):
  from scripts.validate_large_curved_mesh_selection import boundary_moments
  for tag in ('electric_symmetry','magnetic_symmetry'):
   for reflected in (False,True):
    study=Study.from_dict(symmetry_harmonic_study(reflected,tag))
    for value,p in zip(study.values,study.projects()):
     t=.08*value;expected=np.pi*.1*.08**2*(1+t+t*t/3)
     self.assertAlmostEqual(-boundary_moments(space(p))['signed_volume_m3']/expected,1.,places=12)
     self.assertEqual(p.reflect_full,reflected);self.assertEqual(p.case.z_max,tag)

 def test_polynomial_and_expression_tune_native_resume_and_final_gates(self):
  with tempfile.TemporaryDirectory() as tmp:
   for expression in (False,True):
    r=symmetry_harmonic_request(expression);root=Path(tmp)/str(expression)
    first=execute_tune(r,root/'first',max_new_trials=2)
    final=execute_tune(r,root/'rest',checkpoint=first)
    self.assertEqual(final['status'],'TUNED',final['decision']);self.assertEqual(replay_tune(final),final)
    self.assertEqual(first['trial_sources_sha256'],final['trial_sources_sha256'][:2])
    self.assertEqual(final['trials'][-1]['phase'],'refinement')
    for trial,run in zip(final['trials'],final['trial_runs']):
     s=read_te_run(Path(run)/'solution');self.assertIsNotNone(s.reflection_source_case)
     self.assertIsNone(te_quantities(s)['r_over_q_accelerator_ohm'])
     if trial['tracking']:self.assertTrue(trial['tracking']['tracking']['physical_mapping']['symmetry_sector']['reflected'])

 def test_expression_geometry_and_invalid_symmetry_preflight(self):
  from scripts.validate_large_curved_mesh_selection import boundary_moments
  r=symmetry_harmonic_request(True)
  for x in (0.,.125,.25):
   p=_project(r,x,'search');t=.08*np.expm1(x)
   expected=np.pi*.1*.08**2*(1+t+t*t/3)
   self.assertAlmostEqual(-boundary_moments(space(p))['signed_volume_m3']/expected,1.,places=12)
  raw=symmetry_harmonic_study();raw['geometry_coefficients'].update({'/curves/1/end_zr_m/0':[.1,.01],'/curves/2/start_zr_m/0':[.1,.01]})
  with tempfile.TemporaryDirectory() as tmp:
   target=Path(tmp)/'invalid'
   with self.assertRaises(ValueError):execute_study(Study.from_dict(raw),target)
   self.assertFalse(target.exists())

 def test_fixed_rf_and_partition_scope_guards(self):
  from superfish_ng.tuning import _request
  from superfish_ng.te_tuning import validate_te_request
  for expression in (False,True):
   request=symmetry_harmonic_request(expression)
   request['rf_coordinates']='axis_fraction'
   with self.assertRaisesRegex(ValueError,'TE.*fixed'):_request(request)
  raw=symmetry_harmonic_study()
  raw['rf_coordinates']='axis_fraction'
  with self.assertRaisesRegex(ValueError,'TE.*fixed'):Study.from_dict(raw)
  raw=symmetry_harmonic_study()
  raw.update(study_version=4,kind='curved_remesh_sweep',mesh_schedule={})
  with self.assertRaisesRegex(ValueError,'closed PEC'):Study.from_dict(raw)
  request=symmetry_harmonic_request();request['schema_version']=8
  with self.assertRaisesRegex(ValueError,'partition.*closed PEC'):
   validate_te_request(request,Project.from_dict(request['project']))
