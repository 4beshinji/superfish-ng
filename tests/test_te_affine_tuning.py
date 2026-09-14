# SPDX-License-Identifier: Apache-2.0
"""TE affine transport uses electric fields and no accelerating coordinates."""
from dataclasses import replace
from pathlib import Path
import tempfile,unittest
import numpy as np
from superfish_ng import solve
from superfish_ng.model import Model
from superfish_ng.project import Project
from superfish_ng.curved_project_transform import transform_curved_project
from superfish_ng.affine_remesh_tracking import track_affine_remesh_modes
from superfish_ng.tuning import execute_tune,replay_tune
from superfish_ng.te_saved import read_te_run
from superfish_ng.te import te_quantities
from test_curved_tuning import curved_request

class TEAffineTuningTests(unittest.TestCase):
 def request(self):
  r=curved_request();p=Project.from_dict(r['project']);p=replace(p,case=replace(p.case,model=Model(polarization='te'),curved_refinement_levels=3))
  r['project']=p.to_dict();r['rf_coordinates']='fixed';r['target_hz']=float(solve(p.case,mesh_data=p.mesh_data).frequencies_hz[0])/1.1
  return r,p

 def test_te_scale_tuning_native_resume_and_maxwell_law(self):
  r,p=self.request()
  with tempfile.TemporaryDirectory() as tmp:
   first=execute_tune(r,Path(tmp)/'first',max_new_trials=2)
   final=execute_tune(r,Path(tmp)/'rest',checkpoint=first)
   self.assertEqual(final['status'],'TUNED');self.assertEqual(replay_tune(final),final)
   self.assertEqual(first['trial_sources_sha256'],final['trial_sources_sha256'][:2])
   for t,path in zip(final['trials'],final['trial_runs']):
    s=read_te_run(Path(path)/'solution');self.assertFalse(s.case.has_acceleration_overrides)
    self.assertIsNone(te_quantities(s)['r_over_q_accelerator_ohm'])
    if t['phase']!='refinement':self.assertLess(abs(t['frequency_hz']*t['value']/(r['target_hz']*1.1)-1),1e-10)
    if t['tracking']:self.assertEqual(t['tracking']['tracking']['physical_mapping']['field'],'Ephi_V_per_m')
   self.assertAlmostEqual(final['decision']['value'],1.1)

 def test_shear_polynomial_field_volume_and_coordinate_rejection(self):
  from superfish_ng import Case
  from superfish_ng.conics import LineSegment
  from superfish_ng.curved_contour import CurvedContour
  r,_=self.request();vertices=((0.,0.),(.2,0.),(.1,.1))
  curves=tuple(LineSegment(a,b) for a,b in zip(vertices,vertices[1:]+vertices[:1]))
  case=Case((),curved_contour=CurvedContour(curves,('axis','pec','pec'),1e-14),geometry_order=2,
            element_order=2,modes=1,curved_refinement_levels=2,curve_chord_tolerance_m=.001,model=Model(polarization='te'))
  mesh=dict(schema_version=1,length_unit='m',coordinate_order='rz',index_base=0,
            points=[[0.,0.],[0.,.2],[.1,.1]],triangles=[[0,2,1]],
            boundary_edges=[[0,1],[1,2],[2,0]],boundary_tags=['axis','pec','pec'])
  p=Project(case,mesh_data=mesh);affine=dict(radial_scale=1.1,axial_scale=.9,axial_shear=.1)
  with self.assertRaisesRegex(ValueError,'TE.*fixed'):transform_curved_project(p,affine,rf_coordinates='axial')
  q=transform_curved_project(p,affine,rf_coordinates='fixed');self.assertFalse(q.case.has_acceleration_overrides)
  solutions=[solve(x.case,mesh_data=x.mesh_data) for x in [p,q]]
  # A manufactured regular azimuthal field Ephi=r, not an eigenmode.
  fields=[replace(s,coefficients_v_per_m2=np.ones_like(s.coefficients_v_per_m2)) for s in solutions]
  controls=dict(r['controls'],affine_map=affine)
  d=track_affine_remesh_modes(*fields,['Ephi=r'],**controls)
  self.assertAlmostEqual(d['matches'][0]['minimum_principal_overlap'],1.,places=13)
  volumes=d['physical_mapping']['physical_axisymmetric_volumes_m3']
  self.assertAlmostEqual(volumes[1]/volumes[0],1.1**2*.9,places=13)

  from superfish_ng.io import save_run
  from superfish_ng.saved_mode_tracking import build_saved_mode_tracking,replay_mode_tracking
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'native';a=solutions[0];save_run(a.case,a,path)
   controls=dict(r['controls'],mapping='curved_same_domain')
   report=build_saved_mode_tracking(dict(schema_version=1,previous_run=str(path),current_run=str(path),previous_ids=['TE'],controls=controls))
   self.assertEqual(report['status'],'PASS');self.assertEqual(replay_mode_tracking(report),report)
   self.assertEqual(report['tracking']['physical_mapping']['field'],'Ephi_V_per_m')
