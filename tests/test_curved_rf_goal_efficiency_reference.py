# SPDX-License-Identifier: Apache-2.0
"""Independent Maxwell energy, Green moments and full-domain scaling."""
import math
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np

from superfish_ng.adaptive_efficiency_analytic_grid import build_analytic_efficiency_grid
from superfish_ng.config import Case
from superfish_ng.constants import EPS0,MU0
from superfish_ng.curved_rf_goal_efficiency_reference import build_sphere_rf_goal_reference, map_prolate_rf_goal_points
from superfish_ng.curved_rf_goal_efficiency_reference import (_modern_arrays, _reference_two_changes,
    _historical_source, _bindings, load_curved_rf_goal_efficiency_reference)
from superfish_ng.curved_space import case_curved_space
from superfish_ng.mesh_input import mesh_from_dict


def moments(request):
    case=Case.from_dict(request['case']);g=case_curved_space(case,mesh_from_dict(case,request['initial_mesh'])).geometry
    x,w=np.polynomial.legendre.leggauss(8);t=(x+1)/2;w=w/2
    n=np.column_stack(((1-t)*(1-2*t),t*(2*t-1),4*t*(1-t)))
    d=np.column_stack((4*t-3,4*t-1,4-8*t))
    result=np.zeros(3)
    for ids in g.boundary_nodes:
        p=n@g.points_rz_m[ids];dp=d@g.points_rz_m[ids]
        r,z=p.T;dr,dz=dp.T
        result += [np.dot(w,r*dz-z*dr)/2,math.pi*np.dot(w,r*r*dz),np.dot(w,r**4*dz)/4]
    return np.abs(result)


def prolate_grid(order=16,scale=1):
    # Uniform theta partition independently of the native volume-map code.
    x,w=np.polynomial.legendre.leggauss(order);s=(x+1)/2
    initial=map_prolate_rf_goal_points('prolate-scale-1',[[.01,.16]])
    pieces=initial['native_wall_parameter_partitions'];points=[];weights=[]
    for lo,hi in pieces:
        theta=math.pi*(lo+(hi-lo)*s)
        r=.08*np.sin(theta)[:,None]*s[None,:]
        z=.16+.16*np.cos(theta)[:,None]*s[None,:]
        points.append(np.column_stack((r.ravel(),z.ravel()))*scale)
        weights.append((2*math.pi*.16*.08*(.08*np.sin(theta))[:,None]*s[None,:]**2*
                        math.pi*(hi-lo)/4*w[:,None]*w[None,:]).ravel()*scale**3)
    return np.concatenate(points),np.concatenate(weights)


