# SPDX-License-Identifier: Apache-2.0
import copy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from superfish_ng.axis_hphi import AxisHphiCase, AxisAccelerationPath
from superfish_ng.coaxial import CoaxialCase
from superfish_ng.constants import C0
from superfish_ng.hphi_mesh import HphiMeshCase
from superfish_ng.hphi_tuning import validate_hphi_tune, trial_hphi_project, run_hphi_tune, assess_hphi_tune
from superfish_ng.hphi_project import HphiProject
from superfish_ng.hphi_shape_tuning import shape_comparison_mapping
from test_hphi_tuning import request
from test_meridional_overlap import fixture


def coaxial_request():
    result = request(CoaxialCase(.0625,.125,.5,nr=2,nz=8,modes=3,quadrature_order=12))
    result.update(schema_version=2,parameter='length_m',mapping=dict(kind='coaxial_dimensions'),
        bounds=[.5,.75],target_hz=C0/(2*.625))
    return result


def mesh_request(axis=False):
    mesh = fixture(2,axis=axis)
    if axis:
        case = AxisHphiCase(mesh,modes=3,acceleration=AxisAccelerationPath(0.,.09375,1.,0.))
    else:
        case = HphiMeshCase(mesh,modes=3,quadrature_order=12)
    result = request(case)
    # Explicit axial stretch plus radial hole motion, not a uniform scale.
    displacement = np.zeros_like(mesh.points_rz_m)
    displacement[:,1] = mesh.points_rz_m[:,1]/8
    origin = 0 if axis else 1/32
    displacement[:,0] = np.interp(mesh.points_rz_m[:,0],origin+np.arange(4)/32,[0,1/2048,1/2048,0])
    result.update(schema_version=2,parameter='deformation',mapping=dict(kind='general_piecewise_affine',
        reference_value=1.,displacements_rz_m=displacement.tolist(),acceleration_policy='transport_on_axis'),bounds=[1.,2.])
    return result


class HphiShapeTuneRequestTests(unittest.TestCase):
    def test_strict_shape_law_and_all_coaxial_dimensions(self):
        q = coaxial_request()
        for parameter,bounds in (('length_m',[.5,.75]),('inner_radius_m',[.03125,.0625]),('outer_radius_m',[.125,.1875])):
            raw = copy.deepcopy(q);raw.update(parameter=parameter,bounds=bounds)
            project = trial_hphi_project(raw,sum(bounds)/2,'search')
            self.assertEqual(getattr(project.case,parameter),sum(bounds)/2)
            self.assertEqual(project.case.normalization_j,1.)
        for key,value in (('schema_version',True),('parameter','stored_energy_j'),('mapping',{'kind':'uniform_scale'}),('bounds',[.5,False])):
            bad = copy.deepcopy(q);bad[key] = value
            with self.assertRaises(ValueError):validate_hphi_tune(bad)
        for axis in (False,True):
            raw = mesh_request(axis);validate_hphi_tune(raw)
            for key,value in (('reference_value',True),('displacements_rz_m',[[0.,0.]]),('acceleration_policy','fixed'),('extra',0)):
                bad = copy.deepcopy(raw);bad['mapping'][key] = value
                with self.assertRaises(ValueError):validate_hphi_tune(bad)
        bad = mesh_request(True);bad['mapping']['displacements_rz_m'][0][0] = 1e-4
        with self.assertRaisesRegex(ValueError,'axis'):validate_hphi_tune(bad)

    def test_original_project_determinism_volume_and_axis_transport(self):
        for axis in (False,True):
            q = mesh_request(axis);original = copy.deepcopy(q)
            first = trial_hphi_project(q,1.,'search')
            middle = trial_hphi_project(q,1.5,'search')
            last = trial_hphi_project(q,2.,'search')
            self.assertEqual(q,original)
            self.assertEqual(middle.to_dict(),trial_hphi_project(q,1.5,'search').to_dict())
            mapping = shape_comparison_mapping(q,first,last)
            self.assertGreater(np.ptp(np.linalg.det(mapping.jacobians)),0.)
            self.assertAlmostEqual(last.case.mesh.area_m2/first.case.mesh.area_m2,1.125,delta=1e-13)
            def rectangle_volume(p):
                return np.pi*(p[:,0].max()**2-p[:,0].min()**2)*(p[:,1].max()-p[:,1].min())
            mesh = last.case.mesh
            expected = rectangle_volume(mesh.outer_rz_m)-sum(rectangle_volume(h) for h in mesh.holes_rz_m)
            self.assertAlmostEqual(mesh.volume_m3/expected,1.,delta=1e-13)
            refined = trial_hphi_project(q,1.5,'refinement')
            self.assertAlmostEqual(refined.case.mesh.volume_m3/middle.case.mesh.volume_m3,1.,delta=1e-13)
            if axis:
                self.assertEqual(last.case.acceleration.z_end_m,.09375*1.125)
                self.assertEqual(last.case.acceleration.beta,1.)
                bad = copy.deepcopy(q);bad['project']['case']['acceleration']['phase_origin_m'] = -.01
                with self.assertRaisesRegex(ValueError,'axis interval'):validate_hphi_tune(bad)

    def test_original_boundary_vertex_bend_is_explicit_and_has_correct_volume(self):
        q = mesh_request()
        mesh = HphiProject.from_dict(q['project']).case.mesh
        nodes = np.flatnonzero((mesh.points_rz_m[:,1] == 0.) & (mesh.points_rz_m[:,0] == .078125))
        self.assertEqual(len(nodes),1)
        displacement = np.zeros_like(mesh.points_rz_m)
        displacement[nodes[0],1] = -1/1024
        q['mapping']['displacements_rz_m'] = displacement.tolist()
        result = trial_hphi_project(q,2.,'search').case.mesh
        area_increment = (1/1024)*(1/32)/2
        self.assertAlmostEqual(result.area_m2-mesh.area_m2,area_increment,delta=1e-15)
        self.assertAlmostEqual(result.volume_m3-mesh.volume_m3,2*np.pi*.078125*area_increment,delta=1e-15)
        self.assertIn([.078125,-1/1024],result.outer_rz_m.tolist())
        self.assertNotIn([.078125,-1/1024],mesh.outer_rz_m.tolist())
        refined = trial_hphi_project(q,2.,'refinement').case.mesh
        self.assertAlmostEqual(refined.volume_m3,result.volume_m3,delta=1e-15)

    def test_fold_and_budget_rejected_before_solver_or_output(self):
        from superfish_ng.hphi_tuning import execute_hphi_tune
        for mutation in ('fold','budget'):
            q = mesh_request()
            if mutation == 'fold':q['mapping']['displacements_rz_m'][0] = [1.,1.]
            else:q['max_triangles'] = 1
            with tempfile.TemporaryDirectory() as tmp, patch('superfish_ng.hphi_tuning_saved.solve_hphi',side_effect=AssertionError('must not solve')):
                out = Path(tmp)/'output'
                with self.assertRaises(ValueError):execute_hphi_tune(q,out)
                self.assertFalse(out.exists())


