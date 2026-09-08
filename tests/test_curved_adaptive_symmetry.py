# SPDX-License-Identifier: Apache-2.0
"""Reflection invariants for curved adaptive surface regularity."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from superfish_ng import solve
from superfish_ng.symmetry import reflect_solution
from superfish_ng.curved_extrema import bound_surface_peaks
from superfish_ng.curved_adaptive_refinement import validate_request
from superfish_ng.adaptive_refinement import execute_adaptive_refinement, replay_adaptive_refinement
from test_curved_reflection import half_case
from test_curved_adaptive_refinement import request


class CurvedAdaptiveSymmetryTests(unittest.TestCase):
    def request(self, side='z_min', tag='electric_symmetry'):
        r=request();r['case']=half_case(side,tag).to_dict();return r

    def test_reflected_physical_peaks_agree_for_both_parities_and_ends(self):
        for side in ('z_min','z_max'):
            for tag in ('electric_symmetry','magnetic_symmetry'):
                with self.subTest(side=side,tag=tag):
                    case=validate_request(self.request(side,tag))
                    half=solve(case);full_case,full=reflect_solution(case,half)
                    self.assertEqual(set(full_case.curved_contour.edge_tags),{'axis','pec'})
                    a,b=bound_surface_peaks(half),bound_surface_peaks(full)
                    for quantity in ('electric_v_per_m','magnetic_a_per_m'):
                        for end in ('lower_bound','upper_bound'):
                            self.assertLess(abs(a[quantity][end]/b[quantity][end]-1),1e-10)
                    self.assertLess(abs(full.case.normalization_j/(2*case.normalization_j)-1),1e-12)

    def test_smooth_symmetry_request_executes_and_replays(self):
        with tempfile.TemporaryDirectory() as temporary:
            r=self.request();out=Path(temporary)/'run'
            result=execute_adaptive_refinement(r,out,max_new_levels=1)
            self.assertEqual(result['status'],'PAUSED')
            geometry=result['levels'][0]['surface']['geometry_diagnostic']
            self.assertEqual(geometry['status'],'SMOOTH_WITHIN_TOLERANCE')
            self.assertEqual(geometry['symmetry_boundary_tag'],'electric_symmetry')
            self.assertEqual(geometry['surface_domain'],'PEC wall of the original half-domain')
            self.assertEqual(replay_adaptive_refinement(result),result)

    def test_nonsmooth_mirrored_pole_is_rejected(self):
        r=self.request();bad=deepcopy(r)
        # A conical PEC wall is not orthogonal to the axis at its pole.
        bad['case']['geometry']['curves'][1]={'type':'line','start_zr_m':[.1,0.], 'end_zr_m':[0.,.08]}
        with self.assertRaisesRegex(ValueError,'verified smooth'):validate_request(bad)
