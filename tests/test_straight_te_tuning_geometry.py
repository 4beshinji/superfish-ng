# SPDX-License-Identifier: Apache-2.0
"""Original TE polygon laws preserve physical moments and source sectors."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import json,unittest
import numpy as np
from superfish_ng import Case
from superfish_ng.contour import Contour
from superfish_ng.contour_mesh import triangulate_contour
from superfish_ng.mesh_input import mesh_to_dict
from superfish_ng.project import Project
from superfish_ng.model import Model
from superfish_ng.tuning import _request,_project,pair_controls
from superfish_ng.piecewise_remesh_tracking import track_piecewise_remesh_modes
from test_te_piecewise_tracking import CONTROLS


def request(kind='stepped_profile'):
    records=json.loads(Path('docs/noncurved_tuning_scope_cases.json').read_text())['records']
    return deepcopy(next(x['future_request'] for x in records if x['id']=='te-'+kind))


class StraightTETuningGeometryTests(unittest.TestCase):
    def test_original_polygon_physical_moments_before_te_request(self):
        for kind in ('profile','stepped_profile','contour'):
            with self.subTest(kind=kind):
                r=request(kind);source=Project.from_dict(r['project']).case
                polygon=source.contour or Contour.from_profile(source)
                expected=replace(polygon,vertices_zr_m=tuple((1.1*z,1.1*h) for z,h in polygon.vertices_zr_m))
                self.assertAlmostEqual(expected.area_m2/polygon.area_m2,1.1**2)
                self.assertAlmostEqual(expected.volume_m3/polygon.volume_m3,1.1**3)
                _request(r);trial=_project(r,1.1,'search');fine=_project(r,1.1,'refinement')
                self.assertEqual(trial.case.contour or Contour.from_profile(trial.case),expected)
                self.assertEqual(trial.case.model,source.model)
                self.assertEqual(trial.case.to_dict()['rf'],source.to_dict()['rf'])
                self.assertEqual(pair_controls(r,1.1,1.1,trial,fine)['comparison_meshes'][0],pair_controls(r,1.1,1.1,trial,fine)['comparison_meshes'][1])

    def test_mixed_source_end_is_refused_before_field_sampling(self):
        polygon=Contour(((0.,0.),(1.,0.),(1.,.5),(1.,1.),(0.,1.)),
            ('axis','magnetic_symmetry','pec','pec','pec'))
        case=Case((),contour=polygon,model=Model(polarization='te'),modes=1)
        self.assertEqual(case.z_max,'mixed')
        mesh=triangulate_contour(case)
        a=SimpleNamespace(case=case,mesh=mesh,reflection_source_case=None,frequencies_hz=np.array([1.]))
        data=mesh_to_dict(mesh)
        with patch('superfish_ng.te_piecewise_remesh_tracking.FieldSampler.from_solution',side_effect=AssertionError('mixed end entered field sampling')):
            with self.assertRaisesRegex(ValueError,'sector'):
                track_piecewise_remesh_modes(a,a,['A'],comparison_meshes=[data,data],**CONTROLS)


def sector_request(kind='stepped_profile',side='z_max',tag='magnetic_symmetry',reflected=False):
    r=request(kind);geometry=r['project']['case']['geometry']
    source=Project.from_dict(r['project']).case;plane=0. if side=='z_min' else source.length
    r['project']['case']['boundaries']={'z_min':'pec','z_max':'pec'};r['project']['case']['boundaries'][side]=tag
    r['project']['reflect_full']=reflected
    data=r['shape_law']['reference_comparison_mesh']
    for i,edge in enumerate(data['boundary_edges']):
        points=np.asarray(data['points'])[edge]
        if np.all(points[:,1]==plane) and not np.all(points[:,0]==0):data['boundary_tags'][i]=tag
    if kind=='contour':
        r['project']['case'].pop('boundaries',None)
        vertices=geometry['vertices_zr_m']
        for i,(a,b) in enumerate(zip(vertices,vertices[1:]+vertices[:1])):
            if a[0]==b[0]==plane and not a[1]==b[1]==0:geometry['edge_tags'][i]=tag
    return r


class StraightTESectorLawTests(unittest.TestCase):
    def test_all_straight_geometries_both_planes_parities_and_reflection(self):
        for kind in ('profile','stepped_profile','contour'):
            for side in ('z_min','z_max'):
                for tag in ('electric_symmetry','magnetic_symmetry'):
                    for reflected in (False,True):
                        r=sector_request(kind,side,tag,reflected)
                        with self.subTest(kind=kind,side=side,tag=tag,reflected=reflected):
                            _request(r);a=_project(r,.9,'search');b=_project(r,1.1,'refinement')
                            controls=pair_controls(r,.9,1.1,a,b)
                            self.assertEqual(a.reflect_full,reflected);self.assertEqual(getattr(a.case,side),tag)
                            self.assertEqual(controls['comparison_meshes'][0]['boundary_tags'],controls['comparison_meshes'][1]['boundary_tags'])

    def test_two_planes_reflection_without_sector_and_acceleration_overrides_refused(self):
        r=sector_request();r['project']['case']['boundaries']['z_min']='electric_symmetry'
        for modified in (r,dict(request(),project=dict(request()['project'],reflect_full=True))):
            with self.assertRaises(ValueError):_request(modified)
        r=request();r['project']['case']['rf']['active_length_m']=.1
        with self.assertRaisesRegex(ValueError,'TE'):_request(r)

    def test_recovery_wrapper_derives_original_te_maps_with_sector_tags(self):
        r=sector_request(reflected=True);wrapper=dict(schema_version=6,tune_request=r,
            identity_recovery=dict(anchor_selection='latest_resolved_trial',controls=deepcopy(r['controls'])))
        _request(wrapper);a=_project(wrapper,.9,'search');b=_project(wrapper,1.1,'refinement')
        self.assertEqual(pair_controls(wrapper,.9,1.1,a,b),pair_controls(r,.9,1.1,a,b))
