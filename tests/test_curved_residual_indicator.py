# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from types import SimpleNamespace
import unittest
import numpy as np
from scipy.integrate import quad, dblquad
from superfish_ng import Case, solve
from superfish_ng.curved_residual_indicator import _field_derivatives, _components, curved_residual_indicator
from superfish_ng.quadratic_geometry import QuadraticTriangle, _REFERENCE_NODES
from superfish_ng.residual_indicator import residual_indicator, _components as affine_components
from superfish_ng.mesh_input import mesh_from_dict
from superfish_ng.high_order import quadratic_space
from test_curved_reflection import half_case


class CurvedResidualIndicatorTests(unittest.TestCase):
    @staticmethod
    def mapped_triangle():
        x,y = _REFERENCE_NODES.T
        return QuadraticTriangle(np.column_stack((.1+.08*x, .2*y+.03*x*x)))

    def test_physical_derivatives_include_geometry_hessian(self):
        mapping = self.mapped_triangle()
        points = np.array([[.1,.2],[.3,.1],[0.,0.],[1.,0.]])
        r,z = mapping.points_rz_m.T
        for u, expected_gradient, expected_lap in ((r+2*z, (1.,2.), 0.), (r*r, None, 2.)):
            mapped,value,gradient,lap = _field_derivatives(mapping,u,points)
            physical = mapped['points_rz_m']
            if expected_gradient is None:
                expected_gradient = np.column_stack((2*physical[:,0], np.zeros(len(points))))
                expected_value = physical[:,0]**2
            else:
                expected_gradient = np.tile(expected_gradient,(len(points),1))
                expected_value = physical[:,0]+2*physical[:,1]
            np.testing.assert_allclose(value,expected_value,rtol=2e-14,atol=1e-16)
            np.testing.assert_allclose(gradient,expected_gradient,rtol=2e-13,atol=1e-14)
            np.testing.assert_allclose(lap,expected_lap,atol=2e-13)

    def test_independent_physical_volume_and_curved_wall_flux(self):
        mapping = self.mapped_triangle()
        geometry = SimpleNamespace(local_maps=(mapping,),cell_nodes=np.arange(6)[None,:],
                                   boundary_nodes=np.array([[0,1,3],[1,2,4],[2,0,5]]))
        space = SimpleNamespace(geometry=geometry,boundary_tags=np.array(['pec']*3))
        r,z = mapping.points_rz_m.T
        volume,interior,boundary = _components(space,r+2*z,7.,24)
        def point(x,y):return .1+.08*x, .2*y+.03*x*x
        def density(y,x):
            r,z = point(x,y)
            # The control hull diameter is from (.14,0) to (.1,.2), not a vertex edge.
            return (.04**2+.2**2)*.016*r*(3+7*r*(r+2*z))**2
        expected_volume = dblquad(density,0.,1.,lambda x:0.,lambda x:1-x,epsabs=1e-14)[0]
        expected_wall = 0.
        for a,b in ((np.array([0.,0.]),np.array([1.,0.])),(np.array([1.,0.]),np.array([0.,1.])),(np.array([0.,1.]),np.array([0.,0.]))):
            dx,dy = b-a
            def integrands(t):
                x,y = (1-t)*a+t*b
                r,z = point(x,y)
                dr,dz = .08*dx,.2*dy+.06*x*dx
                speed = np.hypot(dr,dz);nr,nz = dz/speed,-dr/speed
                flux = r*(nr+2*nz)+2*nr*(r+2*z)
                return speed, speed*r*flux*flux
            length = quad(lambda t:integrands(t)[0],0.,1.,epsabs=1e-14)[0]
            expected_wall += length*quad(lambda t:integrands(t)[1],0.,1.,epsabs=1e-14)[0]
        self.assertAlmostEqual(volume[0]/expected_volume,1.,places=12)
        self.assertAlmostEqual(boundary[0]/expected_wall,1.,places=12)
        self.assertEqual(interior[0],0.)

    def test_affine_limit_matches_all_three_residual_components(self):
        from superfish_ng.conics import LineSegment
        from superfish_ng.curved_contour import CurvedContour
        from superfish_ng.mesh_controls import ContourMeshControls
        vertices=((0.,0.),(.08,0.),(.08,.1),(0.,.1))
        case=Case((),curved_contour=CurvedContour(tuple(LineSegment(vertices[i],vertices[(i+1)%4]) for i in range(4)),('axis','pec','pec','pec'),0.),
                  curve_chord_tolerance_m=.001,contour_mesh=ContourMeshControls(.025),element_order=2,geometry_order=2,modes=1)
        solution=solve(case);mesh=mesh_from_dict(case,solution.source_mesh_data)
        affine=quadratic_space(mesh)
        def field(p):return p[:,0]+2*p[:,1]+np.maximum(p[:,0]-.05,0.)
        # The same nodal field, including a radial kink, in both representations.
        a=affine_components(mesh,2,field(affine.dof_points),7.)
        b=_components(solution.space,field(solution.space.geometry.points_rz_m),7.,12)
        for x,y in zip(a,b):np.testing.assert_allclose(x,y,rtol=2e-11,atol=1e-18)

    def test_native_amplitude_quadrature_and_invalid_inputs(self):
        case=replace(half_case('z_min','magnetic_symmetry'),quadrature_order=12)
        solution=solve(case)
        a=curved_residual_indicator(case,solution)
        self.assertGreater(a['relative_indicator'],1e-6)
        self.assertLess(solution.residuals[0],1e-7)
        self.assertEqual(a,residual_indicator(case,solution))
        self.assertIsNone(a['physical_error_bound'])
        for factor in (-7.,1e-200,1e200):
            b=curved_residual_indicator(case,replace(solution,u=factor*solution.u))
            np.testing.assert_allclose(a['cell_relative_squared'],b['cell_relative_squared'],rtol=1e-10,atol=1e-16)
        b=curved_residual_indicator(case,solution,quadrature_order=24)
        self.assertLess(abs(b['relative_indicator']/a['relative_indicator']-1),1e-7)
        for kwargs in ({'mode':True},{'mode':-1},{'quadrature_order':True},{'quadrature_order':1},{'quadrature_order':33}):
            with self.assertRaises(ValueError):curved_residual_indicator(case,solution,**kwargs)
        for change in (dict(u=solution.u*0),dict(u=solution.u*float('nan')),dict(source_mesh_data=None),dict(eigenvalues=np.array([0.]))):
            with self.assertRaises(ValueError):curved_residual_indicator(case,replace(solution,**change))
        u=solution.u.copy();u[solution.space.constrained_dofs[0],0]=1.
        with self.assertRaisesRegex(ValueError,'magnetic'):curved_residual_indicator(case,replace(solution,u=u))
        with self.assertRaisesRegex(ValueError,'matching'):curved_residual_indicator(replace(case,name='different'),solution)

    def test_saved_reflections_account_for_symmetry_plane_flux(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from superfish_ng.io import save_run
        from superfish_ng.saved import read_solution
        from superfish_ng.curved_reflection import reflect_curved_solution
        for tag in ('electric_symmetry','magnetic_symmetry'):
            case=half_case('z_min',tag)
            solution=solve(case)
            original=curved_residual_indicator(case,solution)
            full,reflected=reflect_curved_solution(case,solution)
            report=curved_residual_indicator(full,reflected)
            def total(document,key):return sum(document[key+'_relative_squared'])
            self.assertAlmostEqual(total(report,'volume')/total(original,'volume'),1.,places=10)
            if tag == 'magnetic_symmetry':
                self.assertAlmostEqual(report['relative_indicator']/original['relative_indicator'],1.,places=10)
            else:
                # Weak natural symmetry does not force pointwise zero flux. Reflection
                # doubles that flux jump; squared jump / doubled energy gives 2*b_plane.
                plane=total(original,'boundary')-total(report,'boundary')
                self.assertGreater(plane,0.)
                expected=total(original,'interior')+2*plane
                self.assertAlmostEqual(total(report,'interior')/expected,1.,places=10)
                expected=original['relative_indicator']**2+plane
                self.assertAlmostEqual(report['relative_indicator']**2/expected,1.,places=10)
            with tempfile.TemporaryDirectory() as temporary:
                directory=Path(temporary)/'run';save_run(full,reflected,directory)
                with patch('superfish_ng.curved_solution.eigsh',side_effect=AssertionError('must not solve')):
                    restored=read_solution(directory)
                    np.testing.assert_array_equal(reflected.u,restored.u)
                    replay=curved_residual_indicator(full,restored)
                    # Native replay recovers lambda from stored frequency, with one-ulp rounding.
                    canonical=curved_residual_indicator(full,replace(reflected,eigenvalues=restored.eigenvalues))
                    self.assertEqual(canonical,replay)
                    self.assertAlmostEqual(replay['relative_indicator']/report['relative_indicator'],1.,places=12)
            wrong_space=replace(solution.space,axis_dofs=solution.space.axis_dofs[::-1])
            with self.assertRaisesRegex(ValueError,'geometry'):
                curved_residual_indicator(case,replace(solution,space=wrong_space))
