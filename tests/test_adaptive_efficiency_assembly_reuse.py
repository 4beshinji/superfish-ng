# SPDX-License-Identifier: Apache-2.0
"""Exact native matrices, independent Maxwell/Green energies and serial scope."""
from functools import wraps
import math
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import numpy as np

from superfish_ng import curved_adaptive_refinement as adaptive, geometry_surface_numerics as numerics
from superfish_ng.adaptive_efficiency_assembly_reuse import reuse_high_order_assembly
from superfish_ng.adaptive_efficiency_plan import build_adaptive_efficiency_plan
from superfish_ng.adaptive_efficiency_timing import PhaseRecorder
from superfish_ng.config import Case
from superfish_ng.curved_fem import assemble_curved
from superfish_ng.curved_refinement import refine_curved_space
from superfish_ng.curved_space import curved_space
from superfish_ng.mesh import make_mesh


def same_pair(test,a,b):
    for left,right in zip(a,b):
        test.assertEqual(type(left),type(right));test.assertEqual(left.shape,right.shape)
        for name in ('data','indices','indptr'):np.testing.assert_array_equal(getattr(left,name),getattr(right,name))


class AdaptiveEfficiencyAssemblyReuseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        plan=build_adaptive_efficiency_plan()
        cls.case=Case.from_dict(plan['cases'][1]['request']['case'])
        cls.space=curved_space(cls.case,make_mesh(cls.case))

    def test_original_pair_is_computed_once_and_hits_return_independent_exact_copies(self):
        recorder=PhaseRecorder();original=assemble_curved;calls=[];returned=[]
        @wraps(original)
        def spy(*args,**kwargs):
            calls.append((args,kwargs));value=original(*args,**kwargs);returned.append(value);return value
        expected=original(self.space,quadrature_order=24)
        with patch.object(adaptive,'assemble_curved',new=spy),patch.object(numerics,'assemble_curved',new=spy):
            with reuse_high_order_assembly(recorder,self.space,24) as stats:
                first=adaptive.assemble_curved(self.space,quadrature_order=24)
                self.assertIs(first,returned[0]);same_pair(self,first,expected)
                first[0].data[:]*=2
                second=numerics.assemble_curved(self.space,quadrature_order=24)
                same_pair(self,second,expected)
                second[1].data[:]*=3
                same_pair(self,adaptive.assemble_curved(self.space,quadrature_order=24),expected)
            self.assertIs(adaptive.assemble_curved,spy);self.assertIs(numerics.assemble_curved,spy)
        self.assertEqual(len(calls),1);self.assertIs(calls[0][0][0],self.space)
        self.assertEqual(calls[0][1],dict(quadrature_order=24))
        self.assertEqual(stats['original_assemblies'],1);self.assertEqual(stats['cache_hits'],2)
        self.assertGreater(stats['peak_cached_matrix_bytes'],0)
        self.assertEqual(recorder.finish()['status'],'COMPLETE')

    def test_changed_readonly_operand_invalidates_original_matrix_binding(self):
        space=curved_space(self.case,make_mesh(self.case));recorder=PhaseRecorder()
        with reuse_high_order_assembly(recorder,space,24) as stats:
            first=adaptive.assemble_curved(space,quadrature_order=24)
            points=space.geometry.local_maps[0].points_rz_m
            points.setflags(write=True);points[:,0]*=1.0001;points.setflags(write=False)
            second=numerics.assemble_curved(space,quadrature_order=24)
            same_pair(self,second,assemble_curved(space,quadrature_order=24))
            self.assertFalse(np.array_equal(first[1].data,second[1].data))
        self.assertEqual(stats['original_assemblies'],2);self.assertEqual(stats['invalidations'],1)
        self.assertEqual(stats['cache_hits'],0)

    def test_other_space_order_and_invalid_native_arguments_go_to_original(self):
        other=curved_space(self.case,make_mesh(self.case));calls=[]
        @wraps(assemble_curved)
        def spy(*args,**kwargs):calls.append((args,kwargs));return assemble_curved(*args,**kwargs)
        with patch.object(adaptive,'assemble_curved',new=spy),patch.object(numerics,'assemble_curved',new=spy):
            with reuse_high_order_assembly(PhaseRecorder(),self.space,24) as stats:
                adaptive.assemble_curved(self.space,quadrature_order=24)
                numerics.assemble_curved(other,quadrature_order=24)
                numerics.assemble_curved(self.space,quadrature_order=16)
                for invalid in (True,24.,np.int64(24)):
                    with self.assertRaisesRegex(ValueError,'quadrature_order'):
                        numerics.assemble_curved(self.space,quadrature_order=invalid)
        self.assertEqual(len(calls),6);self.assertIs(calls[1][0][0],other)
        self.assertEqual(stats['original_assemblies'],1);self.assertEqual(stats['cache_hits'],0)

    def test_oversized_entry_preserves_results_without_changing_solve_budget(self):
        with reuse_high_order_assembly(PhaseRecorder(),self.space,24,maximum_cache_bytes=0) as stats:
            a=adaptive.assemble_curved(self.space,quadrature_order=24)
            b=numerics.assemble_curved(self.space,quadrature_order=24)
            same_pair(self,a,b)
        self.assertEqual(stats['original_assemblies'],2);self.assertEqual(stats['cache_hits'],0)
        self.assertEqual(stats['oversized_entries'],2);self.assertEqual(stats['peak_cached_matrix_bytes'],0)

    def test_original_exception_identity_and_aliases_are_preserved(self):
        error=RuntimeError('original assembler failure');original_a=adaptive.assemble_curved;original_b=numerics.assemble_curved
        @wraps(assemble_curved)
        def failing(*args,**kwargs):raise error
        with patch.object(adaptive,'assemble_curved',new=failing):
            with self.assertRaises(RuntimeError) as caught:
                with reuse_high_order_assembly(PhaseRecorder(),self.space,24) as stats:
                    adaptive.assemble_curved(self.space,quadrature_order=24)
            self.assertIs(caught.exception,error);self.assertIs(adaptive.assemble_curved,failing)
            self.assertEqual(stats['original_assembly_calls'],1);self.assertEqual(stats['original_assemblies'],0)
        self.assertIs(adaptive.assemble_curved,original_a);self.assertIs(numerics.assemble_curved,original_b)

    def test_external_conflict_is_preserved_and_foreign_thread_cannot_reuse(self):
        recorder=PhaseRecorder();errors=[];original=numerics.assemble_curved
        def foreign():
            try:adaptive.assemble_curved(self.space,quadrature_order=24)
            except BaseException as error:errors.append(error)
        with reuse_high_order_assembly(recorder,self.space,24) as stats:
            thread=threading.Thread(target=foreign);thread.start();thread.join()
        self.assertEqual(len(errors),1);self.assertIsInstance(errors[0],ValueError)
        self.assertEqual(stats['original_assemblies'],0)
        replacement=lambda *args,**kwargs:None
        try:
            with self.assertRaisesRegex(ValueError,'outside its serial context'):
                with reuse_high_order_assembly(PhaseRecorder(),self.space,24):numerics.assemble_curved=replacement
            self.assertIs(numerics.assemble_curved,replacement)
        finally:numerics.assemble_curved=original

    def test_invalid_context_fails_before_any_alias_changes(self):
        originals=(adaptive.assemble_curved,numerics.assemble_curved)
        for space,order,budget in ((None,24,1),(self.space,True,1),(self.space,24,-1)):
            with self.assertRaises(ValueError):
                with reuse_high_order_assembly(PhaseRecorder(),space,order,maximum_cache_bytes=budget):pass
        self.assertEqual((adaptive.assemble_curved,numerics.assemble_curved),originals)

    def test_constant_u_maxwell_green_integrals_and_parent_galerkin_mass_are_preserved(self):
        # Hphi=r has curl_z=2. Independent closed-boundary Green integrals
        # give K[1,1]=4 integral(r dA), M[1,1]=integral(r^3 dA).
        nodes,weights=np.polynomial.legendre.leggauss(6);t=(nodes+1)/2;weights=weights/2
        basis=np.column_stack((2*t*t-3*t+1,2*t*t-t,4*t-4*t*t))
        derivative=np.column_stack((4*t-3,4*t-1,4-8*t))
        integrals=[]
        for power in (1,3):
            integrals.append(abs(math.fsum(float(np.dot(weights,(basis@self.space.geometry.points_rz_m[edge,0])**(power+1)*
                (derivative@self.space.geometry.points_rz_m[edge,1])/(power+1))) for edge in self.space.geometry.boundary_nodes)))
        with reuse_high_order_assembly(PhaseRecorder(),self.space,24):
            coarse=adaptive.assemble_curved(self.space,quadrature_order=24)
            cached=numerics.assemble_curved(self.space,quadrature_order=24)
        same_pair(self,coarse,cached);one=np.ones(len(self.space.geometry.points_rz_m))
        self.assertLess(abs(float(one@(cached[0]@one))/(4*integrals[0])-1),1e-12)
        self.assertLess(abs(float(one@(cached[1]@one))/integrals[1]-1),1e-12)
        refinement=refine_curved_space(self.space)
        with reuse_high_order_assembly(PhaseRecorder(),refinement.space,24):
            adaptive.assemble_curved(refinement.space,quadrature_order=24)
            fine=numerics.assemble_curved(refinement.space,quadrature_order=24)
        for a,b in zip(coarse,fine):
            relative=np.linalg.norm((refinement.prolongation.T@b@refinement.prolongation-a).data)/np.linalg.norm(a.data)
            self.assertLess(relative,1e-10)

    def test_actual_worker_preserves_original_adaptive_fields_rf_and_quadrature(self):
        import test_adaptive_efficiency_worker as fixtures
        from superfish_ng.adaptive_efficiency_worker import execute_efficiency_worker
        from superfish_ng.adaptive_refinement import _assemble
        from superfish_ng.saved import read_solution
        fixture=fixtures.AdaptiveEfficiencyWorkerTests;fixture.setUpClass()
        try:
            execution=next(r for r in fixture.plan['executions'] if r['id']=='sphere-repetition-1-adaptive')
            with tempfile.TemporaryDirectory() as tmp:
                result=execute_efficiency_worker(execution,fixture.bindings,Path(tmp)/'actual',max_new_levels=2)
                original,_=_assemble(execution['request'],result['level_runs'])
                for before,after in zip(original['levels'],result['levels']):
                    for key in ('quantities','indicator','current_mode_ids','marked_cells','refinement_kind','surface','quadrature_check'):
                        self.assertEqual(before[key],after[key])
                    saved=read_solution(after['run'])
                    self.assertEqual(numerics.quadrature_check(saved,after['mode_index']),after['rf_quadrature_check'])
                    self.assertEqual(after['high_order_assembly_reuse']['original_assemblies'],1)
                    self.assertEqual(after['high_order_assembly_reuse']['original_assembly_calls'],1)
                    self.assertEqual(after['high_order_assembly_reuse']['cache_hits'],1)
                self.assertIsNone(result['confirmed_accuracy_hit_index'])
        finally:fixture.tearDownClass()


if __name__=='__main__':unittest.main()
