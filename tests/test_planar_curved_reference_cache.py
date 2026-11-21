# SPDX-License-Identifier: Apache-2.0
"""Exact reference-only reuse must preserve real mapped geometry and field data."""
import unittest
from unittest.mock import patch
import numpy as np
from superfish_ng import planar_curved_geometry as geometry
from superfish_ng.high_order import basis_p2
from test_planar_curved import patch as curved_patch


class ReferenceCacheTests(unittest.TestCase):
    def setUp(self):
        cache=getattr(geometry,'_cached_reference_basis',None)
        if cache is not None:cache.cache_clear()

    def test_identical_reference_rule_reused_across_different_real_geometry(self):
        first=curved_patch().elements[0]
        second=geometry.PlanarQuadraticTriangle(first.points_xy_m*2+[-.04,.03])
        parameters=geometry._canonical_boundary_parameters(np.linspace(0,1,8))
        refs=np.array([[u*(1-v),v] for u in np.linspace(0,1,8) for v in parameters])
        with patch.object(geometry,'basis_p2',wraps=geometry.basis_p2) as evaluate:
            a,b=first.evaluate(refs),second.evaluate(refs)
            self.assertEqual(evaluate.call_count,len(refs))
        np.testing.assert_array_equal(a['basis_values'],b['basis_values'])
        np.testing.assert_allclose(a['basis_values'].sum(axis=1),1,rtol=0,atol=1e-15)
        np.testing.assert_allclose(b['points_xy_m'],2*a['points_xy_m']+[-.04,.03],rtol=0,atol=2e-17)
        np.testing.assert_allclose(b['determinant_m2'],4*a['determinant_m2'],rtol=2e-14,atol=0)
        np.testing.assert_allclose(b['basis_gradients'],a['basis_gradients']/2,rtol=2e-14,atol=1e-12)
        # Explicit old basis calculation and original mapped arithmetic, bitwise.
        pairs=[basis_p2([1-x-y,x,y],geometry._GRADIENTS) for x,y in refs]
        values=np.array([x[0] for x in pairs]);gradients=np.array([x[1] for x in pairs])
        relative=first.points_xy_m-first.points_xy_m[0]
        jac=np.einsum('ia,qib->qab',relative,gradients)
        expected=dict(points_xy_m=first.points_xy_m[0]+values@relative,jacobian=jac,determinant_m2=np.linalg.det(jac),basis_values=values,basis_gradients=np.einsum('qia,qab->qib',gradients,np.linalg.inv(jac)))
        for name,value in expected.items():np.testing.assert_array_equal(a[name],value)

    def test_public_result_mutation_and_distinct_reference_rules_cannot_poison_cache(self):
        element=curved_patch().elements[0];refs=np.array([[.2,.3],[0.,0.],[.5,.5]])
        original=element.evaluate(refs)
        expected={k:v.copy() for k,v in original.items()}
        for value in original.values():value[:]=17.
        again=element.evaluate(refs)
        for name,value in expected.items():np.testing.assert_array_equal(again[name],value)
        distinct=refs.copy();distinct[0,0]=np.nextafter(distinct[0,0],0)
        self.assertFalse(np.array_equal(element.evaluate(distinct)['basis_values'],again['basis_values']))
        # Validation happens before reuse, including closed-boundary membership.
        for bad in ([[True,0]],[[np.nan,0]],[[-np.finfo(float).eps,0]],[[.5,np.nextafter(np.nextafter(.5,1),1)]]):
            with self.assertRaises(ValueError):element.evaluate(bad)

    def test_cache_storage_is_bounded_and_large_rules_bypass_reuse(self):
        element=curved_patch().elements[0]
        cache=geometry._cached_reference_basis
        for i in range(40):element.evaluate([[.1+i/1000,.3]])
        self.assertEqual(cache.cache_info().maxsize,32)
        self.assertLessEqual(cache.cache_info().currsize,32)
        before=cache.cache_info()
        refs=np.tile([[.2,.3]],(4097,1))
        a,b=element.evaluate(refs),element.evaluate(refs)
        self.assertEqual(cache.cache_info(),before)
        for name in a:np.testing.assert_array_equal(a[name],b[name])


if __name__=='__main__':unittest.main()
