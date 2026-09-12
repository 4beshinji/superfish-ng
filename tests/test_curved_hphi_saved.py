# SPDX-License-Identifier: Apache-2.0
import hashlib,json,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from scripts.curved_meridional_reference import fixture
from superfish_ng.curved_meridional_geometry import CurvedMeridionalGeometry
from superfish_ng.curved_hphi import CurvedHphiCase,solve_curved_hphi
from superfish_ng.axis_hphi import AxisAccelerationPath
from superfish_ng.curved_hphi_saved import save_curved_hphi_run,read_curved_hphi_run,curved_hphi_result,export_curved_hphi_probe,_snapshot
from superfish_ng import curved_hphi_saved as saved


def case(axis=False,holes=1,order=2):
    data,_=fixture(axis,holes,shear=1.)
    path=AxisAccelerationPath(.01,.17,.8,.02) if axis else None
    return CurvedHphiCase(CurvedMeridionalGeometry(**data),element_order=order,modes=1,acceleration=path)


def rehash(directory):
    p=directory/'manifest.json';d=json.loads(p.read_text());d['files']={name:hashlib.sha256((directory/name).read_bytes()).hexdigest() for name in d['files']};p.write_text(json.dumps(d))


class CurvedHphiSavedTests(unittest.TestCase):
    def test_complete_native_probe_and_original_fields_roundtrip(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for axis in (False,True):
                for order in (1,2):
                    c=case(axis,2,order);s=solve_curved_hphi(c);run=root/f'{axis}-{order}'
                    result=save_curved_hphi_run(c,s,run);before=_snapshot(run);restored=read_curved_hphi_run(run)
                    self.assertEqual(result,curved_hphi_result(restored));np.testing.assert_array_equal(restored.coefficients,s.coefficients)
                    self.assertEqual(result['excluded_nullspace']['dimension'],0 if axis else 1)
                    point=s.mapped_points(np.array([0]),[[.2,.3,.5]])[0];out=root/f'{axis}-{order}.json'
                    probe=export_curved_hphi_probe(run,out,point)
                    for k,v in s.fields_at(point).items():np.testing.assert_allclose(probe['fields'][k],v,rtol=0,atol=0)
                    self.assertEqual(len(probe['fields']),18);self.assertEqual(_snapshot(run),before)
                    with self.assertRaises(FileExistsError):save_curved_hphi_run(c,s,run)
                    with self.assertRaises(ValueError):export_curved_hphi_probe(run,run/'probe.json',point)
                    with self.assertRaises(ValueError):export_curved_hphi_probe(run,root/'outside.json',[[1.,1.]])
                    self.assertFalse((root/'outside.json').exists())

    def test_rehashed_geometry_fields_rf_and_conventions_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);c=case();s=solve_curved_hphi(c);run=root/'source';save_curved_hphi_run(c,s,run)
            for index,kind in enumerate(('mesh','fields','rf','convention','case','manifest')):
                target=root/str(index);shutil.copytree(run,target)
                if kind in ('mesh','fields'):
                    name='mesh.npz' if kind=='mesh' else 'fields.npz'
                    with np.load(target/name,allow_pickle=False) as archive:arrays={k:archive[k] for k in archive.files}
                    if kind=='mesh':arrays['geometry_points_rz_m'][0,0]+=1e-5
                    else:arrays['coefficients']*=2
                    np.savez_compressed(target/name,**arrays)
                elif kind in ('rf','convention'):
                    p=target/'results.json';d=json.loads(p.read_text())
                    if kind=='rf':d['modes'][0]['q0']*=1.01
                    else:d['conventions']['phasor']='RMS'
                    p.write_text(json.dumps(d))
                elif kind=='case':
                    p=target/'case.json';d=json.loads(p.read_text());d['geometry']['edge_midpoints_rz_m'][0][0]+=1e-4;p.write_text(json.dumps(d))
                else:
                    p=target/'manifest.json';d=json.loads(p.read_text());d['schema_version']=True;p.write_text(json.dumps(d))
                rehash(target)
                with self.assertRaises(ValueError):read_curved_hphi_run(target)

    def test_incomplete_symlink_and_changed_during_read_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);c=case(True);s=solve_curved_hphi(c);run=root/'source';save_curved_hphi_run(c,s,run)
            missing=root/'missing';shutil.copytree(run,missing);(missing/'manifest.json').unlink()
            with self.assertRaises(ValueError):read_curved_hphi_run(missing)
            link=root/'link';link.symlink_to(run,target_is_directory=True)
            with self.assertRaises(ValueError):read_curved_hphi_run(link)
            linked=root/'linked';shutil.copytree(run,linked);(linked/'fields.npz').unlink();(linked/'fields.npz').symlink_to(run/'fields.npz')
            with self.assertRaises(ValueError):read_curved_hphi_run(linked)
            original=saved.curved_hphi_result
            def changed(solution):
                result=original(solution);p=run/'case.json';p.write_text(p.read_text()+'\n');return result
            with patch.object(saved,'curved_hphi_result',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'changed during'):read_curved_hphi_run(run)

    def test_invalid_or_changing_source_never_publishes_completion(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);c=case();s=solve_curved_hphi(c);s.coefficients*=2
            with self.assertRaises(ValueError):save_curved_hphi_run(c,s,root/'bad')
            self.assertFalse((root/'bad').exists());s=solve_curved_hphi(c)
            original=saved.curved_hphi_result
            def changed(solution):
                result=original(solution);s.coefficients[0,0]+=1.;return result
            with patch.object(saved,'curved_hphi_result',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'changed during'):save_curved_hphi_run(c,s,root/'changing')
            self.assertFalse((root/'changing').exists())
            s=solve_curved_hphi(c);original_link=saved.os.link
            def interrupted(source,target):
                if Path(target).name=='manifest.json':raise OSError('injected publication interruption')
                return original_link(source,target)
            with patch.object(saved.os,'link',side_effect=interrupted):
                with self.assertRaises(OSError):save_curved_hphi_run(c,s,root/'partial')
            self.assertFalse((root/'partial/manifest.json').exists())
            with self.assertRaises(ValueError):read_curved_hphi_run(root/'partial')
