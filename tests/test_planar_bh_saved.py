# SPDX-License-Identifier: Apache-2.0
import copy,hashlib,json,shutil,tempfile,unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
import numpy as np
from scripts.planar_bh_reference import uniform_field,layered_field,current_slab
from superfish_ng.planar_bh import PlanarBHCase,solve_planar_bh
from superfish_ng.nonlinear_magnetic import MagneticNewtonControls,MagneticNonlinearFailure
from superfish_ng import planar_bh_saved as saved
from superfish_ng.model import capabilities


def rehash(directory):
    p=directory/'manifest.json';data=json.loads(p.read_text());data['files']={name:hashlib.sha256((directory/name).read_bytes()).hexdigest() for name in data['files']};p.write_text(json.dumps(data))


def failed_cases():
    case=uniform_field(n=2)[0];limited=replace(case,controls=MagneticNewtonControls(max_iterations=1))
    data=case.to_dict();next(v for v in data['boundaries'] if v['id']=='top')['tangential_h_a_per_m']=-1e9;data['controls']['max_backtracks']=3;outside=PlanarBHCase.from_dict(data)
    initial=np.zeros(len(case.partition.mesh.points_xy_m));bottom=next(b for b in case.boundaries if b.id=='bottom');fixed=set(case.partition.mesh.boundary_edges[list(bottom.edge_indices)].ravel());initial[next(i for i in range(len(initial)) if i not in fixed)]=100.
    return (limited,outside,replace(case,initial_az_relative_to_reference_wb_per_m=initial.tolist()))


def failure_of(case):
    try:solve_planar_bh(case)
    except MagneticNonlinearFailure as exc:return exc
    raise AssertionError('expected nonlinear failure')


