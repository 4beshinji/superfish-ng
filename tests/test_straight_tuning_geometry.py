# SPDX-License-Identifier: Apache-2.0
"""Original complete domains, atomic laws and independent boundary moments."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
import numpy as np
from superfish_ng.contour import Contour
from superfish_ng.project import Project
from superfish_ng.mesh_input import mesh_from_dict
from superfish_ng.tuning import _request,_project,pair_controls


def request(kind='stepped_profile'):
    records=json.loads(Path('docs/noncurved_tuning_scope_cases.json').read_text())['records']
    return deepcopy(next(x['future_request'] for x in records if x['id']=='tm-'+kind))


def boundary(case):return case.contour or Contour.from_profile(case)


class StraightTuningGeometryTests(unittest.TestCase):
    def test_original_complete_geometry_atomic_law_and_independent_scale_moments(self):
        for kind in ('profile','stepped_profile','contour'):
            with self.subTest(kind=kind):
                r=request(kind);original=deepcopy(r);source=Project.from_dict(r['project']);polygon=boundary(source.case)
                # The known scaling of each original physical point and boundary
                # moment is established independently before the new API call.
                scaled=Contour(tuple((z*1.1,h*1.1) for z,h in polygon.vertices_zr_m),polygon.edge_tags)
                self.assertAlmostEqual(scaled.area_m2/polygon.area_m2,1.1**2)
                self.assertAlmostEqual(scaled.volume_m3/polygon.volume_m3,1.1**3)
                _request(r)
                first=_project(r,1.1,'search');self.assertEqual(boundary(first.case),scaled)
                other=deepcopy(r);other['shape_law']['bindings'].reverse();other['shape_law']['case_boundary_vertices'].reverse()
                self.assertEqual(_project(other,1.1,'search').to_dict(),first.to_dict())
                self.assertEqual(_project(r,.9,'search').case.model,source.case.model)
                self.assertEqual(r,original)
                finer=_project(r,1.1,'refinement');self.assertEqual(boundary(finer.case),scaled)
                self.assertEqual(finer.case.nr,first.case.nr*2);self.assertEqual(finer.case.nz,first.case.nz*2)
                pair=pair_controls(r,1.1,1.1,first,finer)
                self.assertEqual(pair['comparison_meshes'][0],pair['comparison_meshes'][1])
                for data in pair['comparison_meshes']:mesh_from_dict(first.case,data)

    def test_original_boundary_owners_roles_step_and_budget_are_strict(self):
        for mutate in (
            lambda r:r['shape_law'].update(extra=True),
            lambda r:r['shape_law'].update(version=True),
            lambda r:r['shape_law']['case_boundary_vertices'].pop(),
            lambda r:r['shape_law']['case_boundary_vertices'].append(deepcopy(r['shape_law']['case_boundary_vertices'][0])),
            lambda r:r['shape_law']['case_boundary_vertices'][0].update(reference_vertex=True),
            lambda r:r['shape_law']['reference_comparison_mesh']['boundary_tags'].__setitem__(0,'pec'),
            lambda r:r['shape_law']['bindings'].append(deepcopy(r['shape_law']['bindings'][0])),
            lambda r:r['shape_law']['bindings'][0].update(vertex=True),
            lambda r:r['shape_law']['bindings'][0].update(coordinate='x'),
            lambda r:r['shape_law']['bindings'][0].update(expression={'constant':1.,'unit':'1'}),
            lambda r:r['controls'].update(comparison_meshes=[]),
            lambda r:r['controls'].update(mapping='normalized_profile'),
            lambda r:r['controls'].update(sample_order=33),
        ):
            r=request();mutate(r)
            with self.subTest(mutation=r),self.assertRaises(ValueError):_request(r)
        r=request();owner=r['shape_law']['case_boundary_vertices'][2]['reference_vertex']
        binding=next(b for b in r['shape_law']['bindings'] if b['vertex']==owner and b['coordinate']=='z')
        binding['expression']={'op':'add','args':[binding['expression'],{'constant':.001,'unit':'m'}]}
        with self.assertRaisesRegex(ValueError,'step'):_request(r)

    def test_pair_is_bound_to_actual_case_and_original_field_metadata(self):
        r=request();_request(r);a=_project(r,.9,'search');b=_project(r,1.1,'refinement')
        controls=pair_controls(r,.9,1.1,a,b)
        for p,data in zip((a,b),controls['comparison_meshes']):mesh_from_dict(p.case,data)
        raw=b.to_dict();raw['case']['rf']['normalization_j']=2.;bad=Project.from_dict(raw)
        with self.assertRaises(ValueError):pair_controls(r,.9,1.1,a,bad)
        with self.assertRaises(ValueError):pair_controls(r,.91,1.1,a,b)

    def test_interior_invalid_geometry_stays_invalid_with_valid_bounds(self):
        r=request('contour');binding=next(b for b in r['shape_law']['bindings'] if b['vertex']==0 and b['coordinate']=='r')
        binding['expression']={'op':'if','args':[{'op':'eq','args':[{'variable':'scale'},{'constant':1.,'unit':'1'}]}, {'constant':-.001,'unit':'m'},{'constant':0.,'unit':'m'}]}
        # eq is deliberately unsupported: strict syntax is checked in every branch.
        with self.assertRaises(ValueError):_request(r)
        binding['expression']['args'][0]={'op':'lt','args':[{'op':'abs','args':[{'op':'sub','args':[{'variable':'scale'},{'constant':1.,'unit':'1'}]}]},{'constant':.01,'unit':'1'}]}
        _request(r)
        with self.assertRaises(ValueError):_project(r,1.,'search')

    def test_explicit_mesh_and_zero_geometry_change_refused(self):
        r=request();r['project']['mesh']=deepcopy(r['shape_law']['reference_comparison_mesh'])
        with self.assertRaises(ValueError):_request(r)
        r=request()
        for b in r['shape_law']['bindings']:b['expression']={'constant':r['shape_law']['reference_comparison_mesh']['points'][b['vertex']][0 if b['coordinate']=='r' else 1],'unit':'m'}
        with self.assertRaises(ValueError):_request(r)


    def test_identity_recovery_wrapper_retains_the_same_owned_maps(self):
        r=request();wrapper=dict(schema_version=6,tune_request=r,identity_recovery=dict(anchor_selection='latest_resolved_trial',controls=deepcopy(r['controls'])))
        _request(wrapper);a=_project(wrapper,.9,'search');b=_project(wrapper,1.1,'refinement')
        self.assertEqual(pair_controls(wrapper,.9,1.1,a,b),pair_controls(r,.9,1.1,a,b))
