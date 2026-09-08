# SPDX-License-Identifier: Apache-2.0
"""Independent exhaustive candidate oracle and complete geometry diagnostics."""
import unittest
from unittest.mock import patch
import numpy as np
from superfish_ng.curved_space import _overlapping_box_candidates,check_curved_edges,curved_space
from superfish_ng.mesh import make_mesh
import test_curved_space as fixtures


def exhaustive(bounds):
    for i,a in enumerate(bounds):
        yield i,[j for j in range(i+1,len(bounds))
                 if all(a[1,k]>=bounds[j,0,k] and bounds[j,1,k]>=a[0,k] for k in (0,1))]


class CurvedBoxCandidateTests(unittest.TestCase):
    def test_exact_order_for_random_contact_coincident_and_long_boxes(self):
        rng=np.random.default_rng(287)
        samples=[np.empty((0,2,2)),np.zeros((129,2,2))]
        for size in (1,2,16,17,129):
            low=rng.uniform(-2,2,(size,2));high=low+rng.uniform(0,1,(size,2))
            samples.extend((np.stack((low,high),axis=1),np.stack((low,low),axis=1)))
        # Inclusive corner/edge contact, plus long overlapping x extents with disjoint y.
        low=np.array([(i,j) for i in range(8) for j in range(8)],dtype=float)
        samples.append(np.stack((low,low+1),axis=1))
        low=np.column_stack((np.zeros(65),np.arange(65)*2))
        samples.append(np.stack((low,low+np.array((1000.,1.))),axis=1))
        for bounds in samples:
            for boxes in (bounds,bounds[::-1]):
                self.assertEqual(list(_overlapping_box_candidates(boxes)),list(exhaustive(boxes)))

    def test_complete_report_matches_exhaustive_search(self):
        case=fixtures.CurvedSpaceTests().case()
        geometry=curved_space(case,make_mesh(case)).geometry
        args=(geometry.points_rz_m,geometry.cell_nodes,geometry.boundary_nodes)
        actual=check_curved_edges(*args)
        with patch('superfish_ng.curved_space._overlapping_box_candidates',exhaustive):
            expected=check_curved_edges(*args)
        self.assertEqual(actual,expected)
        self.assertEqual(actual['status'],'PASS')
        self.assertGreater(actual['overlapping_box_pairs'],0)

    def test_crossing_rejection_and_first_failure_match_exhaustive_search(self):
        case=fixtures.CurvedSpaceTests().case()
        geometry=curved_space(case,make_mesh(case)).geometry
        boundary=set(geometry.boundary_nodes[:,2])
        internal=sorted(set(geometry.cell_nodes[:,3:].ravel())-boundary)
        def outcome(points,budget):
            try:
                return check_curved_edges(points,geometry.cell_nodes,geometry.boundary_nodes,max_boxes=budget)
            except ValueError as error:
                return ('ValueError',str(error))
        for budget in (1,10000):
            points=geometry.points_rz_m.copy()
            points[internal[:2]]=[[1.,1.],[-1.,1.]]
            actual=outcome(points,budget)
            with patch('superfish_ng.curved_space._overlapping_box_candidates',exhaustive):
                expected=outcome(points,budget)
            self.assertEqual(actual,expected)
            self.assertIsInstance(actual,tuple)
