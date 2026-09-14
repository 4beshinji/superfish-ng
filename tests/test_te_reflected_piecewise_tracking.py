# SPDX-License-Identifier: Apache-2.0
"""Source-half charts extend over both lobes and sample actual reflected fields."""
from dataclasses import replace
from pathlib import Path
import tempfile,unittest
import numpy as np
from superfish_ng import solve
from superfish_ng.symmetry import reflect_solution
from superfish_ng.piecewise_remesh_tracking import track_piecewise_remesh_modes
from superfish_ng.io import save_run
from superfish_ng.saved_mode_tracking import build_saved_mode_tracking,replay_mode_tracking
from test_te_symmetry_piecewise_tracking import half_fixture,elliptic_half_fixture,controls

class TEReflectedPiecewiseTests(unittest.TestCase):
 def test_both_sides_and_parities_extend_all_chart_versions(self):
  for side in ('z_min','z_max'):
   for tag in ('electric_symmetry','magnetic_symmetry'):
    cases,maps,chart=half_fixture(side,tag)
    half=[solve(c,mesh_data=m['source_mesh']) for c,m in zip(cases,maps)]
    full=[reflect_solution(s.case,s)[1] for s in half]
    for version in (2,3,4,5):
     with self.subTest(side=side,tag=tag,version=version):
      c=controls(maps,version,chart)
      a=track_piecewise_remesh_modes(*half,['TE'],**c);b=track_piecewise_remesh_modes(*full,['TE'],**c)
      self.assertEqual(b['status'],'PASS');self.assertTrue(b['physical_mapping']['symmetry_sector']['reflected'])
      np.testing.assert_allclose(a['overlap_matrix'],b['overlap_matrix'],rtol=1e-11,atol=1e-12)
      np.testing.assert_allclose(b['physical_mapping']['axisymmetric_volumes_m3'],2*np.array(a['physical_mapping']['axisymmetric_volumes_m3']),rtol=1e-12)
      self.assertEqual(b['physical_mapping']['reflection_mapping']['declaration_domain'],'source half-domain')
      if version>=4:self.assertIn('source_common_reference_partition',b['physical_mapping'])
      for key in ('sample_count','comparison_triangle_count'):self.assertEqual(b['physical_mapping'][key],2*a['physical_mapping'][key])

 def test_comparison_uses_the_actual_second_lobe(self):
  cases,maps,chart=half_fixture(tag='electric_symmetry');s=solve(cases[0],mesh_data=maps[0]['source_mesh']);full=reflect_solution(s.case,s)[1]
  v=full.coefficients_v_per_m2.copy();v[full.space.geometry.points_rz_m[:,1]>s.case.length]*=-1
  changed=replace(full,coefficients_v_per_m2=v)
  # Deliberately non-eigenmode adapter: source-half coefficients are unchanged.
  c=controls([maps[0],maps[0]],2,chart)
  result=track_piecewise_remesh_modes(full,changed,['TE'],**c)
  self.assertEqual(result['status'],'UNVERIFIED');self.assertLess(abs(result['overlap_matrix'][0][0]),1e-10)
  from unittest.mock import patch
  with patch('superfish_ng.curved_piecewise_remesh_tracking.MAX_SAMPLES',300):
   track_piecewise_remesh_modes(s,s,['TE'],**c)
   with self.assertRaisesRegex(ValueError,'samples budget'):track_piecewise_remesh_modes(full,full,['TE'],**c)

 def test_true_curved_native_replay(self):
  cases,maps,chart=elliptic_half_fixture();half=[solve(c,mesh_data=m['source_mesh']) for c,m in zip(cases,maps)]
  full=[reflect_solution(s.case,s)[1] for s in half]
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   for i,s in enumerate(full):save_run(s.case,s,root/str(i))
   for version in (2,3,4,5):
    request=dict(schema_version=1,previous_run=str(root/'0'),current_run=str(root/'1'),previous_ids=['TE'],controls=controls(maps,version,chart))
    d=build_saved_mode_tracking(request);self.assertEqual(d['status'],'PASS');self.assertEqual(replay_mode_tracking(d),d)
   p=root/'0/axis_001.csv';p.write_text(p.read_text()+'\n')
   with self.assertRaises(ValueError):replay_mode_tracking(d)
