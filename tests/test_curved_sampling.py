# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import unittest
import numpy as np
from superfish_ng import Case
from superfish_ng.quadratic_geometry import QuadraticTriangle
from superfish_ng.curved_sampling import QuadraticLocator,CurvedFieldSampler
from superfish_ng.curved_solution import solve_curved

NODES=np.array(((0.,0.),(1.,0.),(0.,1.),(.5,0.),(.5,.5),(0.,.5)))


class CurvedSamplingTests(unittest.TestCase):
    def mapping(self,scale=1.):
        x,y=NODES.T
        return QuadraticTriangle(scale*np.column_stack((x,y*(1+.4*x))))

    def test_inverse_in_curved_bulge_axis_and_scaled_domains(self):
        references=np.vstack((NODES,[[.2,.3],[.49,.5],[1e-10,.4]]))
        for scale in (1e-5,1.,1e5):
            mapping=self.mapping(scale)
            positions=mapping.evaluate(references)['points_rz_m']
            locator=QuadraticLocator(mapping)
            for expected,point in zip(references,positions):
                np.testing.assert_allclose(locator.inverse(point),expected,atol=1e-11,rtol=0)
            # (.5,.6) lies outside the corner triangle, but on the curved edge.
            np.testing.assert_allclose(locator.inverse(scale*np.array((.5,.6))),(.5,.5),atol=1e-12)
            self.assertIsNone(locator.inverse(scale*np.array((.5,.7))))
            self.assertIsNone(locator.inverse(scale*np.array((-1.,0))))

    def test_unresolved_is_not_outside_and_invalid_inputs(self):
        locator=QuadraticLocator(self.mapping())
        point=self.mapping().evaluate([[.3,.4]])['points_rz_m'][0]
        with self.assertRaisesRegex(ValueError,'UNVERIFIED'):
            locator.inverse(point,max_iterations=1,max_boxes=1)
        for point in ([True,False],[float('nan'),0],[0],['0','0']):
            with self.assertRaises(ValueError):
                locator.inverse(point)

    def test_physical_probes_match_mapped_cell_evaluation(self):
        case=Case.load(Path(__file__).resolve().parents[1]/'examples/curved_ellipse.json')
        solution=solve_curved(case)
        sampler=CurvedFieldSampler(solution)
        cells=np.argsort(solution.space.geometry.node_displacements_m[solution.space.geometry.cell_nodes].max(axis=1))[-10:]
        for cell in cells:
            expected=solution.fields_in_cell(int(cell),[[.2,.3]])
            actual=sampler.evaluate(expected['points_rz_m'])
            for key in ('Hphi_A_per_m','Er_quadrature_V_per_m','Ez_quadrature_V_per_m'):
                np.testing.assert_allclose(actual[key],expected[key],rtol=1e-10,atol=1e-7)
        outside=sampler.evaluate([[1,1]],outside='nan')
        self.assertFalse(outside['inside'][0])
        self.assertTrue(np.isnan(outside['Hphi_A_per_m'][0]))
        for points in ([],[[float('nan'),0]],[['0','0']]):
            with self.assertRaises(ValueError):
                sampler.evaluate(points)
