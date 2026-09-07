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
    def case(self):
        curved = CurvedContour((LineSegment((0,0),(.2,0)),EllipseArc((.1,0),(.1,.08),0,math.pi)),('axis','pec'),1e-14)
        return Case((),curved_contour=curved,curve_chord_tolerance_m=.002,
                    contour_mesh=ContourMeshControls(.03),modes=1,element_order=2)

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
