# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import json
import math
from pathlib import Path
import tempfile
import unittest
from superfish_ng.constants import C0
from superfish_ng.project import Project
from superfish_ng import Case
from superfish_ng.tuning import _request,_project,execute_tune,read_tune,replay_tune


def coupled_request(unit='m'):
    r=json.loads(Path('examples/tuning/pillbox_length.json').read_text())
    r.update(schema_version=2,parameter='radius',parameter_unit=unit,
        bounds=[.08,.11] if unit=='m' else [.8,1.1],parameter_tolerance=1e-9 if unit=='m' else 1e-8,
        target_hz=C0*2.404825557695773/(2*math.pi*.093),initial_ids=['TM010'],mode_id='TM010')
    r['project']=Project(Case(((0.,.1),(.08,.1)),nr=12,nz=16,modes=1,element_order=2)).to_dict()
    r['bindings']=[dict(path=f'/case/geometry/points_zr_m/{i}/1',multiplier=1. if unit=='m' else .1,offset_m=0.) for i in (0,1)]
    return r


class CoupledTuningTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)

    def test_linked_radius_is_a_cylinder_and_matches_analytic_target(self):
        request=coupled_request();_request(request)
        for radius in (.08,.11):self.assertEqual(_project(request,radius,'search').case.profile,((0.,radius),(.08,radius)))
        result=execute_tune(request,self.root/'run')
        self.assertEqual(result['status'],'TUNED');self.assertLess(abs(result['decision']['value']/.093-1),2e-5)
        self.assertEqual(replay_tune(result),result)
        case=Project.load(Path(result['trial_runs'][-1])/'project.json').case
        self.assertEqual(case.profile[0][1],case.profile[1][1])
        self.assertEqual(case.nr,24);self.assertEqual(case.nz,32)

    def test_atomic_update_is_order_invariant_when_intermediate_shape_is_invalid(self):
        r=coupled_request('1');r['project']=Project(Case(((0.,.1),(.04,.1),(.08,.1)),modes=1)).to_dict()
        r['bounds']=[1.,2.];r['parameter']='axial_scale'
        r['bindings']=[dict(path=f'/case/geometry/points_zr_m/{i}/0',multiplier=z,offset_m=0.) for i,z in [(1,.04),(2,.08)]]
        _request(r);p=_project(r,2.,'search');self.assertEqual(p.case.profile,((0.,.1),(.08,.1),(.16,.1)))
        r['bindings'].reverse();self.assertEqual(_project(r,2.,'search').to_dict(),p.to_dict())

    def test_dimensionless_and_length_variables_preserve_same_geometry(self):
        a=coupled_request();b=coupled_request('1')
        for x,y in [(.08,.8),(.1,1.),(.11,1.1)]:
            pa=_project(a,x,'search').case.profile;pb=_project(b,y,'search').case.profile
            for first,second in zip(pa,pb):self.assertAlmostEqual(first[1],second[1],places=15)
        b['bindings']=[dict(v,multiplier=-.1,offset_m=.2) for v in b['bindings']]
        _request(b);self.assertAlmostEqual(_project(b,1.1,'search').case.profile[0][1],.09)

    def test_strict_bindings_units_and_representable_variation(self):
        r=coupled_request()
        changes=[dict(parameter_unit='mm'),dict(parameter=' '),dict(bindings=[]),
            dict(bindings=[r['bindings'][0]]*2),dict(bindings=[dict(r['bindings'][0],path='/case/solver/modes')]),
            dict(bindings=[dict(r['bindings'][0],path='/case/geometry/points_zr_m/01/1')]),
            dict(bindings=[dict(r['bindings'][0],multiplier=True)]),dict(bindings=[dict(r['bindings'][0],multiplier=10**400)]),
            dict(bindings=[dict(r['bindings'][0],extra=1)]),dict(bindings=[dict(r['bindings'][0],offset_m=float('inf'))]),
            dict(bindings=[dict(v,multiplier=0.) for v in r['bindings']]),
            dict(bindings=[dict(v,multiplier=1e-320,offset_m=.1) for v in r['bindings']]),
            dict(bindings=[dict(v,multiplier=1e308,offset_m=1.79e308) for v in r['bindings']]),
            dict(bindings=[dict(r['bindings'][0],path='/case/geometry/points_zr_m/3/1')])]
        for change in changes:
            with self.subTest(change=change):
                with self.assertRaises(ValueError):execute_tune(dict(r,**change),self.root/'invalid')
                self.assertFalse((self.root/'invalid').exists())

    def test_changed_binding_cannot_resume_a_verified_checkpoint(self):
        r=coupled_request();first=execute_tune(r,self.root/'first',max_new_trials=2)
        saved=read_tune(self.root/'first/checkpoint-002.json')
        changed=deepcopy(r);changed['bindings'][0]['multiplier']=1.01;changed['bindings'][1]['multiplier']=1.01
        with self.assertRaisesRegex(ValueError,'request differs'):execute_tune(changed,self.root/'changed',checkpoint=saved)
        changed=deepcopy(saved);changed['request']['bindings'][0]['multiplier']=1.01
        with self.assertRaises(ValueError):replay_tune(changed)
        final=execute_tune(r,self.root/'resumed',checkpoint=saved)
        self.assertEqual(final['status'],'TUNED');self.assertEqual(final['trial_sources_sha256'][:2],first['trial_sources_sha256'])

    def test_cli_and_v1_compatibility(self):
        from superfish_ng.cli import main
        r=coupled_request();p=self.root/'request.json';p.write_text(json.dumps(r))
        self.assertEqual(main(['tune',str(p),'--out',str(self.root/'cli'),'--max-new-trials','1']),0)
        self.assertEqual(main(['replay-tune',str(self.root/'cli/checkpoint-001.json')]),0)
        old=json.loads(Path('examples/tuning/pillbox_length.json').read_text());_request(old)
        p1=_project(old,.08,'search');self.assertEqual(p1.case.length,.08)
        with self.assertRaises(ValueError):_request(dict(old,bindings=r['bindings']))
