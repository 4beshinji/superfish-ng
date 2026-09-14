# SPDX-License-Identifier: Apache-2.0
"""GUI deformation preserves native boundary geometry and input ownership."""
from copy import deepcopy
from dataclasses import replace
import json
import math
import unittest
from unittest.mock import patch
import numpy as np
from superfish_ng.curved_project_transform import transform_curved_project
from superfish_ng.project import Project
from test_curved_harmonic_deformation import deformation_fixture, folded_deformation_fixture, space


class GUICurvedDeformationTests(unittest.TestCase):
    def test_preview_native_boundary_and_independent_green_ratios_without_solving(self):
        from superfish_ng.gui_curved_deformation import deformation_response
        source,geometry=deformation_fixture();before=deepcopy(source.to_dict())
        with patch('superfish_ng.curved_solution.solve_curved',side_effect=AssertionError('preview cannot solve')):
            result=deformation_response(dict(document=json.dumps(before),geometry_document=json.dumps(geometry),
                rf_coordinates='fixed',minimum_corner_angle_deg=1.))
        self.assertEqual(source.to_dict(),before)
        target=Project.from_dict(result['target']['project'])
        self.assertEqual(target.case.curved_refinement_steps,source.case.curved_refinement_steps)
        self.assertEqual(json.loads(result['serialized']),target.to_dict())
        moments=[]
        for name,project in (('source',source),('target',target)):
            native=space(project).geometry;packet=result[name]['native_boundary']
            np.testing.assert_array_equal(packet['edges_rz_m'],native.points_rz_m[native.boundary_nodes])
            self.assertEqual(packet['cell_count'],len(native.cell_nodes))
            # Independent polynomial integration of each displayed P2 boundary.
            t,w=np.polynomial.legendre.leggauss(5);t=(t+1)/2;w=w/2
            a,b,m=np.asarray(packet['edges_rz_m']).transpose(1,0,2)
            linear=4*m-3*a-b;quadratic=2*(a+b-2*m)
            p=a[:,None,:]+linear[:,None,:]*t[None,:,None]+quadratic[:,None,:]*t[None,:,None]**2
            d=linear[:,None,:]+2*quadratic[:,None,:]*t[None,:,None]
            r,z=p.transpose(2,0,1);dr,dz=d.transpose(2,0,1)
            moments.append([np.sum((r*dz-z*dr)*w)/2,math.pi*np.sum(r*r*dz*w)])
        np.testing.assert_allclose(np.asarray(moments[1])/moments[0],[1.125,1.125**2],rtol=2e-13)

    def test_rf_axis_fraction_and_exact_project_roundtrip(self):
        from superfish_ng.gui_curved_deformation import deformation_response
        source,_=deformation_fixture()
        source=replace(source,case=replace(source.case,active_length_m=.15,voltage_interval_m=(.02,.18),phase_origin_m=.03))
        reference=transform_curved_project(source,dict(radial_scale=1.125,axial_scale=1.25,axial_shear=0.),rf_coordinates='axial')
        result=deformation_response(dict(document=source.to_dict(),geometry_document=reference.case.to_dict()['geometry'],
            rf_coordinates='axis_fraction',minimum_corner_angle_deg=1.))
        target=Project.from_dict(json.loads(result['serialized']))
        self.assertEqual(target.case.acceleration_parameters,reference.case.acceleration_parameters)
        self.assertEqual(target.mesh_data['triangles'],source.mesh_data['triangles'])
        self.assertEqual(target.case.normalization_j,source.case.normalization_j)

    def test_strict_request_unfrozen_history_and_actual_fold_refused(self):
        from superfish_ng.gui_curved_deformation import deformation_response
        source,geometry=deformation_fixture()
        request=dict(document=source.to_dict(),geometry_document=geometry,rf_coordinates='fixed',minimum_corner_angle_deg=1.)
        for field in request:
            missing=deepcopy(request);del missing[field]
            with self.subTest(missing=field),self.assertRaises(ValueError):deformation_response(missing)
        invalid=[dict(request,unexpected=1),dict(request,geometry_document='{"type":"curved_contour","type":"curved_contour"}'),
                 dict(request,rf_coordinates='axial'),dict(request,minimum_corner_angle_deg=True)]
        unfrozen=deepcopy(request);del unfrozen['document']['case']['mesh']['curved_refinement_steps'][0]['split_pattern'];invalid.append(unfrozen)
        for item in invalid:
            with self.subTest(item=item),self.assertRaises(ValueError):deformation_response(item)
        folded,geometry=folded_deformation_fixture()
        with self.assertRaisesRegex(ValueError,'Jacobian'):
            deformation_response(dict(request,document=folded.to_dict(),geometry_document=geometry))
