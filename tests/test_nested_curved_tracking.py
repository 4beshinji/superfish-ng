# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from superfish_ng import solve
from superfish_ng.curved_refinement_steps import CurvedRefinementStep as Step
from superfish_ng.curved_refinement import refine_curved_space
from superfish_ng.curved_marked_refinement import refine_marked_curved_space
from superfish_ng.curved_reflection import reflect_curved_solution
from superfish_ng.curved_fem import assemble_curved
from superfish_ng.fem import triangle_quadrature
from superfish_ng.io import save_run
from superfish_ng.mass_tracking import mass_inner_product_features
from superfish_ng.nested_curved_tracking import track_nested_curved_modes, _nested_transfer
from superfish_ng.saved_mode_tracking import build_saved_mode_tracking, replay_mode_tracking, validate_tracking_controls
from test_curved_reflection import half_case

CONTROLS=dict(mapping='nested_curved',minimum_overlap=.95,minimum_assignment_margin=.05,
              relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)


class NestedCurvedTrackingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case=replace(half_case('z_min','electric_symmetry'),modes=2)
        cls.a=solve(cls.case)
        cls.next_case=replace(cls.case,curved_refinement_steps=(Step('marked',(0,),5.),Step('uniform')))
        cls.b=solve(cls.next_case)

    def test_composed_transfer_and_independent_mass_integral(self):
        p,space,a,b,ancestry=_nested_transfer(self.a,self.b)
        first=refine_marked_curved_space(self.a.space,[0]);second=refine_curved_space(first.space)
        self.assertEqual((p-second.prolongation@first.prolongation).nnz,0)
        self.assertEqual(ancestry['current_steps'],2)
        coarse_mass=assemble_curved(self.a.space,quadrature_order=12)[1]
        mass=assemble_curved(space,quadrature_order=8)[1]
        delta=p.T@mass@p-coarse_mass
        self.assertLess(np.linalg.norm(delta.data)/np.linalg.norm(coarse_mass.data),1e-11)
        x=np.column_stack((p@a,b));x/=np.max(abs(x),axis=0)
        features,scale=mass_inner_product_features(x,mass)
        gram=np.zeros((4,4));rule=list(triangle_quadrature(order=12))
        for mapping,nodes in zip(space.geometry.local_maps,space.geometry.cell_nodes):
            q=mapping.evaluate([n[1:] for n,w in rule])
            values=q['basis_values']@x[nodes]
            weights=np.array([w for n,w in rule])*q['determinant_m2']*q['points_rz_m'][:,0]**3
            gram+=values.T@(weights[:,None]*values)
        np.testing.assert_allclose(features.T@features*scale,gram,rtol=1e-11,atol=np.max(abs(gram))*1e-13)

    def test_sign_permutation_clusters_and_rank_loss(self):
        p,_,_,_,_=_nested_transfer(self.a,self.b)
        b=replace(self.b,u=(p@self.a.u)[:,::-1]*[-3.,7.])
        report=track_nested_curved_modes(self.a,b,['A','B'],**CONTROLS)
        self.assertEqual(report['current_mode_ids'],['B','A']);self.assertEqual(report['status'],'PASS')
        angle=.37;rotation=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
        a=replace(self.a,frequencies_hz=np.array([1.,1.]))
        b=replace(self.b,u=(p@a.u)@rotation,frequencies_hz=np.array([1.,1.]))
        report=track_nested_curved_modes(a,b,['A','B'],**CONTROLS)
        self.assertEqual(report['status'],'PASS');self.assertFalse(report['individual_ids_complete'])
        self.assertEqual(report['current_mode_ids'],[None,None])
        a=replace(a,u=np.column_stack((a.u[:,0],a.u[:,0])))
        report=track_nested_curved_modes(a,replace(b,u=p@a.u),['A','B'],**CONTROLS)
        self.assertEqual(report['status'],'UNVERIFIED')

    def test_both_symmetries_and_reflected_parity_subspaces(self):
        for tag in ('electric_symmetry','magnetic_symmetry'):
            case=replace(half_case('z_min',tag),modes=2)
            a=solve(case);b=solve(replace(case,curved_refinement_steps=(Step('marked',(0,),5.),)))
            direct=track_nested_curved_modes(a,b,['A','B'],**CONTROLS)
            _,ra=reflect_curved_solution(a.case,a);_,rb=reflect_curved_solution(b.case,b)
            reflected=track_nested_curved_modes(ra,rb,['A','B'],**CONTROLS)
            self.assertEqual(reflected['current_mode_ids'],direct['current_mode_ids'])
            self.assertEqual(reflected['status'],'PASS')
            for first,second in zip(direct['matches'],reflected['matches']):
                np.testing.assert_allclose(first['principal_overlaps'],second['principal_overlaps'],atol=1e-12)
            if tag=='magnetic_symmetry':
                with tempfile.TemporaryDirectory() as temporary:
                    root=Path(temporary);save_run(ra.case,ra,root/'old');save_run(rb.case,rb,root/'new')
                    request=dict(schema_version=1,previous_run=str(root/'old'),current_run=str(root/'new'),previous_ids=['A','B'],controls=CONTROLS)
                    with patch('superfish_ng.curved_solution.eigsh',side_effect=AssertionError('must not solve')):
                        document=build_saved_mode_tracking(request)
                        self.assertEqual(document['status'],'PASS')
                        self.assertEqual(document,replay_mode_tracking(document))
            u=rb.u.copy();u[-1,0]+=1.
            with self.assertRaisesRegex(ValueError,'parity'):
                track_nested_curved_modes(ra,replace(rb,u=u),['A','B'],**CONTROLS)
            with self.assertRaisesRegex(ValueError,'construction'):
                track_nested_curved_modes(a,rb,['A','B'],**CONTROLS)

    def test_native_saved_replay_strict_controls_and_ancestry(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);save_run(self.a.case,self.a,root/'old');save_run(self.b.case,self.b,root/'new')
            request=dict(schema_version=1,previous_run=str(root/'old'),current_run=str(root/'new'),previous_ids=['A','B'],controls=CONTROLS)
            with patch('superfish_ng.curved_solution.eigsh',side_effect=AssertionError('must not solve')):
                document=build_saved_mode_tracking(request)
                self.assertEqual(document['status'],'PASS');self.assertEqual(document,replay_mode_tracking(document))
            changed=deepcopy(document);changed['tracking']['physical_mapping']['ancestry']['current_steps']=3
            with self.assertRaises(ValueError):replay_mode_tracking(changed)
        for controls in (dict(CONTROLS,sample_order=8),dict(CONTROLS,marked_cells=[0]),dict(CONTROLS,mapping='bad')):
            with self.assertRaises(ValueError):validate_tracking_controls(controls)
        with self.assertRaisesRegex(ValueError,'extend'):
            track_nested_curved_modes(self.a,self.a,['A','B'],**CONTROLS)
        with self.assertRaisesRegex(ValueError,'source Case'):
            altered=replace(self.b,case=replace(self.b.case,name='different'))
            track_nested_curved_modes(self.a,altered,['A','B'],**CONTROLS)
        with patch('superfish_ng.nested_curved_tracking.MAX_FEATURE_ENTRIES',1):
            with self.assertRaisesRegex(ValueError,'feature entries'):
                track_nested_curved_modes(self.a,self.b,['A','B'],**CONTROLS)

    def test_legacy_uniform_levels_and_ordered_uniform_history_agree(self):
        a=solve(replace(self.case,curved_refinement_levels=1))
        b=solve(replace(self.case,curved_refinement_steps=(Step('uniform'),Step('marked',(0,),5.))))
        report=track_nested_curved_modes(a,b,['A','B'],**CONTROLS)
        self.assertEqual(report['status'],'PASS')
        self.assertEqual(report['physical_mapping']['ancestry']['previous_steps'],1)

    def test_extended_marked_prefix_preserves_the_coarse_mass_form(self):
        case=replace(self.b.case,curved_refinement_steps=self.b.case.curved_refinement_steps+(Step('marked',(1,),5.),))
        current=solve(case)
        transfer,space,_,_,ancestry=_nested_transfer(self.b,current)
        self.assertEqual(ancestry['previous_steps'],2)
        self.assertEqual(ancestry['current_steps'],3)
        # A nested restriction preserves every coarse P2 field's r^3-weighted
        # mass, independently of the coefficients returned by either solve.
        coarse_mass=assemble_curved(self.b.space,quadrature_order=12)[1]
        fine_mass=assemble_curved(space,quadrature_order=12)[1]
        delta=transfer.T@fine_mass@transfer-coarse_mass
        self.assertLess(np.linalg.norm(delta.data)/np.linalg.norm(coarse_mass.data),1e-11)
        np.testing.assert_array_equal(transfer@np.ones(transfer.shape[1]),np.ones(transfer.shape[0]))

    def test_each_native_geometry_is_checked_after_history_reuse(self):
        for solution in (self.a,self.b):
            points=solution.space.geometry.points_rz_m.copy();points[0,1]+=1e-5
            geometry=replace(solution.space.geometry,points_rz_m=points)
            altered=replace(solution,space=replace(solution.space,geometry=geometry))
            pair=(altered,self.b) if solution is self.a else (self.a,altered)
            with self.subTest(which='previous' if solution is self.a else 'current'):
                with self.assertRaisesRegex(ValueError,'native reconstruction'):_nested_transfer(*pair)
        # Matching fabricated metadata in both spaces is also insufficient:
        # the comparison is against the source reconstruction, not each other.
        pair=tuple(replace(solution,space=replace(solution.space,axis_dofs=np.array([],dtype=int)))
                   for solution in (self.a,self.b))
        with self.assertRaisesRegex(ValueError,'native reconstruction'):_nested_transfer(*pair)

    def test_both_native_coefficient_arrays_and_constraints_are_checked(self):
        for index,solution in enumerate((self.a,self.b)):
            for coefficients in (solution.u[:-1],solution.u*float('nan')):
                pair=[self.a,self.b];pair[index]=replace(solution,u=coefficients)
                with self.subTest(index=index,shape=coefficients.shape):
                    with self.assertRaises(ValueError):_nested_transfer(*pair)
        case=replace(half_case('z_min','magnetic_symmetry'),modes=1)
        a=solve(case);b=solve(replace(case,curved_refinement_steps=(Step('marked',(0,),5.),)))
        for index,solution in enumerate((a,b)):
            u=solution.u.copy();u[solution.space.constrained_dofs[0],0]=1.
            pair=[a,b];pair[index]=replace(solution,u=u)
            with self.assertRaisesRegex(ValueError,'essential constraint'):_nested_transfer(*pair)

    def test_equal_mesh_digests_do_not_replace_strict_current_parsing(self):
        from superfish_ng.mesh_input import mesh_digest
        data=deepcopy(self.b.source_mesh_data)
        data['triangles'][0]=tuple(data['triangles'][0])
        self.assertEqual(mesh_digest(data),mesh_digest(self.a.source_mesh_data))
        with self.assertRaisesRegex(ValueError,'rows'):
            _nested_transfer(self.a,replace(self.b,source_mesh_data=data))
