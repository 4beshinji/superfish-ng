# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from contextlib import ExitStack
from types import SimpleNamespace
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from superfish_ng import Case,solve
from superfish_ng.adaptive_refinement import _next,execute_adaptive_refinement,replay_adaptive_refinement

PEAKS=('epk_over_eacc','bpk_over_eacc_mt_per_mv_per_m')

def request():
    r=json.loads(Path('examples/adaptive_refinement/pillbox_confirmed.json').read_text())
    r.update(schema_version=3,surface_relative_tolerances=dict.fromkeys(PEAKS,.01))
    return r

class AdaptiveSurfaceStoppingTests(unittest.TestCase):
    def test_rf_stationarity_cannot_hide_peak_change_or_interval_width(self):
        r=request();case=Case.from_dict(r['case'])
        # A stationary eigenvalue/integral does not constrain a surface maximum.
        levels=[dict(status='PASS',refinement_kind='uniform_confirmation',quantities=dict.fromkeys(r['relative_tolerances'],1.),
                     surface=dict(intervals=dict.fromkeys(PEAKS,[1.,1.]))) for _ in range(5)]
        self.assertEqual(_next(case,r,levels,None)[0]['status'],'TARGETS_MET')
        for key in PEAKS:
            for interval in ([1.02,1.02],[.98,1.02],None):
                bad=deepcopy(levels);bad[-2]['surface']['intervals'][key]=interval
                decision,_=_next(case,r,bad,None)
                self.assertEqual(decision['status'],'QUANTITY_UNVERIFIED' if interval is None else 'LEVEL_LIMIT')
                if interval is not None:
                    self.assertTrue(all(x['passed'] for c in decision['changes'] for x in c.values()))
                    self.assertFalse(decision['surface_changes'][0][key]['passed'])
        from superfish_ng.mesh import make_mesh
        bad=deepcopy(levels);bad[-1]['surface']['intervals'][PEAKS[0]]=[1.02,1.02]
        mesh=make_mesh(case)
        decision,refined=_next(case,dict(r,max_levels=6),bad,SimpleNamespace(mesh=mesh))
        self.assertEqual(decision['status'],'PAUSED');self.assertEqual(decision['next_refinement_kind'],'uniform_confirmation')
        self.assertEqual(len(refined.triangles),4*len(mesh.triangles))
        bad=deepcopy(levels);bad[-2]['refinement_kind']='residual'
        self.assertEqual(_next(case,r,bad,None)[0]['status'],'LEVEL_LIMIT')

    def test_native_resume_peak_bounds_and_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);r=request();r['mode_id']='second'
            first=execute_adaptive_refinement(r,root/'first',max_new_levels=4)
            self.assertEqual(first['status'],'PAUSED');self.assertEqual(first['surface_status'],'NOT_CONFIRMED')
            with patch('superfish_ng.adaptive_refinement.solve',wraps=solve) as calls:
                last=execute_adaptive_refinement(r,root/'last',checkpoint=first)
                self.assertEqual(calls.call_count,1)
            self.assertEqual(last['status'],'TARGETS_MET');self.assertEqual(last['surface_status'],'TARGETS_MET')
            self.assertTrue(all(l['mode_index']==1 for l in last['levels']))
            self.assertEqual(last['sources'][:4],first['sources']);self.assertIsNone(last['physical_error_bound'])
            self.assertEqual(replay_adaptive_refinement(last),last)
            for field in ('surface_status','scope'):
                bad=deepcopy(last);bad[field]='altered'
                with self.assertRaises(ValueError):replay_adaptive_refinement(bad)
            bad=deepcopy(last);bad['levels'][0]['surface']['intervals'][PEAKS[0]][0]*=.5
            with self.assertRaises(ValueError):replay_adaptive_refinement(bad)
            from superfish_ng.cli import main
            self.assertEqual(main(['replay-adaptive-refinement',str(root/'last/checkpoint-005.json')]),0)
            source=Path(last['level_runs'][0])/'case.json';source.write_text(source.read_text()+' ')
            with self.assertRaises(ValueError):replay_adaptive_refinement(last)

    def test_strict_limits_and_geometry_preflight(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);r=request();case=Case.from_dict(r['case'])
            bads=[dict(r,surface_relative_tolerances={}),dict(r,surface_relative_tolerances=dict.fromkeys(PEAKS,0)),
                  dict(r,confirmation='none'),dict(r,case=replace(case,profile=((0.,.1),(.1,.075),(.2,.1))).to_dict()),
                  dict(r,case=replace(Case.load('examples/curved_ellipse.json'),geometry_order=1).to_dict())]
            for bad in bads:
                with self.assertRaises(ValueError):execute_adaptive_refinement(bad,root/'bad')
                self.assertFalse((root/'bad').exists())

    def test_managed_resume_and_gui_scope(self):
        import time
        from superfish_ng.jobs import JobManager
        from superfish_ng.adaptive_refinement import read_adaptive_refinement
        from superfish_ng.gui_adaptive_refinement import adaptive_refinement_response
        with tempfile.TemporaryDirectory() as temp,ExitStack() as cleanup:
            manager=JobManager(Path(temp));cleanup.callback(manager.close)
            def wait(identifier):
                deadline=time.monotonic()+60
                while time.monotonic()<deadline:
                    state=manager.status(identifier)
                    if state['status'] not in ('queued','running'):return manager.status(identifier,verify=True)
                    time.sleep(.025)
                self.fail('surface-confirmed job did not finish')
            r=request()
            with self.assertRaisesRegex(ValueError,'version 3.*CLI'):
                adaptive_refinement_response(manager,'start-adaptive-refinement',dict(request=r))
            identifier=manager.start_adaptive_refinement(r,max_new_levels=4)
            self.assertEqual(wait(identifier)['surface_status'],'NOT_CONFIRMED')
            first=read_adaptive_refinement(Path(temp)/identifier/'adaptive-refinement-results.json')
            with self.assertRaisesRegex(ValueError,'version 3.*CLI'):
                adaptive_refinement_response(manager,'replay-adaptive-refinement',dict(document=first))
            identifier=manager.start_adaptive_refinement(r,checkpoint=first)
            state=wait(identifier);self.assertEqual(state['refinement_status'],'TARGETS_MET')
            self.assertEqual(state['surface_status'],'TARGETS_MET');self.assertEqual(state['numerical_validation'],'not_checked')
            with self.assertRaisesRegex(ValueError,'version 3.*CLI'):
                adaptive_refinement_response(manager,'adaptive-refinement-result',dict(id=identifier))
