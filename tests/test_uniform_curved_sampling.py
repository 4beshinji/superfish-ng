# SPDX-License-Identifier: Apache-2.0
"""P2 parent addresses must preserve original fields and geometric measures."""
from dataclasses import replace
import math
import unittest
import numpy as np

from superfish_ng.curved_refinement import refine_curved_space
from superfish_ng.uniform_curved_sampling import uniform_curved_pair_samples
from superfish_ng.curved_same_domain_tracking import track_curved_same_domain_modes
from superfish_ng.geometry_surface_fields import compare_geometry_surface_fields
from test_geometry_surface_fields import manufactured_fields


class UniformCurvedSamplingTests(unittest.TestCase):
    def pair(self):
        parent=manufactured_fields(); refined=refine_curved_space(parent.space)
        child=replace(parent,case=replace(parent.case,curved_refinement_levels=1),
                      space=refined.space,u=refined.prolongation@parent.u)
        return parent,child

    def test_physical_polynomial_and_volume_invariant_without_inverse(self):
        parent,child=self.pair()
        result=uniform_curved_pair_samples(parent,child,sample_order=10)
        r,z=result['points_rz_m'].T
        expected=r*(2+3*r-4*z)
        for values in result['values']:
            np.testing.assert_allclose(values[:,0],expected,rtol=2e-13,atol=2e-13)
        self.assertAlmostEqual(result['volumes_m3'][0]/result['volumes_m3'][1],1.,places=12)
        self.assertEqual(len(result['weights']),sum(len(s.space.geometry.cell_nodes) for s in (parent,child))*100)
        self.assertTrue((result['weights']>0).all())
        self.assertEqual(result['certificate']['child_polynomials_checked'],len(child.space.geometry.cell_nodes))
        swapped=uniform_curved_pair_samples(child,parent,sample_order=10)
        np.testing.assert_allclose(swapped['values'][0],swapped['values'][1],rtol=2e-13,atol=2e-13)

    def test_field_amplitude_and_rank_exchange_remain_actual(self):
        parent,child=self.pair()
        r,z=parent.space.geometry.points_rz_m.T
        p=replace(parent,u=np.column_stack((np.ones(len(r)),z)),frequencies_hz=np.array([1e9,1.1e9]),
                  case=replace(parent.case,modes=2))
        refined=refine_curved_space(p.space)
        c=replace(child,case=replace(child.case,modes=2),u=(refined.prolongation@p.u)[:,::-1]*1.02,
                  frequencies_hz=np.array([1e9,1.1e9]))
        result=uniform_curved_pair_samples(p,c,sample_order=4)
        np.testing.assert_allclose(result['values'][1],result['values'][0][:,::-1]*1.02,rtol=2e-13,atol=2e-13)

    def test_unrelated_source_local_history_and_changed_polynomial_rejected(self):
        parent,child=self.pair()
        bad=replace(child,source_mesh_data={'different':'source'})
        with self.assertRaisesRegex(ValueError,'UNVERIFIED'):
            uniform_curved_pair_samples(parent,bad,sample_order=4)
        with self.assertRaisesRegex(ValueError,'UNVERIFIED'):
            uniform_curved_pair_samples(parent,parent,sample_order=4)
        # Keep all original boundary nodes but move a child interior midpoint.
        points=child.space.geometry.points_rz_m.copy()
        boundary=set(child.space.geometry.boundary_nodes.ravel())
        interior=next(n for n in child.space.geometry.cell_nodes[:,3:].ravel() if n not in boundary)
        points[interior,0]+=.00001
        from superfish_ng.quadratic_geometry import QuadraticTriangle
        maps=tuple(QuadraticTriangle(points[nodes]) for nodes in child.space.geometry.cell_nodes)
        space=replace(child.space,geometry=replace(child.space.geometry,points_rz_m=points,local_maps=maps))
        with self.assertRaisesRegex(ValueError,'polynomial'):
            uniform_curved_pair_samples(parent,replace(child,space=space),sample_order=4)

    def test_original_inverse_and_declared_parent_controls_agree(self):
        parent,child=self.pair()
        controls=dict(mapping='curved_same_domain',sample_order=3,minimum_overlap=.98,
            minimum_assignment_margin=.05,relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)
        old=track_curved_same_domain_modes(parent,child,['target'],**controls)
        new=track_curved_same_domain_modes(parent,child,['target'],**controls,
            sample_budget=8388608,uniform_parent_sampling=True)
        self.assertEqual(old['status'],new['status'])
        self.assertEqual(old['current_mode_ids'],new['current_mode_ids'])
        self.assertTrue(new['individual_ids_complete'])
        self.assertEqual(old['physical_mapping']['sample_count'],new['physical_mapping']['sample_count'])
        self.assertNotIn('sampling_method',old['physical_mapping'])
        self.assertEqual(new['physical_mapping']['sample_budget'],8388608)
        # Bounds are resource limits; neither an unknown option nor boolean
        # masquerading as an integer may alter the physical tracking gates.
        for budget in (True,0,8388609,1.5):
            with self.assertRaisesRegex(ValueError,'sample_budget'):
                track_curved_same_domain_modes(parent,child,['target'],**controls,sample_budget=budget)
        with self.assertRaisesRegex(ValueError,'exceed declared budget'):
            track_curved_same_domain_modes(parent,child,['target'],**controls,sample_budget=1,uniform_parent_sampling=True)

    def test_resources_never_change_field_gates_and_require_uniform_family(self):
        parent,child=self.pair()
        resources=dict(sample_budget=8388608,sampling='uniform_parent_p2')
        old=compare_geometry_surface_fields(parent,child,['target'],mapping='curved_same_domain')
        new=compare_geometry_surface_fields(parent,child,['target'],mapping='curved_same_domain',native_resources=resources)
        self.assertEqual(old['legacy_comparison'],new['legacy_comparison'])
        self.assertEqual(old['field_gates'],new['field_gates'])
        self.assertEqual(old['current_ids'],new['current_ids'])
        amplified=compare_geometry_surface_fields(parent,replace(child,u=child.u*1.02),['target'],
            mapping='curved_same_domain',native_resources=resources)
        self.assertEqual(amplified['status'],'FAIL')
        self.assertEqual(amplified['native_controls']['resource_limits'],resources)
        self.assertEqual(amplified['native_controls']['sample_order'],10)
        with self.assertRaisesRegex(ValueError,'fixed quadratic'):
            compare_geometry_surface_fields(parent,child,['target'],mapping='analytic_geometry_approximations',native_resources=resources)
        for bad in (dict(resources,sample_budget=True),dict(resources,sample_budget=8388609),dict(resources,sampling='approximate'),dict(resources,minimum_overlap=.9)):
            with self.assertRaises(ValueError):
                compare_geometry_surface_fields(parent,child,['target'],mapping='curved_same_domain',native_resources=bad)
