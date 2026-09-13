# SPDX-License-Identifier: Apache-2.0
import contextlib,copy,io,json,tempfile,unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from scripts.planar_magnetic_force_material_reference import material_body
from superfish_ng.planar_bh import solve_planar_bh
from superfish_ng.planar_recoil import solve_planar_recoil
from superfish_ng.planar_bh_saved import save_planar_bh_run,save_planar_bh_failure
from superfish_ng.planar_recoil_saved import save_planar_recoil_run
from superfish_ng.planar_magnetostatic_saved import _snapshot
from superfish_ng.nonlinear_magnetic import MagneticNewtonControls,MagneticNonlinearFailure
from superfish_ng.planar_magnetic_material_virtual_work import material_planar_magnetic_virtual_work,PlanarMagneticVirtualWorkFailure
from superfish_ng import planar_magnetic_force_saved as saved
from superfish_ng.cli import main
from superfish_ng.model import capabilities


def fixture(root,kind='bh',order=1,virtual=True,failure=None):
    case,body,w,c,ref=material_body(kind,nonlinear=True,principal=(2.,5.),permanent=kind=='recoil',current_a=0. if failure else 1000.,order=order)
    solver=solve_planar_bh if kind=='bh' else solve_planar_recoil;solution=solver(case)
    if failure:
        case=replace(case,controls=MagneticNewtonControls(max_iterations=1),initial_az_relative_to_reference_wb_per_m=solution.az_relative_to_reference_wb_per_m.tolist());solution=solver(case)
    source=root/'source';(save_planar_bh_run if kind=='bh' else save_planar_recoil_run)(case,solution,source)
    translation=[1e-4,5e-5] if failure=='first' else [1e-6,5e-7] if failure=='later' else [1e-5,5e-6];rotation=[.01,.005] if failure=='later' else [.001,.0005]
    request=dict(format='superfish_ng_planar_magnetic_force_request',schema_version=1,body_region_ids=list(body),weights=w.tolist(),origin_xy_m=c.tolist(),virtual_work=dict(translation_steps_m=translation,rotation_steps_rad=rotation) if virtual else None)
    return source,case,request


