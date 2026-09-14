# SPDX-License-Identifier: Apache-2.0
"""Partition choices retain physics and prove independent reference coverage."""
from copy import deepcopy
from dataclasses import replace
import unittest
import numpy as np
from superfish_ng.curved_partition_schedule import build_partition_schedule, partition_index
from superfish_ng.project import Project
from test_curved_reference_partition import rectangle_project, CHART


def partition(project, chart, levels=0):
    return dict(source_mesh=deepcopy(project.mesh_data),reference_vertices=deepcopy(chart),
                curved_refinement_levels=levels,minimum_corner_angle_deg=.1)


def schedule():
    first=rectangle_project();second=rectangle_project(True)
    # Split the axis edge, preserving positive rz orientation and native tags.
    m=deepcopy(second.mesh_data);m['points'].append([0.,.1])
    m['triangles']=[[0,1,4],[4,1,3],[1,2,3]]
    m['boundary_edges']=[[0,4],[4,3],[3,2],[2,1],[1,0]]
    m['boundary_tags']=['axis','axis','pec','pec','pec']
    second=Project(second.case,mesh_data=m)
    return first,dict(schema_version=1,breakpoints=[.5],max_pair_tests=100000,
        partitions=[partition(first,CHART),partition(second,CHART+[[0.,.5]],1)])


class CurvedPartitionScheduleTests(unittest.TestCase):
    def test_different_initial_boundary_and_history_keep_physics_and_exact_coverage(self):
        from superfish_ng.curved_reference_partition import build_curved_reference_partition
        from superfish_ng.fem import triangle_quadrature
        base,s=schedule();before=deepcopy(s);projects=build_partition_schedule(base,s)
        self.assertEqual([len(p.mesh_data['triangles']) for p in projects],[2,3])
        self.assertEqual([p.case.curved_refinement_levels for p in projects],[0,1])
        for p in projects:
            self.assertEqual(p.case.curved_contour,base.case.curved_contour)
            self.assertEqual(p.case.acceleration_parameters,base.case.acceleration_parameters)
            self.assertEqual(p.case.modes,base.case.modes)
        overlay=build_curved_reference_partition(*projects,reference_vertices=[p['reference_vertices'] for p in s['partitions']],max_pair_tests=100000,max_triangles=1000)
        rule=list(triangle_quadrature(4));q=np.array([b[1:] for b,w in rule]);weights=np.array([w for b,w in rule])
        for side in (0,1):
            values=overlay.evaluate(side,q)
            self.assertAlmostEqual(sum(v['determinant_m2']@weights for v in values),.02,places=14)
            self.assertAlmostEqual(sum((2*np.pi*v['points_rz_m'][:,0]*v['determinant_m2'])@weights for v in values),np.pi*.1**2*.2,places=14)
        self.assertEqual(s,before)
        self.assertEqual([partition_index(s,x) for x in (.5,.8,.1,.5)],[1,1,0,1])

    def test_strict_schedule_rejects_unusable_reference_and_physics_overrides(self):
        base,s=schedule();invalid=[]
        for change in (dict(schema_version=True),dict(breakpoints=[float('nan')]),dict(breakpoints=[.5,.5]),dict(max_pair_tests=1),dict(partitions=[])):
            invalid.append(dict(s,**change))
        for change in (dict(solver={'modes':4}),dict(curved_refinement_steps=[]),dict(segments_per_curve=[True]*4)):
            bad=deepcopy(s);bad['partitions'][0].update(change);invalid.append(bad)
        bad=deepcopy(s);bad['partitions'][1]['reference_vertices'][4]=[.1,.5];invalid.append(bad)
        for bad in invalid:
            with self.subTest(bad=bad),self.assertRaises(ValueError):build_partition_schedule(base,bad)
        for value in (True,float('inf'),10**400):
            with self.assertRaises(ValueError):partition_index(s,value)

    def test_original_marked_history_is_not_inherited_by_replacement(self):
        from superfish_ng.curved_refinement_steps import CurvedRefinementStep
        base,s=schedule();base=replace(base,case=replace(base.case,curved_refinement_steps=(CurvedRefinementStep('marked',(0,),1.),)))
        projects=build_partition_schedule(base,s)
        self.assertTrue(all(not p.case.curved_refinement_steps for p in projects))

    def test_pec_curve_subdivision_changes_p2_domain_but_has_valid_reference_coverage(self):
        from test_curved_piecewise_remesh_tracking import curved_comparison_fixture
        from test_curved_harmonic_deformation import space
        from scripts.validate_large_curved_mesh_selection import boundary_moments
        from superfish_ng.curved_project_remesh import remesh_curved_project
        cases,documents=curved_comparison_fixture();base=Project(cases[0],mesh_data=documents[0]['source_mesh'])
        m=deepcopy(base.mesh_data);edge_index=m['boundary_tags'].index('pec');u,v=m['boundary_edges'][edge_index]
        owner=next(i for i,t in enumerate(m['triangles']) if {u,v}<=set(t));w=next(k for k in m['triangles'][owner] if k not in (u,v))
        chart=[[round(x*2**20)/2**20 for x in p] for p in m['points']];other_chart=deepcopy(chart)
        midpoint=len(m['points']);m['points'].append([(m['points'][u][k]+m['points'][v][k])/2 for k in (0,1)])
        other_chart.append([(chart[u][k]+chart[v][k])/2 for k in (0,1)])
        def oriented(t):
            p=np.array([m['points'][i] for i in t])
            return t if np.linalg.det(np.column_stack((p[1]-p[0],p[2]-p[0])))>0 else [t[0],t[2],t[1]]
        m['triangles'][owner]=oriented([u,midpoint,w]);m['triangles'].append(oriented([midpoint,v,w]))
        m['boundary_edges'][edge_index]=[u,midpoint];m['boundary_edges'].append([midpoint,v]);m['boundary_tags'].append('pec')
        candidate=Project(base.case,mesh_data=m)
        schedule=dict(schema_version=1,breakpoints=[.5],max_pair_tests=100000,
            partitions=[partition(base,chart),partition(candidate,other_chart)])
        projects=build_partition_schedule(base,schedule)
        moments=[boundary_moments(space(p)) for p in projects]
        self.assertGreater(abs(moments[1]['signed_volume_m3']/moments[0]['signed_volume_m3']-1),1e-8)
        with self.assertRaisesRegex(ValueError,'quadratic boundary differs'):
            remesh_curved_project(base,dict(schema_version=1,source_mesh=m,curved_refinement_levels=0,minimum_corner_angle_deg=.1))
        self.assertEqual(projects[0].case.curved_contour,projects[1].case.curved_contour)