class PlanarBHSavedTests(unittest.TestCase):
    def test_nonlinear_roundtrip_tables_tangents_history_and_original_probe(self):
        cases=[f(n=2,angle=.7,shift=(-.25,.125),offset=.125,boundary=b)[0] for f in (uniform_field,layered_field,current_slab) for b in ('fixed','tangential')]+[uniform_field(n=2,b_t=0.,offset=.125)[0]]
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for index,case in enumerate(cases):
                s=solve_planar_bh(case);run=root/str(index);result=saved.save_planar_bh_run(case,s,run);before=saved._snapshot(run);restored=saved.read_planar_bh_run(run)
                inventory=capabilities()['planar_bh'];self.assertEqual(result['format'],inventory['result_format']);self.assertEqual(case.to_dict()['format'],inventory['case_format']);self.assertEqual(json.loads(before['manifest.json'])['format'],inventory['native_manifest_format'])
                self.assertEqual(saved.read_planar_bh_outcome(run),result);self.assertEqual(saved.planar_bh_result(restored),result);self.assertEqual(restored.iteration_report,s.iteration_report)
                np.testing.assert_array_equal(restored.az_wb_per_m,s.az_wb_per_m);np.testing.assert_array_equal(restored.az_relative_to_reference_wb_per_m,s.az_relative_to_reference_wb_per_m)
                points=case.partition.mesh.points_xy_m[case.partition.mesh.triangles[[0,-1]]].mean(axis=1)
                if len(case.partition.interface_edges):points=np.vstack((points,case.partition.mesh.points_xy_m[case.partition.interface_edges[0,0]]))
                probe=saved.export_planar_bh_probe(run,root/f'probe-{index}.json',points)
                for name,value in s.probe_at(points).items():self.assertEqual(probe[name],value)
                self.assertEqual(len(probe['fields']),5);self.assertNotIn('mu_r',probe);self.assertNotIn('phasor',probe['conventions']);self.assertIn('[J/m]',probe['conventions']['energy'])
                with np.load(run/'mesh.npz',allow_pickle=False) as arrays:
                    for name in ('material_b_t','material_h_a_per_m','material_table_offsets','cell_tangent_reluctivity_m_per_h','internal_load_a','tangent_csr_data_m_per_h'):self.assertIn(name,arrays.files)
                    self.assertNotIn('mu_r',arrays.files)
                self.assertEqual(saved._snapshot(run),before)
                with self.assertRaises(FileExistsError):saved.save_planar_bh_run(case,s,run)
                with self.assertRaises(ValueError):saved.export_planar_bh_probe(run,run/'probe.json',points)
                for bad in ([[100.,100.]],[[False,0.]],[[1+0j,0.]],[["0",0.]]):
                    with self.assertRaises(ValueError):saved.export_planar_bh_probe(run,root/'invalid-probe.json',bad)
                    self.assertFalse((root/'invalid-probe.json').exists())

    def test_rehashed_coefficients_material_states_tangent_loads_and_histories_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);case=layered_field(n=2)[0];run=root/'source';saved.save_planar_bh_run(case,solve_planar_bh(case),run)
            arrays={'fields.npz':['az_relative_to_reference_wb_per_m','reference_az_wb_per_m','az_wb_per_m'],
                'mesh.npz':['material_b_t','material_h_a_per_m','cell_h_a_per_m','cell_tangent_reluctivity_m_per_h','tangent_csr_data_m_per_h','internal_load_a','current_load_a','boundary_load_a','boundary_owner_indices']}
            for file,names in arrays.items():
                for name in names:
                    target=root/name;shutil.copytree(run,target)
                    with np.load(target/file,allow_pickle=False) as archive:data={k:archive[k] for k in archive.files}
                    data[name].flat[0]+=1;np.savez_compressed(target/file,**data);rehash(target)
                    with self.assertRaises(ValueError):saved.read_planar_bh_run(target)
            for kind in ('dtype','history','energy','coenergy','flux','reaction','convention','controls','provenance','manifest'):
                target=root/kind;shutil.copytree(run,target)
                if kind=='dtype':
                    with np.load(target/'mesh.npz',allow_pickle=False) as archive:data={k:archive[k] for k in archive.files}
                    data['cell_dofs']=data['cell_dofs'].astype(float);np.savez_compressed(target/'mesh.npz',**data)
                else:
                    file='case.json' if kind in ('controls','provenance') else 'manifest.json' if kind=='manifest' else 'results.json';p=target/file;data=json.loads(p.read_text())
                    if kind=='history':data['nonlinear_iteration']['history'][0]['iteration']=False
                    elif kind in ('energy','coenergy'):data['quantities'][kind+'_j_per_m']+=1
                    elif kind=='flux':data['quantities']['boundary_original_normal_flux_wb_per_m']['left']+=1
                    elif kind=='reaction':data['quantities']['fixed_boundary_original_reaction_current_a']['bottom']+=1
                    elif kind=='convention':data['conventions']['energy']='2U, RF peak phasors'
                    elif kind=='controls':data['controls']['max_iterations']+=1
                    elif kind=='provenance':data['partition']['materials'][0]['provenance']='different material source'
                    else:data['schema_version']=True
                    p.write_text(json.dumps(data))
                rehash(target)
                with self.assertRaises(ValueError):saved.read_planar_bh_run(target)

    def test_success_incomplete_links_mutation_and_interrupted_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);case=uniform_field(n=2)[0];s=solve_planar_bh(case);run=root/'source';saved.save_planar_bh_run(case,s,run)
            missing=root/'missing';shutil.copytree(run,missing);(missing/'manifest.json').unlink()
            with self.assertRaises(ValueError):saved.read_planar_bh_run(missing)
            link=root/'link';link.symlink_to(run,target_is_directory=True)
            with self.assertRaises(ValueError):saved.read_planar_bh_run(link)
            linked=root/'linked';shutil.copytree(run,linked);(linked/'fields.npz').unlink();(linked/'fields.npz').symlink_to(run/'fields.npz')
            with self.assertRaises(ValueError):saved.read_planar_bh_run(linked)
            original=saved.planar_bh_result
            def changed(solution):
                result=original(solution);p=run/'case.json';p.write_text(p.read_text()+'\n');return result
            with patch.object(saved,'planar_bh_result',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'changed during'):saved.read_planar_bh_run(run)
            s.internal_load_a=s.internal_load_a+1
            with self.assertRaises(ValueError):saved.save_planar_bh_run(case,s,root/'bad')
            self.assertFalse((root/'bad').exists());s=solve_planar_bh(case)
            def mutate(solution):
                result=original(solution)
                if solution is not s:s.iteration_report['history'][0]['objective']+=1
                return result
            with patch.object(saved,'planar_bh_result',side_effect=mutate):
                with self.assertRaisesRegex(ValueError,'changed during'):saved.save_planar_bh_run(case,s,root/'changing')
            self.assertFalse((root/'changing').exists());s=solve_planar_bh(case);original_link=saved.os.link
            def interrupted(source,target):
                if Path(target).name=='manifest.json':raise OSError('injected publication interruption')
                return original_link(source,target)
            with patch.object(saved.os,'link',side_effect=interrupted):
                with self.assertRaises(OSError):saved.save_planar_bh_run(case,s,root/'partial')
            self.assertFalse((root/'partial/manifest.json').exists())
            with self.assertRaises(ValueError):saved.read_planar_bh_run(root/'partial')

    def test_three_failure_kinds_replay_last_valid_state_without_success_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for index,(case,reason) in enumerate(zip(failed_cases(),('iteration_limit','line_search_limit','invalid_initial_field'))):
                exc=failure_of(case);run=root/str(index);result=saved.save_planar_bh_failure(case,exc,run);before=saved._failure_snapshot(run)
                self.assertEqual(result,exc.report);self.assertEqual(result['reason'],reason);self.assertEqual(saved.read_planar_bh_failure(run),result);self.assertEqual(saved.read_planar_bh_outcome(run),result)
                self.assertEqual(set(before),{'case.json','failure.json','manifest.json'});self.assertEqual(result['last_valid_relative_coefficients'] is None,reason=='invalid_initial_field')
                self.assertEqual(json.loads(before['manifest.json'])['format'],capabilities()['planar_bh']['failure_manifest_format'])
                with self.assertRaises(ValueError):saved.read_planar_bh_run(run)
                with self.assertRaises(ValueError):saved.export_planar_bh_probe(run,root/'failure-probe.json',[[0.,0.]])
                self.assertFalse((root/'failure-probe.json').exists())
                with self.assertRaises(FileExistsError):saved.save_planar_bh_failure(case,exc,run)
                self.assertEqual(saved._failure_snapshot(run),before)
                with self.assertRaises(ValueError):saved.save_planar_bh_failure(uniform_field(n=2)[0],exc,root/'false-failure')
                self.assertFalse((root/'false-failure').exists())

    def test_failure_rehashed_context_history_last_state_and_status_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);case=failed_cases()[0];exc=failure_of(case);run=root/'source';saved.save_planar_bh_failure(case,exc,run)
            for kind in ('reason','history','last_valid','context','status','controls','type','manifest'):
                target=root/kind;shutil.copytree(run,target);p=target/('manifest.json' if kind=='manifest' else 'failure.json');data=json.loads(p.read_text())
                if kind=='reason':data['reason']='line_search_limit'
                elif kind=='history':data['history'].pop()
                elif kind=='last_valid':data['last_valid_relative_coefficients'][0]+=1
                elif kind=='context':data['context']['energy_unit']='J'
                elif kind=='status':data['status']='converged'
                elif kind=='controls':data['controls']['max_iterations']+=1
                elif kind=='type':data['history'][0]['iteration']=False
                else:data['schema_version']=True
                p.write_text(json.dumps(data));rehash(target)
                with self.assertRaises(ValueError):saved.read_planar_bh_failure(target)
            exc.report['last_valid_relative_coefficients'][0]+=1
            with self.assertRaises(ValueError):saved.save_planar_bh_failure(case,exc,root/'bad')
            self.assertFalse((root/'bad').exists())

    def test_failure_links_incomplete_mutation_and_interruption(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);case=failed_cases()[0];exc=failure_of(case);run=root/'source';saved.save_planar_bh_failure(case,exc,run)
            link=root/'link';link.symlink_to(run,target_is_directory=True)
            with self.assertRaises(ValueError):saved.read_planar_bh_failure(link)
            linked=root/'linked';shutil.copytree(run,linked);(linked/'failure.json').unlink();(linked/'failure.json').symlink_to(run/'failure.json')
            with self.assertRaises(ValueError):saved.read_planar_bh_failure(linked)
            original=saved._reproduce_failure
            def changed(request):
                report=original(request);p=run/'failure.json';p.write_text(p.read_text()+'\n');return report
            with patch.object(saved,'_reproduce_failure',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'changed during'):saved.read_planar_bh_failure(run)
            def mutate(request):
                report=original(request);exc.report['history'].pop();return report
            with patch.object(saved,'_reproduce_failure',side_effect=mutate):
                with self.assertRaisesRegex(ValueError,'changed during'):saved.save_planar_bh_failure(case,exc,root/'changing')
            self.assertFalse((root/'changing').exists());exc=failure_of(case);original_link=saved.os.link
            def interrupted(source,target):
                if Path(target).name=='manifest.json':raise OSError('injected publication interruption')
                return original_link(source,target)
            with patch.object(saved.os,'link',side_effect=interrupted):
                with self.assertRaises(OSError):saved.save_planar_bh_failure(case,exc,root/'partial')
            self.assertFalse((root/'partial/manifest.json').exists())
            with self.assertRaises(ValueError):saved.read_planar_bh_failure(root/'partial')
