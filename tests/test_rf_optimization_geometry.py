# SPDX-License-Identifier: Apache-2.0
"""Multivariate curve laws, independent Green moments and RF search ancestry."""
from copy import deepcopy
from pathlib import Path
import json
import unittest
import tempfile
from unittest.mock import patch
import numpy as np
from superfish_ng import rf_optimization as engine
from superfish_ng.project import Project
from test_curved_harmonic_deformation import deformation_fixture,space


def geometry_request():
    project,_=deformation_fixture()
    raw=project.to_dict();raw['case']['mesh']['curved_refinement_steps']=raw['case']['mesh']['curved_refinement_steps'][:1]
    request=json.loads(Path('examples/optimization/frozen_history_rf.json').read_text())
    request.update(schema_version=3,project=raw,rf_coordinates='fixed',minimum_corner_angle_deg=1.)
    request['variables']=[dict(name='radius',unit='m',lower=.08,upper=.0808,initial=.08,step=.0008,tolerance=.0008),
        dict(name='asymmetry',unit='1',lower=-.02,upper=.02,initial=.01,step=.01,tolerance=.01)]
    request['controls']['mapping']='piecewise_remesh'
    def term(coefficient,powers):return dict(coefficient=coefficient,powers=powers)
    request['geometry_terms']={
        '/curves/1/center_zr_m/0':[term(.1,[0,0]),term(-.1,[0,1])],
        '/curves/2/center_zr_m/0':[term(.1,[0,0]),term(-.1,[0,1])],
        '/curves/1/semiaxes_m/0':[term(.1,[0,0]),term(.1,[0,1])],
        '/curves/2/semiaxes_m/0':[term(.1,[0,0]),term(-.1,[0,1])],
        '/curves/1/semiaxes_m/1':[term(1.,[1,0])],
        '/curves/2/semiaxes_m/1':[term(1.,[1,0])]}
    return request