class CurvedRFGoalReferenceGeometryTests(unittest.TestCase):
    def setUp(self):
        self.guard=patch('superfish_ng.curved_solution.eigsh',side_effect=AssertionError('no native eigensolve'))
        self.guard.start();self.addCleanup(self.guard.stop)

    def test_sphere_both_scales_orders_exact_energy_and_full_volume(self):
        for scale in (1,2):
            for order in (16,24):
                with self.subTest(scale=scale,order=order):
                    grid=build_sphere_rf_goal_reference(f'sphere-scale-{scale}',order=order)
                    w=grid['volume_weights_m3'];f=grid['reference_fields']
                    self.assertLess(abs(w.sum()/(4*math.pi*(.08*scale)**3/3)-1),1e-12)
                    self.assertLess(abs(EPS0/4*np.dot(w,np.sum(f[:,:2]**2,axis=1))/(scale**2/2)-1),1e-11)
                    self.assertLess(abs(MU0/4*np.dot(w,f[:,2]**2)/(scale**2/2)-1),1e-11)
                    self.assertLess(abs(grid['axis_weights_m'].sum()/(.16*scale)-1),1e-12)
                    self.assertLess(abs(np.dot(w,grid['native_volume_density_ratio'])/moments(grid['request'])[1]-1),1e-12)
                    self.assertEqual(grid['native_accuracy_status'],'NOT_RUN')

    def test_sphere_scale_one_matches_old_math_and_scale_two_is_maxwell(self):
        a=build_sphere_rf_goal_reference('sphere-scale-1');b=build_sphere_rf_goal_reference('sphere-scale-2')
        old=build_analytic_efficiency_grid('sphere',Case.from_dict(a['request']['case']),a['source_mesh'])
        for key in ('reference_fields','reference_axis_ez','native_volume_points_rz_m','volume_weights_m3','axis_points_rz_m'):
            np.testing.assert_array_equal(a[key],old[key])
        np.testing.assert_allclose(b['reference_fields']*math.sqrt(2),a['reference_fields'],rtol=2e-13,atol=1e-10)
        np.testing.assert_allclose(b['reference_axis_ez']*math.sqrt(2),a['reference_axis_ez'],rtol=2e-13,atol=1e-10)
        np.testing.assert_array_equal(b['volume_weights_m3'],8*a['volume_weights_m3'])
        for key in ('r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm','epk_over_eacc','bpk_over_eacc_mt_per_mv_per_m'):
            self.assertLess(abs(a['reference_quantities'][key]/b['reference_quantities'][key]-1),1e-12)
        self.assertLess(abs(2*b['reference_quantities']['frequency_hz']/a['reference_quantities']['frequency_hz']-1),1e-12)

    def test_prolate_full_p2_area_volume_and_hphi_r_mass_match_green(self):
        for scale in (1,2):
            p,w=prolate_grid(scale=scale)
            m=map_prolate_rf_goal_points(f'prolate-scale-{scale}',p)
            mapped=m['native_volume_points_rz_m'];v=w*m['native_volume_density_ratio'];r=mapped[:,0]
            actual=np.array([np.sum(v/(2*math.pi*r)),np.sum(v),np.sum(v*r*r/(2*math.pi))])
            np.testing.assert_allclose(actual,moments(m['request']),rtol=1e-12,atol=0)
            self.assertLess(abs(w.sum()/(4*math.pi*(.16*scale)*(.08*scale)**2/3)-1),1e-12)
            self.assertGreater(np.max(abs(mapped-p)),1e-9*scale)
            self.assertEqual(m['supplied_point_count'],len(p))

    def test_prolate_scale_and_point_permutation_keep_all_native_points(self):
        p,w=prolate_grid();a=map_prolate_rf_goal_points('prolate-scale-1',p)
        b=map_prolate_rf_goal_points('prolate-scale-2',2*p)
        np.testing.assert_array_equal(b['native_volume_points_rz_m'],2*a['native_volume_points_rz_m'])
        np.testing.assert_array_equal(b['native_volume_density_ratio'],a['native_volume_density_ratio'])
        c=map_prolate_rf_goal_points('prolate-scale-1',p[::-1])
        np.testing.assert_array_equal(c['native_volume_points_rz_m'],a['native_volume_points_rz_m'][::-1])
        np.testing.assert_array_equal(c['native_volume_density_ratio'],a['native_volume_density_ratio'][::-1])

    def test_missing_outside_nonfinite_points_and_wrong_fixed_inputs_fail(self):
        for p in ([],[[0.,.16]],[[.1,.16]],[[.01,float('nan')]],[[True,False]],[[1.]],['x']):
            with self.subTest(points=p),self.assertRaises(ValueError):map_prolate_rf_goal_points('prolate-scale-1',p)
        for case_id in ('prolate','sphere-scale-1','prolate-scale-3',1,True):
            with self.assertRaises(ValueError):map_prolate_rf_goal_points(case_id,[[.01,.16]])
        for order in (True,16.,8,32):
            with self.assertRaises(ValueError):build_sphere_rf_goal_reference('sphere-scale-1',order=order)


