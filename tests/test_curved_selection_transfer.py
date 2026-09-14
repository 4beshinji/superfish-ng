# SPDX-License-Identifier: Apache-2.0
"""Exact material-region selection across nonidentical refinement histories."""
from dataclasses import replace
from fractions import Fraction
from copy import deepcopy
import unittest
from superfish_ng import Case
from superfish_ng.conics import LineSegment
from superfish_ng.curved_contour import CurvedContour
from superfish_ng.mesh_controls import ContourMeshControls
from superfish_ng.project import Project


def triangle_project(levels=0):
    vertices=((0.,0.),(.2,0.),(0.,.1))
    curves=tuple(LineSegment(a,b) for a,b in zip(vertices,vertices[1:]+vertices[:1]))
    case=Case((),curved_contour=CurvedContour(curves,('axis','pec','pec'),1e-14),geometry_order=2,
        element_order=2,curve_chord_tolerance_m=.001,contour_mesh=ContourMeshControls(1.),
        curved_refinement_levels=levels,modes=1,quadrature_order=12)
    mesh=dict(schema_version=1,length_unit='m',coordinate_order='rz',index_base=0,
        points=[[0.,0.],[.1,0.],[0.,.2]],triangles=[[0,1,2]],
        boundary_edges=[[0,2],[2,1],[1,0]],boundary_tags=['axis','pec','pec'])
    return Project(case,mesh_data=mesh)


def transfer_request(cells=(0,),policy='intersects'):
    return dict(schema_version=1,selected_cells=list(cells),boundary_pairing='same_curve_fractions',
        coverage_policy=policy,max_pair_tests=100000)


