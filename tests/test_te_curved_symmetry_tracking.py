# SPDX-License-Identifier: Apache-2.0
"""Sector-safe curved TE comparison and independent full-domain eigensolves."""
from dataclasses import replace
from pathlib import Path
import tempfile,unittest
import numpy as np
from scipy.linalg import eigh
from superfish_ng import solve
from superfish_ng.model import Model
from superfish_ng.symmetry import reflect_solution
from superfish_ng.te import te_quantities
from superfish_ng.curved_same_domain_tracking import track_curved_same_domain_modes
from superfish_ng.saved_mode_tracking import build_saved_mode_tracking,replay_mode_tracking
from superfish_ng.io import save_run
from test_curved_reflection import half_case

CONTROLS=dict(mapping='curved_same_domain',sample_order=4,minimum_overlap=.8,
 minimum_assignment_margin=.05,relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)

def sector(side,tag,level=0):
 return replace(half_case(side,tag,level),model=Model(polarization='te'))

class TECurvedSymmetryTrackingTests(unittest.TestCase):
 def test_both_sides_and_parities_track_with_full_fem_and_rf_invariants(self):
  ranks=[]
  for side in ('z_min','z_max'):
   for tag in ('electric_symmetry','magnetic_symmetry'):
    with self.subTest(side=side,tag=tag):
     half=[solve(sector(side,tag,level)) for level in (0,1)]
     reflected=[reflect_solution(s.case,s)[1] for s in half]
     direct=track_curved_same_domain_modes(*half,['sector-1'],**CONTROLS)
     full=track_curved_same_domain_modes(*reflected,['sector-1'],**CONTROLS)
     for report,is_full in [(direct,False),(full,True)]:
      self.assertEqual(report['status'],'PASS');self.assertEqual(report['current_mode_ids'],['sector-1'])
      self.assertEqual(report['physical_mapping']['field'],'Ephi_V_per_m')
      self.assertEqual(report['physical_mapping']['symmetry_sector']['reflected'],is_full)
      self.assertIn('not full-spectrum',report['physical_mapping']['symmetry_sector']['mode_indices'])
     np.testing.assert_allclose(full['physical_mapping']['axisymmetric_volumes_m3'],2*np.array(direct['physical_mapping']['axisymmetric_volumes_m3']),rtol=1e-12)
     h,f=half[0],reflected[0];qh,qf=map(te_quantities,[h,f])
     for key,factor in [('stored_energy_j',2),('wall_loss_w',2),('geometry_factor_ohm',1),('q0',1)]:
      self.assertLess(abs(qf[key]/(factor*qh[key])-1),1e-10)
     # Solve the unfiltered full-domain FEM system independently; the source
     # sector rank is used neither to select an eigenpair nor to fit a frequency.
     free=np.setdiff1d(np.arange(f.stiffness.shape[0]),f.space.constrained_dofs)
     k=f.stiffness[free][:,free].toarray();m=f.mass[free][:,free].toarray()
     values,vectors=eigh(k,m,subset_by_index=(0,min(7,len(free)-1)))
     rank=int(np.argmin(abs(values/f.eigenvalues[0]-1)));ranks.append(rank+1)
     self.assertLess(abs(values[rank]/f.eigenvalues[0]-1),1e-9)
     v=f.coefficients_v_per_m2[free,0];w=vectors[:,rank]
     overlap=abs(v@m@w)/np.sqrt((v@m@v)*(w@m@w));self.assertGreater(overlap,1-1e-9)
     self.assertIsNone(qf['r_over_q_accelerator_ohm'])
  self.assertTrue(any(rank!=1 for rank in ranks))

 def test_native_replay_and_mixed_sector_rejection(self):
  a,b=[solve(sector('z_max','magnetic_symmetry',level)) for level in (0,1)]
  x,y=[reflect_solution(s.case,s)[1] for s in (a,b)]
  other=solve(sector('z_max','electric_symmetry'))
  for pair in [(a,x),(x,a),(a,other),(x,reflect_solution(other.case,other)[1])]:
   with self.assertRaises(ValueError):track_curved_same_domain_modes(*pair,['sector-1'],**CONTROLS)
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   for name,s in [('a',x),('b',y)]:save_run(s.case,s,root/name)
   report=build_saved_mode_tracking(dict(schema_version=1,previous_run=str(root/'a'),current_run=str(root/'b'),previous_ids=['sector-1'],controls=CONTROLS))
   self.assertEqual(report['status'],'PASS');self.assertEqual(replay_mode_tracking(report),report)
   path=root/'a/axis_001.csv';path.write_text(path.read_text()+'\n')
   with self.assertRaises(ValueError):replay_mode_tracking(report)

 def test_symmetry_affine_transport_preserves_plane_and_maxwell_laws(self):
  from superfish_ng.project import Project
  from superfish_ng.curved_project_transform import transform_curved_project
  from superfish_ng.affine_remesh_tracking import track_affine_remesh_modes
  affine=dict(radial_scale=2.,axial_scale=2.,axial_shear=0.)
  controls=dict(CONTROLS,mapping='affine_remesh',affine_map=affine)
  for side in ('z_min','z_max'):
   for tag in ('electric_symmetry','magnetic_symmetry'):
    with self.subTest(side=side,tag=tag):
     source=Project(sector(side,tag));target=transform_curved_project(source,affine,rf_coordinates='fixed')
     a=solve(source.case);b=solve(target.case,mesh_data=target.mesh_data)
     for reflected in (False,True):
      x,y=[reflect_solution(s.case,s)[1] for s in (a,b)] if reflected else (a,b)
      report=track_affine_remesh_modes(x,y,['sector-1'],**controls)
      self.assertEqual(report['status'],'PASS');self.assertEqual(report['physical_mapping']['symmetry_sector']['reflected'],reflected)
      np.testing.assert_allclose(x.frequencies_hz,2*y.frequencies_hz,rtol=1e-10)
      np.testing.assert_allclose(x.coefficients_v_per_m2,2**2.5*y.coefficients_v_per_m2,rtol=1e-10,atol=1e-9)
      qx,qy=map(te_quantities,(x,y))
      for key,factor in [('stored_energy_j',1),('geometry_factor_ohm',1),('q0',1/np.sqrt(2)),('wall_loss_w',2**1.5)]:
       self.assertLess(abs(qx[key]/(factor*qy[key])-1),1e-10)
      with self.assertRaisesRegex(ValueError,'zero axial shear'):
       track_affine_remesh_modes(x,y,['sector-1'],**dict(controls,affine_map=dict(affine,axial_shear=.1)))
     mirror=transform_curved_project(replace(source,reflect_full=True),affine,rf_coordinates='fixed')
     self.assertTrue(mirror.reflect_full);self.assertEqual(mirror.case,target.case)
     with self.assertRaisesRegex(ValueError,'zero axial shear'):
      transform_curved_project(source,dict(affine,axial_shear=.1),rf_coordinates='fixed')
