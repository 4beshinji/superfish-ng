# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import math
import unittest
import numpy as np
from scipy.integrate import quad
from superfish_ng.constants import EPS0, MU0, TAU
from superfish_ng.planar import PlanarCase, solve_planar, planar_quantities
from superfish_ng.planar_curved import PlanarCurvedCase, PlanarCurvedDomain
from superfish_ng.planar_curved_solver import (solve_planar_curved, restore_planar_curved_solution,
    planar_curved_quantities, PlanarCurvedFieldSampler)
from superfish_ng.planar_curved_location import PlanarCurvedLocator
from test_planar_curved import patch, curved_ellipse, quadratic_nodes


def straight_case(polarization='te', modes=1):
    vertices = [[0, 0], [.02, 0], [.02, .011], [0, .011]]
    points, cells, boundary = quadratic_nodes(vertices, [[0,1,2], [0,2,3]], [0,1,2,3])
    return PlanarCurvedCase(PlanarCurvedDomain(points, cells, boundary), polarization, modes=modes)


class PlanarCurvedSolverTests(unittest.TestCase):
    def test_strict_reference_fields_and_peak_phase_signs(self):
        for polarization in ('te', 'tm'):
            solution = solve_planar_curved(straight_case(polarization))
            # Manufactured linear scalar tests the first signed Maxwell law,
            # not the complete Helmholtz eigenfunction or its second curl law.
            points = solution.space.points_xy_m
            scalar = points[:, 0]+2*points[:, 1]
            manufactured = replace(solution, coefficients=scalar[:, None])
            cells, ref = [0, 1], [[.2, .3], [.3, .2]]
            fields = manufactured.fields_at_reference(cells, ref)
            self.assertEqual(len(fields), 12)
            mapped = manufactured.scalar_at_reference(cells, ref)
            np.testing.assert_allclose(mapped['gradient_xy'], [[1, 2], [1, 2]], rtol=0, atol=1e-14)
            omega = TAU*solution.frequencies_hz[0]
            if polarization == 'te':
                expected = dict(Hz_real_A_per_m=mapped['points_xy_m'][:,0]+2*mapped['points_xy_m'][:,1],
                    Ex_quadrature_V_per_m=np.full(2, -2/(omega*EPS0)), Ey_quadrature_V_per_m=np.full(2, 1/(omega*EPS0)))
            else:
                expected = dict(Ez_real_V_per_m=mapped['points_xy_m'][:,0]+2*mapped['points_xy_m'][:,1],
                    Hx_quadrature_A_per_m=np.full(2, 2/(omega*MU0)), Hy_quadrature_A_per_m=np.full(2, -1/(omega*MU0)))
            for name, values in fields.items():
                np.testing.assert_allclose(values, expected.get(name, np.zeros(2)), rtol=1e-13, atol=1e-13)
            invalid = [([True], [[.2,.3]], 0), ([0.], [[.2,.3]], 0), ([999], [[.2,.3]], 0),
                ([0], [[True,.3]], 0), ([0], [[-.001,.3]], 0), ([0], [[.7,.4]], 0),
                ([0], [[float('nan'),.3]], 0), ([0], [[.2,.3]], True), ([0], [[.2,.3]], 1),
                ([0,1], [[.2,.3]], 0)]
            for cells, ref, mode in invalid:
                with self.subTest(polarization=polarization, input=(cells,ref,mode)), self.assertRaises(ValueError):
                    solution.fields_at_reference(cells, ref, mode)

    def test_curved_membership_rejects_chord_inside_and_arbitrarily_near_exterior(self):
        domain = patch()
        locator = PlanarCurvedLocator(domain)
        cells, ref = locator.locate(domain.points_xy_m)
        np.testing.assert_array_equal(cells, np.zeros(6))
        np.testing.assert_array_equal(ref, [[0,0],[1,0],[0,1],[.5,0],[.5,.5],[0,.5]])
        for point in ([.01,0], [.01, np.nextafter(.001, -np.inf)],
                      [.01, np.nextafter(.01, np.inf)], [-1e-30,.001]):
            with self.subTest(point=point), self.assertRaisesRegex(ValueError, 'outside'):
                locator.locate([point])
        for point in ([.01,np.nextafter(.001,np.inf)], [.01,.003], [.002,.002]):
            cells, ref = locator.locate([point])
            reconstructed = domain.elements[cells[0]].evaluate(ref)['points_xy_m'][0]
            np.testing.assert_allclose(reconstructed, point, rtol=0, atol=1e-15)
        # The lowest cell owns a shared edge even though the other local chart
        # has different coordinates and normal derivative.
        case = straight_case()
        locator = PlanarCurvedLocator(case.domain)
        np.testing.assert_array_equal(locator.locate([[.01,.0055],[0,0],[.02,.011]])[0], [0,0,0])
        for value in ([[True,0]], [['0',0]], [[float('inf'),0]], []):
            with self.assertRaises(ValueError):
                locator.locate(value)

    def test_point_sampler_agrees_with_actual_reference_fields(self):
        solution = solve_planar_curved(PlanarCurvedCase(curved_ellipse(16), modes=2))
        cells = [0, 3, 7, 15]
        ref = np.array([[.2,.3],[.3,.1],[.1,.4],[.3,.3]])
        points = np.array([solution.case.domain.elements[cell].evaluate([point])['points_xy_m'][0] for cell,point in zip(cells,ref)])
        sampler = PlanarCurvedFieldSampler(solution)
        all_fields = solution.all_fields_at_reference(cells, ref)
        for mode in range(2):
            reference = solution.fields_at_reference(cells, ref, mode)
            actual = sampler.evaluate(points, mode)
            for name in reference:
                np.testing.assert_allclose(actual[name], reference[name], rtol=1e-11, atol=1e-8)
                np.testing.assert_allclose(all_fields[name][:,mode], reference[name], rtol=1e-14, atol=1e-8)

    def test_straight_limit_actual_solution_fields_RF_and_native_restore(self):
        for polarization in ('te', 'tm'):
            old = solve_planar(PlanarCase(.02,.011,polarization,nx=8,ny=6,modes=1))
            space = old.space
            cycle = []
            current = 0
            remaining = {int(a):int(b) for a,b in space.boundary_edges}
            while True:
                cycle.append(current)
                current = remaining[current]
                if current == cycle[0]:break
            # Geometry uses exactly the same original DOF coordinates and P2
            # cells; only the wall order and mapped evaluation path differ.
            edge_mid = {tuple(sorted(map(int, row[:2]))):int(row[2]) for row in space.boundary_dofs}
            boundary = [[a,b,edge_mid[tuple(sorted((a,b)))]] for a,b in zip(cycle,cycle[1:]+cycle[:1])]
            domain = PlanarCurvedDomain(space.dof_points_xy_m, space.cell_dofs, boundary)
            solution = solve_planar_curved(PlanarCurvedCase(domain,polarization,modes=1))
            np.testing.assert_allclose(solution.frequencies_hz,old.frequencies_hz,rtol=1e-11,atol=0)
            sign = 1 if old.coefficients[:,0]@(old.mass@solution.coefficients[:,0])>0 else -1
            cells, bary = [0,19,55], np.array([[.2,.3,.5],[.3,.4,.3],[.4,.2,.4]])
            expected = old.fields_in_cells(cells,bary)
            fields = solution.fields_in_cells(cells,bary)
            original_coefficients = restore_planar_curved_solution(solution.case,old.coefficients,old.frequencies_hz)
            mapped_original = original_coefficients.fields_in_cells(cells,bary)
            for name in fields:
                np.testing.assert_allclose(mapped_original[name],expected[name],rtol=1e-10,atol=1e-7)
            # One nearly zero transverse component is not a field-relative
            # norm. Compare each complete E/H vector with the same scalar sign.
            for field,unit in [('E','V_per_m'),('H','A_per_m')]:
                names=[f'{field}{axis}_{phase}_{unit}' for axis in 'xyz' for phase in ('real','quadrature')]
                a=np.column_stack([sign*fields[name] for name in names])
                b=np.column_stack([expected[name] for name in names])
                self.assertLess(np.linalg.norm(a-b)/np.linalg.norm(b),1e-10)
            expected, actual = planar_quantities(old),planar_curved_quantities(solution)
            for name,value in expected.items():
                if isinstance(value,(float,int)):
                    self.assertLess(abs(actual[name]/value-1),1e-10)
                else:self.assertEqual(actual[name],value)
            restored = restore_planar_curved_solution(solution.case,solution.coefficients,solution.frequencies_hz)
            np.testing.assert_array_equal(restored.coefficients,solution.coefficients)
            np.testing.assert_array_equal(restored.frequencies_hz,solution.frequencies_hz)

    def test_independent_energy_and_actual_sidewall_integrals(self):
        # Cartesian field energy and independent adaptive 1D wall quadrature,
        # using original curved cells. No matrix RF formula supplies the reference.
        from numpy.polynomial.legendre import leggauss
        for polarization in ('te','tm'):
            solution = solve_planar_curved(PlanarCurvedCase(curved_ellipse(12),polarization,modes=1))
            nodes,weights = leggauss(12);nodes=(nodes+1)/2;weights=weights/2
            refs=np.array([[u,(1-u)*v] for u in nodes for v in nodes])
            qw=np.array([wu*wv*(1-u) for u,wu in zip(nodes,weights) for wv in weights])
            electric=magnetic=0.
            for cell,element in enumerate(solution.case.domain.elements):
                mapped=element.evaluate(refs)
                fields=solution.fields_at_reference(np.full(len(refs),cell),refs)
                measure=qw*mapped['determinant_m2']
                electric += EPS0/4*sum(float(measure@(fields[f'E{axis}_{phase}_V_per_m']**2)) for axis in 'xyz' for phase in ('real','quadrature'))
                magnetic += MU0/4*sum(float(measure@(fields[f'H{axis}_{phase}_A_per_m']**2)) for axis in 'xyz' for phase in ('real','quadrature'))
            actual=planar_curved_quantities(solution)
            self.assertLess(abs(electric/actual['electric_energy_j_per_m']-1),1e-8)
            self.assertLess(abs(magnetic/actual['magnetic_energy_j_per_m']-1),1e-8)
            self.assertLess(abs(electric/magnetic-1),1e-8)
            wall=0.
            d=solution.case.domain
            for edge,(owner,local) in enumerate(zip(d.boundary_cells,d.boundary_local_edges)):
                p,q,mid=d.points_xy_m[d.boundary_nodes[edge]]
                def integrand(t):
                    ref=[t,0.] if local==0 else [1-t,t] if local==1 else [0.,1-t]
                    fields=solution.fields_at_reference([owner],[ref])
                    derivative=(4*t-1)*(q-p)+(4-8*t)*(mid-p)
                    speed=np.linalg.norm(derivative)
                    tangent=derivative/speed
                    ht=fields['Hz_real_A_per_m'][0] if polarization=='te' else fields['Hx_quadrature_A_per_m'][0]*tangent[0]+fields['Hy_quadrature_A_per_m'][0]*tangent[1]
                    return float(speed*ht*ht)
                wall += quad(integrand,0,1,epsabs=1e-6,epsrel=1e-11)[0]
            self.assertLess(abs(wall/actual['wall_magnetic_integral_a2_per_m']-1),1e-10)
            self.assertLess(abs(actual['stored_energy_j_per_m']-1),1e-10)
            self.assertIsNone(actual['vacc_v'])
            self.assertIsNone(actual['r_over_q_accelerator_ohm'])
            self.assertIsNone(actual['r_over_q_circuit_ohm'])

    def test_scale_rotation_translation_energy_and_conductivity(self):
        for polarization in ('te','tm'):
            domain=curved_ellipse(16)
            original=solve_planar_curved(PlanarCurvedCase(domain,polarization,modes=1))
            angle=.31
            rotation=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
            scaled=PlanarCurvedDomain(2*domain.points_xy_m@rotation.T+[.1,-.2],domain.cell_nodes,domain.boundary_nodes)
            changed=solve_planar_curved(PlanarCurvedCase(scaled,polarization,modes=1))
            base_rf,new_rf=planar_curved_quantities(original),planar_curved_quantities(changed)
            self.assertLess(abs(changed.frequencies_hz[0]/original.frequencies_hz[0]*2-1),1e-10)
            self.assertLess(abs(new_rf['geometry_factor_ohm']/base_rf['geometry_factor_ohm']-1),1e-9)
            self.assertLess(abs(new_rf['q0']/base_rf['q0']/math.sqrt(2)-1),1e-9)
            cells,refs=[0,7,12],[[.2,.3],[.3,.4],[.2,.2]]
            old=original.fields_at_reference(cells,refs);new=changed.fields_at_reference(cells,refs)
            scalar='Hz_real_A_per_m' if polarization=='te' else 'Ez_real_V_per_m'
            vector=['Ex_quadrature_V_per_m','Ey_quadrature_V_per_m'] if polarization=='te' else ['Hx_quadrature_A_per_m','Hy_quadrature_A_per_m']
            sign=1 if np.dot(old[scalar],new[scalar])>0 else -1
            np.testing.assert_allclose(sign*new[scalar]*2,old[scalar],rtol=1e-9,atol=1e-7)
            np.testing.assert_allclose(sign*np.column_stack([new[key] for key in vector])*2,np.column_stack([old[key] for key in vector])@rotation.T,rtol=1e-9,atol=1e-7)
            case=replace(original.case,normalization_j_per_m=3.7,conductivity_s_per_m=4*original.case.conductivity_s_per_m)
            stronger=solve_planar_curved(case);stronger_rf=planar_curved_quantities(stronger)
            self.assertLess(abs(stronger_rf['stored_energy_j_per_m']/3.7-1),1e-10)
            self.assertLess(abs(stronger_rf['wall_loss_w_per_m']/base_rf['wall_loss_w_per_m']/(3.7/2)-1),1e-10)
            self.assertLess(abs(stronger_rf['q0']/base_rf['q0']/2-1),1e-10)

    def test_restore_rejects_rehashed_style_physical_mismatches(self):
        for polarization in ('te','tm'):
            domain=curved_ellipse(12)
            large=solve_planar_curved(PlanarCurvedCase(domain,polarization,modes=3))
            case=replace(large.case,modes=1)
            with self.assertRaisesRegex(ValueError,'lowest positive'):
                restore_planar_curved_solution(case,large.coefficients[:,1:2],large.frequencies_hz[1:2])
            for coefficients,frequencies in [(large.coefficients[:,:1]*2,large.frequencies_hz[:1]),
                (large.coefficients[:,:1],large.frequencies_hz[:1]*1.001)]:
                with self.assertRaises(ValueError):
                    restore_planar_curved_solution(case,coefficients,frequencies)
            coefficients=large.coefficients[:,:1].copy()
            if polarization=='te':coefficients+=1
            else:coefficients[domain.boundary_nodes[0,0],0]=1
            with self.assertRaises(ValueError):
                restore_planar_curved_solution(case,coefficients,large.frequencies_hz[:1])
            for array in (large.coefficients,large.frequencies_hz,large.residuals):
                with self.assertRaises(ValueError):array.setflags(write=True)


if __name__=='__main__':
    unittest.main()