class CurvedRFGoalReferenceIntegrityTests(unittest.TestCase):
    def test_reference_binding_relocation_requires_every_original_input_and_exact_archive_sha(self):
        from superfish_ng.curved_rf_goal_efficiency_reference import _verify_reference_bindings
        from superfish_ng.completion import digest
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.py';archive=root/'archive.py';grid=root/'grid.npz';extra=root/'extra.py'
            source.write_text('current source');archive.write_text('original source');grid.write_bytes(b'fixed independent grid');extra.write_text('optional implementation source')
            a=digest(archive);g=digest(grid);e=digest(extra)
            required={str(archive):a,str(grid):g}
            reference=dict(required_bound_inputs=required,bound_inputs=dict(required,**{str(extra):e}),
                source_relocations={str(source):dict(path=str(archive),sha256=a)})
            archives={a:str(archive),e:str(extra)}
            original={str(source):a,str(grid):g}
            _verify_reference_bindings(original,reference,archives)
            _verify_reference_bindings(dict(required,**{str(extra):e}),reference,archives)
            for bad in ({str(grid):g},{str(source):a},{str(source):'0'*64,str(grid):g},
                        {str(root/'wrong-source.py'):a,str(grid):g},dict(original,unknown='0'*64),
                        dict(original,**{str(root/'extra-source.py'):[]})):
                with self.subTest(bad=bad),self.assertRaises(ValueError):_verify_reference_bindings(bad,reference,archives)

    def test_explicit_historical_archive_binds_exact_bytes_and_never_executes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);current=root/'current.py';archive=root/'archive.py'
            current.write_text('changed current source\n')
            archive.write_text('raise AssertionError("provenance archive must never execute")\n')
            sha=hashlib.sha256(archive.read_bytes()).hexdigest();bound={}
            with self.assertRaises(ValueError):_historical_source(current,sha,bound,{})
            self.assertEqual(_historical_source(current,sha,bound,{}, {sha:str(archive)}),archive)
            self.assertEqual(bound,{str(archive):sha})
            for bad in ({sha:'relative.py'},{sha:str(current)},[]):
                with self.subTest(bad=bad),self.assertRaises(ValueError):_historical_source(current,sha,{}, {},bad)
            archive.write_text('altered archive\n')
            with self.assertRaises(ValueError):_historical_source(current,sha,{}, {},{sha:str(archive)})

    def arrays(self):
        return dict(analytic_volume_points_rz_m=np.ones((4,2)), volume_weights_m3=np.ones(4),
                    axis_points_rz_m=np.column_stack((np.zeros(2),np.arange(2))),axis_weights_m=np.ones(2),
                    fixed_native_volume_points_rz_m=np.ones((4,2)),native_volume_density_ratio=np.ones(4),
                    reference_fields_levels=np.ones((3,6,5,3)),reference_selected_indices=np.array([[0,1,2]]*3),
                    reference_target_indices=np.zeros(3,dtype=int),reference_frequencies_hz_levels=np.ones((3,5)))

    def quantities(self):
        return [dict(frequency_hz=1.,r_over_q_accelerator_ohm=2.,r_over_q_circuit_ohm=1.,geometry_factor_ohm=1.,
                     epk_over_eacc=1.,bpk_over_eacc_mt_per_mv_per_m=1.) for _ in range(3)]

    def test_complete_h_modes_points_indices_weights_and_axis_are_mandatory(self):
        original=self.arrays();_modern_arrays(original,4,2)
        for key in original:
            a=deepcopy(original);a.pop(key)
            with self.subTest(missing=key),self.assertRaises(ValueError):_modern_arrays(a,4,2)
        changes=[('reference_fields_levels',np.ones((2,6,5,3))),('reference_fields_levels',np.ones((3,6,4,3))),
                 ('reference_fields_levels',np.ones((3,5,5,3))),('axis_points_rz_m',np.ones((2,2))),
                 ('volume_weights_m3',np.array([1.,1.,1.,0.])),('native_volume_density_ratio',np.full(4,np.nan)),
                 ('reference_target_indices',np.ones(3,dtype=int)),('reference_selected_indices',np.zeros((3,3),dtype=int)),
                 ('reference_selected_indices',np.zeros((3,3),dtype=bool))]
        for key,value in changes:
            a=deepcopy(original);a[key]=value
            with self.subTest(key=key,shape=value.shape),self.assertRaises(ValueError):_modern_arrays(a,4,2)

    def test_one_common_sign_axis_and_all_nine_reference_gates(self):
        a=self.arrays();q=self.quantities()
        a['reference_fields_levels'][1]*=-1
        rows=_reference_two_changes(a,q)
        self.assertTrue(all(r['status']=='PASS' and r['single_sign']==-1 for r in rows))
        for key in q[0]:
            bad=deepcopy(q);bad[1][key]*=2
            with self.subTest(quantity=key),self.assertRaises(ValueError):_reference_two_changes(a,bad)
        for region,component in ((slice(0,4),0),(slice(0,4),2),(slice(4,6),1)):
            b=deepcopy(a);b['reference_fields_levels'][1,region,0,component]*=-1
            with self.subTest(region=region,component=component),self.assertRaises(ValueError):_reference_two_changes(b,q)

    def test_rehashed_missing_unknown_manifest_bindings_fail_before_data(self):
        bindings,_,_=_bindings(None)
        bads=[{},dict(bindings,extra={}),dict(bindings,prolate_manifest=dict(bindings['prolate_manifest'],sha256='0'*64)),
              dict(bindings,prolate_manifest=dict(bindings['prolate_manifest'],path='/tmp/nonexistent-rf-goal-reference.json'))]
        for bad in bads:
            with self.subTest(keys=list(bad)),self.assertRaises(ValueError):
                load_curved_rf_goal_efficiency_reference('prolate-scale-1',bindings=bad)
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'manifest.json';source=Path(bindings['prolate_manifest']['path']).read_bytes();p.write_bytes(source+b' ')
            for expected in (bindings['prolate_manifest']['sha256'],hashlib.sha256(p.read_bytes()).hexdigest()):
                bad=deepcopy(bindings);bad['prolate_manifest']=dict(path=str(p),sha256=expected)
                with self.assertRaises(ValueError):load_curved_rf_goal_efficiency_reference('prolate-scale-1',bindings=bad)

    def test_historical_source_alias_preserves_exact_bytes_and_refuses_symlinks(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);old=root/'old.py';archive=root/'archive.py';data=b'original source\n';digest=hashlib.sha256(data).hexdigest()
            archive.write_bytes(data);old.write_bytes(b'later implementation\n')
            aliases={str(old):dict(path=str(archive),sha256=digest)};bound={}
            self.assertEqual(_historical_source(old,digest,bound,aliases),archive)
            self.assertEqual(bound,{str(archive):digest})
            archive.write_bytes(data+b' ')
            with self.assertRaises(ValueError):_historical_source(old,digest,{},aliases)
            archive.write_bytes(data);old.unlink();old.symlink_to(archive)
            with self.assertRaisesRegex(ValueError,'symlink'):_historical_source(old,digest,{},aliases)
            old.unlink();archive.unlink()
            with self.assertRaises(ValueError):_historical_source(old,digest,{},aliases)


if __name__=='__main__':unittest.main()
