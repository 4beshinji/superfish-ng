# SPDX-License-Identifier: Apache-2.0
import contextlib,copy,io,json,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts.planar_magnetic_force_reference import current_body
from scripts.planar_magnetic_multipole_material_reference import linear_limit
from superfish_ng.planar_magnetostatic import solve_planar_magnetostatic
from superfish_ng.planar_magnetostatic_saved import save_planar_magnetostatic_run,_snapshot
from superfish_ng.planar_bh import solve_planar_bh
from superfish_ng.planar_bh_saved import save_planar_bh_run
from superfish_ng.planar_magnetic_force import planar_magnetic_force
from superfish_ng import planar_magnetic_force_saved as saved
from superfish_ng.model import capabilities
from superfish_ng.cli import main


def fixture(root,pair=False,order=1,virtual=False):
    case,body,w,origin,ref=current_body(pair=pair,order=order);solution=solve_planar_magnetostatic(case);run=root/'source';save_planar_magnetostatic_run(case,solution,run)
    request=dict(format='superfish_ng_planar_magnetic_force_request',schema_version=1,body_region_ids=list(body),weights=w.tolist(),origin_xy_m=origin.tolist(),virtual_work=dict(translation_steps_m=[1e-5,5e-6],rotation_steps_rad=[1e-3,5e-4]) if virtual else None)
    return run,solution,body,w,origin,request


