# SPDX-License-Identifier: Apache-2.0
"""Noncylindrical TE tuning keeps Maxwell similarity and native checkpoints."""
from dataclasses import replace
from pathlib import Path
import tempfile,unittest
from superfish_ng import Case,solve
from superfish_ng.model import Model
from superfish_ng.project import Project
from superfish_ng.tuning import execute_tune,replay_tune,_project
from superfish_ng.te_saved import read_te_run
from superfish_ng.te import te_quantities
from test_te_tuning import te_request


def profile_request(end='pec',reflected=False):
    case=Case(((0.,.07),(.04,.09),(.1,.08)),nr=32,nz=48,modes=1,
              element_order=2,model=Model(polarization='te'),z_max=end)
    r=te_request(end,reflected)
    r.update(schema_version=2,project=Project(case,reflect_full=reflected).to_dict(),
             parameter='scale',parameter_unit='1',bounds=[.9,1.1],
             target_hz=float(solve(case).frequencies_hz[0]),frequency_tolerance_hz=1e4,mesh_frequency_tolerance_hz=1e5)
    r.pop('path',None)
    r['bindings']=[dict(path=f'/case/geometry/points_zr_m/{i}/{j}',multiplier=v,offset_m=0.)
                   for i,point in enumerate(case.profile) for j,v in enumerate(point) if v]
    r['controls']['mapping']='normalized_profile'
    return r


class TEProfileTuningTests(unittest.TestCase):
    def test_nonconstant_profile_scale_law_restart_and_refinement(self):
        for end,reflected in [('pec',False),('magnetic_symmetry',False),('electric_symmetry',True)]:
            with self.subTest(end=end,reflected=reflected),tempfile.TemporaryDirectory() as tmp:
                r=profile_request(end,reflected)
                first=execute_tune(r,Path(tmp)/'first',max_new_trials=2)
                self.assertEqual(first['status'],'PAUSED')
                final=execute_tune(r,Path(tmp)/'rest',checkpoint=first)
                self.assertEqual(final['status'],'TUNED');self.assertEqual(replay_tune(final),final)
                self.assertEqual(first['trial_sources_sha256'],final['trial_sources_sha256'][:2])
                for t,path in zip(final['trials'],final['trial_runs']):
                    if t['phase']!='refinement':
                        self.assertLess(abs(t['frequency_hz']*t['value']/r['target_hz']-1),1e-10)
                    s=read_te_run(Path(path)/'solution');self.assertIsNone(te_quantities(s)['r_over_q_circuit_ohm'])
                    if t['tracking']:
                        m=t['tracking']['tracking']['physical_mapping'];self.assertEqual(m['name'],'normalized_profile')
                        self.assertEqual(m['field_multiplier'],'R(z)/Rmax')
                self.assertAlmostEqual(final['decision']['value'],1.,places=5)

    def test_local_radius_expression_changes_shape_and_replays(self):
        from test_expression_tuning import c,op,X
        r=profile_request();r.update(schema_version=7,geometry_kind='profile',parameter='x',bounds=[-.03,.03])
        r['bindings']=[dict(path='/case/geometry/points_zr_m/1/1',expression=op('mul',c(.09,'m'),op('exp',X)))]
        pilot=_project(r,0.,'search');r['target_hz']=float(solve(pilot.case).frequencies_hz[0])
        with tempfile.TemporaryDirectory() as tmp:
            result=execute_tune(r,Path(tmp)/'run')
            self.assertEqual(result['status'],'TUNED');self.assertEqual(replay_tune(result),result)
            self.assertAlmostEqual(result['decision']['value'],0.,places=5)
            cases=[read_te_run(Path(path)/'solution').case for path in result['trial_runs']]
            self.assertNotEqual(cases[0].profile[1][1],cases[1].profile[1][1])
            self.assertEqual(cases[0].profile[0],cases[1].profile[0])
