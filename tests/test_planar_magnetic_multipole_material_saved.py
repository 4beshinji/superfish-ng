# SPDX-License-Identifier: Apache-2.0
import contextlib,copy,hashlib,io,json,shutil,tempfile,unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from scripts.planar_magnetic_multipole_material_reference import linear_limit,exterior_material
from scripts.planar_bh_reference import uniform_field
from superfish_ng.planar_bh import PlanarBHCase,solve_planar_bh
from superfish_ng.planar_recoil import solve_planar_recoil
from superfish_ng.planar_bh_saved import save_planar_bh_run,save_planar_bh_failure
from superfish_ng.planar_recoil_saved import save_planar_recoil_run
from superfish_ng.planar_magnetostatic_saved import _snapshot
from superfish_ng.nonlinear_magnetic import MagneticNewtonControls,MagneticNonlinearFailure
from superfish_ng.planar_magnetic_multipole_extraction import extract_planar_magnetic_multipoles
from superfish_ng import planar_magnetic_multipole_saved as saved
from superfish_ng.model import capabilities
from superfish_ng.cli import main


def fixture(root,kind='bh',exterior=True,order=1):
    case,frame,ref=exterior_material(kind,order=order,angle=.3) if exterior else linear_limit(kind,'quadrupole' if order==2 else 'dipole',order=order,n=4,rotation_rad=.3)
    solution=solve_planar_bh(case) if kind=='bh' else solve_planar_recoil(case);run=root/'source';publish=save_planar_bh_run if kind=='bh' else save_planar_recoil_run;publish(case,solution,run)
    request=dict(format='superfish_ng_planar_magnetic_multipole_request',schema_version=1,frame=frame.to_dict(),maximum_order=8,angular_samples=128);return run,solution,frame,request


