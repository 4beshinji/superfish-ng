# SPDX-License-Identifier: Apache-2.0
"""Symmetry-preserving harmonic Project motion retains physical TE fields."""
from copy import deepcopy
from dataclasses import replace
import unittest
import numpy as np
from superfish_ng import solve
from superfish_ng.project import Project
from superfish_ng.model import Model
from superfish_ng.curved_harmonic_deformation import deform_curved_project
from superfish_ng.curved_project_transform import transform_curved_project
from superfish_ng.curved_refinement_steps import CurvedRefinementStep as Step
from superfish_ng.frozen_curved_refinement import freeze_curved_refinement
from superfish_ng.symmetry import reflect_solution
from superfish_ng.te import te_quantities
from test_te_symmetry_piecewise_tracking import half_fixture,elliptic_half_fixture,controls
from test_curved_harmonic_deformation import space
from superfish_ng.piecewise_remesh_tracking import track_piecewise_remesh_modes


def deform(project,geometry):return deform_curved_project(project,geometry,rf_coordinates='fixed',minimum_corner_angle_deg=1.)

class TESymmetryDeformationTests(unittest.TestCase):
 def test_all_sectors_and_reflection_keep_fixed_history_and_plane(self):
  for side in ('z_min','z_max'):
   for tag in ('electric_symmetry','magnetic_symmetry'):
    cases,maps,_=half_fixture(side,tag)
    for reflected in (False,True):
     with self.subTest(side=side,tag=tag,reflected=reflected):
      source=freeze_curved_refinement(Project(replace(cases[0],curved_refinement_levels=0,curved_refinement_steps=(Step('marked',(0,),1.),Step('uniform'))),reflect_full=reflected,mesh_data=maps[0]['source_mesh']))
      before=source.to_dict();target=deform(source,cases[1].to_dict()['geometry'])
      self.assertEqual(source.to_dict(),before);self.assertEqual(target.reflect_full,reflected)
      self.assertEqual(target.case.curved_refinement_steps,source.case.curved_refinement_steps)
      self.assertEqual(getattr(target.case,side),tag)
      np.testing.assert_array_equal(space(source).geometry.cell_nodes,space(target).geometry.cell_nodes)
      np.testing.assert_allclose(space(source).geometry.boundary_parameters,space(target).geometry.boundary_parameters,rtol=0,atol=2e-14)

 def test_elliptic_motion_full_fields_and_maxwell_scaling(self):
  cases,maps,chart=elliptic_half_fixture();source=Project(cases[0],reflect_full=True,mesh_data=maps[0]['source_mesh'])
  target=deform(source,cases[1].to_dict()['geometry'])
  x=np.c_[np.array(source.mesh_data['points']),np.ones(len(source.mesh_data['points']))];y=np.array(target.mesh_data['points'])
  self.assertGreater(np.linalg.norm(x@np.linalg.lstsq(x,y,rcond=None)[0]-y),1e-3)
  scaled=transform_curved_project(target,dict(radial_scale=2.,axial_scale=2.,axial_shear=0.),rf_coordinates='fixed')
  solutions=[]
  for p in (source,target,scaled):
   s=solve(p.case,mesh_data=p.mesh_data);solutions.append(reflect_solution(s.case,s)[1])
  a,b,c=solutions
  np.testing.assert_allclose(b.frequencies_hz,2*c.frequencies_hz,rtol=1e-10)
  np.testing.assert_allclose(b.coefficients_v_per_m2,2**2.5*c.coefficients_v_per_m2,rtol=1e-10,atol=1e-9)
  qb,qc=map(te_quantities,(b,c))
  for key,factor in [('stored_energy_j',1),('geometry_factor_ohm',1),('q0',1/np.sqrt(2)),('wall_loss_w',2**1.5)]:self.assertLess(abs(qb[key]/(factor*qc[key])-1),1e-10)
  self.assertIsNone(qb['r_over_q_accelerator_ohm'])
  docs=[dict(schema_version=2,source_mesh=p.mesh_data,curved_refinement_levels=0) for p in (source,target)]
  result=track_piecewise_remesh_modes(a,b,['TE'],**controls(docs,2,chart));self.assertEqual(result['status'],'PASS')
  self.assertTrue(result['physical_mapping']['symmetry_sector']['reflected'])

 def test_invalid_plane_tags_rf_and_tm_symmetry_are_rejected(self):
  cases,maps,_=half_fixture();source=Project(cases[0],mesh_data=maps[0]['source_mesh']);g=cases[1].to_dict()['geometry']
  with self.assertRaisesRegex(ValueError,'fixed'):deform_curved_project(source,g,rf_coordinates='axis_fraction',minimum_corner_angle_deg=1.)
  bad=deepcopy(g);bad['edge_tags'][1]='electric_symmetry'
  with self.assertRaisesRegex(ValueError,'edge tags'):deform(source,bad)
  bad=deepcopy(g);bad['curves'][1]['end_zr_m'][0]+=.01;bad['curves'][2]['start_zr_m'][0]+=.01
  with self.assertRaises(ValueError):deform(source,bad)
  tm=replace(source,case=replace(source.case,model=Model()))
  with self.assertRaisesRegex(ValueError,'closed PEC'):deform(tm,g)
