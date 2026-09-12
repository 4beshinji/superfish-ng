# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import numpy as np
from superfish_ng.constants import C0, EPS0
from superfish_ng.jobs import JobManager
from superfish_ng.planar import solve_planar
from superfish_ng.planar_polygon import PlanarPolygonCase
from superfish_ng.planar_saved import save_planar_run
from superfish_ng.planar_tracking import PlanarTrackingRequest, track_planar_modes
from superfish_ng.planar_tracking_affine_remesh import PolygonAffineRemeshMapping
from superfish_ng.planar_tracking_exact_mapping import (
    PolygonExactAffineRemeshMapping, polygon_exact_affine_remesh_overlay)
from superfish_ng.planar_tracking_fields import _electric_grams
from superfish_ng.planar_tracking_history import PlanarTrackingHistoryRequest
from superfish_ng.planar_tracking_history_saved import execute_planar_history, read_planar_history
from superfish_ng.planar_tracking_jobs import execute_planar_tracking, read_planar_tracking
from test_planar_tracking_exact_affine import rectangle


def reflected_pair(pol='tm', order=2, grids=(6, 8), width=.5, height=.25):
    mapping = PolygonExactAffineRemeshMapping([[-1., 0.], [0., 1.]])
    legacy = PolygonAffineRemeshMapping(mapping.linear_xy)
    a = solve_planar(PlanarPolygonCase(rectangle(grids[0], grids[0], width, height), pol, order, 2))
    b = solve_planar(PlanarPolygonCase(legacy.transform_mesh(
        rectangle(grids[1], grids[1], width, height, True)), pol, order, 2))
    return a, b, mapping


