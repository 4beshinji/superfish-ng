# SPDX-License-Identifier: Apache-2.0
"""Numbering invariance of boundary-anchored quadratic comparison maps."""
from copy import deepcopy
from dataclasses import replace
import unittest
import numpy as np
from superfish_ng.curved_space import case_curved_space
from superfish_ng.mesh_input import mesh_from_dict
from test_curved_piecewise_remesh_tracking import curved_comparison_fixture,CONTROLS


def automatic_maps(documents,*,renumber=True):
    result=deepcopy(documents)
    for i,document in enumerate(result):
        document.update(schema_version=3,boundary_pairing='ordered_curve_vertices')
        if renumber:document['source_mesh'],_=renumber_source(document['source_mesh'],seed=517+97*i)
    return result


def renumber_source(source, seed=482):
    rng=np.random.default_rng(seed);result=deepcopy(source)
    points=np.asarray(source['points']);order=rng.permutation(len(points));inverse=np.argsort(order)
    result['points']=points[order].tolist()
    triangles=inverse[np.asarray(source['triangles'])]
    cell_order=rng.permutation(len(triangles));triangles=triangles[cell_order]
    triangles=np.array([np.roll(t,int(rng.integers(3))) for t in triangles])
    result['triangles']=triangles.tolist()
    edge_order=rng.permutation(len(source['boundary_edges']))
    result['boundary_edges']=inverse[np.asarray(source['boundary_edges'])[edge_order]][:,::-1].tolist()
    result['boundary_tags']=np.asarray(source['boundary_tags'])[edge_order].tolist()
    return result,cell_order


