# SPDX-License-Identifier: Apache-2.0
import sys, unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.validate_meridional_overlap import mesh
from superfish_ng.hphi_mass_projection import hphi_mass_coupling, project_hphi_coefficients


def declared(n=1, holes=0, axis=True, seed=7, scale=1.):
    return mesh(n, holes, axis, ({(1,0):scale/32,(0,0):0. if axis else scale/32},
        {(0,1):scale/32}), seed)[0]


class HphiMassProjectionTests(unittest.TestCase):
    def test_original_polynomials_and_constant_circulation_are_preserved(self):
        for axis in (False, True):
            for holes in (0, 1, 2):
                for order in (1, 2):
                    a, b = declared(1, holes, axis), declared(2, holes, axis, 19)
                    coupling = hphi_mass_coupling(a, b, previous_order=order, current_order=order)
                    def values(points):
                        r, z = (points*32).T
                        return np.column_stack((np.ones(len(r)), 1+2*r-3*z+(r*r+r*z+2*z*z if order==2 else 0)))
                    original = values(coupling.previous_space.dof_points); before = original.copy()
                    projected = project_hphi_coefficients(a, b, original, previous_order=order, current_order=order)
                    np.testing.assert_allclose(projected.coefficients, values(coupling.current_space.dof_points), rtol=1e-11, atol=1e-11)
                    np.testing.assert_array_equal(original, before)
                    self.assertLess(max(projected.diagnostic['relative_mass_error']), 1e-11)
                    self.assertFalse(projected.coefficients.flags.writeable)
                    self.assertFalse(coupling.cross_mass.data.flags.writeable)
                    self.assertEqual(coupling.diagnostic['unknown'], 'u=Hphi/r' if axis else 'q=r*Hphi')

    def test_noncontained_space_loses_field_and_obeys_orthogonality(self):
        for axis in (False, True):
            a, b = declared(1, 1, axis), declared(1, 1, axis, 31)
            coupling = hphi_mass_coupling(a, b, previous_order=2, current_order=1)
            r,z = (coupling.previous_space.dof_points*32).T
            values = (1+r*r+z*z)[:,None]
            result = project_hphi_coefficients(a, b, values, previous_order=2, current_order=1)
            self.assertGreater(result.diagnostic['relative_mass_error'][0], 1e-3)
            np.testing.assert_allclose(coupling.current_mass @ result.coefficients,
                coupling.cross_mass.T @ values, rtol=1e-11, atol=1e-18)
            finer = project_hphi_coefficients(a, declared(2, 1, axis, 31), values, previous_order=2, current_order=1)
            self.assertLess(finer.diagnostic['relative_mass_error'][0], .3*result.diagnostic['relative_mass_error'][0])

    def test_arbitrary_coefficients_same_space_and_zero_columns(self):
        for axis in (False, True):
            a = declared(1, 2, axis)
            coupling = hphi_mass_coupling(a, a)
            values = np.random.default_rng(23).normal(size=(coupling.previous_mass.shape[0],3));values[:,2]=0.
            result = project_hphi_coefficients(a, a, values)
            np.testing.assert_allclose(result.coefficients, values, rtol=1e-11, atol=1e-11)
            self.assertEqual(result.diagnostic['relative_mass_error'][2], 0.)
            self.assertLess(max(result.diagnostic['relative_mass_error']), 1e-11)

    def test_incompatible_domains_unknowns_budgets_and_coefficients_rejected(self):
        a, b = declared(), declared(2)
        for bad in (declared(2, 1), declared(2, scale=2), declared(2, axis=False)):
            with self.assertRaises(ValueError): hphi_mass_coupling(a, bad)
        for key in ('previous_order','current_order','quadrature_order','max_candidate_tests','max_overlay_triangles','max_dofs'):
            with self.assertRaises(ValueError): hphi_mass_coupling(a, b, **{key:True})
        for controls in ({'max_dofs':1}, {'max_overlay_triangles':1}, {'max_candidate_tests':1}, {'previous_order':3}):
            with self.assertRaises(ValueError): hphi_mass_coupling(a, b, **controls)
        for values in ([1.,2.], [[float('nan')]], [[1j]], [[True]], np.zeros((1,0)), np.ones((1,1))):
            with self.assertRaises(ValueError): project_hphi_coefficients(a,b,values)
        coupling = hphi_mass_coupling(a,b)
        with self.assertRaises(ValueError):
            project_hphi_coefficients(a,b,np.full((coupling.previous_mass.shape[0],1),1e-200))


if __name__=='__main__':unittest.main()
