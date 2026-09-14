# SPDX-License-Identifier: Apache-2.0
"""Half-domain TE charts retain sector tags and variable physical measure."""
from dataclasses import replace
from pathlib import Path
import tempfile,unittest
import numpy as np
from scipy.integrate import dblquad
from superfish_ng import Case,solve
from superfish_ng.model import Model
from superfish_ng.conics import LineSegment
from superfish_ng.curved_contour import CurvedContour
from superfish_ng.piecewise_remesh_tracking import track_piecewise_remesh_modes
from superfish_ng.io import save_run
from superfish_ng.saved_mode_tracking import build_saved_mode_tracking,replay_mode_tracking
from test_te_curved_symmetry_tracking import CONTROLS


def half_fixture(side='z_max',tag='magnetic_symmetry'):
 points=np.array([[0.,0.],[0.,.1],[.08,.1],[.08,.05],[.08,0.]])
 triangles=[[0,2,1],[0,3,2],[0,4,3]]
 tags=['axis',tag if side=='z_max' else 'pec','pec','pec',tag if side=='z_min' else 'pec']
 cases=[];documents=[]
 for factor in (1.,1.08):
  vertices=points.copy();vertices[3,0]*=factor
  zr=[tuple(map(float,p[::-1])) for p in vertices]
  contour=CurvedContour(tuple(LineSegment(a,b) for a,b in zip(zr,zr[1:]+zr[:1])),tuple(tags),1e-14)
  case=Case((),curved_contour=contour,geometry_order=2,element_order=2,curved_refinement_levels=1,
   curve_chord_tolerance_m=.001,model=Model(polarization='te'),modes=1,quadrature_order=12)
  mesh=dict(schema_version=1,length_unit='m',coordinate_order='rz',index_base=0,points=vertices.tolist(),
   triangles=triangles,boundary_edges=[[i,(i+1)%5] for i in range(5)],boundary_tags=tags)
  cases.append(case);documents.append(dict(schema_version=2,source_mesh=mesh,curved_refinement_levels=0))
 return cases,documents,points.tolist()


def controls(documents,version,chart):
 maps=[dict(d,schema_version=version) for d in documents]
 for m in maps:
  if version>=3:m['boundary_pairing']='declared_reference_polylines' if version==5 else 'ordered_curve_vertices'
  if version>=4:m['max_pair_tests']=10000
  if version==5:m['reference_vertices']=chart
 return dict(CONTROLS,mapping='piecewise_remesh',sample_order=8,comparison_meshes=maps)