class CurvedCorrespondenceGeometryTests(unittest.TestCase):
    def test_nonaffine_p2_maps_are_invariant_to_independent_numbering(self):
        from superfish_ng.curved_comparison_correspondence import infer_curved_comparison_correspondence
        cases,maps=curved_comparison_fixture();spaces=[]
        expected=case_curved_space(cases[1],mesh_from_dict(cases[1],maps[1]['source_mesh']))
        for case,document,seed in zip(cases,maps,(517,391)):
            mesh,_=renumber_source(document['source_mesh'],seed)
            spaces.append(case_curved_space(case,mesh_from_dict(case,mesh)))
        with self.assertRaisesRegex(ValueError,'fractions'):
            infer_curved_comparison_correspondence(cases,spaces,boundary_pairing='same_curve_fractions')
        pairing=infer_curved_comparison_correspondence(cases,spaces,boundary_pairing='ordered_curve_vertices')
        node_map=np.asarray(pairing['current_node_for_previous']);cell_map=np.asarray(pairing['current_cell_for_previous'])
        self.assertEqual(len(set(node_map)),len(node_map));self.assertEqual(len(set(cell_map)),len(cell_map))
        # Independently identify each old cell by its original vertex positions.
        original=case_curved_space(cases[0],mesh_from_dict(cases[0],maps[0]['source_mesh']))
        positions={tuple(p):i for i,p in enumerate(original.geometry.points_rz_m)}
        for nodes in spaces[0].geometry.cell_nodes:
            canonical=[positions[tuple(spaces[0].geometry.points_rz_m[n])] for n in nodes]
            np.testing.assert_allclose(spaces[1].geometry.points_rz_m[node_map[nodes]],expected.geometry.points_rz_m[canonical],rtol=0,atol=2e-16)

    def test_refined_same_domain_preserves_all_quadratic_nodes(self):
        from superfish_ng.curved_comparison_correspondence import infer_curved_comparison_correspondence
        cases,maps=curved_comparison_fixture();case=replace(cases[0],curved_refinement_levels=2)
        changed,_=renumber_source(maps[0]['source_mesh'])
        spaces=[case_curved_space(case,mesh_from_dict(case,m)) for m in (maps[0]['source_mesh'],changed)]
        pairing=infer_curved_comparison_correspondence((case,case),spaces,boundary_pairing='same_curve_fractions')
        np.testing.assert_allclose(spaces[0].geometry.points_rz_m,spaces[1].geometry.points_rz_m[pairing['current_node_for_previous']],rtol=0,atol=2e-16)

    def test_equal_counts_and_boundary_do_not_hide_a_different_diagonal(self):
        from superfish_ng import Case
        from superfish_ng.conics import LineSegment
        from superfish_ng.curved_contour import CurvedContour
        from superfish_ng.curved_comparison_correspondence import infer_curved_comparison_correspondence
        vertices=[(0.,0.),(.2,0.),(.2,.1),(0.,.1)]
        curves=tuple(LineSegment(a,b) for a,b in zip(vertices,vertices[1:]+vertices[:1]))
        case=Case((),curved_contour=CurvedContour(curves,('axis','pec','pec','pec'),1e-14),
            geometry_order=2,element_order=2,curve_chord_tolerance_m=.001)
        source=dict(schema_version=1,length_unit='m',coordinate_order='rz',index_base=0,
            points=[[r,z] for z,r in vertices],triangles=[[0,2,1],[0,3,2]],
            boundary_edges=[[0,1],[1,2],[2,3],[3,0]],boundary_tags=['axis','pec','pec','pec'])
        target=dict(source,triangles=[[0,3,1],[1,3,2]])
        spaces=[case_curved_space(case,mesh_from_dict(case,m)) for m in (source,target)]
        with self.assertRaisesRegex(ValueError,'(topology|adjacent)'):
            infer_curved_comparison_correspondence((case,case),spaces,boundary_pairing='same_curve_fractions')

    def test_local_history_is_interpreted_before_automatic_numbering(self):
        from superfish_ng.curved_refinement_steps import steps_from_dict
        from superfish_ng.curved_comparison_correspondence import infer_curved_comparison_correspondence
        cases,maps=curved_comparison_fixture();source=maps[0]['source_mesh'];other,order=renumber_source(source)
        spaces=[]
        for mesh,cell in ((source,0),(other,int(np.flatnonzero(order==0)[0]))):
            steps=steps_from_dict([dict(kind='marked',marked_cells=[cell],minimum_corner_angle_deg=1.),dict(kind='uniform')])
            case=replace(cases[0],curved_refinement_steps=steps)
            spaces.append(case_curved_space(case,mesh_from_dict(case,mesh)))
        pairing=infer_curved_comparison_correspondence((cases[0],cases[0]),spaces,boundary_pairing='same_curve_fractions')
        np.testing.assert_allclose(spaces[0].geometry.points_rz_m,spaces[1].geometry.points_rz_m[pairing['current_node_for_previous']],rtol=0,atol=2e-16)

    def test_version_and_boundary_policy_are_explicit_and_strict(self):
        from superfish_ng.saved_mode_tracking import validate_tracking_controls
        _,maps=curved_comparison_fixture();maps=automatic_maps(maps)
        validate_tracking_controls(dict(CONTROLS,comparison_meshes=maps))
        invalid=[]
        for change in ({'boundary_pairing':None},{'boundary_pairing':'nearest'},{'schema_version':True},{'extra':1}):
            bad=deepcopy(maps);bad[0].update(change);invalid.append(bad)
        bad=deepcopy(maps);del bad[0]['boundary_pairing'];invalid.append(bad)
        bad=deepcopy(maps);bad[0]['boundary_pairing']='same_curve_fractions';invalid.append(bad)
        bad=deepcopy(maps);bad[0]['schema_version']=2;del bad[0]['boundary_pairing'];invalid.append(bad)
        # Legacy version 2 retains the explicit-numbering contract.
        bad=deepcopy(maps)
        for m in bad:m['schema_version']=2;del m['boundary_pairing']
        invalid.append(bad)
        for bad in invalid:
            with self.subTest(bad=bad[0].keys()),self.assertRaises(ValueError):
                validate_tracking_controls(dict(CONTROLS,comparison_meshes=bad))


class CurvedCorrespondenceTrackingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from superfish_ng import solve
        cls.cases,cls.maps=curved_comparison_fixture()
        cls.solutions=[solve(cls.cases[0],mesh_data=cls.maps[0]['source_mesh']),
            solve(replace(cls.cases[1],curved_refinement_levels=1),mesh_data=cls.maps[1]['source_mesh'])]

    def test_native_overlap_volume_and_quadrature_are_numbering_invariant(self):
        from superfish_ng.piecewise_remesh_tracking import track_piecewise_remesh_modes
        reports=[];documents=automatic_maps(self.maps);before=deepcopy(documents)
        for maps in (automatic_maps(self.maps,renumber=False),documents):
            reports.append(track_piecewise_remesh_modes(*self.solutions,['A'],**dict(CONTROLS,comparison_meshes=maps)))
        a,b=reports
        self.assertEqual(a['status'],b['status']);self.assertEqual(b['status'],'PASS')
        np.testing.assert_allclose(a['overlap_matrix'],b['overlap_matrix'],rtol=0,atol=2e-14)
        np.testing.assert_allclose(a['physical_mapping']['axisymmetric_volumes_m3'],b['physical_mapping']['axisymmetric_volumes_m3'],rtol=2e-14)
        self.assertAlmostEqual(b['physical_mapping']['axisymmetric_volumes_m3'][1]/b['physical_mapping']['axisymmetric_volumes_m3'][0],1.125**2,places=12)
        self.assertEqual(documents,before)

    def test_saved_correspondence_is_recomputed_and_tampering_rejected(self):
        import json
        from pathlib import Path
        import tempfile
        from superfish_ng.io import save_run
        from superfish_ng.saved_mode_tracking import save_mode_tracking,read_mode_tracking
        from superfish_ng.mode_tracking_history import start_mode_history,extend_mode_history
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,s in zip(('old','new'),self.solutions):save_run(s.case,s,root/name)
            maps=automatic_maps(self.maps);controls=dict(CONTROLS,comparison_meshes=maps)
            pair=save_mode_tracking(dict(schema_version=1,previous_run='old',current_run='new',previous_ids=['A'],controls=controls),root/'pair.json',base_directory=root)
            self.assertEqual(read_mode_tracking(root/'pair.json'),pair)
            history=extend_mode_history(start_mode_history(pair),dict(current_run='old',controls=dict(controls,comparison_meshes=maps[::-1])),base_directory=root)
            self.assertEqual(history['status'],'PASS');self.assertEqual(history['current_mode_ids'],['A'])
            data=deepcopy(pair);mapping=data['tracking']['physical_mapping']['numbering_correspondence']['current_node_for_previous']
            mapping[0],mapping[1]=mapping[1],mapping[0]
            (root/'changed.json').write_text(json.dumps(data))
            with self.assertRaises(ValueError):read_mode_tracking(root/'changed.json')

    def test_mismatched_final_partition_and_reapproximated_boundary_are_rejected(self):
        from superfish_ng.piecewise_remesh_tracking import track_piecewise_remesh_modes
        maps=automatic_maps(self.maps);maps[1]['curved_refinement_levels']=1
        with self.assertRaisesRegex(ValueError,'triangulations'):
            track_piecewise_remesh_modes(*self.solutions,['A'],**dict(CONTROLS,comparison_meshes=maps))
        maps=automatic_maps(self.maps);maps[1]['boundary_pairing']=maps[0]['boundary_pairing']='same_curve_fractions'
        with self.assertRaisesRegex(ValueError,'fractions'):
            track_piecewise_remesh_modes(*self.solutions,['A'],**dict(CONTROLS,comparison_meshes=maps))
        maps=automatic_maps(self.maps);mesh=maps[1]['source_mesh']
        node=next(i for edge in mesh['boundary_edges'] for i in edge if mesh['points'][i][0]>0)
        mesh['points'][node][0]+=.001
        with self.assertRaises(ValueError):
            track_piecewise_remesh_modes(*self.solutions,['A'],**dict(CONTROLS,comparison_meshes=maps))


if __name__=='__main__':unittest.main()
