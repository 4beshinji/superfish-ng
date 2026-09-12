# SPDX-License-Identifier: Apache-2.0
import hashlib,json,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from scripts.off_axis_magnetostatic_reference import layered_current,uniform_field
from superfish_ng.off_axis_magnetostatic import solve_off_axis_magnetostatic
from superfish_ng import off_axis_magnetostatic_saved as saved
from superfish_ng.off_axis_magnetostatic_saved import save_off_axis_magnetostatic_run,read_off_axis_magnetostatic_run,off_axis_magnetostatic_result,export_off_axis_magnetostatic_probe,_snapshot
from superfish_ng.model import capabilities
from superfish_ng.constants import MU0


def rehash(directory):
    p=directory/'manifest.json';data=json.loads(p.read_text());data['files']={name:hashlib.sha256((directory/name).read_bytes()).hexdigest() for name in data['files']};p.write_text(json.dumps(data))


class OffAxisMagnetostaticSavedTests(unittest.TestCase):
    def test_full_magnetic_roundtrip_reference_psi_and_one_sided_probe(self):
        cases=[layered_current(order=order,n=2)[0] for order in (1,2)]+[uniform_field(holes=holes,boundary='tangential',reference_psi=.125)[0] for holes in (0,2)]+[uniform_field(order=order,field_t=0.,reference_psi=.125)[0] for order in (1,2)]
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for index,case in enumerate(cases):
                s=solve_off_axis_magnetostatic(case);run=root/str(index);result=save_off_axis_magnetostatic_run(case,s,run);before=_snapshot(run);restored=read_off_axis_magnetostatic_run(run)
                inventory=capabilities()['off_axis_magnetostatic'];self.assertEqual(case.to_dict()['format'],inventory['case_format'])
                self.assertEqual(result['physics'],case.to_dict()['physics']);self.assertEqual(result['physics'],'linear_magnetostatic')
                self.assertEqual(result['format'],inventory['result_format']);self.assertEqual(json.loads(before['manifest.json'])['format'],inventory['native_manifest_format'])
                self.assertEqual(result,off_axis_magnetostatic_result(restored));np.testing.assert_array_equal(restored.psi_wb,s.psi_wb)
                np.testing.assert_array_equal(restored.psi_relative_to_reference_wb,s.psi_relative_to_reference_wb)
                self.assertEqual(restored.reference_psi_wb,s.reference_psi_wb)
                points=case.partition.mesh.points_rz_m[case.partition.mesh.triangles[[0,-1]]].mean(axis=1)
                if len(case.partition.interface_edges):points=np.vstack((points,case.partition.mesh.points_rz_m[case.partition.interface_edges[0]].mean(axis=0)))
                probe=export_off_axis_magnetostatic_probe(run,root/f'probe-{index}.json',points);expected=s.probe_at(points)
                for key,value in expected.items():self.assertEqual(probe[key],value)
                for axis in ('r','z'):np.testing.assert_array_equal(probe['fields']['H'+axis+'_A_per_m'],((1./MU0)/np.asarray(probe['mu_r']))*np.asarray(probe['fields']['B'+axis+'_T']))
                self.assertEqual(len(probe['fields']),6);self.assertNotIn('phasor',probe['conventions']);self.assertEqual(_snapshot(run),before)
                with self.assertRaises(FileExistsError):save_off_axis_magnetostatic_run(case,s,run)
                with self.assertRaises(ValueError):export_off_axis_magnetostatic_probe(run,run/'probe.json',points)
                with self.assertRaises(ValueError):export_off_axis_magnetostatic_probe(run,root/'outside.json',[[100.,100.]])
                self.assertFalse((root/'outside.json').exists())
                for bad in ([[False,0.]],[[0.,True]],[[1+0j,0.]],[["0",0.]]):
                    with self.assertRaises(ValueError):export_off_axis_magnetostatic_probe(run,root/'invalid-type.json',bad)
                    self.assertFalse((root/'invalid-type.json').exists())
                self.assertEqual(result['topology']['volume_m3'],case.partition.mesh.volume_m3);self.assertEqual(result['topology']['holes'],len(case.partition.mesh.holes_rz_m));self.assertFalse(result['topology']['axis_present'])
                self.assertIn('[J]',result['conventions']['energy']);self.assertNotIn('capacitance',result['conventions']);self.assertNotIn('inductance_h',result['quantities'])
                with np.load(run/'mesh.npz',allow_pickle=False) as arrays:
                    self.assertNotIn('axis_dofs',arrays.files);self.assertIn('region_volume_m3',arrays.files);self.assertIn('boundary_components',arrays.files)
                    self.assertIn('volume_load_a',arrays.files);self.assertIn('boundary_load_a',arrays.files)

    def test_rehashed_material_boundary_coefficients_reference_and_quantities_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);case=layered_current(n=2)[0];s=solve_off_axis_magnetostatic(case);run=root/'source';save_off_axis_magnetostatic_run(case,s,run)
            kinds=('mu','reluctivity','owner','load','volume','component','dtype','coefficients','reference','absolute','energy','surface_current','flux','convention','current','fixed_psi','manifest')
            for kind in kinds:
                target=root/kind;shutil.copytree(run,target)
                if kind in ('mu','reluctivity','owner','load','volume','component','dtype','coefficients','reference','absolute'):
                    name='fields.npz' if kind in ('coefficients','reference','absolute') else 'mesh.npz'
                    with np.load(target/name,allow_pickle=False) as archive:arrays={k:archive[k] for k in archive.files}
                    if kind=='mu':arrays['mu_r'][0]*=2
                    elif kind=='reluctivity':arrays['reluctivity_m_per_h'][0]*=2
                    elif kind=='owner':arrays['boundary_owner_indices'][0]+=1
                    elif kind=='load':arrays['boundary_load_a'][0]+=1e-8
                    elif kind=='volume':arrays['region_volume_m3'][0]*=2
                    elif kind=='component':arrays['boundary_components'][0]+=1
                    elif kind=='dtype':arrays['cell_dofs']=arrays['cell_dofs'].astype(float)
                    elif kind=='coefficients':arrays['psi_relative_to_reference_wb']*=2
                    elif kind=='reference':arrays['reference_psi_wb']+=1
                    else:arrays['psi_wb']+=1
                    np.savez_compressed(target/name,**arrays)
                elif kind in ('energy','surface_current','flux','convention'):
                    p=target/'results.json';data=json.loads(p.read_text())
                    if kind=='energy':data['quantities']['energy_j']*=1.01
                    elif kind=='surface_current':data['quantities']['fixed_boundary_original_reaction_a']['inner']*=1.01
                    elif kind=='flux':data['quantities']['boundary_original_normal_flux_wb']['bottom']+=1.
                    else:data['conventions']['energy']='RF peak phasor 1/4'
                    p.write_text(json.dumps(data))
                elif kind in ('current','fixed_psi'):
                    p=target/'case.json';data=json.loads(p.read_text())
                    if kind=='current':data['current_density_phi_a_per_m2']['inside']=1.
                    else:data['boundaries'][0]['psi_wb']+=1
                    p.write_text(json.dumps(data))
                else:
                    p=target/'manifest.json';data=json.loads(p.read_text());data['schema_version']=True;p.write_text(json.dumps(data))
                rehash(target)
                with self.assertRaises(ValueError):read_off_axis_magnetostatic_run(target)

    def test_incomplete_links_and_changes_during_read_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);case=layered_current(n=2)[0];s=solve_off_axis_magnetostatic(case);run=root/'source';save_off_axis_magnetostatic_run(case,s,run)
            missing=root/'missing';shutil.copytree(run,missing);(missing/'manifest.json').unlink()
            with self.assertRaises(ValueError):read_off_axis_magnetostatic_run(missing)
            link=root/'link';link.symlink_to(run,target_is_directory=True)
            with self.assertRaises(ValueError):read_off_axis_magnetostatic_run(link)
            linked=root/'linked';shutil.copytree(run,linked);(linked/'fields.npz').unlink();(linked/'fields.npz').symlink_to(run/'fields.npz')
            with self.assertRaises(ValueError):read_off_axis_magnetostatic_run(linked)
            original=saved.off_axis_magnetostatic_result
            def changed(solution):
                result=original(solution);p=run/'case.json';p.write_text(p.read_text()+'\n');return result
            with patch.object(saved,'off_axis_magnetostatic_result',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'changed during'):read_off_axis_magnetostatic_run(run)

    def test_bad_or_changing_source_cannot_publish_a_completion_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);case=layered_current(n=2)[0];s=solve_off_axis_magnetostatic(case);s.psi_relative_to_reference_wb=s.psi_relative_to_reference_wb*2
            with self.assertRaises(ValueError):save_off_axis_magnetostatic_run(case,s,root/'bad')
            self.assertFalse((root/'bad').exists());s=solve_off_axis_magnetostatic(case);original=saved.off_axis_magnetostatic_result
            def changed(solution):
                result=original(solution);s.psi_relative_to_reference_wb=s.psi_relative_to_reference_wb+1.;return result
            with patch.object(saved,'off_axis_magnetostatic_result',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'changed during'):save_off_axis_magnetostatic_run(case,s,root/'changing')
            self.assertFalse((root/'changing').exists());s=solve_off_axis_magnetostatic(case);original_link=saved.os.link
            def interrupted(source,target):
                if Path(target).name=='manifest.json':raise OSError('injected publication interruption')
                return original_link(source,target)
            with patch.object(saved.os,'link',side_effect=interrupted):
                with self.assertRaises(OSError):save_off_axis_magnetostatic_run(case,s,root/'partial')
            self.assertFalse((root/'partial/manifest.json').exists())
            with self.assertRaises(ValueError):read_off_axis_magnetostatic_run(root/'partial')