class TESymmetryPiecewiseTrackingTests(unittest.TestCase):
 def test_all_sectors_and_chart_versions_preserve_native_identity(self):
  for side in ('z_min','z_max'):
   for tag in ('electric_symmetry','magnetic_symmetry'):
    cases,maps,chart=half_fixture(side,tag)
    solutions=[solve(c,mesh_data=m['source_mesh']) for c,m in zip(cases,maps)]
    for version in (2,3,4,5):
     with self.subTest(side=side,tag=tag,version=version):
      report=track_piecewise_remesh_modes(*solutions,['sector-1'],**controls(maps,version,chart))
      self.assertEqual(report['status'],'PASS')
      metadata=report['physical_mapping']['symmetry_sector']
      self.assertFalse(metadata['reflected']);self.assertIn('not full-spectrum',metadata['mode_indices'])
      self.assertEqual(metadata['source_end_conditions'][side],tag)

 def test_variable_weight_independent_integral_and_native_replay(self):
  cases,maps,chart=half_fixture();solutions=[solve(c,mesh_data=m['source_mesh']) for c,m in zip(cases,maps)]
  manufactured=[replace(s,coefficients_v_per_m2=np.ones_like(s.coefficients_v_per_m2)) for s in solutions]
  totals=np.zeros(3);volumes=np.zeros(2)
  for tri in maps[0]['source_mesh']['triangles']:
   points=[np.array(m['source_mesh']['points'])[tri] for m in maps]
   det=[abs(np.linalg.det(np.column_stack((p[1]-p[0],p[2]-p[0])))) for p in points]
   def radius(p,x,y):return ((1-x-y)*p[0]+x*p[1]+y*p[2])[0]
   for i in range(2):volumes[i]+=2*np.pi*det[i]*sum(points[i][:,0])/6
   def integral(x,y,k):
    r0,r1=[radius(p,x,y) for p in points]
    return [(r0*r1)**1.5*np.sqrt(det[0]*det[1]),r0**3*det[0],r1**3*det[1]][k]
   for k in range(3):totals[k]+=dblquad(lambda y,x:integral(x,y,k),0,1,lambda x:0,lambda x:1-x,epsabs=1e-15,epsrel=1e-10)[0]
  expected=totals[0]/np.sqrt(totals[1]*totals[2]);self.assertLess(expected,1-1e-5)
  for version in (2,3,4,5):
   report=track_piecewise_remesh_modes(*manufactured,['Ephi=r'],**controls(maps,version,chart))
   self.assertAlmostEqual(report['matches'][0]['minimum_principal_overlap'],expected,places=8)
   np.testing.assert_allclose(report['physical_mapping']['axisymmetric_volumes_m3'],volumes,rtol=1e-12)
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   for i,s in enumerate(solutions):save_run(s.case,s,root/str(i))
   report=build_saved_mode_tracking(dict(schema_version=1,previous_run=str(root/'0'),current_run=str(root/'1'),previous_ids=['sector-1'],controls=controls(maps,5,chart)))
   self.assertEqual(replay_mode_tracking(report),report)
   p=root/'0/axis_001.csv';p.write_text(p.read_text()+'\n')
   with self.assertRaises(ValueError):replay_mode_tracking(report)

 def test_cross_sector_and_reflected_fields_are_rejected(self):
  from superfish_ng.symmetry import reflect_solution
  cases,maps,chart=half_fixture();a=solve(cases[0],mesh_data=maps[0]['source_mesh'])
  other,othermaps,_=half_fixture(tag='electric_symmetry');b=solve(other[1],mesh_data=othermaps[1]['source_mesh'])
  with self.assertRaisesRegex(ValueError,'same symmetry sector'):track_piecewise_remesh_modes(a,b,['TE'],**controls(maps,2,chart))
  from superfish_ng.piecewise_remesh_tracking import validate_comparison_meshes
  with self.assertRaisesRegex(ValueError,'closed PEC'):validate_comparison_meshes([m['source_mesh'] for m in maps])
  tm=solve(replace(cases[0],model=Model()),mesh_data=maps[0]['source_mesh'])
  with self.assertRaisesRegex(ValueError,'closed PEC'):track_piecewise_remesh_modes(tm,tm,['TM'],**controls(maps,2,chart))
  reflected=reflect_solution(a.case,a)[1]
  with self.assertRaisesRegex(ValueError,'reflected'):track_piecewise_remesh_modes(reflected,reflected,['TE'],**controls(maps,2,chart))

 def test_true_elliptic_boundaries_and_maxwell_scaling(self):
  from superfish_ng.project import Project
  from superfish_ng.curved_project_transform import transform_curved_project
  from superfish_ng.te import te_quantities,TEFieldSampler
  cases,maps,chart=elliptic_half_fixture()
  solutions=[solve(c,mesh_data=m['source_mesh']) for c,m in zip(cases,maps)]
  scaled_projects=[transform_curved_project(Project(c,mesh_data=m['source_mesh']),dict(radial_scale=2.,axial_scale=2.,axial_shear=0.),rf_coordinates='fixed') for c,m in zip(cases,maps)]
  scaled=[solve(p.case,mesh_data=p.mesh_data) for p in scaled_projects]
  scaled_maps=[dict(m,source_mesh=p.mesh_data) for m,p in zip(maps,scaled_projects)]
  for a,b in zip(solutions,scaled):
   np.testing.assert_allclose(a.frequencies_hz,2*b.frequencies_hz,rtol=1e-10)
   np.testing.assert_allclose(a.coefficients_v_per_m2,2**2.5*b.coefficients_v_per_m2,rtol=1e-10,atol=1e-9)
   qa,qb=map(te_quantities,(a,b))
   for key,factor in [('stored_energy_j',1),('geometry_factor_ohm',1),('q0',1/np.sqrt(2)),('wall_loss_w',2**1.5)]:
    self.assertLess(abs(qa[key]/(factor*qb[key])-1),1e-10)
   points=np.concatenate([m.evaluate(np.array([[1/3,1/3]]))['points_rz_m'] for m in a.space.geometry.local_maps])
   fa,fb=TEFieldSampler(a).evaluate(points),TEFieldSampler(b).evaluate(2*points)
   for key in ('Ephi_V_per_m','Hr_quadrature_A_per_m','Hz_quadrature_A_per_m'):
    np.testing.assert_allclose(fa[key],2**1.5*fb[key],rtol=1e-10,atol=1e-9)
   self.assertIsNone(qa['r_over_q_accelerator_ohm'])
  for version in (2,3,4,5):
   a=track_piecewise_remesh_modes(*solutions,['TE'],**controls(maps,version,chart))
   b=track_piecewise_remesh_modes(*scaled,['TE'],**controls(scaled_maps,version,chart))
   self.assertEqual(a['status'],'PASS');self.assertEqual(b['status'],'PASS')
   np.testing.assert_allclose(a['overlap_matrix'],b['overlap_matrix'],rtol=1e-10,atol=1e-12)
   np.testing.assert_allclose(b['physical_mapping']['axisymmetric_volumes_m3'],8*np.array(a['physical_mapping']['axisymmetric_volumes_m3']),rtol=1e-12)


