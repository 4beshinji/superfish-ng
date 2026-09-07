# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import json
import math
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng import Case,solve
from superfish_ng.conics import LineSegment,EllipseArc
from superfish_ng.curved_contour import CurvedContour
from superfish_ng.mesh_controls import ContourMeshControls
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution


class CurvedCaseTests(unittest.TestCase):
    def test_curved_reflection_both_ends_and_field_parities(self):
        from dataclasses import replace
        from superfish_ng.symmetry import reflect_solution
        from superfish_ng.mesh_input import mesh_to_dict
        from superfish_ng.rf import quantities
        for side in (0,1):
            for tag in ('electric_symmetry','magnetic_symmetry'):
                if side:
                    curves=(LineSegment((0,0),(.1,0)),LineSegment((.1,0),(.1,.08)),
                            EllipseArc((.1,0),(.1,.08),math.pi/2,math.pi/2))
                    tags=('axis',tag,'pec')
                else:
                    curves=(LineSegment((0,0),(.1,0)),EllipseArc((0,0),(.1,.08),0,math.pi/2),
                            LineSegment((0,.08),(0,0)))
                    tags=('axis','pec',tag)
                half=Case((),curved_contour=CurvedContour(curves,tags,1e-14),curve_chord_tolerance_m=.001,
                          contour_mesh=ContourMeshControls(.025),modes=1,element_order=2)
                sol=solve(half)
                full,reflected=reflect_solution(half,sol)
                self.assertAlmostEqual(full.curved_contour.area_m2/half.curved_contour.area_m2,2)
                self.assertAlmostEqual(full.curved_contour.volume_m3/half.curved_contour.volume_m3,2)
                hq,fq=quantities(half,sol),quantities(full,reflected)
                self.assertAlmostEqual(fq['stored_energy_j']/hq['stored_energy_j'],2)
                direct_case=replace(full,modes=4)
                direct=solve(direct_case,mesh_data=mesh_to_dict(reflected.mesh))
                mode=int(np.argmin(abs(direct.frequencies_hz-reflected.frequencies_hz[0])))
                dq=quantities(direct_case,direct,mode)
                for key in ('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm'):
                    self.assertAlmostEqual(fq[key]/dq[key],1,places=8)
                with tempfile.TemporaryDirectory() as tmp:
                    save_run(full,reflected,Path(tmp)/'run')
                    self.assertEqual(read_solution(Path(tmp)/'run').case.curved_contour,full.curved_contour)

    def case(self):
        curved = CurvedContour((LineSegment((0,0),(.2,0)),EllipseArc((.1,0),(.1,.08),0,math.pi)),('axis','pec'),1e-14)
        return Case((),curved_contour=curved,curve_chord_tolerance_m=.002,
                    contour_mesh=ContourMeshControls(.03),modes=1,element_order=2)

    def test_preview_preserves_curve_and_reports_geometric_error(self):
        from superfish_ng.gui import preview_document
        from superfish_ng.project import Project
        case = self.case()
        preview = preview_document(Project.from_dict(case.to_dict()))
        self.assertEqual(preview["project"]["case"]["geometry"], case.to_dict()["geometry"])
        self.assertTrue(preview["outline_closed"])
        self.assertEqual(preview["outline_zr_m"], [list(p) for p in case.contour.vertices_zr_m])
        error = preview["geometry_approximation"]
        exact_volume = 4 * math.pi * .1 * .08**2 / 3
        self.assertAlmostEqual(error["analytic_volume_m3"], exact_volume)
        self.assertAlmostEqual(error["volume_difference_m3"], case.contour.volume_m3 - exact_volume)
        self.assertLess(error["volume_difference_m3"], 0)

    def test_original_curves_and_chords_survive_save_reload(self):
        case = self.case()
        raw = case.to_dict()
        self.assertEqual(raw['geometry']['type'],'curved_contour')
        self.assertEqual(Case.from_dict(json.loads(json.dumps(raw))),case)
        solution = solve(case)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'solution'
            save_run(case,solution,out)
            loaded = read_solution(out)
            self.assertEqual(loaded.case.curved_contour,case.curved_contour)
            self.assertEqual(loaded.case.contour,case.contour)
            report = json.loads((out/'results.json').read_text())['geometry_approximation']
            self.assertEqual(report['geometry_order'],1)
            self.assertLess(report['area_difference_m2'],0)
            self.assertAlmostEqual(report['analytic_area_m2'],math.pi*.1*.08/2)
            self.assertAlmostEqual(report['analytic_volume_m3'],4*math.pi*.1*.08**2/3)
            self.assertLess(report['volume_difference_m3'],0)
            self.assertEqual(report['chord_volume_m3'],case.contour.volume_m3)
            np.testing.assert_array_equal(solve(loaded.case).u,solution.u)

    def test_unknown_curve_fields_and_missing_tolerance_fail(self):
        original = self.case().to_dict()
        for mode in ('unknown','missing','null','curve_unknown','curve_type'):
            raw = deepcopy(original)
            if mode=='unknown':raw['geometry']['unexpected']=1
            if mode=='missing':del raw['geometry']['chord_tolerance_m']
            if mode=='null':raw['geometry']['chord_tolerance_m']=None
            if mode=='curve_unknown':raw['geometry']['curves'][0]['radius_m']=1
            if mode=='curve_type':raw['geometry']['curves'][0]['type']='spline'
            with self.subTest(mode=mode),self.assertRaises(ValueError):Case.from_dict(raw)
