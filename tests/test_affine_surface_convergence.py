# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from superfish_ng import Case
from superfish_ng.contour import Contour
from superfish_ng.affine_corners import classify_affine_corners
from superfish_ng.adaptive_refinement import execute_adaptive_refinement
from superfish_ng.affine_surface_convergence import assess_affine_surface_convergence,save_affine_surface_convergence,read_affine_surface_convergence,replay_affine_surface_convergence


class AffineCornerTests(unittest.TestCase):
    def test_exact_convex_reentrant_and_subdivided_polygon_turns(self):
        for scale in (2.**-100,1.,2.**100):
            cylinder=Case(((0.,scale),(2*scale,scale)))
            report=classify_affine_corners(cylinder)
            self.assertEqual(report['status'],'NO_REENTRANT_CORNERS')
            self.assertEqual(sum(j['classification']=='convex_pec_corner' for j in report['joins']),2)
            points=((0,0),(2,0),(2,1),(1,1),(1,.5),(0,.5))
            case=Case((),contour=Contour(tuple((z*scale,r*scale) for z,r in points),('axis',*['pec']*5)))
            result=classify_affine_corners(case);self.assertEqual(result['status'],'SINGULAR_GEOMETRY')
            self.assertEqual(sum(j['classification']=='reentrant_pec_corner' for j in result['joins']),1)
        split=Case((),contour=Contour(((0,0),(1,0),(2,0),(2,1),(1,1),(0,1)),('axis','axis',*['pec']*4)))
        result=classify_affine_corners(split);self.assertEqual(result['status'],'NO_REENTRANT_CORNERS')
        self.assertIn('axis_subdivision',[j['classification'] for j in result['joins']])
        self.assertIn('straight_pec_join',[j['classification'] for j in result['joins']])

    def test_axis_symmetry_and_chord_geometry_are_not_silently_accepted(self):
        cone=Case((),contour=Contour(((0,0),(2,0),(1,1)),('axis','pec','pec')))
        self.assertEqual(classify_affine_corners(cone)['status'],'UNVERIFIED_GEOMETRY')
        for tag in ('electric_symmetry','magnetic_symmetry'):
            case=Case(((0.,1.),(2.,1.)),z_min=tag)
            self.assertEqual(classify_affine_corners(case)['status'],'NO_REENTRANT_CORNERS')
            case=replace(case,profile=((0.,1.),(2.,1.5)))
            self.assertEqual(classify_affine_corners(case)['status'],'UNVERIFIED_GEOMETRY')
        curved=Case.load('examples/curved_ellipse.json')
        self.assertEqual(classify_affine_corners(replace(curved,geometry_order=1))['status'],'UNVERIFIED_GEOMETRY')
        with self.assertRaises(ValueError):classify_affine_corners(replace(curved,geometry_order=2))


class AffineSurfaceConvergenceTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.request=json.loads(Path('examples/adaptive_refinement/pillbox_confirmed.json').read_text())
    def test_confirmation_pending_and_tracked_second_mode_saved_replay(self):
        self.request['mode_id']='second'
        first=execute_adaptive_refinement(self.request,self.root/'first',max_new_levels=4)
        pending=assess_affine_surface_convergence(first,'second')
        self.assertEqual(pending['status'],'CONFIRMATION_PENDING')
        final=execute_adaptive_refinement(self.request,self.root/'final',checkpoint=first)
        saved=save_affine_surface_convergence(final,'second',self.root/'assessment.json')
        self.assertEqual(saved['status'],'TARGETS_MET');self.assertTrue(saved['two_uniform_steps_present'])
        self.assertTrue(all(r['mode_index']==1 for r in saved['rows']))
        self.assertEqual(saved['checkpoint'],final);self.assertEqual(final['surface_status'],'UNASSESSED')
        self.assertEqual(read_affine_surface_convergence(self.root/'assessment.json'),saved)
        self.assertEqual(set(saved['limits']),set(saved['rows'][0]['intervals']))
        from superfish_ng.cli import main
        source=self.root/'checkpoint.json';source.write_text(json.dumps(final))
        self.assertEqual(main(['assess-affine-surface-convergence',str(source),'--mode-id','second','--out',str(self.root/'cli.json')]),0)
        self.assertEqual(main(['replay-affine-surface-convergence',str(self.root/'cli.json')]),0)
        self.assertEqual(read_affine_surface_convergence(self.root/'cli.json'),saved)

    def test_short_unverified_and_tampered_sources_are_rejected(self):
        first=execute_adaptive_refinement(self.request,self.root/'short',max_new_levels=1)
        with self.assertRaisesRegex(ValueError,'three'):assess_affine_surface_convergence(first,'fundamental')
        final=execute_adaptive_refinement(self.request,self.root/'final',checkpoint=first)
        result=save_affine_surface_convergence(final,'fundamental',self.root/'assessment.json')
        for field in ('status','limits','rows','geometry_diagnostic'):
            changed=deepcopy(result);changed[field]=None
            with self.assertRaisesRegex(ValueError,'replay'):replay_affine_surface_convergence(changed)
        with self.assertRaisesRegex(ValueError,'individual'):assess_affine_surface_convergence(final,'missing')
        source=Path(final['level_runs'][0])/'case.json';source.write_text(source.read_text()+'\n')
        with self.assertRaises(ValueError):read_affine_surface_convergence(self.root/'assessment.json')

    def test_reentrant_native_series_cannot_pass_surface_gate(self):
        case=Case.from_dict(self.request['case']);case=replace(case,profile=((0.,.1),(.1,.075),(.2,.1)))
        self.request['case']=case.to_dict();self.request['minimum_angle_deg']=1.
        self.request['controls']['minimum_overlap']=.8
        checkpoint=execute_adaptive_refinement(self.request,self.root/'neck',max_new_levels=3)
        report=assess_affine_surface_convergence(checkpoint,'fundamental')
        self.assertEqual(report['status'],'SINGULAR_GEOMETRY')
        self.assertEqual(len(report['rows']),3)
        self.assertIsNone(report['physical_error_bound'])