class HphiShapeTuneExecutionTests(unittest.TestCase):
    def test_actual_inner_and_outer_radius_bisection_against_bessel_root(self):
        from scripts.validate_coaxial import radial_roots
        for parameter,bounds in (('inner_radius_m',[.0625,.078125]),('outer_radius_m',[.125,.140625])):
            case = CoaxialCase(.0625,.125,.03125,nr=8,nz=2,modes=3,quadrature_order=12)
            q = coaxial_request();q['project'] = HphiProject(case).to_dict()
            q.update(parameter=parameter,bounds=bounds)
            target_case = replace(case,**{parameter:sum(bounds)/2})
            q['target_hz'] = C0*radial_roots(target_case.inner_radius_m,target_case.outer_radius_m,1)[0]/(2*np.pi)
            run = run_hphi_tune(q)
            self.assertEqual(run.report['status'],'TUNED',run.report['decision'])
            self.assertEqual(run.report['trials'][-1]['value'],sum(bounds)/2)
            for trial,solution in zip(run.report['trials'],run.solutions):
                exact = C0*radial_roots(solution.case.inner_radius_m,solution.case.outer_radius_m,1)[0]/(2*np.pi)
                self.assertAlmostEqual(trial['frequency_hz']/exact,1.,delta=4e-5)
                self.assertTrue(trial['tracking']['individual_ids_complete'])

    def test_actual_coaxial_length_bisection_tem_and_unverified_stop(self):
        q = coaxial_request();run = run_hphi_tune(q)
        self.assertEqual(run.report['status'],'TUNED',run.report['decision'])
        self.assertEqual(run.report['parameter_unit'],'m')
        self.assertEqual(run.report['scope'],'coaxial_dimensions')
        self.assertEqual([t['value'] for t in run.report['trials']],[.5,.75,.625,.625])
        for trial,solution in zip(run.report['trials'],run.solutions):
            self.assertAlmostEqual(trial['frequency_hz']/(C0/(2*solution.case.length_m)),1.,delta=2e-5)
            self.assertTrue(trial['tracking']['individual_ids_complete'])
            self.assertEqual(trial['tracking']['physical_mapping']['previous_frequency_scale'],1.)
        bad = copy.deepcopy(q);bad['controls']['relative_cluster_gap'] = .9
        refused = assess_hphi_tune(bad,run.solutions[:1])
        self.assertEqual(refused.report['status'],'UNVERIFIED')
        self.assertIsNone(refused.report['trials'][0]['frequency_hz'])
        with self.assertRaisesRegex(ValueError,'terminal'):assess_hphi_tune(bad,run.solutions[:2])
