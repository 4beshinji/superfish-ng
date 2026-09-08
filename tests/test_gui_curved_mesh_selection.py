# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import unittest
import numpy as np
from superfish_ng.project import Project
from superfish_ng.curved_refinement_steps import CurvedRefinementStep as Step
from superfish_ng.curved_space import case_curved_space
from superfish_ng.mesh import make_mesh
from test_curved_reflection import half_case


class CurvedMeshSelectionTests(unittest.TestCase):
    def test_displayed_ids_and_quadratic_nodes_match_the_calculation_space(self):
        from superfish_ng.gui_curved_mesh import curved_mesh_document
        case=replace(half_case('z_min','electric_symmetry'),
                     curved_refinement_steps=(Step('marked',(0,),5.),Step('uniform')))
        expected=case_curved_space(case,make_mesh(case))
        result=curved_mesh_document(Project(case))
        np.testing.assert_array_equal(result['points_rz_m'],expected.geometry.points_rz_m)
        np.testing.assert_array_equal(result['cell_nodes'],expected.geometry.cell_nodes)
        self.assertEqual(result['case'],case.to_dict())
        self.assertEqual(result['cell_index_origin'],0)

    def test_unsupported_geometry_and_display_budget_are_explicit(self):
        from superfish_ng.gui_curved_mesh import curved_mesh_document
        from superfish_ng import Case
        with self.assertRaisesRegex(ValueError,'geometry_order=2'):
            curved_mesh_document(Project(Case(((0.,.1),(.2,.1)))))
        case=half_case('z_min','electric_symmetry')
        with self.assertRaises(ValueError):curved_mesh_document(Project(case),maximum_cells=3)
        self.assertEqual(case.curved_refinement_steps,())