class PlanarMagneticForceMaterialSavedTests(unittest.TestCase):
    def test_material_success_and_null_report_roundtrip_preserve_original_native(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for index,(kind,order,virtual) in enumerate((('bh',1,False),('bh',1,True),('recoil',1,False),('recoil',1,True),('recoil',2,False),('recoil',2,True))):
                directory=root/str(index);directory.mkdir();source,case,request=fixture(directory,kind,order,virtual);before=_snapshot(source);path=directory/'report.json';report=saved.export_planar_magnetic_force(source,path,request);self.assertEqual(report,saved.replay_planar_magnetic_force(source,path));self.assertEqual(report['schema_version'],2);self.assertEqual(report['status'],'complete');self.assertEqual(report['source_physics'],case.to_dict()['physics']);self.assertEqual(report['force']['schema_version'],2);self.assertEqual(_snapshot(source),before)
                if virtual:
                    self.assertEqual(report['virtual_work']['schema_version'],2);self.assertEqual(report['virtual_work']['status'],'complete');self.assertEqual(len(report['stress_virtual_work_comparison']),6)
                else:self.assertIsNone(report['virtual_work']);self.assertIsNone(report['stress_virtual_work_comparison'])

    def test_actual_displacement_failure_is_published_replayed_and_keeps_completed_pairs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for mode in ('first','later'):
                directory=root/mode;directory.mkdir();source,case,request=fixture(directory,failure=mode);before=_snapshot(source);path=directory/'failure-report.json';report=saved.export_planar_magnetic_force(source,path,request);self.assertEqual(report['status'],'virtual_work_failed');self.assertEqual(report['virtual_work']['status'],'failed');self.assertEqual(report,saved.replay_planar_magnetic_force(source,path));self.assertEqual(_snapshot(source),before)
                comparison=report['stress_virtual_work_comparison'];self.assertIsNone(comparison[-1]['virtual_work_value']);self.assertIsNone(comparison[-1]['difference']);self.assertEqual(comparison[-1]['stress_value'],report['force']['nodal_rotation_stress_torque_z_nm_per_m'] if mode=='later' else report['force']['force_xy_n_per_m'][0])
                if mode=='later':self.assertEqual(len(comparison),5);self.assertTrue(all(row['virtual_work_value'] is not None for row in comparison[:-1]))
                with self.assertRaises(PlanarMagneticVirtualWorkFailure) as caught:material_planar_magnetic_virtual_work(case,request['body_region_ids'],request['weights'],request['origin_xy_m'],**request['virtual_work'])
                self.assertEqual(caught.exception.report,report['virtual_work']);self.assertIsNotNone(report['virtual_work']['failure']['nonlinear_failure']['last_valid_relative_coefficients'])

    def test_tampered_material_motion_potential_status_and_failure_history_reject(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for label,kind,mode in (('recoil','recoil',None),('failure','bh','later')):
                directory=root/label;directory.mkdir();source,case,request=fixture(directory,kind,1,True,mode);path=directory/'report.json';report=saved.export_planar_magnetic_force(source,path,request)
                mutations=[(('schema_version',),True),(('status',),'complete' if mode else 'virtual_work_failed'),(('source_physics',),'linear_magnetostatic'),(('source_native_manifest_format',),'superfish_ng_planar_magnetostatic_manifest')]
                if mode:mutations += [(('virtual_work','failure','nonlinear_failure','history',0,'relative_residual'),1.),(('virtual_work','failure','nonlinear_failure','last_valid_relative_coefficients',0),1.),(('stress_virtual_work_comparison',4,'difference'),0.)]
                else:mutations += [(('virtual_work','records',4,'trials',0,'case','partition','regions',1,'orientation_rad'),0.),(('virtual_work','records',0,'trials',0,'constitutive_potential_j_per_m'),0.),(('virtual_work','records',0,'trials',0,'constitutive_reference'),'H=0')]
                for index,(parts,value) in enumerate(mutations):
                    changed=copy.deepcopy(report);target=changed
                    for key in parts[:-1]:target=target[key]
                    target[parts[-1]]=value;edited=directory/f'edited-{index}.json';edited.write_text(json.dumps(changed))
                    with self.assertRaises(ValueError):saved.replay_planar_magnetic_force(source,edited)

    def test_cli_complete_failed_and_invalid_exit_codes_match_api_json_and_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for label,kind,virtual,failure,status in (('null','recoil',False,None,0),('work','recoil',True,None,0),('failure','bh',True,'later',1)):
                directory=root/label;directory.mkdir();source,case,request=fixture(directory,kind,1,virtual,failure);req=directory/'request.json';req.write_text(json.dumps(request));api=directory/'api.json';cli=directory/'cli.json';expected=saved.export_planar_magnetic_force(source,api,request)
                for args in (['analyze-planar-magnetic-force',str(source),'--request',str(req),'--out',str(cli)],['replay-planar-magnetic-force',str(source),str(cli)]):
                    out,err=io.StringIO(),io.StringIO()
                    with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):code=main(args)
                    self.assertEqual(code,status,err.getvalue());self.assertEqual(json.loads(out.getvalue()),expected)
                self.assertEqual(api.read_bytes(),cli.read_bytes())
                with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):code=main(['analyze-planar-magnetic-force',str(source),'--request',str(req),'--out',str(cli)])
                self.assertEqual(code,2)

    def test_failed_source_and_material_midchange_link_or_interruption_reject(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source,case,request=fixture(root,'bh',1,True,'first');before=_snapshot(source);original=saved.material_planar_magnetic_virtual_work
            def changed(*args,**kwargs):
                try:return original(*args,**kwargs)
                finally:(source/'case.json').write_bytes(before['case.json']+b'\n')
            with patch.object(saved,'material_planar_magnetic_virtual_work',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'changed during'):saved.export_planar_magnetic_force(source,root/'changed.json',request)
            self.assertFalse((root/'changed.json').exists());(source/'case.json').write_bytes(before['case.json']);path=root/'report.json';saved.export_planar_magnetic_force(source,path,request);linked=root/'linked.json';linked.symlink_to(path)
            with self.assertRaises(ValueError):saved.replay_planar_magnetic_force(source,linked)
            with patch.object(saved.os,'link',side_effect=OSError('interrupted')):
                with self.assertRaises(OSError):saved.export_planar_magnetic_force(source,root/'partial.json',request)
            self.assertFalse((root/'partial.json').exists());self.assertEqual(_snapshot(source),before)
            failed_case=replace(case,initial_az_relative_to_reference_wb_per_m=None)
            try:solve_planar_bh(failed_case)
            except MagneticNonlinearFailure as exc:save_planar_bh_failure(failed_case,exc,root/'failed-source')
            else:self.fail('expected actual nonlinear source failure')
            with self.assertRaises(ValueError):saved.export_planar_magnetic_force(root/'failed-source',root/'invalid-source-report.json',request)
            self.assertFalse((root/'invalid-source-report.json').exists())

    def test_capabilities_and_strict_material_request_formats(self):
        inventory=capabilities()['planar_magnetic_force'];self.assertEqual(inventory['report_schema_versions'],[1,2]);self.assertEqual(inventory['source_element_orders']['nonlinear_bh'],[1]);self.assertEqual(inventory['cli_exit_codes']['retained_virtual_work_failure'],1);self.assertFalse(inventory['gui'])
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source,case,request=fixture(root,'recoil',1,False)
            for key,value in (('schema_version',2),('unknown',0),('origin_xy_m',[True,0.]),('virtual_work',{})):
                changed=copy.deepcopy(request);changed[key]=value
                with self.assertRaises(ValueError):saved.export_planar_magnetic_force(source,root/'invalid.json',changed)
                self.assertFalse((root/'invalid.json').exists())


if __name__=='__main__':unittest.main()
