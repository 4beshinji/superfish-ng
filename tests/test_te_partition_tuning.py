# SPDX-License-Identifier: Apache-2.0
"""TE partition tuning preserves native physics across independent meshes."""
from copy import deepcopy
from pathlib import Path
import math
import tempfile
import unittest
import numpy as np
from superfish_ng import solve
from superfish_ng.tuning import _request,_project,pair_controls,execute_tune,replay_tune
from superfish_ng.te import te_quantities
from superfish_ng.te_saved import read_te_run
from superfish_ng.curved_project_transform import transform_curved_project
from test_partition_tuning import partition_request
from test_te import reference


def te_partition_request():
    r=partition_request();r['project']['case']['model']['polarization']='te'
    r['mesh_schedule']['max_pair_tests']=300000
    for p in r['mesh_schedule']['partitions']:p['curved_refinement_levels']=3
    return r


def te_curved_partition_request(levels=1):
    """Independent PEC edge split; charts cover the same reference domain."""
    from superfish_ng.project import Project
    from test_curved_piecewise_remesh_tracking import curved_comparison_fixture
    from test_curved_partition_schedule import partition
    from test_expression_tuning import expression_request,c,op,X
    cases,documents=curved_comparison_fixture()
    raw=Project(cases[0],mesh_data=documents[0]['source_mesh']).to_dict()
    raw['case']['model']['polarization']='te';base=Project.from_dict(raw)
    mesh=deepcopy(base.mesh_data);edge=mesh['boundary_tags'].index('pec')
    u,v=mesh['boundary_edges'][edge]
    owner=next(i for i,t in enumerate(mesh['triangles']) if {u,v}<=set(t))
    w=next(k for k in mesh['triangles'][owner] if k not in (u,v))
    chart=[[round(x*2**20)/2**20 for x in p] for p in mesh['points']]
    other=deepcopy(chart);midpoint=len(mesh['points'])
    mesh['points'].append([(mesh['points'][u][k]+mesh['points'][v][k])/2 for k in (0,1)])
    other.append([(chart[u][k]+chart[v][k])/2 for k in (0,1)])
    def oriented(t):
        points=np.array([mesh['points'][i] for i in t])
        return t if np.linalg.det(np.column_stack((points[1]-points[0],points[2]-points[0])))>0 else [t[0],t[2],t[1]]
    mesh['triangles'][owner]=oriented([u,midpoint,w]);mesh['triangles'].append(oriented([midpoint,v,w]))
    mesh['boundary_edges'][edge]=[u,midpoint];mesh['boundary_edges'].append([midpoint,v]);mesh['boundary_tags'].append('pec')
    r=expression_request(True)
    r.update(schema_version=8,project=base.to_dict(),mesh_schedule=dict(schema_version=1,breakpoints=[.05],max_pair_tests=300000,
        partitions=[partition(base,chart,levels),partition(Project(base.case,mesh_data=mesh),other,levels)]),
        bindings=[dict(path=f'/case/geometry/curves/{i}/semiaxes_m/1',expression=op('mul',c(.08,'m'),op('exp',X))) for i in (1,2)])
    return r


class TEPartitionTuningTests(unittest.TestCase):
    def test_partition_geometry_has_independent_cylinder_moments_and_fixed_rf(self):
        from scripts.validate_large_curved_mesh_selection import boundary_moments
        from test_curved_harmonic_deformation import space
        r=te_partition_request();_request(r);projects=[_project(r,x,'search') for x in (0.,.05)]
        self.assertEqual([len(p.mesh_data['triangles']) for p in projects],[2,3])
        for x,p in zip((0.,.05),projects):
            radius=.1*math.exp(x);m=boundary_moments(space(p))
            self.assertAlmostEqual(m['signed_area_m2'],-.2*radius,places=14)
            self.assertAlmostEqual(m['signed_volume_m3'],-math.pi*.2*radius**2,places=14)
            self.assertFalse(p.case.has_acceleration_overrides)
        controls=pair_controls(r,0.,.05,*projects)
        self.assertEqual([c['schema_version'] for c in controls['comparison_meshes']],[5,5])
        self.assertEqual([len(c['reference_vertices']) for c in controls['comparison_meshes']],[4,5])

    def test_real_switch_restart_earlier_refinement_and_maxwell_laws(self):
        r=te_partition_request();p=_project(r,0.,'search');a=solve(p.case,mesh_data=p.mesh_data)
        r['target_hz']=float(a.frequencies_hz[0]);exact_f,exact_g,_=reference()
        self.assertLess(abs(a.frequencies_hz[0]/exact_f-1),1e-3)
        coarse_g_error=abs(te_quantities(a)['geometry_factor_ohm']/exact_g-1)
        doubled=transform_curved_project(p,dict(radial_scale=2.,axial_scale=2.,axial_shear=0.),rf_coordinates='fixed')
        b=solve(doubled.case,mesh_data=doubled.mesh_data)
        np.testing.assert_allclose(a.frequencies_hz,2*b.frequencies_hz,rtol=1e-10)
        np.testing.assert_allclose(a.coefficients_v_per_m2,2**2.5*b.coefficients_v_per_m2,rtol=1e-10,atol=1e-10)
        qa,qb=map(te_quantities,[a,b])
        for key,factor in [('stored_energy_j',1),('geometry_factor_ohm',1),('q0',1/np.sqrt(2)),('wall_loss_w',2**1.5)]:
            self.assertLess(abs(qa[key]/(factor*qb[key])-1),1e-10)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);first=execute_tune(r,root/'first',max_new_trials=2)
            self.assertEqual(first['decision']['next_trial']['parent_index'],0)
            final=execute_tune(r,root/'rest',checkpoint=first)
            self.assertEqual(final['status'],'TUNED');self.assertEqual(replay_tune(final),final)
            self.assertEqual(first['trial_sources_sha256'],final['trial_sources_sha256'][:2])
            self.assertEqual([len(_project(r,t['value'],t['phase']).mesh_data['triangles']) for t in final['trials']],[2,3,2])
            for trial,path in zip(final['trials'],final['trial_runs']):
                q=te_quantities(read_te_run(Path(path)/'solution'))
                self.assertIsNone(q['r_over_q_accelerator_ohm']);self.assertIsNone(q['r_over_q_circuit_ohm'])
                if trial['tracking']:self.assertEqual(trial['tracking']['tracking']['physical_mapping']['field'],'Ephi_V_per_m')
            refined=read_te_run(Path(final['trial_runs'][-1])/'solution')
            refined_g_error=abs(te_quantities(refined)['geometry_factor_ohm']/exact_g-1)
            self.assertLess(refined_g_error,.02)
            self.assertLess(refined_g_error,coarse_g_error)
            meshes=final['trials'][-1]['tracking']['request']['controls']['comparison_meshes']
            self.assertEqual([m['curved_refinement_levels'] for m in meshes],[3,4])
            bad=deepcopy(final);bad['request']['mesh_schedule']['breakpoints']=[.2]
            with self.assertRaises(ValueError):replay_tune(bad)

    def test_te_contract_rejects_accelerating_coordinates_and_reflection(self):
        r=te_partition_request();_request(r)
        bad=deepcopy(r);bad['rf_coordinates']='axial'
        with self.assertRaisesRegex(ValueError,'TE.*fixed'):_request(bad)
        bad=deepcopy(r);bad['project']['reflect_full']=True
        with self.assertRaises(ValueError):_request(bad)
        bad=deepcopy(r);bad['project']['case']['rf']['active_length_m']=.1
        with self.assertRaises(ValueError):_request(bad)