def elliptic_half_fixture():
 from copy import deepcopy
 from superfish_ng import make_mesh
 from superfish_ng.mesh_input import mesh_to_dict
 from test_curved_piecewise_remesh_tracking import curved_comparison_fixture
 raw=curved_comparison_fixture()[0][0].to_dict()
 g=raw['geometry'];g['curves'][0]['end_zr_m'][0]=.15
 radial=float(.08*np.sin(np.pi/3))
 g['curves'][1].update(start_rad=float(np.pi/3),sweep_rad=float(np.pi/6))
 from superfish_ng.conics import curve_from_dict
 endpoint=list(map(float,curve_from_dict(g['curves'][1]).evaluate(0.)['points_zr_m']))
 g['curves'][0]['end_zr_m'][0]=endpoint[0]
 g['curves'].insert(1,dict(type='line',start_zr_m=[endpoint[0],0.],end_zr_m=endpoint))
 g['edge_tags']=['axis','magnetic_symmetry','pec','pec'];g['segments_per_curve']=[1,1,2,3]
 raw['model']['polarization']='te';raw['mesh']['curved_refinement_levels']=1
 old=Case.from_dict(raw);source=mesh_to_dict(make_mesh(old))
 new=deepcopy(raw);g=new['geometry'];g['curves'][1]['end_zr_m'][1]*=1.08
 g['curves'][2].update(center_zr_m=[.08,0.],semiaxes_m=[.14,.0864])
 g['curves'][3].update(center_zr_m=[.08,0.],semiaxes_m=[.08,.0864])
 endpoint=list(map(float,curve_from_dict(g['curves'][2]).evaluate(0.)['points_zr_m']))
 g['curves'][0]['end_zr_m'][0]=endpoint[0];g['curves'][1].update(start_zr_m=[endpoint[0],0.],end_zr_m=endpoint)
 target=deepcopy(source)
 for p in target['points']:
  p[0]*=1.08;p[1]=.8*p[1] if p[1]<=.1 else .08+1.4*(p[1]-.1)
 maps=[dict(schema_version=2,source_mesh=m,curved_refinement_levels=0) for m in (source,target)]
 return (old,Case.from_dict(new)),maps,source['points']