class RFOptimizationGeometryTests(unittest.TestCase):
    def test_independent_nonaffine_geometry_moments_and_refinement_prefix(self):
        from scripts.validate_large_curved_mesh_selection import boundary_moments
        request=geometry_request();before=deepcopy(request);engine.validate_optimization_request(request)
        base=engine._projects(request,dict(values=[.08,0.],phase='search'))[0]
        reference=boundary_moments(space(base))
        for radius,bias in ((.08,-.02),(.0804,.01),(.0808,.02)):
            projects=engine._projects(request,dict(values=[radius,bias],phase='search'))
            moments=[boundary_moments(space(p)) for p in projects]
            for m in moments:
                self.assertAlmostEqual(m['signed_area_m2']/reference['signed_area_m2'],radius/.08,places=12)
                self.assertAlmostEqual(m['signed_volume_m3']/reference['signed_volume_m3'],(radius/.08)**2,places=12)
            final=engine._projects(request,dict(values=[radius,bias],phase='final'))
            self.assertEqual([p.to_dict() for p in projects[1:]],[p.to_dict() for p in final[:2]])
            prefix=request['project']['case']['mesh']['curved_refinement_steps']
            for i,p in enumerate(final):self.assertEqual(p.case.to_dict()['mesh']['curved_refinement_steps'],prefix+[dict(kind='uniform')]*(i+1))
        self.assertEqual(request,before)

    def test_mixed_terms_and_dimensioned_reparameterization(self):
        request=geometry_request()
        for i in (1,2):request['geometry_terms'][f'/curves/{i}/semiaxes_m/1'].append(dict(coefficient=.1,powers=[1,2]))
        unit=deepcopy(request);unit['variables'][0].update(name='radius_factor',unit='1',lower=1.,upper=1.01,initial=1.,step=.01,tolerance=.01)
        for terms in unit['geometry_terms'].values():
            for term in terms:term['coefficient']*=.08**term['powers'][0]
        a=engine._projects(request,dict(values=[.0804,.01],phase='search'))[0]
        b=engine._projects(unit,dict(values=[1.005,.01],phase='search'))[0]
        self.assertAlmostEqual(a.case.curved_contour.curves[1].semiaxes_m[1],.0804*(1+.1*.01**2),places=15)
        np.testing.assert_allclose(a.mesh_data['points'],b.mesh_data['points'],rtol=0,atol=2e-15)

    def test_three_variables_include_axial_length_and_signed_bounds(self):
        from superfish_ng.rf_optimization_geometry import trial_project
        from scripts.validate_large_curved_mesh_selection import boundary_moments
        request=geometry_request();request['rf_coordinates']='axis_fraction'
        base=trial_project(request,Project.from_dict(request['project']),[.08,.01])
        request['variables'].append(dict(name='axis_length',unit='m',lower=.18,upper=.22,initial=.2,step=.01,tolerance=.01))
        for terms in request['geometry_terms'].values():
            for term in terms:term['powers'].append(0)
        for i in (1,2):
            request['geometry_terms'][f'/curves/{i}/center_zr_m/0']=[dict(coefficient=.5,powers=[0,0,1]),dict(coefficient=-.5,powers=[0,1,1])]
            request['geometry_terms'][f'/curves/{i}/semiaxes_m/0']=[dict(coefficient=.5,powers=[0,0,1]),dict(coefficient=.5 if i==1 else -.5,powers=[0,1,1])]
        request['geometry_terms']['/curves/0/end_zr_m/0']=[dict(coefficient=1.,powers=[0,0,1])]
        engine.validate_optimization_request(request)
        changed=trial_project(request,Project.from_dict(request['project']),[.08,.01,.19])
        np.testing.assert_allclose(changed.mesh_data['points'],np.asarray(base.mesh_data['points'])*[1.,.95],rtol=0,atol=2e-15)
        for key,value in boundary_moments(space(base)).items():self.assertAlmostEqual(boundary_moments(space(changed))[key]/value,.95,places=14)
        self.assertAlmostEqual(changed.case.acceleration_parameters[0]/base.case.acceleration_parameters[0],.95,places=15)

    def test_strict_terms_units_ranges_and_control_derivation(self):
        request=geometry_request();invalid=[]
        for version in (True,1,2,4):invalid.append(dict(request,schema_version=version))
        for variable in (dict(request['variables'][0],unit='mm'),dict(request['variables'][0],step=0.),
                         dict(request['variables'][0],initial=-.1),dict(request['variables'][0],name='asymmetry')):
            invalid.append(dict(request,variables=[variable,request['variables'][1]]))
        for term in (dict(coefficient=True,powers=[1,0]),dict(coefficient=float('nan'),powers=[1,0]),
                     dict(coefficient=1.,powers=[1]),dict(coefficient=1.,powers=[1,False]),
                     dict(coefficient=1.,powers=[1,-1]),dict(coefficient=1.,powers=[1,.5])):
            bad=deepcopy(request);bad['geometry_terms']['/curves/1/semiaxes_m/1']=[term];invalid.append(bad)
        duplicate=deepcopy(request);duplicate['geometry_terms']['/curves/1/semiaxes_m/1']*=2;invalid.append(duplicate)
        unused=deepcopy(request);unused['variables'].append(dict(name='unused',unit='1',lower=0.,upper=1.,initial=0.,step=.1,tolerance=.1))
        for terms in unused['geometry_terms'].values():
            for term in terms:term['powers'].append(0)
        invalid += [unused,dict(request,geometry_terms={'/curves/01/semiaxes_m/1':[]}),dict(request,geometry_terms={}),
            dict(request,rf_coordinates='axial'),dict(request,minimum_corner_angle_deg=60),
            dict(request,controls=dict(request['controls'],comparison_meshes=[]))]
        for bad in invalid:
            with self.subTest(bad=bad),self.assertRaises(ValueError):engine.validate_optimization_request(bad)

    def test_real_multilevel_pause_resume_final_maps_and_replay(self):
        request=geometry_request();request['max_trials']=2
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);first=engine.execute_rf_optimization(request,root/'first',max_new_trials=1)
            self.assertEqual(first['status'],'PAUSED');self.assertEqual(first['completed_fem_solves'],3)
            final=engine.execute_rf_optimization(request,root/'rest',checkpoint=first)
            self.assertEqual(final['status'],'SEARCH_COMPLETE');self.assertEqual(final['completed_fem_solves'],6)
            self.assertEqual(engine.replay_rf_optimization(final),final)
            self.assertEqual(final['trial_sources_sha256'][0],first['trial_sources_sha256'][0])
            meshes=final['trials'][1]['tracking']['request']['controls']['comparison_meshes']
            self.assertEqual(meshes[0],meshes[1])
            self.assertEqual(meshes[0]['curved_refinement_steps'],request['project']['case']['mesh']['curved_refinement_steps'])
            for key in ('terms','parent','comparison'):
                bad=deepcopy(final)
                if key=='terms':bad['request']['geometry_terms']['/curves/1/semiaxes_m/1'][0]['coefficient']=1.001
                elif key=='parent':bad['trials'][1]['parent_index']=1
                else:bad['trials'][1]['tracking']['request']['controls']['comparison_meshes'][1]['source_mesh']['points'][1][0]+=.001
                with self.subTest(key=key),self.assertRaises(ValueError):engine.replay_rf_optimization(bad)

    def test_invalid_candidate_preserves_failure_without_objective_or_fem(self):
        request=geometry_request()
        for i in (1,2):request['geometry_terms'][f'/curves/{i}/semiaxes_m/1'][0]['coefficient']=-1.
        with tempfile.TemporaryDirectory() as tmp,patch.object(engine,'execute_project') as solve:
            out=Path(tmp)/'invalid'
            with self.assertRaises(ValueError):engine.execute_rf_optimization(request,out)
            solve.assert_not_called();failure=json.loads((out/'failure-001.json').read_text())
            self.assertEqual(failure['fem_calls_attempted'],0);self.assertNotIn('objective',failure)
            self.assertFalse(list(out.glob('checkpoint-*.json')))

    def test_gui_strict_transport_preserves_variable_order_and_terms(self):
        from superfish_ng.gui_rf_optimization import rf_optimization_response
        request=geometry_request();result=rf_optimization_response(None,'prepare-rf-optimization',dict(request=json.dumps(request)))
        self.assertEqual(result['request'],request);self.assertEqual(json.loads(result['serialized']),request)
        duplicate=json.dumps(request).replace('"name": "radius"','"name": "radius", "name": "changed"',1)
        with self.assertRaisesRegex(ValueError,'duplicate'):rf_optimization_response(None,'prepare-rf-optimization',dict(request=duplicate))
