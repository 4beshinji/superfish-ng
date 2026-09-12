# SPDX-License-Identifier: Apache-2.0
import hashlib,json,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from scripts.planar_recoil_reference import interface_patch,layered_remanence,uniform_remanence,quadratic_current
from superfish_ng.planar_recoil import solve_planar_recoil
from superfish_ng import planar_recoil_saved as saved
from superfish_ng.planar_recoil_saved import save_planar_recoil_run,read_planar_recoil_run,planar_recoil_result,export_planar_recoil_probe,_snapshot
from superfish_ng.model import capabilities
from superfish_ng.constants import MU0


def rehash(directory):
    p=directory/'manifest.json';data=json.loads(p.read_text());data['files']={name:hashlib.sha256((directory/name).read_bytes()).hexdigest() for name in data['files']};p.write_text(json.dumps(data))


class PlanarRecoilSavedTests(unittest.TestCase):
    def test_full_magnetic_roundtrip_reference_az_and_one_sided_probe(self):
        cases=[factory(order=order,angle=.7,shift=(-.25,.125))[0] for factory in (interface_patch,layered_remanence) for order in (1,2)]+[uniform_remanence(order=order,amplitude=0.,offset=.125)[0] for order in (1,2)]+[quadratic_current(concave=concave,angle=.7)[0] for concave in (False,True)]
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for index,case in enumerate(cases):
                s=solve_planar_recoil(case);run=root/str(index);result=save_planar_recoil_run(case,s,run);before=_snapshot(run);restored=read_planar_recoil_run(run)
                inventory=capabilities()['planar_recoil'];self.assertEqual(case.to_dict()['format'],inventory['case_format'])
                self.assertEqual(result['physics'],case.to_dict()['physics']);self.assertEqual(result['physics'],'linear_recoil_magnetostatic')
                self.assertEqual(result['format'],inventory['result_format']);self.assertEqual(json.loads(before['manifest.json'])['format'],inventory['native_manifest_format'])
                self.assertEqual(result,planar_recoil_result(restored));np.testing.assert_array_equal(restored.az_wb_per_m,s.az_wb_per_m)
                np.testing.assert_array_equal(restored.az_relative_to_reference_wb_per_m,s.az_relative_to_reference_wb_per_m)
                self.assertEqual(restored.reference_az_wb_per_m,s.reference_az_wb_per_m)
                points=case.partition.mesh.points_xy_m[case.partition.mesh.triangles[[0,-1]]].mean(axis=1)
                if len(case.partition.interface_edges):points=np.vstack((points,case.partition.mesh.points_xy_m[case.partition.interface_edges[0,0]]))
                probe=export_planar_recoil_probe(run,root/f'probe-{index}.json',points);expected=s.probe_at(points)
                for key,value in expected.items():self.assertEqual(probe[key],value)
                b=np.column_stack((probe['fields']['Bx_T'],probe['fields']['By_T']));h=np.column_stack((probe['fields']['Hx_A_per_m'],probe['fields']['Hy_A_per_m']));br=np.asarray(probe['remanent_b_t']);nu=np.linalg.inv(MU0*np.asarray(probe['mu_r_tensor']));expected_h=np.einsum('qij,qj->qi',nu,b-br)
                self.assertLess(np.linalg.norm(h-expected_h)/(1.+np.linalg.norm(h)+np.linalg.norm(np.einsum('qij,qj->qi',nu,br))),1e-11)
                self.assertEqual(len(probe['fields']),5);self.assertNotIn('phasor',probe['conventions']);self.assertEqual(_snapshot(run),before)
                with self.assertRaises(FileExistsError):save_planar_recoil_run(case,s,run)
                with self.assertRaises(ValueError):export_planar_recoil_probe(run,run/'probe.json',points)
                with self.assertRaises(ValueError):export_planar_recoil_probe(run,root/'outside.json',[[100.,100.]])
                self.assertFalse((root/'outside.json').exists())
                for bad in ([[False,0.]],[[0.,True]],[[1+0j,0.]],[["0",0.]]):
                    with self.assertRaises(ValueError):export_planar_recoil_probe(run,root/'invalid-type.json',bad)
                    self.assertFalse((root/'invalid-type.json').exists())
                self.assertNotIn('volume_m3',result['topology']);self.assertEqual(result['topology']['holes'],0)
                self.assertIn('[J/m]',result['conventions']['constitutive_potentials']);self.assertNotIn('capacitance',result['conventions']);self.assertNotIn('inductance_h_per_m',result['quantities'])
                with np.load(run/'mesh.npz',allow_pickle=False) as arrays:
                    self.assertNotIn('axis_dofs',arrays.files);self.assertNotIn('region_volume_m3',arrays.files)
                    self.assertIn('current_load_a',arrays.files);self.assertIn('boundary_load_a',arrays.files)

    def test_rehashed_material_boundary_coefficients_reference_and_quantities_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);case=interface_patch()[0];s=solve_planar_recoil(case);run=root/'source';save_planar_recoil_run(case,s,run)
            kinds=('mu','reluctivity','remanence','orientation','owner','load','remanent_load','dtype','coefficients','reference','absolute','quadratic','potential_b0','potential_h0','coupling','reference_constant','surface_current','flux','convention','current','fixed_az','manifest')
            for kind in kinds:
                target=root/kind;shutil.copytree(run,target)
                if kind in ('mu','reluctivity','remanence','orientation','owner','load','remanent_load','dtype','coefficients','reference','absolute'):
                    name='fields.npz' if kind in ('coefficients','reference','absolute') else 'mesh.npz'
                    with np.load(target/name,allow_pickle=False) as archive:arrays={k:archive[k] for k in archive.files}
                    if kind=='mu':arrays['mu_r_tensor'][0]*=2
                    elif kind=='reluctivity':arrays['reluctivity_tensor_m_per_h'][0]*=2
                    elif kind=='remanence':arrays['remanent_b_t'][0]+=1.
                    elif kind=='orientation':arrays['region_orientation_rad'][0]+=.1
                    elif kind=='remanent_load':arrays['remanent_load_a'][0]+=1.
                    elif kind=='owner':arrays['boundary_owner_indices'][0]+=1
                    elif kind=='load':arrays['boundary_load_a'][0]+=1e-8
                    elif kind=='dtype':arrays['cell_dofs']=arrays['cell_dofs'].astype(float)
                    elif kind=='coefficients':arrays['az_relative_to_reference_wb_per_m']*=2
                    elif kind=='reference':arrays['reference_az_wb_per_m']+=1
                    else:arrays['az_wb_per_m']+=1
                    np.savez_compressed(target/name,**arrays)
                elif kind in ('quadratic','potential_b0','potential_h0','coupling','reference_constant','surface_current','flux','convention'):
                    p=target/'results.json';data=json.loads(p.read_text())
                    if kind in ('quadratic','potential_b0','potential_h0','coupling','reference_constant'):
                        key={'quadratic':'b_quadratic_j_per_m','potential_b0':'constitutive_potential_b0_j_per_m','potential_h0':'constitutive_potential_h0_j_per_m','coupling':'remanence_coupling_j_per_m','reference_constant':'remanent_reference_constant_j_per_m'}[kind];data['quantities'][key]+=1.
                    elif kind=='surface_current':data['quantities']['fixed_boundary_original_reaction_current_a']['fixed']*=1.01
                    elif kind=='flux':data['quantities']['boundary_original_normal_flux_wb_per_m']['fixed']+=1.
                    else:data['conventions']['constitutive_potentials']='RF peak phasor 1/4'
                    p.write_text(json.dumps(data))
                elif kind in ('current','fixed_az'):
                    p=target/'case.json';data=json.loads(p.read_text())
                    if kind=='current':data['current_density_z_a_per_m2']['region-0']=1.
                    else:data['boundaries'][0]['az_wb_per_m']+=1
                    p.write_text(json.dumps(data))
                else:
                    p=target/'manifest.json';data=json.loads(p.read_text());data['schema_version']=True;p.write_text(json.dumps(data))
                rehash(target)
                with self.assertRaises(ValueError):read_planar_recoil_run(target)

    def test_incomplete_links_and_changes_during_read_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);case=interface_patch()[0];s=solve_planar_recoil(case);run=root/'source';save_planar_recoil_run(case,s,run)
            missing=root/'missing';shutil.copytree(run,missing);(missing/'manifest.json').unlink()
            with self.assertRaises(ValueError):read_planar_recoil_run(missing)
            link=root/'link';link.symlink_to(run,target_is_directory=True)
            with self.assertRaises(ValueError):read_planar_recoil_run(link)
            linked=root/'linked';shutil.copytree(run,linked);(linked/'fields.npz').unlink();(linked/'fields.npz').symlink_to(run/'fields.npz')
            with self.assertRaises(ValueError):read_planar_recoil_run(linked)
            original=saved.planar_recoil_result
            def changed(solution):
                result=original(solution);p=run/'case.json';p.write_text(p.read_text()+'\n');return result
            with patch.object(saved,'planar_recoil_result',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'changed during'):read_planar_recoil_run(run)

    def test_bad_or_changing_source_cannot_publish_a_completion_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);case=interface_patch()[0];s=solve_planar_recoil(case);s.az_relative_to_reference_wb_per_m=s.az_relative_to_reference_wb_per_m*2
            with self.assertRaises(ValueError):save_planar_recoil_run(case,s,root/'bad')
            self.assertFalse((root/'bad').exists());s=solve_planar_recoil(case);original=saved.planar_recoil_result
            def changed(solution):
                result=original(solution);s.az_relative_to_reference_wb_per_m=s.az_relative_to_reference_wb_per_m+1.;return result
            with patch.object(saved,'planar_recoil_result',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'changed during'):save_planar_recoil_run(case,s,root/'changing')
            self.assertFalse((root/'changing').exists());s=solve_planar_recoil(case);original_link=saved.os.link
            def interrupted(source,target):
                if Path(target).name=='manifest.json':raise OSError('injected publication interruption')
                return original_link(source,target)
            with patch.object(saved.os,'link',side_effect=interrupted):
                with self.assertRaises(OSError):save_planar_recoil_run(case,s,root/'partial')
            self.assertFalse((root/'partial/manifest.json').exists())
            with self.assertRaises(ValueError):read_planar_recoil_run(root/'partial')
