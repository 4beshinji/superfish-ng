# SPDX-License-Identifier: Apache-2.0
from fractions import Fraction as F
import unittest
import numpy as np
from superfish_ng.planar_affine_shape import PlanarAffineShapeLaw
from superfish_ng.planar_curved import PlanarCurvedCase
from superfish_ng.planar_project import PlanarProject
from superfish_ng.planar_curved_shape import PlanarCurvedAffineShapeLaw
from test_planar_curved_comparison import analytic_patch


def law():
    return PlanarCurvedAffineShapeLaw(PlanarAffineShapeLaw([[[1,.5],[0]],[[0],[1,.25]]],[[0],[0]],[0,1]))


class PlanarCurvedTuningTrialTests(unittest.TestCase):
    def test_two_level_charts_retain_original_quadratic_polynomial_everywhere(self):
        from superfish_ng.planar_curved_tuning_trials import generate_planar_curved_trial
        base,_=analytic_patch()
        original=PlanarProject(PlanarCurvedCase(base,modes=2,normalization_j_per_m=3.7))
        trial=generate_planar_curved_trial(original,law(),1.,refinement_levels=2)
        self.assertEqual(len(trial.project.case.domain.cell_nodes),16)
        self.assertEqual(trial.reference_project.to_dict(),law().project(original,1.).to_dict())
        self.assertEqual(trial.diagnostic['geometry']['base_reference_areas'],[[1,2]])
        self.assertTrue(trial.diagnostic['geometry']['exact_native_restrictions'])
        for cell,row in zip(trial.project.case.domain.cell_nodes,trial.native_cells):
            vertices=[tuple(F(*v) for v in point) for point in row['reference_vertices']]
            refs=vertices+[tuple((vertices[i][axis]+vertices[j][axis])/2 for axis in (0,1)) for i,j in ((0,1),(1,2),(2,0))]
            expected=[[float(F(3,2)*(-F(1,4)+x/8)),float(F(5,4)*(y+x*(1-x-y)/4)/8)] for x,y in refs]
            np.testing.assert_array_equal(trial.project.case.domain.points_xy_m[cell],expected)
        self.assertEqual(trial.project.case.normalization_j_per_m,3.7)
        self.assertEqual(original.to_dict(),PlanarProject(PlanarCurvedCase(base,modes=2,normalization_j_per_m=3.7)).to_dict())

    def test_real_two_phase_original_fields_energy_and_reference_pair(self):
        from superfish_ng.planar_curved_tuning_trials import generate_planar_curved_trial,planar_curved_trial_comparison
        from superfish_ng.planar_curved_solver import solve_planar_curved,planar_curved_quantities
        from superfish_ng.planar_curved_field_overlap import planar_curved_field_grams
        from test_planar_curved import curved_ellipse
        for polarization in ('te','tm'):
            original=PlanarProject(PlanarCurvedCase(curved_ellipse(8),polarization,modes=2,quadrature_order=16))
            search=generate_planar_curved_trial(original,law(),0.)
            final=generate_planar_curved_trial(original,law(),1.,refinement_levels=2)
            domain=planar_curved_trial_comparison(search,final)
            sources=[solve_planar_curved(trial.project.case) for trial in (search,final)]
            before=[(s.coefficients.tobytes(),s.frequencies_hz.tobytes(),[planar_curved_quantities(s,i) for i in range(s.case.modes)]) for s in sources]
            result=planar_curved_field_grams(*sources,domain,previous_cells=search.native_cells,current_cells=final.native_cells)
            self.assertLess(result.diagnostic['maximum_source_gram_difference'],1e-10)
            self.assertEqual(result.diagnostic['geometry']['base_reference_areas'],[[1,2]]*8)
            self.assertEqual(before,[(s.coefficients.tobytes(),s.frequencies_hz.tobytes(),[planar_curved_quantities(s,i) for i in range(s.case.modes)]) for s in sources])
            cells=final.native_cells;cells[0]['base_cell']=999
            self.assertEqual(final.native_cells[0]['base_cell'],0)
            self.assertLessEqual(max(final.diagnostic['geometry']['maximum_original_map_relative_bounds']),512*np.finfo(float).eps)

    def test_complete_final_budgets_preflight_and_pair_source_binding(self):
        from dataclasses import replace
        from unittest.mock import patch
        from superfish_ng.planar_curved_tuning_trials import generate_planar_curved_trial,planar_curved_trial_comparison
        from superfish_ng.planar_curved_comparison import PlanarCurvedComparisonBudgetExceeded
        from test_planar_curved import curved_ellipse
        original=PlanarProject(PlanarCurvedCase(curved_ellipse(8),modes=2))
        for options in ({'max_triangles':127},{'max_dofs':288},{'max_pair_tests':1087}):
            with patch('superfish_ng.planar_curved_tuning_trials.refine_planar_curved_domain',side_effect=AssertionError('partial refinement')):
                with self.assertRaises(PlanarCurvedComparisonBudgetExceeded) as caught:
                    generate_planar_curved_trial(original,law(),0.,refinement_levels=2,**options)
                self.assertEqual(caught.exception.status,'UNVERIFIED')
        for options in ({'refinement_levels':True},{'refinement_levels':9},{'max_triangles':True},{'max_dofs':0}):
            with self.assertRaises(ValueError):generate_planar_curved_trial(original,law(),0.,**options)
        a=generate_planar_curved_trial(original,law(),0.)
        b=generate_planar_curved_trial(replace(original,case=replace(original.case,normalization_j_per_m=3.7)),law(),0.)
        with self.assertRaisesRegex(ValueError,'original Project'):
            planar_curved_trial_comparison(a,b)

    def test_composed_original_chart_rejects_corrupted_later_level_geometry(self):
        from dataclasses import replace
        from unittest.mock import patch
        from superfish_ng.planar_curved_tuning_trials import generate_planar_curved_trial
        from superfish_ng.planar_curved_refinement import refine_planar_curved_domain
        from superfish_ng.planar_curved import PlanarCurvedDomain
        base,_=analytic_patch()
        project=PlanarProject(PlanarCurvedCase(base,modes=2))
        calls=0
        def corrupt(domain,**kwargs):
            nonlocal calls
            result=refine_planar_curved_domain(domain,**kwargs);calls+=1
            if calls==2:
                geometry=result.domain
                interior=sorted(set(geometry.cell_nodes.ravel())-set(geometry.boundary_nodes.ravel()))
                points=geometry.points_xy_m.copy();points[interior[0],0]+=2**-36
                changed=PlanarCurvedDomain(points,geometry.cell_nodes,geometry.boundary_nodes)
                # A claimed local zero error cannot bless changed original-map
                # coefficients in the accumulated final native geometry.
                result=replace(result,domain=changed,maximum_relative_coordinate_bound=0.)
            return result
        with patch('superfish_ng.planar_curved_tuning_trials.refine_planar_curved_domain',side_effect=corrupt):
            with self.assertRaisesRegex(ValueError,'roundoff'):
                generate_planar_curved_trial(project,law(),1.,refinement_levels=2)
        self.assertEqual(calls,2)


if __name__=='__main__':unittest.main()
