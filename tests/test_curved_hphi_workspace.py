# SPDX-License-Identifier: Apache-2.0
from contextlib import ExitStack
from dataclasses import replace
from pathlib import Path
import hashlib,json,tempfile,threading,unittest
import numpy as np
from scripts.curved_meridional_reference import fixture
from superfish_ng.curved_meridional_geometry import CurvedMeridionalGeometry
from superfish_ng.curved_hphi import CurvedHphiCase
from superfish_ng.axis_hphi import AxisAccelerationPath
from superfish_ng.hphi_project import HphiProject
from superfish_ng.hphi_study import HphiStudy
from superfish_ng.hphi_native import hphi_result,read_hphi_run,solve_hphi
from superfish_ng.hphi_display import display_hphi_fields
from superfish_ng.curved_hphi_display import _triangle_path
from superfish_ng.hphi_jobs import execute_hphi_project
from superfish_ng.hphi_convergence import HphiConvergence
from superfish_ng.hphi_field_overlap import hphi_field_grams,_declared_mesh
from superfish_ng.jobs import JobManager,read_job
from superfish_ng.gui_hphi import hphi_response


def example(axis=True,order=2,holes=1):
    data,_=fixture(axis,holes,shear=0.)
    # Both physical coordinates are nonlinear, with positive radial derivative.
    def mapped(points):
        points=np.asarray(points);r,z=points.T
        return np.column_stack((r+2*r*r,z-r*r))
    base=data['base_mesh'];raw=base.to_dict()
    for key in ('outer_rz_m','points_rz_m'):raw[key]=mapped(raw[key]).tolist()
    raw['holes_rz_m']=[mapped(h).tolist() for h in raw['holes_rz_m']]
    data['base_mesh']=type(base).from_dict(raw)
    data['edge_midpoints_rz_m']=mapped(data['edge_midpoints_rz_m'])
    case=CurvedHphiCase(CurvedMeridionalGeometry(**data),element_order=order,modes=2,
        acceleration=AxisAccelerationPath(.01,.16,.8,.02) if axis else None)
    return HphiProject(case,'mm')


