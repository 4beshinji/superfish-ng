# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from fractions import Fraction
import unittest
import numpy as np
from superfish_ng.planar_affine_shape import PlanarAffineShapeLaw
from superfish_ng.planar_curved import PlanarCurvedCase
from superfish_ng.planar_project import PlanarProject
from test_planar_curved_comparison import analytic_patch


class PlanarCurvedShapeTests(unittest.TestCase):
    def test_complete_quadratic_nodes_nonuniform_area_and_original_regeneration(self):
        from superfish_ng.planar_curved_shape import PlanarCurvedAffineShapeLaw
        base,_ = analytic_patch()
        project = PlanarProject(PlanarCurvedCase(base,'te',modes=2,normalization_j_per_m=3.7),display_length_unit='m')
        before = deepcopy(project.to_dict())
        # F_t=(x+t*y/4+1/8, (1+t/2)*y-1/4), det=1+t/2.
        law = PlanarCurvedAffineShapeLaw(PlanarAffineShapeLaw([[[1],[0,.25]],[[0],[1,.5]]],[[.125],[-.25]],[-1,1]))
        for value in (1.,-.5,0.,1.):
            mapped = law.project(project,value)
            x,y = base.points_xy_m.T
            expected = np.column_stack((x+value*y/4+1/8,(1+value/2)*y-1/4))
            np.testing.assert_array_equal(mapped.case.domain.points_xy_m,expected)
            np.testing.assert_array_equal(mapped.case.domain.cell_nodes,base.cell_nodes)
            np.testing.assert_array_equal(mapped.case.domain.boundary_nodes,base.boundary_nodes)
            self.assertAlmostEqual(mapped.case.domain.area_m2/base.area_m2,1+value/2,places=13)
            self.assertEqual(mapped.case.normalization_j_per_m,3.7)
            self.assertEqual(mapped.display_length_unit,'m')
        self.assertEqual(project.to_dict(),before)
        self.assertEqual(law.to_dict(),PlanarCurvedAffineShapeLaw.from_dict(law.to_dict()).to_dict())

    def test_circle_real_fem_scale_f_energy_fields_and_wall_rf(self):
        from superfish_ng.planar_curved_shape import PlanarCurvedAffineShapeLaw
        from superfish_ng.planar_curved_solver import solve_planar_curved,planar_curved_quantities
        from test_planar_curved import curved_ellipse
        law=PlanarCurvedAffineShapeLaw(PlanarAffineShapeLaw([[[0,1],[0]],[[0],[0,1]]],[[0],[0]],[1,2]))
        for polarization,modes in (('te',2),('tm',1)):
            project=PlanarProject(PlanarCurvedCase(curved_ellipse(16,axes=(.02,.02),shift=(0.,0.)),polarization,
                modes=modes,quadrature_order=16,normalization_j_per_m=2.3))
            base,mapped=(solve_planar_curved(law.project(project,value).case) for value in (1.,2.))
            np.testing.assert_allclose(mapped.frequencies_hz*2,base.frequencies_hz,rtol=1e-11)
            # A circular TE doublet may rotate its basis. Compare the complete
            # scalar subspace rather than asserting a per-rank phasor label.
            material = __import__('superfish_ng.constants',fromlist=['EPS0','MU0'])
            factor=material.MU0 if polarization=='te' else material.EPS0
            gram=(base.coefficients.T@(base.mass@(2*mapped.coefficients)))*factor/(2*project.case.normalization_j_per_m)
            np.testing.assert_allclose(np.linalg.svd(gram,compute_uv=False),np.ones(modes),rtol=0,atol=1e-10)
            for mode in range(modes):
                a,b=planar_curved_quantities(base,mode),planar_curved_quantities(mapped,mode)
                self.assertAlmostEqual(a['stored_energy_j_per_m'],2.3,places=10)
                self.assertAlmostEqual(b['stored_energy_j_per_m'],2.3,places=10)
                self.assertLess(abs(b['geometry_factor_ohm']/a['geometry_factor_ohm']-1),1e-9)
                self.assertLess(abs(b['q0']/a['q0']/np.sqrt(2)-1),1e-9)
            domain=law.comparison(project,1.,2.)
            self.assertEqual(domain.previous.to_dict(),base.case.domain.to_dict())
            self.assertEqual(domain.current.to_dict(),mapped.case.domain.to_dict())

    def test_closed_interval_singular_reversed_and_unresolved_float_maps_refused(self):
        from superfish_ng.planar_curved_shape import PlanarCurvedAffineShapeLaw
        for coefficients in ([9/64,-3/4,1],[0,1],[-1,1],[0]):
            with self.assertRaisesRegex(ValueError,'determinant'):
                PlanarCurvedAffineShapeLaw(PlanarAffineShapeLaw([[coefficients,[0]],[[0],[1]]],[[0],[0]],[0,1]))
        with self.assertRaisesRegex(ValueError,'positive determinant'):
            PlanarCurvedAffineShapeLaw(PlanarAffineShapeLaw([[[-1],[0]],[[0],[1]]],[[0],[0]],[0,1]))
        # Preserve exact large integer bounds; float(lower) would escape this
        # valid interval. All transformation coefficients are constant here.
        valid=PlanarCurvedAffineShapeLaw(PlanarAffineShapeLaw([[[1],[0]],[[0],[1]]],[[0],[0]],[2**53+1,2**53+3]))
        self.assertEqual(valid.exact_transform(2**53+1)[0],((Fraction(1),Fraction(0)),(Fraction(0),Fraction(1))))
        base,_=analytic_patch();project=PlanarProject(PlanarCurvedCase(base,modes=2))
        original=project.to_dict()
        collapsed=PlanarCurvedAffineShapeLaw(PlanarAffineShapeLaw([[[1],[0]],[[0],[1]]],[[1e30],[1e30]],[0,1]))
        with self.assertRaises(ValueError):collapsed.project(project,.5)
        self.assertEqual(project.to_dict(),original)

    def test_strict_units_version_case_and_input_ownership(self):
        from superfish_ng.planar_curved_shape import PlanarCurvedAffineShapeLaw
        from superfish_ng.planar import PlanarCase
        raw=PlanarAffineShapeLaw([[[1],[0,.25]],[[0],[1]]],[[0],[0]],[0,1]).to_dict()
        law=PlanarCurvedAffineShapeLaw(PlanarAffineShapeLaw.from_dict(raw))
        raw['linear_xy_coefficients'][0][0][0]=9
        self.assertEqual(law.exact_transform(.5)[0][0][0],1)
        for key,value in (('schema_version',True),('orientation','reversing'),('kind','straight_xy'),('extra',0)):
            bad=law.to_dict();bad[key]=value
            with self.assertRaises(ValueError):PlanarCurvedAffineShapeLaw.from_dict(bad)
        bad=law.to_dict();bad['shape_law']['parameter_unit']='m'
        with self.assertRaises(ValueError):PlanarCurvedAffineShapeLaw.from_dict(bad)
        with self.assertRaisesRegex(ValueError,'quadratic PlanarProject'):
            law.project(PlanarProject(PlanarCase(.02,.01)),.5)
        for value in (True,1.1,float('inf')):
            base,_=analytic_patch()
            with self.assertRaises(ValueError):law.project(PlanarProject(PlanarCurvedCase(base,modes=2)),value)


if __name__=='__main__':unittest.main()
