# SPDX-License-Identifier: Apache-2.0
"""Expression-driven native geometry, independent moments and FEM restart."""
from copy import deepcopy
import json
import math
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng.tuning import _request, _project, execute_tune, replay_tune
from test_coupled_tuning import coupled_request
from test_curved_harmonic_tuning import harmonic_request
from test_curved_harmonic_deformation import space


def c(value, unit='1'): return dict(constant=value, unit=unit)
def op(name, *args): return dict(op=name, args=list(args))
X = dict(variable='x')


def expression_request(curved=False):
    r = harmonic_request() if curved else coupled_request('1')
    r.update(schema_version=7, parameter='x', geometry_kind='curved_harmonic' if curved else 'profile', bounds=[0., .1])
    if curved:
        laws = r.pop('geometry_coefficients')
        r['bindings'] = [dict(path='/case/geometry'+p, expression=op('add', c(a, 'm'),
            op('mul', c(b, 'm'), op('sub', op('exp', X), c(1))))) for p, (a, b) in laws.items()]
    else:
        r['bindings'] = [dict(path=b['path'], expression=op('mul', c(.1, 'm'), op('exp', X))) for b in r['bindings']]
    return r


class ExpressionTuningTests(unittest.TestCase):
    def test_exponential_profile_units_atomicity_and_refinement(self):
        r=expression_request();original=deepcopy(r);_request(r)
        for x in (0., .03, .1):
            p=_project(r,x,'search');self.assertEqual(p.case.profile,((0.,.1*math.exp(x)),(.08,.1*math.exp(x))))
            fine=_project(r,x,'refinement');self.assertEqual(fine.case.profile,p.case.profile)
            self.assertEqual(fine.case.nr,2*p.case.nr)
        metres=deepcopy(r);metres['parameter_unit']='m'
        for b in metres['bindings']:b['expression']['args'][1]['args']=[op('div',X,c(.1,'m'))]
        self.assertEqual(_project(r,.1,'search').to_dict(),_project(metres,.01,'search').to_dict())
        self.assertEqual(r,original)

    def test_nonaffine_curve_law_independent_area_volume_and_history(self):
        from scripts.validate_large_curved_mesh_selection import boundary_moments
        from superfish_ng.tuning import pair_controls
        r=expression_request(True);_request(r);old=deepcopy(r)
        base=boundary_moments(space(_project(r,0.,'search')))
        p=_project(r,.1,'search');actual=boundary_moments(space(p));ratio=1+math.expm1(.1)/8
        self.assertAlmostEqual(actual['signed_area_m2']/base['signed_area_m2'],ratio,places=12)
        self.assertAlmostEqual(actual['signed_volume_m3']/base['signed_volume_m3'],ratio**2,places=12)
        fine=_project(r,.1,'refinement')
        pair=pair_controls(r,.1,.1,p,fine)
        self.assertEqual(pair['comparison_meshes'][0],pair['comparison_meshes'][1])
        np.testing.assert_array_equal(space(p).geometry.cell_nodes,space(_project(r,0.,'search')).geometry.cell_nodes)
        self.assertEqual(r,old)

    def test_strict_paths_units_active_laws_and_controls(self):
        r=expression_request();bad=[dict(r,geometry_kind='unknown'),dict(r,bindings=[]),dict(r,bindings=r['bindings']*2)]
        for expression in (c(.1),c(.1,'m'),op('log',X),op('mul',c(.1,'m'),op('log',X))):
            bad.append(dict(r,bindings=[dict(b,expression=expression) for b in r['bindings']]))
        for path in ('/case/solver/modes','/case/geometry/points_zr_m/01/1','/case/geometry/points_zr_m/99/1'):
            bad.append(dict(r,bindings=[dict(r['bindings'][0],path=path)]))
        bad.append(dict(r,bindings=[dict(r['bindings'][0],extra=True)]))
        curve=expression_request(True)
        bad.extend([dict(curve,refinement_scale=3),dict(curve,controls=dict(curve['controls'],comparison_meshes=[])),
                    dict(curve,bindings=[dict(path='/case/geometry/curves/1/start_rad',expression=c(.1,'m'))])])
        for request in bad:
            with self.subTest(request=request),self.assertRaises(ValueError):_request(request)
        recovery=dict(schema_version=6,tune_request=r,identity_recovery=dict(anchor_selection='latest_resolved_trial',controls=r['controls']))
        _request(recovery)
        self.assertEqual(_project(recovery,.04,'search').to_dict(),_project(r,.04,'search').to_dict())

    def test_real_fem_log_radius_target_replay_and_changed_expression_rejected(self):
        r=expression_request();r['bounds']=[-.2,.1]
        with tempfile.TemporaryDirectory() as tmp:
            result=execute_tune(r,Path(tmp)/'run')
            self.assertEqual(result['status'],'TUNED')
            self.assertLess(abs(result['decision']['value']-math.log(.093/.1)),2e-5)
            self.assertEqual(replay_tune(result),result)
            bad=deepcopy(result);bad['request']['bindings'][0]['expression']['args'][0]['constant']=.101
            with self.assertRaises(ValueError):replay_tune(bad)

    def test_interior_domain_failure_preserves_checkpoint_and_skips_fem(self):
        from superfish_ng.constants import C0
        from unittest.mock import patch
        r=expression_request();r.update(bounds=[0.,1.],target_hz=C0*2.404825557695773/(2*math.pi*.1045),frequency_tolerance_hz=1.)
        law=op('add',c(.1,'m'),op('add',op('mul',c(.001,'m'),X),op('div',c(.001,'m'),op('pow',op('sub',X,c(.5)),c(2)))))
        r['bindings']=[dict(b,expression=law) for b in r['bindings']]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);first=execute_tune(r,root/'first',max_new_trials=2)
            self.assertEqual(first['decision']['next_trial']['value'],.5)
            files={p:p.read_bytes() for p in (root/'first').rglob('*') if p.is_file()}
            with patch('superfish_ng.tuning.execute_project') as solve:
                with self.assertRaises(ValueError):execute_tune(r,root/'failed',checkpoint=first)
                solve.assert_not_called()
            self.assertEqual(files,{p:p.read_bytes() for p in files})
            failure=json.loads((root/'failed/failure-003.json').read_text())
            self.assertEqual(failure['status'],'FAILED');self.assertFalse((root/'failed/trial-003').exists())
            self.assertEqual(replay_tune(first),first)
