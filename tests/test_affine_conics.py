# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from superfish_ng.conics import LineSegment,EllipseArc,HyperbolaArc
from superfish_ng.affine_conics import transform_curve


class AffineConicTests(unittest.TestCase):
    def test_fraction_tangent_curvature_and_area_transform(self):
        curves=[LineSegment((.1,.2),(.4,.3)),EllipseArc((.2,.3),(.1,.06),.4,2.1,.7),
                EllipseArc((.2,.3),(.1,.1),-.4,-2.1,-.3)]
        curves += [HyperbolaArc((.2,.3),(.1,.06),-.8,.6,branch,.7) for branch in (-1,1)]
        for curve in curves:
            for a,b,c in ((1.2,.35,.8),(.8,-.2,1.3),(2.,0.,2.)):
                with self.subTest(curve=curve,a=a,b=b,c=c):
                    matrix=np.array([[c,b],[0,a]]);det=a*c
                    new=transform_curve(curve,dict(radial_scale=a,axial_shear=b,axial_scale=c))
                    before=curve.evaluate(np.linspace(0,1,19));after=new.evaluate(np.linspace(0,1,19))
                    np.testing.assert_allclose(after['points_zr_m'],before['points_zr_m']@matrix.T,rtol=2e-13,atol=2e-14)
                    tangent=before['tangent_zr']@matrix.T;norm=np.linalg.norm(tangent,axis=1)
                    np.testing.assert_allclose(after['tangent_zr'],tangent/norm[:,None],atol=2e-13)
                    np.testing.assert_allclose(after['curvature_per_m'],before['curvature_per_m']*det/norm**3,rtol=2e-12,atol=2e-13)
                    self.assertAlmostEqual(new.signed_line_area_m2,det*curve.signed_line_area_m2,places=13)
                    inverse=dict(radial_scale=1/a,axial_scale=1/c,axial_shear=-b/(a*c))
                    restored=transform_curve(new,inverse)
                    np.testing.assert_allclose(restored.evaluate(np.linspace(0,1,19))['points_zr_m'],before['points_zr_m'],atol=3e-14)

    def test_identity_and_strict_unsupported_map(self):
        curve=EllipseArc((.2,.3),(.1,.06),.4,2.1,.7)
        identity=dict(radial_scale=1.,axial_scale=1.,axial_shear=0.)
        self.assertIs(transform_curve(curve,identity),curve)
        for change in (dict(radial_scale=0),dict(axial_scale=-1),dict(axial_shear=True),dict(extra=1)):
            with self.assertRaises(ValueError):transform_curve(curve,dict(identity,**change))
        with self.assertRaises(ValueError):transform_curve(object(),identity)
        with self.assertRaisesRegex(ValueError,'UNVERIFIED'):
            transform_curve(curve,dict(radial_scale=1e-14,axial_scale=1.,axial_shear=0.))

    def test_native_quadratic_mesh_similarity_and_tracking(self):
        from dataclasses import replace
        from copy import deepcopy
        from superfish_ng import Case,solve
        from superfish_ng.affine_remesh_tracking import track_affine_remesh_modes
        from superfish_ng.rf import quantities
        raw=Case.load('examples/curved_ellipse.json').to_dict()
        raw['mesh']['geometry_order']=2
        raw['mesh']['contour_mesh'].update(max_edge_m=.08,min_angle_deg=5.)
        raw['geometry']['chord_tolerance_m']=.008
        case=Case.from_dict(raw);old=solve(case)
        mapping=dict(radial_scale=2.,axial_scale=2.,axial_shear=0.)
        contour=replace(case.curved_contour,curves=tuple(transform_curve(c,mapping) for c in case.curved_contour.curves),
                        join_tolerance_m=case.curved_contour.join_tolerance_m*2)
        new_case=replace(case,curved_contour=contour,contour=None,curve_chord_tolerance_m=case.curve_chord_tolerance_m*2)
        mesh=deepcopy(old.source_mesh_data);mesh['points']=(np.array(mesh['points'])*2).tolist()
        new=solve(new_case,mesh_data=mesh)
        report=track_affine_remesh_modes(old,new,['A'],mapping='affine_remesh',affine_map=mapping,sample_order=5,
            minimum_overlap=.98,minimum_assignment_margin=.05,relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)
        self.assertEqual(report['status'],'PASS')
        self.assertLess(abs(new.frequencies_hz[0]*2/old.frequencies_hz[0]-1),1e-11)
        first=quantities(case,old);second=quantities(new_case,new)
        for key in ('r_over_q_accelerator_ohm','geometry_factor_ohm'):
            self.assertLess(abs(second[key]/first[key]-1),1e-10)