class PlanarMagneticForceSavedTests(unittest.TestCase):
    def test_original_stress_and_optional_displaced_fem_report_roundtrip(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for i,(pair,order,virtual) in enumerate(((False,1,False),(True,2,False),(True,1,True),(False,2,True))):
                directory=root/str(i);directory.mkdir();run,solution,body,w,origin,request=fixture(directory,pair,order,virtual);before=_snapshot(run);path=directory/'report.json';report=saved.export_planar_magnetic_force(run,path,request);self.assertEqual(report,saved.replay_planar_magnetic_force(run,path));self.assertEqual(report['force'],planar_magnetic_force(solution,body,w,origin));self.assertEqual(_snapshot(run),before)
                if virtual:
                    self.assertEqual(len(report['virtual_work']['records']),6);self.assertEqual(len(report['stress_virtual_work_comparison']),6)
                    for row in report['stress_virtual_work_comparison']:
                        if row['kind']=='rotation':self.assertEqual(row['stress_quantity'],'nodal_rotation_stress_torque_z_nm_per_m')
                    if pair and order==1:self.assertGreater(abs(report['force']['nodal_minus_weighted_torque_nm_per_m']),1e-5)
                else:self.assertIsNone(report['virtual_work']);self.assertIsNone(report['stress_virtual_work_comparison'])
                with self.assertRaises(FileExistsError):saved.export_planar_magnetic_force(run,path,request)
                with self.assertRaises(ValueError):saved.export_planar_magnetic_force(run,run/'report.json',request)
                self.assertEqual(_snapshot(run),before)

    def test_modified_force_weight_motion_potential_units_and_comparison_reject(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);run,solution,body,w,origin,request=fixture(root,True,1,True);path=root/'report.json';report=saved.export_planar_magnetic_force(run,path,request)
            changes=(('schema_version',),('force','force_xy_n_per_m',0),('force','nodal_rotation_stress_torque_z_nm_per_m'),('force','torque_z_nm_per_m'),('force','weights',100),('virtual_work','records',0,'trials',0,'stationary_potential_j_per_m'),('virtual_work','records',4,'trials',1,'case','partition','geometry','points_xy_m',0,0),('stress_virtual_work_comparison',4,'difference'))
            for index,parts in enumerate(changes):
                changed=copy.deepcopy(report);parent=changed
                for key in parts[:-1]:parent=parent[key]
                parent[parts[-1]]=True if parts[-1]=='schema_version' else parent[parts[-1]]+1;target=root/f'edited-{index}.json';target.write_text(json.dumps(changed))
                with self.assertRaises(ValueError):saved.replay_planar_magnetic_force(run,target)
            changed=copy.deepcopy(report);changed['stress_virtual_work_comparison'][4]['unit']='N';path.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):saved.replay_planar_magnetic_force(run,path)

    def test_strict_requests_unknown_sources_and_capabilities(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);run,solution,body,w,origin,request=fixture(root);inventory=capabilities()['planar_magnetic_force'];self.assertEqual(inventory['request_format'],request['format']);self.assertEqual(inventory['force_unit'],'N/m');self.assertEqual(inventory['torque_unit'],'N m/m');self.assertFalse(inventory['gui'])
            for key,value in (('schema_version',True),('unknown',0),('body_region_ids',['unknown']),('weights',[False]*len(w)),('origin_xy_m',[False,0.]),('virtual_work',False),('virtual_work',dict(translation_steps_m=[0.,1.],rotation_steps_rad=[.1,.05]))):
                changed=copy.deepcopy(request);changed[key]=value;path=root/'invalid.json'
                with self.assertRaises(ValueError):saved.export_planar_magnetic_force(run,path,changed)
                self.assertFalse(path.exists())
            case,_,_=linear_limit('bh','dipole',order=1,n=4);bh=root/'bh';save_planar_bh_run(case,solve_planar_bh(case),bh)
            with self.assertRaises(ValueError):saved.export_planar_magnetic_force(bh,root/'unsupported.json',request)
            self.assertFalse((root/'unsupported.json').exists())

    def test_source_report_and_request_changes_during_verification_reject(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);run,solution,body,w,origin,request=fixture(root);before=_snapshot(run);original=saved.planar_magnetic_force
            def source_changed(*args):
                result=original(*args);p=run/'case.json';p.write_text(p.read_text()+'\n');return result
            with patch.object(saved,'planar_magnetic_force',side_effect=source_changed):
                with self.assertRaisesRegex(ValueError,'changed during'):saved.export_planar_magnetic_force(run,root/'changed.json',request)
            self.assertFalse((root/'changed.json').exists());(run/'case.json').write_bytes(before['case.json'])
            def request_changed(*args):
                result=original(*args);request['origin_xy_m'][0]+=.01;return result
            with patch.object(saved,'planar_magnetic_force',side_effect=request_changed):
                with self.assertRaisesRegex(ValueError,'request changed'):saved.export_planar_magnetic_force(run,root/'request.json',request)
            self.assertFalse((root/'request.json').exists());path=root/'report.json';saved.export_planar_magnetic_force(run,path,request)
            def report_changed(*args):
                result=original(*args);path.write_text(path.read_text()+'\n');return result
            with patch.object(saved,'planar_magnetic_force',side_effect=report_changed):
                with self.assertRaisesRegex(ValueError,'changed during'):saved.replay_planar_magnetic_force(run,path)

    def test_links_wrong_source_and_interrupted_publication_reject(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);run,solution,body,w,origin,request=fixture(root);path=root/'report.json';saved.export_planar_magnetic_force(run,path,request);before=_snapshot(run);linked=root/'link.json';linked.symlink_to(path)
            with self.assertRaises(ValueError):saved.replay_planar_magnetic_force(run,linked)
            linked_run=root/'linked-run';linked_run.symlink_to(run,target_is_directory=True)
            with self.assertRaises(ValueError):saved.export_planar_magnetic_force(linked_run,root/'bad.json',request)
            (root/'other').mkdir();other,*_=fixture(root/'other',pair=True)
            with self.assertRaisesRegex(ValueError,'hashes disagree'):saved.replay_planar_magnetic_force(other,path)
            with patch.object(saved.os,'link',side_effect=OSError('interrupted')):
                with self.assertRaises(OSError):saved.export_planar_magnetic_force(run,root/'partial.json',request)
            self.assertFalse((root/'partial.json').exists());self.assertFalse(list(root.glob('.planar-force-report-*')));self.assertEqual(_snapshot(run),before)

    def test_cli_exact_json_and_bytes_with_and_without_virtual_work(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for virtual in (False,True):
                directory=root/str(virtual);directory.mkdir();run,solution,body,w,origin,request=fixture(directory,True,1,virtual);before=_snapshot(run);req=directory/'request.json';req.write_text(json.dumps(request));api=directory/'api.json';cli=directory/'cli.json';report=saved.export_planar_magnetic_force(run,api,request)
                for args in (['analyze-planar-magnetic-force',str(run),'--request',str(req),'--out',str(cli)],['replay-planar-magnetic-force',str(run),str(cli)]):
                    out,err=io.StringIO(),io.StringIO()
                    with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):status=main(args)
                    self.assertEqual(status,0,err.getvalue());self.assertEqual(json.loads(out.getvalue()),report)
                self.assertEqual(api.read_bytes(),cli.read_bytes());self.assertEqual(_snapshot(run),before)
                with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):status=main(['analyze-planar-magnetic-force',str(run),'--request',str(req),'--out',str(cli)])
                self.assertEqual(status,2)


if __name__=='__main__':unittest.main()
