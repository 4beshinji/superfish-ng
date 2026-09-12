# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from scripts.electrostatic_reference import parallel_plate as axis_case
from scripts.planar_electrostatic_reference import parallel_plate as planar_case
from superfish_ng.electrostatic import solve_axisymmetric_electrostatic
from superfish_ng.planar_electrostatic import solve_planar_electrostatic


class StaticCoordinateTests(unittest.TestCase):
    def solutions(self):
        return (solve_axisymmetric_electrostatic(axis_case()[0]),solve_planar_electrostatic(planar_case()[0]))

    def test_mixed_python_boolean_coordinates_barycentrics_and_cell_ids_are_rejected(self):
        for solution in self.solutions():
            for points in ([[False,0.]],[[0.,False]],[['0',0.]],[[10**1000,0.]]):
                with self.assertRaises(ValueError):solution.probe_at(points)
            for cells,bary in (([0],[[False,.5,.5]]),([0],[[0.,True,0.]]),([0,True],[[.2,.3,.5],[.2,.3,.5]]),([0,10**1000],[[.2,.3,.5],[.2,.3,.5]]),([0.],[[.2,.3,.5]])):
                with self.assertRaises(ValueError):solution.fields_in_cells(cells,bary)

    def test_typed_numeric_coordinates_and_integer_cells_retain_original_values(self):
        for solution in self.solutions():
            first=solution.fields_in_cells([0,1],[[.2,.3,.5],[.2,.3,.5]])
            typed=solution.fields_in_cells(np.array([0,1],dtype=np.uint64),np.array([[.2,.3,.5],[.2,.3,.5]]))
            for key in first:np.testing.assert_array_equal(first[key],typed[key])
            original=solution.probe_at([[0.,0.]])
            typed=solution.probe_at(np.array([[0,0]],dtype=np.int64));self.assertEqual(original,typed)
