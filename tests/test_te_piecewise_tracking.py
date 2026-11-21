# SPDX-License-Identifier: Apache-2.0
"""Independent physical weighting and native TE polygon correspondence."""
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch
import json,tempfile,unittest
import numpy as np
from scipy.integrate import dblquad
from superfish_ng import Case,solve
from superfish_ng.model import Model
from superfish_ng.mesh import make_mesh
from superfish_ng.mesh_input import mesh_to_dict
from superfish_ng.piecewise_remesh_tracking import track_piecewise_remesh_modes


CONTROLS=dict(mapping='piecewise_remesh',sample_order=10,minimum_overlap=.8,
              minimum_assignment_margin=.05,relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)


class TEPiecewiseTrackingTests(unittest.TestCase):
    def test_independent_nonuniform_volume_integral_uses_electric_phi(self):
        cases=[Case(((0.,1.),(.5,1.),(1.,1.)),nr=2,nz=2,model=Model(polarization='te')),
               Case(((0.,1.),(.35,.8),(1.,1.)),nr=2,nz=2,model=Model(polarization='te'))]
        maps=[mesh_to_dict(make_mesh(cases[0]))];current=deepcopy(maps[0])
        for p in current['points']:
            if p[1]==.5:p[0]*=.8;p[1]=.35
        maps.append(current)
        solutions=[SimpleNamespace(case=c,mesh=make_mesh(c),reflection_source_case=None,frequencies_hz=np.array([1.])) for c in cases]
        sampler=SimpleNamespace(evaluate=lambda points,*a,**kw:dict(Ephi_V_per_m=points[:,0]))
        cross=old=new=0.
        for triangle in maps[0]['triangles']:
            vertices=[np.array(m['points'])[triangle] for m in maps]
            det=[np.linalg.det(np.column_stack((v[1]-v[0],v[2]-v[0]))) for v in vertices]
            def radius(k,x,y):return (vertices[k][0]*(1-x-y)+vertices[k][1]*x+vertices[k][2]*y)[0]
            def integrate(fn):return dblquad(lambda y,x:fn(x,y),0.,1.,lambda x:0.,lambda x:1-x,epsabs=1e-11,epsrel=1e-11)[0]
            cross+=integrate(lambda x,y:(radius(0,x,y)*radius(1,x,y))**1.5*np.sqrt(det[0]*det[1]))
            old+=integrate(lambda x,y:radius(0,x,y)**3*det[0]);new+=integrate(lambda x,y:radius(1,x,y)**3*det[1])
        expected=cross/np.sqrt(old*new)
        self.assertLess(expected,.999)
        with patch('superfish_ng.piecewise_remesh_tracking.FieldSampler.from_solution',return_value=sampler):
            result=track_piecewise_remesh_modes(*solutions,['electric-polynomial'],comparison_meshes=maps,**CONTROLS)
        self.assertAlmostEqual(result['matches'][0]['minimum_principal_overlap'],expected,places=8)
        self.assertEqual(result['physical_mapping']['field'],'Ephi_V_per_m')

    def test_actual_step_scale_native_saved_history_and_reverse(self):
        from superfish_ng.io import save_run
        from superfish_ng.te import TEFieldSampler,te_quantities
        from superfish_ng.saved_mode_tracking import build_saved_mode_tracking,replay_mode_tracking
        from superfish_ng.mode_tracking_history import start_mode_history,extend_mode_history
        from superfish_ng.te_saved import read_te_run
        case=Case(((0.,.0625),(.0625,.0625),(.0625,.09375),(.125,.09375)),
            geometry_type='stepped_profile',nr=10,nz=16,modes=2,element_order=2,model=Model(polarization='te'))
        scaled=replace(case,profile=tuple((1.25*z,1.25*r) for z,r in case.profile),nr=14,nz=20)
        maps=[mesh_to_dict(make_mesh(replace(case,nr=2,nz=4)))];other=deepcopy(maps[0])
        other['points']=(np.asarray(other['points'])*1.25).tolist();maps.append(other)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);solutions=[]
            for i,c in enumerate((case,scaled)):
                s=solve(c);save_run(c,s,root/str(i));solutions.append(read_te_run(root/str(i)))
            controls=CONTROLS|dict(comparison_meshes=maps)
            native_before=native_hashes(root/'0',root/'1')
            request=dict(schema_version=1,previous_run=str(root/'0'),current_run=str(root/'1'),previous_ids=['A','B'],controls=controls)
            pair=build_saved_mode_tracking(request)
            self.assertEqual(pair['status'],'PASS');self.assertEqual(pair['tracking']['current_mode_ids'],['A','B'])
            self.assertEqual(pair,replay_mode_tracking(pair))
            history=extend_mode_history(start_mode_history(pair),dict(current_run=str(root/'0'),controls=CONTROLS|dict(comparison_meshes=maps[::-1])))
            self.assertEqual(history['status'],'PASS');self.assertEqual(history['current_mode_ids'],['A','B'])
            for mode in range(2):
                a,b=solutions
                self.assertLess(abs(a.frequencies_hz[mode]/b.frequencies_hz[mode]/1.25-1),.003)
                points=a.mesh.points[a.mesh.triangles].mean(axis=1)
                fa=TEFieldSampler(a).evaluate(points,mode);fb=TEFieldSampler(b).evaluate(points*1.25,mode)
                sign=np.sign(fa['Ephi_V_per_m']@fb['Ephi_V_per_m'])
                for field in ('Ephi_V_per_m','Hr_quadrature_A_per_m','Hz_quadrature_A_per_m'):
                    error=np.linalg.norm(fa[field]-sign*fb[field]*1.25**1.5)/np.linalg.norm(fa[field])
                    self.assertLess(error,.08,(field,error))
                rf=[te_quantities(s,mode) for s in solutions]
                for value in rf:
                    self.assertIsNone(value['r_over_q_accelerator_ohm']);self.assertIsNone(value['r_over_q_circuit_ohm'])
                    self.assertAlmostEqual(value['stored_energy_j'],1.,places=10)
            self.assertEqual(native_before,native_hashes(root/'0',root/'1'))
            mapping=pair['tracking']['physical_mapping']
            self.assertEqual(mapping['field'],'Ephi_V_per_m')
            self.assertNotEqual(*mapping['solver_triangle_counts'])
            self.assertAlmostEqual(mapping['axisymmetric_volumes_m3'][1]/mapping['axisymmetric_volumes_m3'][0],1.25**3)

    def test_both_source_planes_electric_and_magnetic_parities_with_original_fields(self):
        from superfish_ng.te_reflection import reflect_te_solution
        from superfish_ng.te import TEFieldSampler,te_quantities
        for order in (1,2):
            for side in ('z_min','z_max'):
                for tag in ('electric_symmetry','magnetic_symmetry'):
                    with self.subTest(order=order,side=side,tag=tag):
                        case=Case(((0.,.0625),(.0625,.0625),(.0625,.09375),(.125,.09375)),
                            geometry_type='stepped_profile',nr=6,nz=10,modes=1,element_order=order,model=Model(polarization='te'),**{side:tag})
                        scaled=replace(case,profile=tuple((1.25*z,1.25*r) for z,r in case.profile))
                        half=[solve(c) for c in (case,scaled)]
                        full=[reflect_te_solution(c,s)[1] for c,s in zip((case,scaled),half)]
                        maps=[mesh_to_dict(make_mesh(replace(case,nr=2,nz=4)))];other=deepcopy(maps[0]);other['points']=(np.array(other['points'])*1.25).tolist();maps.append(other)
                        report=track_piecewise_remesh_modes(*full,['sector-A'],comparison_meshes=maps,**CONTROLS)
                        self.assertEqual(report['status'],'PASS');self.assertEqual(report['current_mode_ids'],['sector-A'])
                        mapping=report['physical_mapping'];self.assertTrue(mapping['symmetry_sector']['reflected'])
                        self.assertIn('not full-spectrum',mapping['symmetry_sector']['mode_indices'])
                        self.assertEqual(mapping['sample_count'],2*len(maps[0]['triangles'])*CONTROLS['sample_order']**2)
                        for source,s in zip(half,full):
                            points=source.mesh.points[source.mesh.triangles].mean(axis=1)
                            plane=0. if side=='z_min' else case.length
                            shift=case.length if side=='z_min' else 0.
                            if s is full[1]:plane*=1.25;shift*=1.25
                            original=points.copy();original[:,1]+=shift
                            mirror=points.copy();mirror[:,1]=2*plane-mirror[:,1]+shift
                            f=TEFieldSampler(s).evaluate(original);g=TEFieldSampler(s).evaluate(mirror)
                            parity=1 if tag=='magnetic_symmetry' else -1
                            for field,sign in [('Ephi_V_per_m',parity),('Hz_quadrature_A_per_m',parity),('Hr_quadrature_A_per_m',-parity)]:
                                np.testing.assert_allclose(g[field],sign*f[field],rtol=1e-9,atol=1e-7)
                            self.assertAlmostEqual(te_quantities(s)['stored_energy_j'],2.,places=10)
                            self.assertAlmostEqual(te_quantities(s)['wall_loss_w']/te_quantities(source)['wall_loss_w'],2.,places=10)
                        volume=case.contour.volume_m3 if case.contour else __import__('superfish_ng.contour',fromlist=['Contour']).Contour.from_profile(case).volume_m3
                        self.assertAlmostEqual(mapping['axisymmetric_volumes_m3'][0],2*volume,places=12)

    def test_guards_refuse_mixed_sector_and_malformed_domains_before_sampling(self):
        case=Case(((0.,1.),(1.,1.)),nr=2,nz=2,modes=1,model=Model(polarization='te'))
        a=SimpleNamespace(case=case,mesh=make_mesh(case),reflection_source_case=None,frequencies_hz=np.array([1.]))
        maps=[mesh_to_dict(a.mesh)]*2
        b=SimpleNamespace(**vars(a));b.case=replace(case,z_max='electric_symmetry')
        tm=SimpleNamespace(**vars(a));tm.case=replace(case,model=Model())
        reflected=SimpleNamespace(**vars(a));reflected.reflection_source_case=replace(case,z_max='magnetic_symmetry')
        for other in (b,tm,reflected):
            with self.subTest(case=other.case),patch('superfish_ng.piecewise_remesh_tracking.FieldSampler.from_solution',side_effect=AssertionError('invalid sector entered field sampling')):
                with self.assertRaises(ValueError):track_piecewise_remesh_modes(a,other,['A'],comparison_meshes=maps,**CONTROLS)
        for kind in ('missing','boundary','fold','tags','unknown'):
            bad=deepcopy(maps)
            if kind=='missing':
                for data in bad:data['triangles'].pop()
            elif kind=='boundary':bad[1]['points'][2][0]+=.1
            elif kind=='fold':bad[1]['points'][4][1]=2.
            elif kind=='tags':bad[1]['boundary_tags'][0]='magnetic_symmetry'
            else:bad[0]['unknown']=True
            with self.subTest(kind=kind),patch('superfish_ng.piecewise_remesh_tracking.FieldSampler.from_solution',side_effect=AssertionError('invalid domain entered field sampling')):
                with self.assertRaises(ValueError):track_piecewise_remesh_modes(a,a,['A'],comparison_meshes=bad,**CONTROLS)

    def test_reflection_sample_budget_counts_both_lobes_before_mesh_construction(self):
        case=Case(((0.,1.),(1.,1.)),nr=2,nz=2,modes=1,model=Model(polarization='te'),z_max='magnetic_symmetry')
        a=SimpleNamespace(case=case,mesh=make_mesh(case),reflection_source_case=case,frequencies_hz=np.array([1.]))
        data=mesh_to_dict(a.mesh);data['triangles']*=17
        with patch('superfish_ng.te_piecewise_remesh_tracking.mesh_from_dict',side_effect=AssertionError('budget exceeded before construction')):
            with self.assertRaisesRegex(ValueError,'262144'):track_piecewise_remesh_modes(a,a,['A'],comparison_meshes=[data,data],**(CONTROLS|dict(sample_order=32)))

    def test_actual_folded_contour_saved_geometry_and_electric_field_ids(self):
        from test_straight_tuning_geometry import request
        from superfish_ng.project import Project
        from superfish_ng.io import save_run
        from superfish_ng.saved_mode_tracking import build_saved_mode_tracking,replay_mode_tracking
        r=request('contour');r['project']['case']['model']['polarization']='te'
        r['project']['case']['mesh']['contour_mesh']=dict(max_edge_m=.03125,min_angle_deg=5.,max_triangles=20000,max_rounds=12)
        r['project']['case']['solver']['modes']=1
        case=Project.from_dict(r['project']).case
        polygon=case.contour;scaled=replace(case,contour=replace(polygon,vertices_zr_m=tuple((1.25*z,1.25*h) for z,h in polygon.vertices_zr_m)),
            contour_mesh=replace(case.contour_mesh,max_edge_m=case.contour_mesh.max_edge_m*1.25))
        maps=[r['shape_law']['reference_comparison_mesh']];other=deepcopy(maps[0]);other['points']=(np.array(other['points'])*1.25).tolist();maps.append(other)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);solutions=[]
            for i,c in enumerate((case,scaled)):
                s=solve(c);save_run(c,s,root/str(i));solutions.append(s)
            request=dict(schema_version=1,previous_run=str(root/'0'),current_run=str(root/'1'),previous_ids=['fold-A'],controls=CONTROLS|dict(comparison_meshes=maps))
            result=build_saved_mode_tracking(request)
            self.assertEqual(result['status'],'PASS');self.assertEqual(result['tracking']['current_mode_ids'],['fold-A'])
            self.assertEqual(result,replay_mode_tracking(result));self.assertEqual(result['tracking']['physical_mapping']['field'],'Ephi_V_per_m')
            self.assertAlmostEqual(solutions[0].frequencies_hz[0]/solutions[1].frequencies_hz[0],1.25,places=10)

    def test_actual_ambiguous_cluster_keeps_individual_ids_unresolved(self):
        case=Case(((0.,.0625),(.125,.0625)),nr=8,nz=12,modes=2,element_order=2,model=Model(polarization='te'))
        a=solve(case);data=mesh_to_dict(make_mesh(replace(case,nr=2,nz=4)))
        result=track_piecewise_remesh_modes(a,a,['A','B'],comparison_meshes=[data,data],**(CONTROLS|dict(relative_cluster_gap=.99)))
        self.assertFalse(result['individual_ids_complete'])
        self.assertEqual(result['current_mode_ids'],[None,None])