class ExactAffineMappingTests(unittest.TestCase):
    def test_strict_versioned_declaration_and_unresolved_field_transform(self):
        mapping = PolygonExactAffineRemeshMapping([[1., .25], [0., 2.]], (.125, -.25))
        request = PlanarTrackingRequest(1, 1, ['fundamental'], mapping=mapping)
        self.assertEqual(request.to_dict()['tracking_version'], 7)
        self.assertEqual(PlanarTrackingRequest.from_dict(request.to_dict()), request)
        for version in (1, 2, 3, 4, 5, 6, True, 7., 8):
            with self.subTest(version=version), self.assertRaises(ValueError):
                PlanarTrackingRequest.from_dict(dict(request.to_dict(), tracking_version=version))
        for change in ({'name':'polygon_affine_remesh'}, {'inverse':1}, {'max_candidate_tests':True},
                       {'linear_xy':[[1.,1.],[1.,1.]]}, {'linear_xy':[[True,0.],[0.,1.]]},
                       {'translation_xy_m':[float('inf'),0.]}, {'extra':1}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                PolygonExactAffineRemeshMapping.from_dict(dict(mapping.to_dict(), **change))
        with self.assertRaisesRegex(ValueError, 'binary64'):
            PolygonExactAffineRemeshMapping([[2.**-1074,0.],[0.,1.]], inverse=True)
        old = replace(request, mapping=PolygonAffineRemeshMapping(mapping.linear_xy))
        self.assertEqual(old.to_dict()['tracking_version'], 6)
        with self.assertRaisesRegex(ValueError, 'polygon_exact_affine_remesh'):
            PlanarTrackingRequest.from_dict(dict(old.to_dict(), tracking_version=7))

    def test_inverse_adjugate_uses_exact_determinant_before_rounding(self):
        delta = 2.**-27
        a, d = 1.+delta, 1.-delta
        self.assertEqual(a*d-1., 0.)  # Floating products lose the nonzero determinant.
        mapping = PolygonExactAffineRemeshMapping([[a,1.],[1.,d]], inverse=True)
        det = -Fraction(1, 2**54)
        self.assertEqual(mapping.exact_determinant, det)
        expected = np.array([[float(Fraction(v)/det) for v in row] for row in mapping.linear_xy])
        np.testing.assert_array_equal(mapping.current_to_previous_linear, expected)
        self.assertFalse(mapping.current_to_previous_linear.flags.writeable)
        self.assertFalse(mapping.orientation_preserving)
        third = PolygonExactAffineRemeshMapping([[3.,0.],[0.,1.]], inverse=True)
        np.testing.assert_array_equal(third.current_to_previous_linear, [[1.,0.],[0.,1/3]])

    def test_forward_and_inverse_original_fields_current_area_and_scalar_law(self):
        mapping = PolygonExactAffineRemeshMapping([[-1.,.25],[0.,2.]], (.125,-.25))
        legacy = PolygonAffineRemeshMapping(mapping.linear_xy, mapping.translation_xy_m)
        for pol in ('te','tm'):
            for orders in ((1,2),(2,1),(2,2)):
                a = solve_planar(PlanarPolygonCase(rectangle(3,3),pol,orders[0],2))
                b = solve_planar(PlanarPolygonCase(legacy.transform_mesh(rectangle(4,4,flipped=True)),pol,orders[1],2))
                def scalar(xy):
                    x,y=xy.T
                    return np.column_stack((1+x+.25*y, .25-x+y))
                a = replace(a, coefficients=scalar(a.space.dof_points_xy_m))
                xy = (b.space.dof_points_xy_m-np.array(mapping.translation_xy_m))@np.linalg.inv(legacy.matrix).T
                b = replace(b, coefficients=scalar(xy), frequencies_hz=a.frequencies_hz)
                for left,right,direction in ((a,b,mapping),(b,a,replace(mapping,inverse=True))):
                    overlay = polygon_exact_affine_remesh_overlay(left.case.mesh,right.case.mesh,direction)
                    self.assertAlmostEqual(sum(overlay.reference_determinants)/2,right.case.mesh.area_m2,places=13)
                    grams = _electric_grams(left,right,overlay,5,
                        current_to_previous_rotation=direction.current_to_previous_linear)
                    scale = np.sqrt(np.diag(grams[0]))
                    for gram in grams[1:]:
                        np.testing.assert_allclose(gram/scale[:,None]/scale[None,:],
                            grams[0]/scale[:,None]/scale[None,:],rtol=3e-12,atol=3e-12)

    def test_independent_boundary_tracking_and_energy_measure_in_both_directions(self):
        for pol in ('te','tm'):
            for order in (1,2):
                a,b,mapping=reflected_pair(pol,order,(12,16))
                self.assertNotEqual(len(a.case.mesh.boundary_edges),len(b.case.mesh.boundary_edges))
                frequency=C0/2*np.hypot(2.,4. if pol=='tm' else 0.)
                for solution in (a,b):
                    self.assertLess(abs(solution.frequencies_hz[0]/frequency-1.),.009)
                for left,right,direction in ((a,b,mapping),(b,a,replace(mapping,inverse=True))):
                    result=track_planar_modes(left,right,PlanarTrackingRequest(1,1,['fundamental'],mapping=direction))
                    self.assertEqual(result['result_version'],7)
                    self.assertEqual(result['status'],'PASS')
                    self.assertEqual(result['current_mode_ids'],['fundamental'])
                    physical=result['physical_mapping']
                    self.assertEqual(physical['reference_measure'],'current physical xy area in m^2 in both declaration directions')
                    self.assertIn('original cell indices',physical['orientation'])
                    # Integral |E|^2 = 2 U'/epsilon0 for each actual eigenfield.
                    expected=2*left.case.normalization_j_per_m/EPS0
                    self.assertAlmostEqual(physical['electric_gram_previous'][0][0]/expected,1.,places=10)

    def test_nonbinary_inverse_real_fem_and_anisotropic_rank_crossing(self):
        mapping=PolygonExactAffineRemeshMapping([[3.,0.],[0.,1.]], inverse=True)
        a=solve_planar(PlanarPolygonCase(rectangle(12,12,1.5,.25),'te',2,4))
        b=solve_planar(PlanarPolygonCase(rectangle(16,16,.5,.25,True),'te',2,4))
        result=track_planar_modes(a,b,PlanarTrackingRequest(1,1,['fundamental'],mapping=mapping))
        self.assertEqual(result['status'],'PASS')
        self.assertEqual(result['physical_mapping']['effective_determinant_exact'],'1/3')
        expected=2*a.case.normalization_j_per_m/(3*EPS0)
        self.assertAlmostEqual(result['physical_mapping']['electric_gram_previous'][0][0]/expected,1.,places=10)
        mapping=PolygonExactAffineRemeshMapping([[.75,0.],[0.,1.5]])
        a=solve_planar(PlanarPolygonCase(rectangle(16,16,.375,.25),'te',2,4))
        b=solve_planar(PlanarPolygonCase(rectangle(20,20,.28125,.375,True),'te',2,4))
        result=track_planar_modes(a,b,PlanarTrackingRequest(2,2,['x','y'],mapping=mapping))
        self.assertEqual(result['status'],'PASS')
        self.assertEqual(result['current_mode_ids'],['y','x'])

    def test_degenerate_identity_set_and_guard_refusal(self):
        for pol,count in (('te',2),('tm',3)):
            mapping=PolygonExactAffineRemeshMapping([[-1.,0.],[0.,1.]])
            legacy=PolygonAffineRemeshMapping(mapping.linear_xy)
            a=solve_planar(PlanarPolygonCase(rectangle(6,6),pol,2,count+1))
            b=solve_planar(PlanarPolygonCase(legacy.transform_mesh(rectangle(8,8,flipped=True)),pol,2,count+1))
            ids=[f'mode-{i}' for i in range(count)]
            result=track_planar_modes(a,b,PlanarTrackingRequest(count,count,ids,mapping=mapping))
            self.assertEqual(result['status'],'PASS')
            self.assertTrue(any(match['kind']=='SUBSPACE' for match in result['matches']))
            cut=track_planar_modes(a,b,PlanarTrackingRequest(count-1,count-1,ids[:-1],mapping=mapping))
            self.assertEqual(cut['status'],'UNVERIFIED')
            self.assertTrue(any(cut['guard_overlap']))
            self.assertEqual(cut['current_mode_ids'],[None]*(count-1))

    def test_portable_history_and_rehashed_mapping_result_tamper_rejected(self):
        a,b,mapping=reflected_pair()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,solution in (('a',a),('b',b)):
                save_planar_run(solution.case,solution,root/name)
            for name,left,right,direction in (('ab','a','b',mapping),('ba','b','a',replace(mapping,inverse=True))):
                result=execute_planar_tracking(root/left,root/right,
                    PlanarTrackingRequest(1,1,['fundamental'],mapping=direction),root/name)
                self.assertEqual(result['status'],'PASS')
            history=execute_planar_history([root/'ab',root/'ba'],PlanarTrackingHistoryRequest(2),root/'history')
            self.assertEqual(history['status'],'PASS')
            self.assertEqual(history['current_mode_ids'],['fundamental'])
            shutil.rmtree(root/'a');shutil.rmtree(root/'b')
            self.assertEqual(history,read_planar_history(root/'history'))
            target=root/'ab'/'tracking-results.json'
            original=target.read_bytes()
            for change in ('measure','transport','determinant','version'):
                data=json.loads(original)
                if change=='measure':data['physical_mapping']['reference_measure']='previous area'
                elif change=='transport':data['physical_mapping']['current_to_previous_linear'][1][1]=1.
                elif change=='determinant':data['physical_mapping']['effective_determinant_exact']='1'
                else:data['result_version']=6
                target.write_text(json.dumps(data))
                manifest=root/'ab'/'manifest.json';document=json.loads(manifest.read_text())
                document['files']['tracking-results.json']=hashlib.sha256(target.read_bytes()).hexdigest()
                manifest.write_text(json.dumps(document))
                with self.subTest(change=change),self.assertRaisesRegex(ValueError,'full native'):
                    read_planar_tracking(root/'ab')

    def test_preflight_rejects_wrong_map_and_budgets_without_output(self):
        a,b,mapping=reflected_pair()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,solution in (('a',a),('b',b)):
                save_planar_run(solution.case,solution,root/name)
            request=PlanarTrackingRequest(1,1,['fundamental'],mapping=mapping)
            invalid=(replace(request,mapping=replace(mapping,translation_xy_m=(.125,0.))),
                     replace(request,mapping=replace(mapping,max_candidate_tests=1)),
                     replace(request,controls=replace(request.controls,max_overlay_triangles=1)),
                     replace(request,controls=replace(request.controls,max_refined_triangles=1)))
            for item in invalid:
                with self.subTest(request=item),self.assertRaises(ValueError):
                    execute_planar_tracking(root/'a',root/'b',item,root/'invalid')
                self.assertFalse((root/'invalid').exists())

    def test_actual_worker_cancel_restart_import_and_cli_replay(self):
        a,b,mapping=reflected_pair()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,solution in (('a',a),('b',b)):
                save_planar_run(solution.case,solution,root/name)
            request=PlanarTrackingRequest(1,1,['fundamental'],mapping=mapping)
            manager=JobManager(root/'workspace')
            try:
                cancelled=manager.start_planar_tracking(root/'a',root/'b',request)
                deadline=time.monotonic()+30
                while manager.status(cancelled)['status']=='queued' and time.monotonic()<deadline:time.sleep(.01)
                self.assertEqual(manager.status(cancelled)['status'],'running')
                self.assertEqual(manager.cancel(cancelled)['status'],'cancelled')
                identifier=manager.start_planar_tracking(root/'a',root/'b',request)
                self.assertEqual(manager.processes[identifier].wait(timeout=60),0)
                directory=manager.directory(identifier)
                imported=manager.import_planar_result(directory/'current')
                manager.close();manager=JobManager(root/'workspace')
                self.assertEqual(manager.status(identifier,verify=True)['status'],'complete')
                self.assertEqual(manager.status(imported,verify=True)['status'],'complete')
                saved=read_planar_tracking(directory)
                request.save(root/'request.json')
                for args in (['execute-planar-tracking',str(root/'a'),str(root/'b'),str(root/'request.json'),'--out',str(root/'cli')],
                             ['replay-planar-tracking',str(root/'cli')]):
                    run=subprocess.run([sys.executable,'-m','superfish_ng',*args],capture_output=True,text=True,timeout=60)
                    self.assertEqual(run.returncode,0,run.stderr)
                    self.assertEqual(json.loads(run.stdout),saved)
            finally:manager.close()


if __name__=='__main__':unittest.main()
