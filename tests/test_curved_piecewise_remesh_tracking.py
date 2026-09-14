# SPDX-License-Identifier: Apache-2.0
"""Non-affine curved comparison maps, independent of the solved meshes."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
import numpy as np
from scipy.integrate import dblquad
from superfish_ng import Case, solve, make_mesh
from superfish_ng.curved_space import case_curved_space
from superfish_ng.mesh_input import mesh_to_dict, mesh_from_dict
from superfish_ng.piecewise_remesh_tracking import track_piecewise_remesh_modes
from superfish_ng.saved_mode_tracking import save_mode_tracking, read_mode_tracking, validate_tracking_controls
from superfish_ng.mode_tracking_history import start_mode_history, extend_mode_history
from superfish_ng.io import save_run


def curved_comparison_fixture(scale=1.):
    raw=Case.load('examples/curved_ellipse.json').to_dict()
    raw['mesh']['geometry_order']=2;raw['mesh']['contour_mesh'].update(max_edge_m=.08*scale,min_angle_deg=5.)
    raw['solver']['quadrature_order']=12
    g=raw['geometry'];g['curves'][0]['end_zr_m'][0]=.2*scale
    arc=g['curves'][1];arc.update(center_zr_m=[.1*scale,0.],semiaxes_m=[.1*scale,.08*scale],sweep_rad=np.pi/2)
    g['curves'].append(dict(arc,start_rad=np.pi/2));g['edge_tags'].append('pec')
    g.update(segments_per_curve=[1,3,3],chord_tolerance_m=.008*scale,join_tolerance_m=1e-14*scale)
    old=Case.from_dict(raw);source=mesh_to_dict(make_mesh(old))
    new=deepcopy(raw);new['geometry']['curves'][1].update(center_zr_m=[.08*scale,0.],semiaxes_m=[.12*scale,.09*scale])
    new['geometry']['curves'][2].update(center_zr_m=[.08*scale,0.],semiaxes_m=[.08*scale,.09*scale])
    target=deepcopy(source)
    for p in target['points']:
        p[0]*=1.125
        p[1]=.8*p[1] if p[1]<=.1*scale else .08*scale+1.2*(p[1]-.1*scale)
    current=Case.from_dict(new)
    documents=[dict(schema_version=2,source_mesh=mesh,curved_refinement_levels=0) for mesh in (source,target)]
    return (old,current),documents


CONTROLS=dict(mapping='piecewise_remesh',sample_order=8,minimum_overlap=.9,
    minimum_assignment_margin=.05,relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)


class CurvedPiecewiseRemeshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases,cls.maps=curved_comparison_fixture()
        cls.solutions=[solve(cls.cases[0],mesh_data=cls.maps[0]['source_mesh']),
                       solve(replace(cls.cases[1],curved_refinement_levels=1),mesh_data=cls.maps[1]['source_mesh'])]
        cls.controls=dict(CONTROLS,comparison_meshes=cls.maps)

    def test_native_nonaffine_domains_and_independent_solver_connectivity(self):
        result=track_piecewise_remesh_modes(*self.solutions,['A'],**self.controls)
        self.assertEqual(result['status'],'PASS')
        mapping=result['physical_mapping']
        self.assertEqual(mapping['comparison_geometry_order'],2)
        self.assertEqual(mapping['solver_triangle_counts'][1],4*mapping['solver_triangle_counts'][0])
        self.assertEqual(mapping['comparison_triangle_count'],mapping['solver_triangle_counts'][0])
        self.assertAlmostEqual(mapping['axisymmetric_volumes_m3'][1]/mapping['axisymmetric_volumes_m3'][0],1.125**2,places=12)
        self.assertTrue(all(b['maximum_coefficient_distance_m']<=b['roundoff_tolerance_m'] for b in mapping['boundary_coincidence']))

    def test_variable_curved_volume_weight_against_independent_integrals(self):
        # Analytic test field u=1, Hphi=r. These adapters are not eigenmodes.
        solutions=[replace(s,u=np.ones_like(s.u)) for s in self.solutions]
        result=track_piecewise_remesh_modes(*solutions,['polynomial'],**self.controls)
        spaces=[case_curved_space(case,mesh_from_dict(case,m['source_mesh'])) for case,m in zip(self.cases,self.maps)]
        def evaluate(nodes,x,y):
            l=1-x-y
            basis=np.array([l*(2*l-1),x*(2*x-1),y*(2*y-1),4*l*x,4*x*y,4*y*l])
            dx=np.array([1-4*l,4*x-1,0,4*(l-x),4*y,-4*y])
            dy=np.array([1-4*l,0,4*y-1,-4*x,4*x,4*(l-y)])
            return (basis@nodes)[0],float(np.linalg.det(np.column_stack((dx@nodes,dy@nodes))))
        totals=np.zeros(3)
        for i in range(len(spaces[0].geometry.cell_nodes)):
            points=[s.geometry.points_rz_m[s.geometry.cell_nodes[i]] for s in spaces]
            def integrand(x,y,kind):
                (r0,d0),(r1,d1)=[evaluate(p,x,y) for p in points]
                return [(r0*r1)**1.5*np.sqrt(d0*d1),r0**3*d0,r1**3*d1][kind]
            for kind in range(3):totals[kind]+=dblquad(lambda y,x:integrand(x,y,kind),0,1,lambda x:0,lambda x:1-x,epsabs=1e-15,epsrel=1e-10)[0]
        expected=totals[0]/np.sqrt(totals[1]*totals[2])
        self.assertLess(expected,.999)
        self.assertAlmostEqual(result['matches'][0]['minimum_principal_overlap'],expected,places=8)

    def test_saved_history_reverse_and_refined_comparison_mesh(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,s in zip(('old','new'),self.solutions):save_run(s.case,s,root/name)
            pair=save_mode_tracking(dict(schema_version=1,previous_run='old',current_run='new',previous_ids=['A'],controls=self.controls),root/'pair.json',base_directory=root)
            self.assertEqual(read_mode_tracking(root/'pair.json'),pair)
            history=extend_mode_history(start_mode_history(pair),dict(current_run='old',controls=dict(self.controls,comparison_meshes=self.maps[::-1])),base_directory=root)
            self.assertEqual(history['status'],'PASS');self.assertEqual(history['current_mode_ids'],['A'])
            self.assertAlmostEqual(pair['tracking']['matches'][0]['minimum_principal_overlap'],history['steps'][1]['tracking']['matches'][0]['minimum_principal_overlap'],places=13)
        refined=[dict(m,curved_refinement_levels=1) for m in self.maps]
        result=track_piecewise_remesh_modes(*self.solutions,['A'],**dict(self.controls,comparison_meshes=refined))
        self.assertEqual(result['status'],'PASS')

    def test_strict_versioned_declarations_and_no_mixed_geometry(self):
        validate_tracking_controls(self.controls)
        invalid=[]
        for change in ({'unknown':1},{'curved_refinement_levels':True},{'curved_refinement_levels':-1},
                       {'curved_refinement_steps':[]},{'curved_refinement_steps':[{'kind':'uniform'}]},
                       {'schema_version':True}):
            bad=deepcopy(self.maps);bad[0].update(change);invalid.append(bad)
        invalid.append([self.maps[0],self.maps[1]['source_mesh']])
        for bad in invalid:
            with self.subTest(bad=bad[0].keys()),self.assertRaises(ValueError):validate_tracking_controls(dict(self.controls,comparison_meshes=bad))
        straight=solve(Case(((0.,.1),(.2,.1)),nr=2,nz=3))
        with self.assertRaisesRegex(ValueError,'curved'):
            track_piecewise_remesh_modes(self.solutions[0],straight,['A'],**self.controls)

    def test_wrong_boundary_fold_connectivity_and_budget_are_rejected(self):
        bad=deepcopy(self.maps);bad[1]['source_mesh']['points'][0][0]+=.001
        with self.assertRaises(ValueError):track_piecewise_remesh_modes(*self.solutions,['A'],**dict(self.controls,comparison_meshes=bad))
        bad=deepcopy(self.maps)
        for m in bad:m['source_mesh']['triangles'][0].reverse()
        with self.assertRaises(ValueError):track_piecewise_remesh_modes(*self.solutions,['A'],**dict(self.controls,comparison_meshes=bad))
        bad=deepcopy(self.maps);bad[1]['curved_refinement_levels']=1
        with self.assertRaisesRegex(ValueError,'connectivity'):
            track_piecewise_remesh_modes(*self.solutions,['A'],**dict(self.controls,comparison_meshes=bad))
        bad=deepcopy(self.maps)
        for m in bad:m['curved_refinement_levels']=12
        with self.assertRaisesRegex(ValueError,'(budget|samples|maximum|max_triangles)'):
            track_piecewise_remesh_modes(*self.solutions,['A'],**dict(self.controls,comparison_meshes=bad))
        different=replace(self.cases[0],curve_segments_per_curve=(1,4,4),contour=None)
        reprojected=solve(different)
        with self.assertRaisesRegex(ValueError,'(boundary|mesh)'):
            track_piecewise_remesh_modes(reprojected,self.solutions[1],['A'],**self.controls)

    def test_explicit_native_mesh_without_generator_controls(self):
        solutions=[replace(s,case=replace(s.case,contour_mesh=None)) for s in self.solutions]
        result=track_piecewise_remesh_modes(*solutions,['A'],**self.controls)
        self.assertEqual(result['status'],'PASS')

    def test_ordered_comparison_history_preserves_the_same_volume_map(self):
        levels=[dict(m,curved_refinement_levels=1) for m in self.maps]
        steps=[dict(schema_version=2,source_mesh=m['source_mesh'],curved_refinement_steps=[{'kind':'uniform'}]) for m in self.maps]
        before=deepcopy(steps)
        a=track_piecewise_remesh_modes(*self.solutions,['A'],**dict(self.controls,comparison_meshes=levels))
        b=track_piecewise_remesh_modes(*self.solutions,['A'],**dict(self.controls,comparison_meshes=steps))
        np.testing.assert_array_equal(a['overlap_matrix'],b['overlap_matrix'])
        self.assertEqual(a['physical_mapping']['axisymmetric_volumes_m3'],b['physical_mapping']['axisymmetric_volumes_m3'])
        self.assertEqual(steps,before)

    def test_whole_quadratic_boundary_is_checked_before_sampling(self):
        old=self.solutions[0];g=old.space.geometry;points=g.points_rz_m.copy()
        mid=g.boundary_nodes[np.flatnonzero(old.space.boundary_tags=='pec')[0],2]
        points[mid,0]+=.0001
        changed=replace(old,space=replace(old.space,geometry=replace(g,points_rz_m=points)))
        with self.assertRaisesRegex(ValueError,'quadratic boundary'):
            track_piecewise_remesh_modes(changed,self.solutions[1],['A'],**self.controls)
