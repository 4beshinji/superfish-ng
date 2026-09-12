# SPDX-License-Identifier: Apache-2.0
import hashlib,json,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from scripts.axis_magnetostatic_reference import uniform_field,cylinder_current,layered_current
from superfish_ng.axis_magnetostatic import solve_axis_magnetostatic
from superfish_ng import axis_magnetostatic_saved as saved
from superfish_ng.axis_magnetostatic_saved import save_axis_magnetostatic_run,read_axis_magnetostatic_run,axis_magnetostatic_result,export_axis_magnetostatic_probe,_snapshot
from superfish_ng.model import capabilities
from superfish_ng.constants import MU0


def rehash(directory):
    path=directory/'manifest.json';data=json.loads(path.read_text());data['files']={name:hashlib.sha256((directory/name).read_bytes()).hexdigest() for name in data['files']};path.write_text(json.dumps(data))


class AxisMagnetostaticSavedTests(unittest.TestCase):
    def test_full_roundtrip_axis_holes_one_sided_material_and_SI_units(self):
        cases=[uniform_field(order=order)[0] for order in (1,2)]+[cylinder_current(holes=2,boundary='fixed')[0],layered_current(n=2)[0],uniform_field(field_t=0.,boundary='tangential')[0]]
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for index,case in enumerate(cases):
                solution=solve_axis_magnetostatic(case);run=root/str(index);result=save_axis_magnetostatic_run(case,solution,run);before=_snapshot(run);restored=read_axis_magnetostatic_run(run)
                inventory=capabilities()['axis_magnetostatic'];self.assertEqual(case.to_dict()['format'],inventory['case_format'])
                self.assertEqual(result['format'],inventory['result_format']);self.assertEqual(result['physics'],'linear_magnetostatic')
                self.assertEqual(json.loads(before['manifest.json'])['format'],inventory['native_manifest_format']);self.assertEqual(result,axis_magnetostatic_result(restored))
                np.testing.assert_array_equal(restored.aphi_over_r_t,solution.aphi_over_r_t)
                p=case.partition;points=p.mesh.points_rz_m[p.mesh.triangles[[0,-1]]].mean(axis=1)
                points=np.vstack((points,p.mesh.points_rz_m[p.mesh.axis_nodes].mean(axis=0)))
                if len(p.interface_edges):points=np.vstack((points,p.mesh.points_rz_m[p.interface_edges[0]].mean(axis=0)))
                probe=export_axis_magnetostatic_probe(run,root/f'probe-{index}.json',points)
                for key,value in solution.probe_at(points).items():self.assertEqual(probe[key],value)
                self.assertEqual(len(probe['fields']),6);self.assertEqual(probe['fields']['Aphi_Wb_per_m'][2],0.);self.assertEqual(probe['fields']['Br_T'][2],0.)
                for coordinate in ('r','z'):np.testing.assert_array_equal(probe['fields'][f'H{coordinate}_A_per_m'],((1./MU0)/np.asarray(probe['mu_r']))*np.asarray(probe['fields'][f'B{coordinate}_T']))
                self.assertIn('[J]',result['conventions']['energy']);self.assertIn('[Wb]',result['conventions']['flux']);self.assertIn('[A m^2]',result['conventions']['fixed_boundary_reaction'])
                self.assertEqual(result['topology']['holes'],len(p.mesh.holes_rz_m));self.assertEqual(result['topology']['volume_m3'],p.mesh.volume_m3)
                self.assertNotIn('capacitance',result['quantities']);self.assertNotIn('reference_az_wb_per_m',result)
                with np.load(run/'mesh.npz',allow_pickle=False) as arrays:
                    for name in ('axis_dofs','axis_edges','region_volume_m3','reluctivity_m_per_h','volume_load_a_m2','boundary_load_a_m2'):self.assertIn(name,arrays.files)
                with np.load(run/'fields.npz',allow_pickle=False) as arrays:self.assertEqual(arrays.files,['aphi_over_r_t'])
                self.assertEqual(_snapshot(run),before)
                with self.assertRaises(FileExistsError):save_axis_magnetostatic_run(case,solution,run)
                with self.assertRaises(ValueError):export_axis_magnetostatic_probe(run,run/'probe.json',points)
                for bad in ([[False,0.]],[[0.,True]],[[1+0j,0.]],[["0",0.]],[[-.1,0.]],[[100.,100.]]):
                    with self.assertRaises(ValueError):export_axis_magnetostatic_probe(run,root/'rejected.json',bad)
                    self.assertFalse((root/'rejected.json').exists())

    def test_rehashed_material_axis_source_coefficients_and_quantities_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);case=uniform_field()[0];solution=solve_axis_magnetostatic(case);run=root/'source';save_axis_magnetostatic_run(case,solution,run)
            kinds=('mu','reluctivity','axis','load','dtype','coefficients','field_dtype','energy','weighted_h','flux','convention','current','fixed_a','manifest')
            for kind in kinds:
                target=root/kind;shutil.copytree(run,target)
                if kind in ('mu','reluctivity','axis','load','dtype','coefficients','field_dtype'):
                    name='fields.npz' if kind in ('coefficients','field_dtype') else 'mesh.npz'
                    with np.load(target/name,allow_pickle=False) as archive:arrays={k:archive[k] for k in archive.files}
                    if kind=='mu':arrays['mu_r'][0]*=2
                    elif kind=='reluctivity':arrays['reluctivity_m_per_h'][0]*=2
                    elif kind=='axis':arrays['axis_dofs'][0]+=1
                    elif kind=='load':arrays['boundary_load_a_m2'][0]+=1.
                    elif kind=='dtype':arrays['cell_dofs']=arrays['cell_dofs'].astype(float)
                    elif kind=='coefficients':arrays['aphi_over_r_t']+=.001
                    else:arrays['aphi_over_r_t']=arrays['aphi_over_r_t'].astype('float32')
                    np.savez_compressed(target/name,**arrays)
                elif kind in ('energy','weighted_h','flux','convention'):
                    path=target/'results.json';data=json.loads(path.read_text())
                    if kind=='energy':data['quantities']['energy_j']*=1.01
                    elif kind=='weighted_h':data['quantities']['fixed_boundary_original_reaction_a_m2']['outer']*=1.01
                    elif kind=='flux':data['quantities']['boundary_original_normal_flux_wb']['top']*=1.01
                    else:data['conventions']['fixed_boundary_reaction']='current [A]'
                    path.write_text(json.dumps(data))
                elif kind in ('current','fixed_a'):
                    path=target/'case.json';data=json.loads(path.read_text())
                    if kind=='current':data['current_density_phi_a_per_m2']['all']=1.
                    else:data['boundaries'][1]['aphi_over_r_t']+=.001
                    path.write_text(json.dumps(data))
                else:
                    path=target/'manifest.json';data=json.loads(path.read_text());data['schema_version']=True;path.write_text(json.dumps(data))
                rehash(target)
                with self.assertRaises(ValueError):read_axis_magnetostatic_run(target)

    def test_incomplete_links_and_changes_during_read_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);case=uniform_field()[0];s=solve_axis_magnetostatic(case);run=root/'source';save_axis_magnetostatic_run(case,s,run)
            missing=root/'missing';shutil.copytree(run,missing);(missing/'manifest.json').unlink()
            with self.assertRaises(ValueError):read_axis_magnetostatic_run(missing)
            link=root/'link';link.symlink_to(run,target_is_directory=True)
            with self.assertRaises(ValueError):read_axis_magnetostatic_run(link)
            linked=root/'linked';shutil.copytree(run,linked);(linked/'fields.npz').unlink();(linked/'fields.npz').symlink_to(run/'fields.npz')
            with self.assertRaises(ValueError):read_axis_magnetostatic_run(linked)
            original=saved.axis_magnetostatic_result
            def changed(solution):
                result=original(solution);p=run/'case.json';p.write_text(p.read_text()+'\n');return result
            with patch.object(saved,'axis_magnetostatic_result',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'changed during'):read_axis_magnetostatic_run(run)

    def test_bad_or_changing_source_cannot_publish_a_completion_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);case=uniform_field()[0];s=solve_axis_magnetostatic(case);s.aphi_over_r_t=s.aphi_over_r_t*2
            with self.assertRaises(ValueError):save_axis_magnetostatic_run(case,s,root/'bad')
            self.assertFalse((root/'bad').exists());s=solve_axis_magnetostatic(case);original=saved.axis_magnetostatic_result
            def changed(solution):
                result=original(solution);s.aphi_over_r_t=s.aphi_over_r_t+1.;return result
            with patch.object(saved,'axis_magnetostatic_result',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'changed during'):save_axis_magnetostatic_run(case,s,root/'changing')
            self.assertFalse((root/'changing').exists());s=solve_axis_magnetostatic(case);original_link=saved.os.link
            def interrupted(source,target):
                if Path(target).name=='manifest.json':raise OSError('injected publication interruption')
                return original_link(source,target)
            with patch.object(saved.os,'link',side_effect=interrupted):
                with self.assertRaises(OSError):save_axis_magnetostatic_run(case,s,root/'partial')
            self.assertFalse((root/'partial/manifest.json').exists())
            with self.assertRaises(ValueError):read_axis_magnetostatic_run(root/'partial')