class CurvedHphiWorkspaceTests(unittest.TestCase):
    def test_full_quadratic_scaling_energy_and_conductivity_laws(self):
        for axis in (False,True):
            for order in (1,2):
                project=example(axis,order);first,second=HphiStudy(project,'uniform_scale',[1,2]).projects()
                self.assertEqual(HphiProject.from_dict(project.to_dict()),project)
                np.testing.assert_array_equal(second.case.geometry.points_rz_m,2*first.case.geometry.points_rz_m)
                if axis:self.assertEqual(second.case.acceleration,AxisAccelerationPath(.02,.32,.8,.04))
                values=[hphi_result(solve_hphi(p.case))['modes'][0] for p in (first,second)]
                for key,factor in dict(frequency_hz=.5,stored_energy_j=1.,wall_loss_w=2**-1.5,q0=2**.5,geometry_factor_ohm=1.).items():
                    self.assertAlmostEqual(values[1][key]/values[0][key],factor,delta=1e-9,msg=key)
                if axis:
                    self.assertAlmostEqual(values[1]['r_over_q_accelerator_ohm']/values[0]['r_over_q_accelerator_ohm'],1.,delta=1e-9)
                    a,b=(complex(v['vacc_v']['real'],v['vacc_v']['imag']) for v in values)
                    self.assertAlmostEqual(abs(b/a),2**-.5,delta=1e-9)
                for parameter,ratios in (('/case/rf/stored_energy_j',{'stored_energy_j':4.,'wall_loss_w':4.,'q0':1.}),
                    ('/case/rf/conductivity_s_per_m',{'stored_energy_j':1.,'wall_loss_w':.5,'q0':2.})):
                    original=project.case.normalization_j if parameter.endswith('stored_energy_j') else project.case.conductivity_s_per_m
                    changed=HphiStudy(project,parameter,[original,4*original]).projects()[1]
                    result=hphi_result(solve_hphi(changed.case))['modes'][0]
                    self.assertEqual(result['frequency_hz'],values[0]['frequency_hz'])
                    for key,factor in ratios.items():self.assertAlmostEqual(result[key]/values[0][key],factor,delta=1e-9)
                with self.assertRaisesRegex(ValueError,'coaxial dimension'):HphiStudy(project,'/case/geometry/length_m',[.1,.2])
                null=HphiProject(replace(project.case,acceleration=None))
                self.assertTrue(all(p.case.acceleration is None for p in HphiStudy(null,'uniform_scale',[1,2]).projects()))

    def test_original_fields_and_quadratic_display_boundaries(self):
        try:import matplotlib
        except ImportError:self.skipTest('optional matplotlib unavailable')
        for axis in (False,True):
            for order in (1,2):
                solution=solve_hphi(example(axis,order,2).case);sample=display_hphi_fields(solution)
                expected=solution.fields_in_cells(sample['parent_cells'],sample['barycentric'])
                for key in expected:np.testing.assert_array_equal(sample['fields'][key],expected[key])
                self.assertEqual(len(sample['triangles']),64*len(solution.space.cell_dofs))
                # A quadratic Bezier midpoint must reproduce each mapped edge midpoint,
                # including P1 fields on the non-affine quadratic physical geometry.
                for nodes in sample['quadratic_points_rz_m'][::31]:
                    path=_triangle_path(nodes,1.);v=path.vertices
                    for a,c,b,index in ((0,1,2,3),(2,3,4,4),(4,5,6,5)):
                        np.testing.assert_allclose((v[a]+2*v[c]+v[b])/4,nodes[index][[1,0]],rtol=0,atol=2e-16)
                with self.assertRaisesRegex(ValueError,'curved Hphi'):hphi_field_grams(solution,solution)
                with self.assertRaisesRegex(ValueError,'curved Hphi'):_declared_mesh(solution)
                with self.assertRaisesRegex(ValueError,'curved Hphi convergence'):HphiConvergence([example(axis,order)]*3)

    def test_real_worker_owned_import_cancel_and_restart(self):
        with tempfile.TemporaryDirectory() as temp,ExitStack() as cleanup:
            root=Path(temp);manager=JobManager(root/'jobs');cleanup.callback(manager.close)
            cancelled=manager.start_hphi(example());self.assertEqual(manager.cancel(cancelled)['status'],'cancelled')
            identifier=manager.start_hphi(example());self.assertEqual(manager.processes[identifier].wait(timeout=60),0)
            self.assertEqual(manager.status(identifier,verify=True)['status'],'complete')
            source=manager.directory(identifier)/'solution';before={p.name:p.read_bytes() for p in source.iterdir()}
            imports=[manager.import_hphi_result(source),manager.import_hphi_result(manager.directory(identifier))]
            for imported in imports:
                self.assertEqual(before,{p.name:p.read_bytes() for p in (manager.directory(imported)/'solution').iterdir()})
            manager.close();manager.directory(identifier).rename(root/'moved-original')
            manager=JobManager(root/'jobs');cleanup.callback(manager.close)
            for imported in imports:self.assertEqual(manager.status(imported,verify=True)['case_format'],'superfish_ng_curved_hphi_case')
            self.assertEqual(manager.status(cancelled)['status'],'cancelled')
            self.assertEqual(before,{p.name:p.read_bytes() for p in (root/'moved-original'/'solution').iterdir()})

    def test_rehashed_project_geometry_and_job_kind_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            for change in ('kind','geometry'):
                directory=Path(temp)/change;execute_hphi_project(example(False),directory)
                if change=='kind':
                    for name in ('job.json','manifest.json'):
                        path=directory/name;raw=json.loads(path.read_text());raw['kind']='solve';path.write_text(json.dumps(raw))
                else:
                    path=directory/'project.json';raw=json.loads(path.read_text());raw['case']['geometry']['edge_midpoints_rz_m'][0][1]+=1e-5;path.write_text(json.dumps(raw))
                    path=directory/'manifest.json';raw=json.loads(path.read_text());raw['files']={name:hashlib.sha256((directory/name).read_bytes()).hexdigest() for name in raw['files']};path.write_text(json.dumps(raw))
                with self.assertRaises(ValueError):read_job(directory)

    def test_gui_study_point_and_full_axis_probe(self):
        with tempfile.TemporaryDirectory() as temp,ExitStack() as cleanup:
            root=Path(temp);manager=JobManager(root/'jobs');cleanup.callback(manager.close);lock=threading.Lock()
            def request(action,**data):return hphi_response(manager,action,data,lock,root/'cache')[0]
            project=example();study=HphiStudy(project,'uniform_scale',[1,2]);document=study.to_dict()
            self.assertEqual(request('hphi-normalize',document=project.to_dict()),project.to_dict())
            self.assertEqual(request('hphi-normalize-study',document=document),document)
            identifier=request('hphi-start-study',document=document)['id'];self.assertEqual(manager.processes[identifier].wait(timeout=60),0)
            self.assertEqual(request('hphi-study-result',id=identifier)['result']['mode_tracking'],'not_performed')
            point=request('hphi-study-point',id=identifier,index=1)['id'];reply=request('hphi-result',id=point)
            self.assertEqual(reply['project'],study.projects()[1].to_dict())
            self.assertIsNotNone(reply['result']['modes'][0]['vacc_v'])
            points=[[0.,0.],[0.,.375]];data=request('hphi-probe',id=point,points_rz_m=points,mode=1)
            metadata=request('hphi-probe-metadata',id=point,points_rz_m=points,mode=1)
            self.assertEqual(metadata['data_sha256'],hashlib.sha256(data).hexdigest())
            self.assertEqual(len(data.splitlines()[0].split(b',')),20)
            self.assertEqual(metadata['case']['acceleration']['phase_origin_m'],.04)


if __name__=='__main__':unittest.main()
