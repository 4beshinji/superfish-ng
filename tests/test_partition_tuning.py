# SPDX-License-Identifier: Apache-2.0
"""Actual partition ancestry, deterministic restart and separate refinement."""
from copy import deepcopy
import math
from pathlib import Path
import tempfile
import unittest
from superfish_ng.tuning import _request,_project,pair_controls,execute_tune,replay_tune
from test_curved_partition_schedule import schedule
from test_curved_harmonic_tuning import harmonic_request
from test_expression_tuning import c,op,X


def partition_request():
    base,plans=schedule();plans['breakpoints']=[.05]
    plans['partitions'][0]['curved_refinement_levels']=1
    r=harmonic_request();r.pop('geometry_coefficients')
    r.update(schema_version=8,project=base.to_dict(),geometry_kind='curved_harmonic',parameter='x',
        bounds=[0.,.1],mesh_schedule=plans,frequency_tolerance_hz=5e7,mesh_frequency_tolerance_hz=5e7,
        bindings=[dict(path=f'/case/geometry/curves/{i}/{key}/1',expression=op('mul',c(.1,'m'),op('exp',X)))
                  for i,key in ((1,'end_zr_m'),(2,'start_zr_m'),(2,'end_zr_m'),(3,'start_zr_m'))])
    return r


class PartitionTuningTests(unittest.TestCase):
    def test_trial_values_choose_mesh_and_reference_history_in_both_directions(self):
        from test_curved_harmonic_deformation import space
        from scripts.validate_large_curved_mesh_selection import boundary_moments
        r=partition_request();before=deepcopy(r);_request(r)
        a=_project(r,0.,'search');b=_project(r,.05,'search')
        self.assertEqual([len(p.mesh_data['triangles']) for p in (a,b)],[2,3])
        for value,p in ((0.,a),(.05,b)):
            moments=boundary_moments(space(p));radius=.1*math.exp(value)
            # The declared boundary edges are clockwise in (r,z).
            self.assertAlmostEqual(moments['signed_area_m2'],-.2*radius,places=14)
            self.assertAlmostEqual(moments['signed_volume_m3'],-math.pi*radius**2*.2,places=14)
        forward=pair_controls(r,0.,.05,a,b);backward=pair_controls(r,.05,0.,b,a)
        self.assertEqual(forward['comparison_meshes'],backward['comparison_meshes'][::-1])
        fine=_project(r,0.,'refinement');pair=pair_controls(r,0.,0.,a,fine)
        self.assertEqual([d['curved_refinement_levels'] for d in pair['comparison_meshes']],[1,2])
        self.assertEqual([len(d['reference_vertices']) for d in pair['comparison_meshes']],[4,4])
        self.assertEqual(r,before)

    def test_real_switch_and_earlier_endpoint_refinement_survive_restart(self):
        from superfish_ng import solve
        r=partition_request();p=_project(r,0.,'search');r['target_hz']=float(solve(p.case,mesh_data=p.mesh_data).frequencies_hz[0])
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);first=execute_tune(r,root/'first',max_new_trials=2)
            self.assertEqual(first['decision']['next_trial']['parent_index'],0)
            self.assertEqual(first['decision']['next_trial']['phase'],'refinement')
            final=execute_tune(r,root/'rest',checkpoint=first)
            self.assertEqual(final['status'],'TUNED');self.assertEqual(replay_tune(final),final)
            self.assertEqual(final['trial_sources_sha256'][:2],first['trial_sources_sha256'])
            meshes=final['trials'][-1]['tracking']['request']['controls']['comparison_meshes']
            self.assertEqual([len(m['source_mesh']['triangles']) for m in meshes],[2,2])
            bad=deepcopy(final);bad['request']['mesh_schedule']['breakpoints']=[.2]
            with self.assertRaises(ValueError):replay_tune(bad)

    def test_strict_version_controls_and_recovery_wrapper(self):
        r=partition_request()
        for changed in (dict(geometry_kind='profile'),dict(refinement_scale=3),dict(mesh_schedule={}),
                        dict(controls=dict(r['controls'],comparison_meshes=[]))):
            with self.subTest(changed=changed),self.assertRaises(ValueError):_request(dict(r,**changed))
        wrapper=dict(schema_version=6,tune_request=r,identity_recovery=dict(anchor_selection='latest_resolved_trial',controls=r['controls']))
        _request(wrapper)
        self.assertEqual(_project(wrapper,.05,'search').to_dict(),_project(r,.05,'search').to_dict())
