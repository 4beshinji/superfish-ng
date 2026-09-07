# SPDX-License-Identifier: Apache-2.0
"""Physical-domain tests for a finite hyperboloid of revolution."""
from dataclasses import replace
import math
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng import Case, solve
from superfish_ng.conics import LineSegment, HyperbolaArc
from superfish_ng.curved_contour import CurvedContour
from superfish_ng.mesh_controls import ContourMeshControls
from superfish_ng.mesh_input import mesh_to_dict
from superfish_ng.rf import quantities
from superfish_ng.symmetry import reflect_solution
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution


class HyperbolaCaseTests(unittest.TestCase):
    def test_cardinal_rotation_has_no_artificial_endpoint_gap(self):
        from superfish_ng.conics import rotation_cos_sin
        arc = HyperbolaArc((0,0),(.05,.08),-.5,0,rotation_rad=math.pi/2)
        self.assertEqual(arc.evaluate(1.)['points_zr_m'].tolist(),[0.,.05])
        self.assertEqual(rotation_cos_sin(math.pi/2),(0.,1.))
        for angle in (math.nextafter(math.pi/2,0),math.nextafter(math.pi/2,math.inf)):
            self.assertEqual(rotation_cos_sin(angle),(math.cos(angle),math.sin(angle)))
            self.assertNotEqual(rotation_cos_sin(angle)[0],0.)

    def test_hyperboloid_geometry_and_saved_fem(self):
        case = Case.load(Path(__file__).resolve().parents[1]/'examples/curved_hyperbola.json')
        a,b,h = .05,.08,.05
        exact_area = a*(h*math.sqrt(1+(h/b)**2)+b*math.asinh(h/b))
        exact_volume = 2*math.pi*a*a*(h+h**3/(3*b*b))
        self.assertAlmostEqual(case.curved_contour.area_m2/exact_area,1)
        self.assertAlmostEqual(case.curved_contour.volume_m3/exact_volume,1)
        errors = []
        for tolerance in (.0005,.000125,.00003125):
            refined = replace(case,contour=None,curve_chord_tolerance_m=tolerance)
            errors.append(refined.contour.volume_m3-exact_volume)
        # The graph r(z)=a sqrt(1+((z-h)/b)^2) is convex: chords lie outside.
        self.assertTrue(all(e>0 for e in errors))
        self.assertTrue(all(x>y for x,y in zip(errors,errors[1:])))
        solution = solve(case)
        with tempfile.TemporaryDirectory() as tmp:
            save_run(case,solution,Path(tmp)/'solution')
            loaded = read_solution(Path(tmp)/'solution')
            self.assertEqual(loaded.case.curved_contour,case.curved_contour)
            np.testing.assert_array_equal(loaded.u,solution.u)
            metadata = loaded.results['geometry_approximation']
            self.assertAlmostEqual(metadata['analytic_volume_m3']/exact_volume,1)
            self.assertGreater(metadata['volume_difference_m3'],0)

    def test_hyperboloid_scale_invariance(self):
        case = Case.load(Path(__file__).resolve().parents[1]/'examples/curved_hyperbola.json')
        raw = case.to_dict()
        factor = 3.
        for curve in raw['geometry']['curves']:
            for key in ('start_zr_m','end_zr_m','center_zr_m','semiaxes_m'):
                if key in curve:
                    curve[key] = [factor*v for v in curve[key]]
        for key in ('chord_tolerance_m','join_tolerance_m','minimum_gap_m'):
            raw['geometry'][key] *= factor
        raw['mesh']['contour_mesh']['max_edge_m'] *= factor
        scaled = Case.from_dict(raw)
        qa,qb = quantities(case,solve(case)),quantities(scaled,solve(scaled))
        self.assertAlmostEqual(qa['frequency_hz']/qb['frequency_hz'],factor,places=8)
        for key in ('r_over_q_accelerator_ohm','geometry_factor_ohm','transit_time_factor_abs'):
            self.assertAlmostEqual(qa[key]/qb[key],1,places=8)
        self.assertAlmostEqual(scaled.curved_contour.volume_m3/case.curved_contour.volume_m3,factor**3)

    def test_hyperbola_reflection_both_planes_and_parities(self):
        a,b,h = .05,.08,.05
        end_radius = a*math.sqrt(1+(h/b)**2)
        parameter = math.asinh(h/b)
        for side in (0,1):
            for parity in ('electric_symmetry','magnetic_symmetry'):
                center = side*h
                radius_left = end_radius if side else a
                radius_right = a if side else end_radius
                arc = HyperbolaArc((center,0),(a,b),0 if side else -parameter,
                                   parameter if side else 0,rotation_rad=math.pi/2)
                curves = (LineSegment((0,0),(h,0)),
                          LineSegment((h,0),(h,radius_right)),arc,
                          LineSegment((0,radius_left),(0,0)))
                tags = ('axis',parity if side else 'pec','pec','pec' if side else parity)
                half = Case((),curved_contour=CurvedContour(curves,tags,1e-14),
                            curve_chord_tolerance_m=.0005,contour_mesh=ContourMeshControls(.02),
                            element_order=2,modes=1)
                sol = solve(half)
                full, mirrored = reflect_solution(half,sol)
                self.assertAlmostEqual(full.curved_contour.volume_m3/half.curved_contour.volume_m3,2)
                self.assertAlmostEqual(full.curved_contour.area_m2/half.curved_contour.area_m2,2)
                self.assertAlmostEqual(quantities(full,mirrored)['stored_energy_j']/
                                       quantities(half,sol)['stored_energy_j'],2)
                independent = solve(replace(full,modes=4),mesh_data=mesh_to_dict(mirrored.mesh))
                index = int(np.argmin(abs(independent.frequencies_hz-mirrored.frequencies_hz[0])))
                actual,reference = quantities(full,mirrored),quantities(full,independent,index)
                for key in ('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm'):
                    self.assertAlmostEqual(actual[key]/reference[key],1,places=8)
                with tempfile.TemporaryDirectory() as tmp:
                    save_run(full,mirrored,Path(tmp)/'full')
                    self.assertEqual(read_solution(Path(tmp)/'full').case.curved_contour,full.curved_contour)