def native_hashes(*directories):
    import hashlib
    return [{p.relative_to(d).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in d.rglob('*') if p.is_file()} for d in directories]


class TEPiecewiseReflectionEvidenceTests(unittest.TestCase):
    def test_full_reflected_native_saved_pair_and_unmodified_source_bytes(self):
        from superfish_ng.io import save_run
        from superfish_ng.symmetry import reflect_solution
        from superfish_ng.saved_mode_tracking import build_saved_mode_tracking,replay_mode_tracking
        case=Case(((0.,.0625),(.0625,.0625),(.0625,.09375),(.125,.09375)),
            geometry_type='stepped_profile',nr=8,nz=12,modes=2,element_order=2,model=Model(polarization='te'),z_min='magnetic_symmetry')
        scaled=replace(case,profile=tuple((1.25*z,1.25*r) for z,r in case.profile))
        data=mesh_to_dict(make_mesh(replace(case,nr=2,nz=4)));other=deepcopy(data);other['points']=(np.array(other['points'])*1.25).tolist()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for i,c in enumerate((case,scaled)):
                full,solution=reflect_solution(c,solve(c));save_run(full,solution,root/str(i))
            before=native_hashes(root/'0',root/'1')
            request=dict(schema_version=1,previous_run=str(root/'0'),current_run=str(root/'1'),previous_ids=['A','B'],
                controls=CONTROLS|dict(comparison_meshes=[data,other]))
            result=build_saved_mode_tracking(request);self.assertEqual(result,replay_mode_tracking(result))
            self.assertEqual(result['status'],'PASS');self.assertEqual(result['tracking']['current_mode_ids'],['A','B'])
            self.assertTrue(result['tracking']['physical_mapping']['symmetry_sector']['reflected'])
            self.assertEqual(before,native_hashes(root/'0',root/'1'))

    def test_actual_second_lobe_is_sampled_instead_of_inferred_from_the_first(self):
        from superfish_ng.symmetry import reflect_solution
        case=Case(((0.,.0625),(.125,.0625)),nr=8,nz=12,modes=1,element_order=2,model=Model(polarization='te'),z_max='magnetic_symmetry')
        _,a=reflect_solution(case,solve(case))
        coefficients=a.coefficients_v_per_m2.copy()
        # Deliberately perturb interpolation coefficients for this sampling
        # test only; this array is neither published nor called an eigenmode.
        coefficients[a.space.dof_points[:,1]>case.length]=0.
        altered=replace(a,coefficients_v_per_m2=coefficients)
        data=mesh_to_dict(make_mesh(replace(case,nr=2,nz=4)))
        report=track_piecewise_remesh_modes(a,altered,['A'],comparison_meshes=[data,data],**CONTROLS)
        self.assertLess(report['overlap_matrix'][0][0],.8)
        self.assertEqual(report['status'],'UNVERIFIED')

    def test_uniform_mesh_scale_preserves_original_maxwell_fields_and_rf(self):
        from superfish_ng.te import TEFieldSampler,te_quantities
        case=Case(((0.,.0625),(.0625,.0625),(.0625,.09375),(.125,.09375)),
            geometry_type='stepped_profile',nr=10,nz=16,modes=2,element_order=2,model=Model(polarization='te'))
        scaled=replace(case,profile=tuple((1.25*z,1.25*r) for z,r in case.profile))
        a,b=solve(case),solve(scaled)
        np.testing.assert_allclose(a.frequencies_hz,1.25*b.frequencies_hz,rtol=2e-12)
        points=a.mesh.points[a.mesh.triangles].mean(axis=1)
        errors={}
        for mode in range(2):
            f=TEFieldSampler(a).evaluate(points,mode);g=TEFieldSampler(b).evaluate(points*1.25,mode)
            sign=np.sign(f['Ephi_V_per_m']@g['Ephi_V_per_m'])
            for field in ('Ephi_V_per_m','Hr_quadrature_A_per_m','Hz_quadrature_A_per_m'):
                error=float(np.linalg.norm(f[field]-sign*g[field]*1.25**1.5)/np.linalg.norm(f[field]))
                self.assertLess(error,1e-10);errors[str(mode)+'/'+field]=error
            rf=[te_quantities(s,mode) for s in (a,b)]
            self.assertAlmostEqual(rf[0]['geometry_factor_ohm']/rf[1]['geometry_factor_ohm'],1.,places=10)
            self.assertAlmostEqual(rf[1]['q0']/rf[0]['q0'],np.sqrt(1.25),places=10)
            for r in rf:
                self.assertIsNone(r['r_over_q_accelerator_ohm']);self.assertIsNone(r['r_over_q_circuit_ohm'])
                self.assertAlmostEqual(r['electric_energy_j'],.5,places=10);self.assertAlmostEqual(r['magnetic_energy_j'],.5,places=10)
        print('original stepped TE Ephi/Hr/Hz scale errors:',json.dumps(errors),flush=True)
