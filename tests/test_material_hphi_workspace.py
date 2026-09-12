# SPDX-License-Identifier: Apache-2.0
from contextlib import ExitStack
from dataclasses import replace
from pathlib import Path
import hashlib,json,tempfile,threading,unittest
import numpy as np
from test_rf_materials import partition
from superfish_ng.rf_materials import RFMaterialPartition,LinearRFMaterial
from superfish_ng.material_hphi import MaterialHphiCase
from superfish_ng.constants import MU0
from superfish_ng.model import capabilities
from superfish_ng.axis_hphi import AxisAccelerationPath
from superfish_ng.hphi_project import HphiProject
from superfish_ng.hphi_study import HphiStudy
from superfish_ng.hphi_native import hphi_result,read_hphi_run,solve_hphi
from superfish_ng.hphi_display import display_hphi_fields
from superfish_ng.hphi_jobs import execute_hphi_project
from superfish_ng.hphi_convergence import HphiConvergence
from superfish_ng.hphi_field_overlap import hphi_field_grams,_declared_mesh
from superfish_ng.jobs import JobManager,read_job
from superfish_ng.gui_hphi import hphi_response


def example(axis=True,order=2,holes=1):
    p=partition(axis,holes)
    if axis:p=RFMaterialPartition(p.mesh,[LinearRFMaterial('low',1.,1.),p.materials[1]],p.regions)
    case=MaterialHphiCase(p,element_order=order,modes=2,
        acceleration=AxisAccelerationPath(.01,.06,.8,.02) if axis else None)
    return HphiProject(case,'mm')


class MaterialHphiWorkspaceTests(unittest.TestCase):
    def test_complete_material_scaling_energy_and_conductivity_laws(self):
        for axis in (False,True):
            for order in (1,2):
                project=example(axis,order);first,second=HphiStudy(project,'uniform_scale',[1,2]).projects()
                self.assertEqual(HphiProject.from_dict(project.to_dict()),project)
                self.assertEqual(first.case.partition.to_dict()['materials'],second.case.partition.to_dict()['materials'])
                self.assertEqual(first.case.partition.to_dict()['regions'],second.case.partition.to_dict()['regions'])
                np.testing.assert_array_equal(second.case.partition.mesh.points_rz_m,2*first.case.partition.mesh.points_rz_m)
                if axis:self.assertEqual(second.case.acceleration,AxisAccelerationPath(.02,.12,.8,.04))
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

    def test_display_keeps_material_magnetic_flux_and_rejects_vacuum_comparison(self):
        for axis in (False,True):
            for order in (1,2):
                project=example(axis,order,2);solution=solve_hphi(project.case);sample=display_hphi_fields(solution)
                expected=solution.fields_in_cells(sample['parent_cells'],sample['barycentric'])
                for key in expected:np.testing.assert_array_equal(sample['fields'][key],expected[key])
                mu=project.case.partition.mu_r[sample['parent_cells']]
                np.testing.assert_array_equal(sample['fields']['Bphi_real_T'],MU0*mu*sample['fields']['Hphi_real_A_per_m'])
                self.assertEqual(len(sample['triangles']),(1 if order==1 else 4)*len(solution.space.cell_dofs))
                with self.assertRaisesRegex(ValueError,'material Hphi'):hphi_field_grams(solution,solution)
                with self.assertRaisesRegex(ValueError,'material Hphi'):_declared_mesh(solution)
                with self.assertRaisesRegex(ValueError,'material Hphi convergence'):HphiConvergence([project]*3)
                with self.assertRaises(ValueError):HphiStudy(project,'/case/partition/materials/0/epsilon_r',[1.,2.])
                metadata=capabilities()['material_hphi_rf']
                self.assertEqual(metadata['project']['format'],project.to_dict()['format']);self.assertEqual(metadata['gui'],'/hphi.html')
                self.assertEqual(metadata['study']['kind'],'sweep');self.assertFalse(metadata['tracking'])

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
            for imported in imports:self.assertEqual(manager.status(imported,verify=True)['case_format'],'superfish_ng_material_hphi_case')
            self.assertEqual(manager.status(cancelled)['status'],'cancelled')
            self.assertEqual(before,{p.name:p.read_bytes() for p in (root/'moved-original'/'solution').iterdir()})

    def test_rehashed_project_material_and_job_kind_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            for change in ('kind','material'):
                directory=Path(temp)/change;execute_hphi_project(example(False),directory)
                if change=='kind':
                    for name in ('job.json','manifest.json'):
                        path=directory/name;raw=json.loads(path.read_text());raw['kind']='solve';path.write_text(json.dumps(raw))
                else:
                    path=directory/'project.json';raw=json.loads(path.read_text());raw['case']['partition']['materials'][0]['mu_r']*=2;path.write_text(json.dumps(raw))
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
            self.assertEqual(len(data.splitlines()[0].split(b',')),25)
            self.assertEqual(metadata['case']['acceleration']['phase_origin_m'],.04)
            self.assertEqual(metadata['material_samples']['epsilon_r'],[1.,5.])
            self.assertEqual(metadata['material_samples']['mu_r'],[1.,7.])
            self.assertIn('mu_r(original cell)',metadata['magnetic_flux_density'])


if __name__=='__main__':unittest.main()
