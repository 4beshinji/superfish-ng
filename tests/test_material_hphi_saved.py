# SPDX-License-Identifier: Apache-2.0
import hashlib,json,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from test_rf_materials import partition
from superfish_ng.rf_materials import RFMaterialPartition,LinearRFMaterial
from superfish_ng.material_hphi import MaterialHphiCase,solve_material_hphi
from superfish_ng.axis_hphi import AxisAccelerationPath
from superfish_ng.material_hphi_saved import save_material_hphi_run,read_material_hphi_run,material_hphi_result,export_material_hphi_probe,_snapshot
from superfish_ng import material_hphi_saved as saved
from superfish_ng.constants import MU0
from superfish_ng.model import capabilities


def case(axis=False,holes=1,order=2):
    p=partition(axis,holes)
    if axis:p=RFMaterialPartition(p.mesh,[LinearRFMaterial('low',1.,1.),p.materials[1]],p.regions)
    path=AxisAccelerationPath(.01,.06,.8,.02) if axis else None
    return MaterialHphiCase(p,element_order=order,modes=1,acceleration=path)


def rehash(directory):
    p=directory/'manifest.json';d=json.loads(p.read_text());d['files']={name:hashlib.sha256((directory/name).read_bytes()).hexdigest() for name in d['files']};p.write_text(json.dumps(d))


class MaterialHphiSavedTests(unittest.TestCase):
    def test_complete_native_probe_and_original_fields_roundtrip(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for axis in (False,True):
                for order in (1,2):
                    c=case(axis,2,order);s=solve_material_hphi(c);run=root/f'{axis}-{order}'
                    result=save_material_hphi_run(c,s,run);before=_snapshot(run);restored=read_material_hphi_run(run)
                    inventory=capabilities()['material_hphi_rf']
                    self.assertEqual(c.to_dict()['format'],inventory['case_format'])
                    self.assertEqual(result['format'],inventory['result_format'])
                    self.assertEqual(json.loads(before['manifest.json'])['format'],inventory['native_manifest_format'])
                    self.assertIn(order,inventory['element_orders']);self.assertIn(axis,inventory['axis_connected'])
                    self.assertFalse(inventory['project']);self.assertFalse(inventory['gui']);self.assertFalse(inventory['study'])
                    self.assertEqual(result,material_hphi_result(restored));np.testing.assert_array_equal(restored.coefficients,s.coefficients)
                    self.assertEqual(result['excluded_nullspace']['dimension'],0 if axis else 1)
                    point=np.array([[.2,.3,.5]])@c.partition.mesh.points_rz_m[c.partition.mesh.triangles[0]];out=root/f'{axis}-{order}.json'
                    probe=export_material_hphi_probe(run,out,point)
                    for k,v in s.fields_at(point).items():np.testing.assert_allclose(probe['fields'][k],v,rtol=0,atol=0)
                    expected=s.probe_at(point)
                    for key in ('cell_indices','barycentric','region_ids','material_ids','epsilon_r','mu_r','interface_policy'):
                        self.assertEqual(probe[key],expected[key])
                    np.testing.assert_array_equal(probe['fields']['Bphi_real_T'],MU0*np.asarray(probe['mu_r'])*np.asarray(probe['fields']['Hphi_real_A_per_m']))
                    self.assertEqual(len(probe['fields']),18);self.assertEqual(_snapshot(run),before)
                    with self.assertRaises(FileExistsError):save_material_hphi_run(c,s,run)
                    with self.assertRaises(ValueError):export_material_hphi_probe(run,run/'probe.json',point)
                    with self.assertRaises(ValueError):export_material_hphi_probe(run,root/'outside.json',[[1.,1.]])
                    self.assertFalse((root/'outside.json').exists())

    def test_rehashed_material_fields_rf_and_conventions_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);c=case();s=solve_material_hphi(c);run=root/'source';save_material_hphi_run(c,s,run)
            for index,kind in enumerate(('mesh','interface','ownership','dtype','fields','rf','region_rf','convention','case','manifest')):
                target=root/str(index);shutil.copytree(run,target)
                if kind in ('mesh','interface','ownership','dtype','fields'):
                    name='fields.npz' if kind=='fields' else 'mesh.npz'
                    with np.load(target/name,allow_pickle=False) as archive:arrays={k:archive[k] for k in archive.files}
                    if kind=='mesh':arrays['mu_r'][0]*=2
                    elif kind=='interface':arrays['interface_cells'][0]=arrays['interface_cells'][0][::-1]
                    elif kind=='ownership':arrays['cell_region_indices'][0]=1-arrays['cell_region_indices'][0]
                    elif kind=='dtype':arrays['cell_dofs']=arrays['cell_dofs'].astype(float)
                    else:arrays['coefficients']*=2
                    np.savez_compressed(target/name,**arrays)
                elif kind in ('rf','region_rf','convention'):
                    p=target/'results.json';d=json.loads(p.read_text())
                    if kind=='rf':d['modes'][0]['q0']*=1.01
                    elif kind=='region_rf':d['modes'][0]['regions'][0]['electric_energy_j']*=1.01
                    else:d['conventions']['phasor']='RMS'
                    p.write_text(json.dumps(d))
                elif kind=='case':
                    p=target/'case.json';d=json.loads(p.read_text());d['partition']['materials'][0]['epsilon_r']*=2;p.write_text(json.dumps(d))
                else:
                    p=target/'manifest.json';d=json.loads(p.read_text());d['schema_version']=True;p.write_text(json.dumps(d))
                rehash(target)
                with self.assertRaises(ValueError):read_material_hphi_run(target)

    def test_incomplete_symlink_and_changed_during_read_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);c=case(True);s=solve_material_hphi(c);run=root/'source';save_material_hphi_run(c,s,run)
            missing=root/'missing';shutil.copytree(run,missing);(missing/'manifest.json').unlink()
            with self.assertRaises(ValueError):read_material_hphi_run(missing)
            link=root/'link';link.symlink_to(run,target_is_directory=True)
            with self.assertRaises(ValueError):read_material_hphi_run(link)
            linked=root/'linked';shutil.copytree(run,linked);(linked/'fields.npz').unlink();(linked/'fields.npz').symlink_to(run/'fields.npz')
            with self.assertRaises(ValueError):read_material_hphi_run(linked)
            original=saved.material_hphi_result
            def changed(solution):
                result=original(solution);p=run/'case.json';p.write_text(p.read_text()+'\n');return result
            with patch.object(saved,'material_hphi_result',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'changed during'):read_material_hphi_run(run)

    def test_invalid_or_changing_source_never_publishes_completion(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);c=case();s=solve_material_hphi(c);s.coefficients*=2
            with self.assertRaises(ValueError):save_material_hphi_run(c,s,root/'bad')
            self.assertFalse((root/'bad').exists());s=solve_material_hphi(c)
            original=saved.material_hphi_result
            def changed(solution):
                result=original(solution);s.coefficients[0,0]+=1.;return result
            with patch.object(saved,'material_hphi_result',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'changed during'):save_material_hphi_run(c,s,root/'changing')
            self.assertFalse((root/'changing').exists())
            s=solve_material_hphi(c);original_link=saved.os.link
            def interrupted(source,target):
                if Path(target).name=='manifest.json':raise OSError('injected publication interruption')
                return original_link(source,target)
            with patch.object(saved.os,'link',side_effect=interrupted):
                with self.assertRaises(OSError):save_material_hphi_run(c,s,root/'partial')
            self.assertFalse((root/'partial/manifest.json').exists())
            with self.assertRaises(ValueError):read_material_hphi_run(root/'partial')
