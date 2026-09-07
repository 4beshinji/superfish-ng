# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from superfish_ng.quadratic_boundary import QuadraticEdge,check_quadratic_boundary,separated_edges,adjacent_edges
from superfish_ng import Case
from superfish_ng.mesh import make_mesh
from superfish_ng.curved_mesh import curve_geometry_candidate
from pathlib import Path


def square(bottom=0.,top=1.):
    points = np.array(((0,0),(1,0),(1,1),(0,1),(.5,bottom),(1,.5),(.5,top),(0,.5)))
    nodes = np.array(((0,1,4),(1,2,5),(2,3,6),(3,0,7)))
    return points,nodes


class QuadraticBoundaryTests(unittest.TestCase):
    def test_curved_cycle_and_reversed_unordered_edges(self):
        points,nodes = square(.4,.6)
        for scale in (1e-5,1.,1e5):
            result = check_quadratic_boundary(points*scale,nodes)
            self.assertEqual(result['status'],'PASS')
            changed = nodes[[2,0,3,1]].copy()
            changed[[0,2],:2] = changed[[0,2],:2][:,::-1]
            self.assertEqual(check_quadratic_boundary(points*scale,changed)['status'],'PASS')
        lower = QuadraticEdge.from_nodes(*points[nodes[0]])
        upper = QuadraticEdge.from_nodes(*points[nodes[2]])
        with self.assertRaisesRegex(ValueError,'budget'):
            separated_edges(lower,upper,padding=1e-13,max_boxes=1)
        self.assertGreater(separated_edges(lower,upper,padding=1e-13),1)

    def test_curves_cross_despite_simple_endpoint_polygon(self):
        for bottom,top in ((.8,.2),(.5,.5)):
            points,nodes = square(bottom,top)
            with self.assertRaisesRegex(ValueError,'FAIL|UNVERIFIED'):
                check_quadratic_boundary(points,nodes)
        points,nodes = square()
        points[4] = (1.5,0)  # One edge turns back on itself.
        with self.assertRaisesRegex(ValueError,'reversal'):
            check_quadratic_boundary(points,nodes)

    def test_adjacent_edges_cross_away_from_the_shared_node(self):
        first = QuadraticEdge.from_nodes((0,0),(1,0),(.5,1))
        second = QuadraticEdge.from_nodes((1,0),(0,1),(.5,-1))
        # Besides (1,0), these parabolas intersect at (.1,.36).
        with self.assertRaisesRegex(ValueError,'FAIL|UNVERIFIED'):
            adjacent_edges(first,second,padding=1e-13)

    def test_invalid_topology_and_controls(self):
        points,nodes = square()
        for bad in (nodes[:-1],np.vstack((nodes,nodes[0])),nodes.astype(float),nodes+100):
            with self.assertRaises(ValueError):
                check_quadratic_boundary(points,bad)
        for budget in (True,0,1.5):
            with self.assertRaises(ValueError):
                check_quadratic_boundary(points,nodes,max_boxes=budget)
        a = QuadraticEdge.from_nodes((0,0),(1,0),(.5,0))
        for fraction in (-1,2,True,float('nan')):
            with self.assertRaises(ValueError):
                a.split(fraction)

    def test_native_shared_candidates_have_simple_boundaries(self):
        for name in ('curved_ellipse','curved_hyperbola'):
            case = Case.load(Path(__file__).resolve().parents[1]/f'examples/{name}.json')
            candidate = curve_geometry_candidate(case,make_mesh(case))
            result = check_quadratic_boundary(candidate.points_rz_m,candidate.boundary_nodes)
            self.assertEqual(result['status'],'PASS')
            self.assertEqual(result['edges'],len(candidate.boundary_nodes))
