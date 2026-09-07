# SPDX-License-Identifier: Apache-2.0
import math
from pathlib import Path
import unittest
import numpy as np
from superfish_ng import Case
from superfish_ng.curved_contour import CurvedContour
from superfish_ng.curved_mesh import curve_geometry_candidate
from superfish_ng.fem import triangle_quadrature
from superfish_ng.mesh import make_mesh


class CurvedMeshTests(unittest.TestCase):
    def test_parameter_intervals_follow_canonical_rotation(self):
        case = Case.load(Path(__file__).resolve().parents[1]/'examples/curved_hyperbola.json')
        original = case.curved_contour
        rotated = CurvedContour(original.curves[1:]+original.curves[:1],
                                original.edge_tags[1:]+original.edge_tags[:1],original.join_tolerance_m)
        approximation = rotated.linearize(.000125)
        self.assertEqual(approximation.contour.vertices_zr_m[0],(0.,0.))
        self.assertEqual(len(approximation.segment_parameter_intervals),len(approximation.segment_curve_indices))
        vertices = np.asarray(approximation.contour.vertices_zr_m)
        for i,(owner,interval) in enumerate(zip(approximation.segment_curve_indices,
                                               approximation.segment_parameter_intervals)):
            actual = rotated.curves[owner].evaluate(interval)['points_zr_m']
            expected = vertices[[i,(i+1)%len(vertices)]]
            np.testing.assert_allclose(actual,expected,atol=1e-14,rtol=0)
            self.assertEqual(approximation.contour.edge_tags[i],rotated.edge_tags[owner])
        for owner in range(len(rotated.curves)):
            intervals = sorted(p for j,p in zip(approximation.segment_curve_indices,
                                                approximation.segment_parameter_intervals) if j==owner)
            self.assertEqual(intervals[0][0],0.)
            self.assertEqual(intervals[-1][1],1.)
            self.assertTrue(all(a[1]==b[0] for a,b in zip(intervals,intervals[1:])))

    def test_curving_rejects_a_fold_without_mutating_source(self):
        from dataclasses import replace
        case = Case.load(Path(__file__).resolve().parents[1]/'examples/curved_hyperbola.json')
        case = replace(case,contour=None,curve_chord_tolerance_m=.004,
                       contour_mesh=replace(case.contour_mesh,max_edge_m=.005))
        mesh = make_mesh(case)
        original = mesh.points.copy()
        with self.assertRaisesRegex(ValueError,'cell .*Jacobian'):
            curve_geometry_candidate(case,mesh)
        np.testing.assert_array_equal(mesh.points,original)

    def test_shared_geometry_preserves_source_and_improves_analytic_moments(self):
        rule = list(triangle_quadrature(order=5))
        positions = [b[1:] for b,w in rule]
        weights = np.array([w for b,w in rule])
        for name in ('curved_ellipse','curved_hyperbola'):
            case = Case.load(Path(__file__).resolve().parents[1]/f'examples/{name}.json')
            mesh = make_mesh(case)
            original_points = mesh.points.copy()
            candidate = curve_geometry_candidate(case,mesh)
            np.testing.assert_array_equal(mesh.points,original_points)
            self.assertTrue(all(m.determinant_lower_bound_m2>0 for m in candidate.local_maps))
            area,volume = 0.,0.
            for mapping in candidate.local_maps:
                result = mapping.evaluate(positions)
                measure = weights*result['determinant_m2']
                area += measure.sum()
                volume += np.dot(measure,2*math.pi*result['points_rz_m'][:,0])
            self.assertLess(abs(area-case.curved_contour.area_m2),
                            abs(case.contour.area_m2-case.curved_contour.area_m2)/10)
            self.assertLess(abs(volume-case.curved_contour.volume_m3),
                            abs(case.contour.volume_m3-case.curved_contour.volume_m3)/10)
            # Shared edge nodes are a single index regardless of local orientation.
            edge_nodes = {}
            for nodes in candidate.cell_nodes:
                for i,(a,b) in enumerate(((0,1),(1,2),(2,0))):
                    edge = tuple(sorted((int(nodes[a]),int(nodes[b]))))
                    if edge in edge_nodes:
                        self.assertEqual(edge_nodes[edge],nodes[3+i])
                    edge_nodes[edge] = nodes[3+i]
            for nodes,owner,interval in zip(candidate.boundary_nodes,candidate.boundary_curve_indices,
                                             candidate.boundary_parameters):
                curve = case.curved_contour.curves[owner]
                point = curve.evaluate(float(interval.mean()))['points_zr_m'][::-1]
                np.testing.assert_allclose(candidate.points_rz_m[nodes[2]],point,atol=1e-14,rtol=0)
            axis_nodes = candidate.boundary_nodes[mesh.boundary_tags=='axis']
            self.assertTrue(np.all(candidate.points_rz_m[axis_nodes,0]==0))
            with self.assertRaises(ValueError):
                candidate.points_rz_m[0,0]=2.