class CurvedSelectionTransferTests(unittest.TestCase):
    def test_parent_to_descendants_preserves_exact_selected_area(self):
        from superfish_ng.curved_selection_transfer import transfer_curved_cell_selection
        result=transfer_curved_cell_selection(triangle_project(),triangle_project(2),transfer_request())
        selection=result['selection']
        self.assertEqual(selection['selected_cells'],list(range(16)))
        self.assertEqual(selection['partially_covered_cells'],[])
        self.assertEqual(selection['source_reference_area'],[1,2])
        self.assertEqual(selection['intersection_reference_area'],[1,2])
        self.assertTrue(all(row['covered_fraction']==[1,1] for row in selection['coverage']))

    def test_coarsening_distinguishes_cover_from_containment(self):
        from superfish_ng.curved_selection_transfer import transfer_curved_cell_selection
        source=triangle_project(1);target=triangle_project()
        a=transfer_curved_cell_selection(source,target,transfer_request())['selection']
        b=transfer_curved_cell_selection(source,target,transfer_request(policy='contained'))['selection']
        self.assertEqual(a['selected_cells'],[0]);self.assertEqual(b['selected_cells'],[])
        self.assertEqual(a['partially_covered_cells'],[0]);self.assertEqual(a['coverage'][0]['covered_fraction'],[1,4])
        self.assertEqual(a['intersection_reference_area'],[1,8])

    def test_non_nested_local_histories_partition_each_selected_region(self):
        from superfish_ng.curved_selection_transfer import transfer_curved_cell_selection
        from superfish_ng.curved_refinement_steps import CurvedRefinementStep as Step
        from superfish_ng.curved_space import case_curved_space
        from superfish_ng.mesh_input import mesh_from_dict
        base=triangle_project(1)
        source=replace(base,case=replace(base.case,curved_refinement_levels=0,curved_refinement_steps=(Step('uniform'),Step('marked',(0,),1.))))
        target=replace(base,case=replace(base.case,curved_refinement_levels=0,curved_refinement_steps=(Step('uniform'),Step('marked',(1,),1.))))
        native=case_curved_space(source.case,mesh_from_dict(source.case,source.mesh_data))
        partial=False
        for cell,nodes in enumerate(native.geometry.cell_nodes):
            result=transfer_curved_cell_selection(source,target,transfer_request((cell,)))['selection']
            partial |= bool(result['partially_covered_cells'])
            p=native.geometry.points_rz_m[nodes[:3]]
            # Straight native maps: physical determinant independently gives the
            # selected area relative to the 0.1 by 0.2 base coordinate scales.
            expected=abs((p[1,0]-p[0,0])*(p[2,1]-p[0,1])-(p[1,1]-p[0,1])*(p[2,0]-p[0,0]))/2/.02
            self.assertAlmostEqual(float(Fraction(*result['source_reference_area'])),expected,places=14)
            self.assertEqual(result['source_reference_area'],result['intersection_reference_area'])
            self.assertTrue(all(Fraction(*row['reference_area'])>0 for row in result['overlaps']))
        self.assertTrue(partial)

    def test_renumbered_scaled_base_transfers_the_same_material_region(self):
        import numpy as np
        from superfish_ng.curved_selection_transfer import transfer_curved_cell_selection
        from superfish_ng.curved_project_transform import transform_curved_project
        from superfish_ng.curved_space import case_curved_space
        from superfish_ng.mesh_input import mesh_from_dict
        from test_curved_comparison_correspondence import renumber_source
        source=triangle_project(1);target=triangle_project(2)
        target=transform_curved_project(target,dict(radial_scale=2.,axial_scale=2.,axial_shear=0.),rf_coordinates='axial')
        mesh,_=renumber_source(target.mesh_data);target=replace(target,mesh_data=mesh)
        result=transfer_curved_cell_selection(source,target,transfer_request())['selection']
        self.assertEqual(len(result['selected_cells']),4);self.assertEqual(result['partially_covered_cells'],[])
        native=case_curved_space(target.case,mesh_from_dict(target.case,target.mesh_data))
        expected=[]
        for cell,nodes in enumerate(native.geometry.cell_nodes):
            centre=native.geometry.points_rz_m[nodes[:3]].mean(axis=0)
            if centre[0]/.2+centre[1]/.4<.5:expected.append(cell)
        self.assertEqual(result['selected_cells'],expected)

    def test_strict_requests_budget_and_native_geometry_scope(self):
        from superfish_ng.curved_selection_transfer import transfer_curved_cell_selection
        source=triangle_project();target=triangle_project(2);request=transfer_request()
        invalid=[dict(request,schema_version=True),dict(request,selected_cells=[]),dict(request,selected_cells=[True]),
            dict(request,selected_cells=[0,0]),dict(request,selected_cells=[1]),dict(request,coverage_policy='nearest'),
            dict(request,boundary_pairing='guess'),dict(request,max_pair_tests=15),dict(request,max_pair_tests=True),dict(request,unknown=1)]
        bad=deepcopy(request);del bad['coverage_policy'];invalid.append(bad)
        for bad in invalid:
            with self.subTest(bad=bad),self.assertRaises(ValueError):transfer_curved_cell_selection(source,target,bad)
        with self.assertRaisesRegex(ValueError,'max_triangles'):
            transfer_curved_cell_selection(source,replace(target,case=replace(target.case,contour_mesh=replace(target.case.contour_mesh,max_triangles=3))),request)
        with self.assertRaisesRegex(ValueError,'native P2'):
            transfer_curved_cell_selection(source,Project(Case(((0.,.1),(.2,.1)))),request)
        raw=source.case.to_dict();raw['model']['polarization']='te'
        with self.assertRaisesRegex(ValueError,'TM'):
            transfer_curved_cell_selection(source,replace(source,case=Case.from_dict(raw)),request)

    def test_original_symmetry_domain_preserves_selected_descendants(self):
        from superfish_ng.curved_selection_transfer import transfer_curved_cell_selection
        from test_curved_reflection import half_case
        for tag in ('electric_symmetry','magnetic_symmetry'):
            source=Project(half_case('z_min',tag));target=replace(source,case=replace(source.case,curved_refinement_levels=1))
            result=transfer_curved_cell_selection(source,target,transfer_request())
            with self.subTest(tag=tag):
                self.assertEqual(result['selection']['selected_cells'],[0,1,2,3])
                self.assertEqual(result['selection']['source_reference_area'],[1,2])
                self.assertEqual(result['current_project'],target.to_dict())

    def test_saved_reconstruction_cli_exclusivity_and_tampering(self):
        import json
        from pathlib import Path
        import tempfile
        from superfish_ng.cli import main
        from superfish_ng.curved_selection_transfer import transfer_curved_cell_selection,replay_curved_selection_transfer
        source=triangle_project(1);target=triangle_project();request=transfer_request();before=source.to_dict(),target.to_dict(),deepcopy(request)
        result=transfer_curved_cell_selection(source,target,request)
        self.assertEqual(replay_curved_selection_transfer(result),result)
        self.assertEqual(before,(source.to_dict(),target.to_dict(),request))
        for kind in ('selection','overlap','boolean'):
            bad=deepcopy(result)
            if kind=='selection':bad['selection']['selected_cells']=[]
            elif kind=='overlap':bad['selection']['overlaps'][0]['reference_area']=[1,2]
            else:bad['selection']['coverage'][0]['covered_fraction'][0]=True
            with self.subTest(kind=kind),self.assertRaises(ValueError):replay_curved_selection_transfer(bad)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source.save(root/'old.json');target.save(root/'new.json');(root/'request.json').write_text(json.dumps(request))
            args=['transfer-curved-selection',str(root/'old.json'),str(root/'new.json'),'--request',str(root/'request.json'),'--out',str(root/'result.json')]
            self.assertEqual(main(args),0);saved=(root/'result.json').read_bytes();self.assertEqual(json.loads(saved),result)
            self.assertEqual(main(args),2);self.assertEqual((root/'result.json').read_bytes(),saved)
            self.assertEqual(main(['replay-curved-selection-transfer',str(root/'result.json')]),0)
            (root/'request.json').write_text('{"schema_version":1,"schema_version":1}');args[-1]=str(root/'invalid.json')
            self.assertEqual(main(args),2);self.assertFalse((root/'invalid.json').exists())

    def test_browser_integer_spelling_of_floats_preserves_values_but_not_boolean_ids(self):
        import json
        from superfish_ng.curved_selection_transfer import transfer_curved_cell_selection,replay_curved_selection_transfer
        result=transfer_curved_cell_selection(triangle_project(1),triangle_project(),transfer_request())
        def browser(value):
            if type(value) is dict:return {k:browser(v) for k,v in value.items()}
            if type(value) is list:return [browser(v) for v in value]
            if type(value) is float and value.is_integer():return int(value)
            return value
        serialized=browser(json.loads(json.dumps(result)))
        self.assertEqual(replay_curved_selection_transfer(serialized),result)
        for value in (False,0.0):
            bad=deepcopy(serialized);bad['selection']['selected_cells']=[value]
            with self.subTest(value=value),self.assertRaises(ValueError):replay_curved_selection_transfer(bad)


if __name__=='__main__':unittest.main()
