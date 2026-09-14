# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import unittest
from unittest.mock import patch
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

    def test_large_mesh_preserves_native_numbering_and_quadratic_geometry(self):
        from superfish_ng.gui_curved_mesh import curved_mesh_document
        case=half_case('z_min','electric_symmetry',level=4)
        original=case.to_dict()
        expected=case_curved_space(case,make_mesh(case))
        # Each uniform step has four children per parent; a display budget must
        # not select a coarser history just to make the view fit.
        base=half_case('z_min','electric_symmetry')
        self.assertEqual(len(expected.geometry.cell_nodes),len(make_mesh(base).triangles)*4**4)
        self.assertGreater(len(expected.geometry.cell_nodes),5000)
        with patch('superfish_ng.curved_solution.solve_curved',side_effect=AssertionError('view must not solve')):
            document=curved_mesh_document(Project(case))
        np.testing.assert_array_equal(document['points_rz_m'],expected.geometry.points_rz_m)
        np.testing.assert_array_equal(document['cell_nodes'],expected.geometry.cell_nodes)
        self.assertEqual(document['case'],original)
        self.assertEqual(case.to_dict(),original)

    def test_large_view_keeps_the_original_case_budget_and_external_mesh(self):
        from superfish_ng.gui_curved_mesh import curved_mesh_document
        from superfish_ng.mesh_input import mesh_to_dict
        case=half_case('z_min','electric_symmetry',level=1)
        mesh_data=mesh_to_dict(make_mesh(case))
        direct=curved_mesh_document(Project(case))
        external=curved_mesh_document(Project(case,mesh_data=mesh_data))
        self.assertEqual(external,direct)
        limited=replace(case,curved_refinement_levels=4,
                        contour_mesh=replace(case.contour_mesh,max_triangles=5000))
        with self.assertRaisesRegex(ValueError,'max_triangles=5000'):
            curved_mesh_document(Project(limited))
        for invalid in (True,0,1.5):
            with self.assertRaises(ValueError):curved_mesh_document(Project(case),maximum_cells=invalid)
