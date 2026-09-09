# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import json
import math
from pathlib import Path
import tempfile
import unittest
from superfish_ng.constants import C0
from superfish_ng.tuning import _request,_project,execute_tune,replay_tune
from test_coupled_tuning import coupled_request


def polynomial_request(scale=1.):
    request=coupled_request('1');request['schema_version']=3
    request['parameter']='radius_factor_squared'
    request['bounds']=[.8,1.1]
    request['bindings']=[dict(path=b['path'],coefficients=[0.,0.,.1*scale]) for b in request['bindings']]
    request['target_hz']/=scale
    for point in request['project']['case']['geometry']['points_zr_m']:
        point[:]=[x*scale for x in point]
    request['frequency_tolerance_hz']/=scale;request['mesh_frequency_tolerance_hz']/=scale
    return request


class PolynomialTuningTests(unittest.TestCase):
    def test_power_law_coordinates_units_order_and_linear_compatibility(self):
        r=polynomial_request();_request(r)
        for x in (.8,.93,1.1):
            p=_project(r,x,'search')
            self.assertAlmostEqual(p.case.profile[0][1],.1*x*x)
            self.assertEqual(p.case.profile[0][1],p.case.profile[1][1])
        r['bindings'].reverse();self.assertEqual(_project(r,.93,'search').to_dict(),_project(polynomial_request(),.93,'search').to_dict())
        old=coupled_request();new=deepcopy(old);new['schema_version']=3
        new['bindings']=[dict(path=b['path'],coefficients=[b['offset_m'],b['multiplier']]) for b in old['bindings']]
        for x in (.08,.1,.11):self.assertEqual(_project(old,x,'search').to_dict(),_project(new,x,'search').to_dict())

    def test_actual_fem_power_law_target_resume_and_source_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);r=polynomial_request()
            first=execute_tune(r,root/'first',max_new_trials=2)
            final=execute_tune(r,root/'resumed',checkpoint=first)
            self.assertEqual(final['status'],'TUNED')
            self.assertLess(abs(final['decision']['value']/math.sqrt(.93)-1),2e-5)
            self.assertEqual(replay_tune(final),final)
            self.assertEqual(first['trial_sources_sha256'],final['trial_sources_sha256'][:2])
            for trial in final['trials']:
                radius=.1*trial['value']**2
                exact=C0*2.404825557695773/(2*math.pi*radius)
                self.assertLess(abs(trial['frequency_hz']/exact-1),1e-5)
            changed=deepcopy(first);changed['request']['bindings'][0]['coefficients'][2]=.101
            with self.assertRaises(ValueError):replay_tune(changed)

    def test_strict_polynomials_and_invalid_interior_preserve_prior_checkpoints(self):
        r=polynomial_request()
        for coefficients in ([],None,'x*x',[True],[float('inf')],[10**400],[.1],[.1,0,0],[0,0,1.79e308]):
            changed=deepcopy(r)
            for b in changed['bindings']:b['coefficients']=coefficients
            with self.subTest(coefficients=coefficients),self.assertRaises(ValueError):_request(changed)
        changed=deepcopy(r);changed['bindings'][0]['multiplier']=1
        with self.assertRaises(ValueError):_request(changed)
        # Positive radii at x=0,1, but negative at the first bisection point.
        # Endpoint frequencies bracket the target; invalid geometry is not a solve.
        r['bounds']=[0.,1.]
        for b in r['bindings']:b['coefficients']=[.08,-.37,.4]
        _request(r)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);first=execute_tune(r,root/'first',max_new_trials=2)
            self.assertEqual(first['decision']['next_trial']['value'],.5)
            with self.assertRaises(ValueError):execute_tune(r,root/'invalid',checkpoint=first)
            self.assertEqual(replay_tune(first),first)
            self.assertFalse((root/'invalid/checkpoint-003.json').exists())
