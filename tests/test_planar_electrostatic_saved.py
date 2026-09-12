# SPDX-License-Identifier: Apache-2.0
import hashlib,json,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from scripts.planar_electrostatic_reference import parallel_plate,manufactured_quadratic
from superfish_ng.planar_electrostatic import solve_planar_electrostatic
from superfish_ng import planar_electrostatic_saved as saved
from superfish_ng.planar_electrostatic_saved import save_planar_electrostatic_run,read_planar_electrostatic_run,planar_electrostatic_result,export_planar_electrostatic_probe,_snapshot
from superfish_ng.model import capabilities
from superfish_ng.constants import EPS0


def rehash(directory):
    p=directory/'manifest.json';data=json.loads(p.read_text());data['files']={name:hashlib.sha256((directory/name).read_bytes()).hexdigest() for name in data['files']};p.write_text(json.dumps(data))


class PlanarElectrostaticSavedTests(unittest.TestCase):
    def test_full_static_roundtrip_reference_potential_and_one_sided_probe(self):
        cases=[parallel_plate(order)[0] for order in (1,2)]+[manufactured_quadratic(concave=concave,direction='x',rotation=[[.6,-.8],[.8,.6]],shift=(-.5,.25))[0] for concave in (False,True)]+[parallel_plate(voltage=0.,offset=3.)[0]]
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for index,case in enumerate(cases):
                s=solve_planar_electrostatic(case);run=root/str(index);result=save_planar_electrostatic_run(case,s,run);before=_snapshot(run);restored=read_planar_electrostatic_run(run)
                inventory=capabilities()['planar_electrostatic'];self.assertEqual(case.to_dict()['format'],inventory['case_format'])
                self.assertEqual(result['physics'],case.to_dict()['physics']);self.assertEqual(result['physics'],'linear_electrostatic')
                self.assertEqual(result['format'],inventory['result_format']);self.assertEqual(json.loads(before['manifest.json'])['format'],inventory['native_manifest_format'])
                self.assertEqual(result,planar_electrostatic_result(restored));np.testing.assert_array_equal(restored.potential_v,s.potential_v)
                np.testing.assert_array_equal(restored.potential_relative_to_reference_v,s.potential_relative_to_reference_v)
                self.assertEqual(restored.reference_potential_v,s.reference_potential_v)
                points=case.partition.mesh.points_xy_m[case.partition.mesh.triangles[[0,-1]]].mean(axis=1)
                if len(case.partition.interface_edges):points=np.vstack((points,case.partition.mesh.points_xy_m[case.partition.interface_edges[0]].mean(axis=0)))
                probe=export_planar_electrostatic_probe(run,root/f'probe-{index}.json',points);expected=s.probe_at(points)
                for key,value in expected.items():self.assertEqual(probe[key],value)
                for axis in ('x','y'):np.testing.assert_array_equal(probe['fields']['D'+axis+'_C_per_m2'],EPS0*np.asarray(probe['epsilon_r'])*np.asarray(probe['fields']['E'+axis+'_V_per_m']))
                self.assertEqual(len(probe['fields']),5);self.assertNotIn('phasor',probe['conventions']);self.assertEqual(_snapshot(run),before)
                with self.assertRaises(FileExistsError):save_planar_electrostatic_run(case,s,run)
                with self.assertRaises(ValueError):export_planar_electrostatic_probe(run,run/'probe.json',points)
                with self.assertRaises(ValueError):export_planar_electrostatic_probe(run,root/'outside.json',[[100.,100.]])
                self.assertFalse((root/'outside.json').exists())
                for bad in ([[False,0.]],[[0.,True]],[[1+0j,0.]],[["0",0.]]):
                    with self.assertRaises(ValueError):export_planar_electrostatic_probe(run,root/'invalid-type.json',bad)
                    self.assertFalse((root/'invalid-type.json').exists())
                self.assertNotIn('volume_m3',result['topology']);self.assertEqual(result['topology']['holes'],0)
                self.assertIn('[J/m]',result['conventions']['energy']);self.assertIn('[F/m]',result['conventions']['capacitance'])
                with np.load(run/'mesh.npz',allow_pickle=False) as arrays:
                    self.assertNotIn('axis_dofs',arrays.files);self.assertNotIn('region_volume_m3',arrays.files)
                    self.assertIn('volume_load_c_per_m',arrays.files);self.assertIn('boundary_load_c_per_m',arrays.files)

    def test_rehashed_material_boundary_coefficients_reference_and_quantities_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);case=parallel_plate()[0];s=solve_planar_electrostatic(case);run=root/'source';save_planar_electrostatic_run(case,s,run)
            kinds=('epsilon','owner','load','dtype','coefficients','reference','absolute','energy','surface_charge','convention','charge','electrode','manifest')
            for kind in kinds:
                target=root/kind;shutil.copytree(run,target)
                if kind in ('epsilon','owner','load','dtype','coefficients','reference','absolute'):
                    name='fields.npz' if kind in ('coefficients','reference','absolute') else 'mesh.npz'
                    with np.load(target/name,allow_pickle=False) as archive:arrays={k:archive[k] for k in archive.files}
                    if kind=='epsilon':arrays['epsilon_r'][0]*=2
                    elif kind=='owner':arrays['boundary_owner_indices'][0]+=1
                    elif kind=='load':arrays['boundary_load_c_per_m'][0]+=1e-8
                    elif kind=='dtype':arrays['cell_dofs']=arrays['cell_dofs'].astype(float)
                    elif kind=='coefficients':arrays['potential_relative_to_reference_v']*=2
                    elif kind=='reference':arrays['reference_potential_v']+=1
                    else:arrays['potential_v']+=1
                    np.savez_compressed(target/name,**arrays)
                elif kind in ('energy','surface_charge','convention'):
                    p=target/'results.json';data=json.loads(p.read_text())
                    if kind=='energy':data['quantities']['energy_j_per_m']*=1.01
                    elif kind=='surface_charge':data['quantities']['electrode_original_field_charge_c_per_m']['upper']*=1.01
                    else:data['conventions']['energy']='RF peak phasor 1/4'
                    p.write_text(json.dumps(data))
                elif kind in ('charge','electrode'):
                    p=target/'case.json';data=json.loads(p.read_text())
                    if kind=='charge':data['charge_density_c_per_m3']['bottom']=1e-8
                    else:data['boundaries'][0]['potential_v']+=1
                    p.write_text(json.dumps(data))
                else:
                    p=target/'manifest.json';data=json.loads(p.read_text());data['schema_version']=True;p.write_text(json.dumps(data))
                rehash(target)
                with self.assertRaises(ValueError):read_planar_electrostatic_run(target)

    def test_incomplete_links_and_changes_during_read_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);case=parallel_plate()[0];s=solve_planar_electrostatic(case);run=root/'source';save_planar_electrostatic_run(case,s,run)
            missing=root/'missing';shutil.copytree(run,missing);(missing/'manifest.json').unlink()
            with self.assertRaises(ValueError):read_planar_electrostatic_run(missing)
            link=root/'link';link.symlink_to(run,target_is_directory=True)
            with self.assertRaises(ValueError):read_planar_electrostatic_run(link)
            linked=root/'linked';shutil.copytree(run,linked);(linked/'fields.npz').unlink();(linked/'fields.npz').symlink_to(run/'fields.npz')
            with self.assertRaises(ValueError):read_planar_electrostatic_run(linked)
            original=saved.planar_electrostatic_result
            def changed(solution):
                result=original(solution);p=run/'case.json';p.write_text(p.read_text()+'\n');return result
            with patch.object(saved,'planar_electrostatic_result',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'changed during'):read_planar_electrostatic_run(run)

    def test_bad_or_changing_source_cannot_publish_a_completion_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);case=parallel_plate()[0];s=solve_planar_electrostatic(case);s.potential_relative_to_reference_v=s.potential_relative_to_reference_v*2
            with self.assertRaises(ValueError):save_planar_electrostatic_run(case,s,root/'bad')
            self.assertFalse((root/'bad').exists());s=solve_planar_electrostatic(case);original=saved.planar_electrostatic_result
            def changed(solution):
                result=original(solution);s.potential_relative_to_reference_v=s.potential_relative_to_reference_v+1.;return result
            with patch.object(saved,'planar_electrostatic_result',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'changed during'):save_planar_electrostatic_run(case,s,root/'changing')
            self.assertFalse((root/'changing').exists());s=solve_planar_electrostatic(case);original_link=saved.os.link
            def interrupted(source,target):
                if Path(target).name=='manifest.json':raise OSError('injected publication interruption')
                return original_link(source,target)
            with patch.object(saved.os,'link',side_effect=interrupted):
                with self.assertRaises(OSError):save_planar_electrostatic_run(case,s,root/'partial')
            self.assertFalse((root/'partial/manifest.json').exists())
            with self.assertRaises(ValueError):read_planar_electrostatic_run(root/'partial')