class PlanarMagneticMultipoleMaterialSavedTests(unittest.TestCase):
    def test_exact_original_material_source_history_and_four_traces_roundtrip(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for index,(kind,exterior,order) in enumerate((('bh',False,1),('bh',True,1),('recoil',False,1),('recoil',False,2),('recoil',True,1),('recoil',True,2))):
                directory=root/str(index);directory.mkdir();run,solution,frame,request=fixture(directory,kind,exterior,order);before=_snapshot(run);path=directory/'report.json';result=saved.export_planar_magnetic_multipoles(run,path,request);self.assertEqual(result,saved.replay_planar_magnetic_multipoles(run,path));self.assertEqual(result['schema_version'],2);self.assertEqual(result['source_physics'],solution.case.to_dict()['physics']);self.assertEqual(result['source_native_manifest_format'],json.loads(before['manifest.json'])['format']);self.assertEqual(result['extraction'],extract_planar_magnetic_multipoles(solution,frame,8,128));self.assertEqual(_snapshot(run),before)
                if kind=='bh':self.assertIn('iteration',before['results.json'].decode())
                with self.assertRaises(FileExistsError):saved.export_planar_magnetic_multipoles(run,path,request)

    def test_edited_source_kind_schema_samples_and_material_claim_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);run,solution,frame,request=fixture(root);path=root/'report.json';report=saved.export_planar_magnetic_multipoles(run,path,request)
            edits=(('schema_version',1),('schema_version',True),('source_physics','linear_magnetostatic'),('source_native_manifest_format','superfish_ng_planar_recoil_manifest'))
            for key,value in edits:
                changed=copy.deepcopy(report);changed[key]=value;path.write_text(json.dumps(changed))
                with self.assertRaises(ValueError):saved.replay_planar_magnetic_multipoles(run,path)
            for kind in ('material','sample','coefficient','diagnostic'):
                changed=copy.deepcopy(report);extraction=changed['extraction']
                if kind=='material':extraction['source_free_disk']['linear_aperture_model']['checked_material_ids']=['invented']
                elif kind=='sample':extraction['traces'][3]['b_xy_t'][0][0]+=.01
                elif kind=='coefficient':extraction['series']['normal_t'][0]+=.01
                else:extraction['radial_coefficient_relative_difference']+=.01
                path.write_text(json.dumps(changed))
                with self.assertRaises(ValueError):saved.replay_planar_magnetic_multipoles(run,path)

    def test_rehashed_native_coefficients_and_missing_or_unknown_source_rejected(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);run,solution,frame,request=fixture(root,'recoil');before=_snapshot(run)
            with np.load(run/'fields.npz',allow_pickle=False) as archive:fields={k:archive[k] for k in archive.files}
            fields['az_relative_to_reference_wb_per_m']*=1.01;np.savez_compressed(run/'fields.npz',**fields);manifest=json.loads(before['manifest.json']);manifest['files']={name:hashlib.sha256((run/name).read_bytes()).hexdigest() for name in manifest['files']};(run/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):saved.export_planar_magnetic_multipoles(run,root/'bad.json',request)
            self.assertFalse((root/'bad.json').exists())
            for name,value in before.items():(run/name).write_bytes(value)
            manifest=json.loads(before['manifest.json']);manifest['format']='superfish_ng_axis_bh_manifest';(run/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'successful planar'):saved.export_planar_magnetic_multipoles(run,root/'unknown.json',request)
            (run/'manifest.json').unlink()
            with self.assertRaises(ValueError):saved.export_planar_magnetic_multipoles(run,root/'incomplete.json',request)

    def test_nonlinear_failure_native_is_not_a_valid_harmonic_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);run,solution,frame,request=fixture(root);case=replace(uniform_field(n=2)[0],controls=MagneticNewtonControls(max_iterations=1));failure=root/'failure'
            try:solve_planar_bh(case)
            except MagneticNonlinearFailure as exc:save_planar_bh_failure(case,exc,failure)
            else:self.fail('expected nonconvergence')
            before={p.name:p.read_bytes() for p in failure.iterdir()}
            with self.assertRaises(ValueError):saved.export_planar_magnetic_multipoles(failure,root/'bad.json',request)
            self.assertFalse((root/'bad.json').exists());self.assertEqual(before,{p.name:p.read_bytes() for p in failure.iterdir()})

    def test_source_links_midpublication_changes_and_interruption_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);run,solution,frame,request=fixture(root,'recoil');before=_snapshot(run);linked=root/'linked';linked.symlink_to(run,target_is_directory=True)
            with self.assertRaises(ValueError):saved.export_planar_magnetic_multipoles(linked,root/'link.json',request)
            original=saved.extract_planar_magnetic_multipoles
            def changed(*args):
                result=original(*args);p=run/'results.json';p.write_text(p.read_text()+'\n');return result
            with patch.object(saved,'extract_planar_magnetic_multipoles',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'changed during'):saved.export_planar_magnetic_multipoles(run,root/'changed.json',request)
            self.assertFalse((root/'changed.json').exists());(run/'results.json').write_bytes(before['results.json'])
            with patch.object(saved.os,'link',side_effect=OSError('interrupted')):
                with self.assertRaises(OSError):saved.export_planar_magnetic_multipoles(run,root/'partial.json',request)
            self.assertFalse((root/'partial.json').exists());self.assertEqual(_snapshot(run),before)

    def test_cli_full_json_bytes_and_material_capabilities(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);inventory=capabilities()['planar_magnetic_multipoles'];self.assertEqual(inventory['report_schema_versions'],[1,2]);self.assertEqual(inventory['extraction_schema_versions'],[1,2]);self.assertEqual(inventory['source_element_orders']['nonlinear_isotropic_magnetostatic'],[1]);self.assertFalse(inventory['gui'])
            for kind in ('bh','recoil'):
                directory=root/kind;directory.mkdir();run,solution,frame,request=fixture(directory,kind);before=_snapshot(run);req=directory/'request.json';req.write_text(json.dumps(request));api=directory/'api.json';cli=directory/'cli.json';report=saved.export_planar_magnetic_multipoles(run,api,request);self.assertIn(report['source_native_manifest_format'],inventory['source_native_manifest_formats'])
                for args in (['extract-planar-magnetic-multipoles',str(run),'--request',str(req),'--out',str(cli)],['replay-planar-magnetic-multipoles',str(run),str(cli)]):
                    out,err=io.StringIO(),io.StringIO()
                    with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):status=main(args)
                    self.assertEqual(status,0,err.getvalue());self.assertEqual(json.loads(out.getvalue()),report)
                self.assertEqual(api.read_bytes(),cli.read_bytes());self.assertEqual(_snapshot(run),before)


if __name__=='__main__':unittest.main()
