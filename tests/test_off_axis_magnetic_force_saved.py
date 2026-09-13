# SPDX-License-Identifier: Apache-2.0
import contextlib,copy,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts.off_axis_magnetic_force_reference import axial_current_body
from scripts.planar_magnetic_force_reference import current_body
from superfish_ng.off_axis_magnetostatic import solve_off_axis_magnetostatic
from superfish_ng.off_axis_magnetostatic_saved import save_off_axis_magnetostatic_run,_snapshot
from superfish_ng.planar_magnetostatic import solve_planar_magnetostatic
from superfish_ng.planar_magnetostatic_saved import save_planar_magnetostatic_run
from superfish_ng import off_axis_magnetic_force_saved as saved
from superfish_ng.cli import main
from superfish_ng.model import capabilities


def fixture(root,order=1,virtual=False,current=10.,mu=1.):
    case,body,w,ref=axial_current_body(order=order,current_a=current,body_mu_r=mu);source=root/'source';save_off_axis_magnetostatic_run(case,solve_off_axis_magnetostatic(case),source);request=dict(format='superfish_ng_off_axis_magnetic_force_request',schema_version=1,body_region_ids=list(body),weights=w.tolist(),virtual_work=dict(translation_steps_m=[1e-5,5e-6]) if virtual else None);return source,request,ref


class OffAxisMagneticForceSavedTests(unittest.TestCase):
    def test_full_ring_stress_and_optional_work_roundtrip_with_unchanged_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for order in (1,2):
                for virtual in (False,True):
                    directory=root/f'{order}-{virtual}';directory.mkdir();source,request,ref=fixture(directory,order,virtual);before=_snapshot(source);path=directory/'report.json';report=saved.export_off_axis_magnetic_force(source,path,request);self.assertEqual(report,saved.replay_off_axis_magnetic_force(source,path));self.assertEqual(_snapshot(source),before);self.assertLess(abs(report['force']['force_z_n']-ref['force_z_n'])/ref['force_scale_n'],1e-9)
                    if virtual:
                        self.assertEqual(len(report['virtual_work']['records']),2)
                        for row in report['stress_virtual_work_comparison']:self.assertLess(abs(row['difference_n'])/ref['force_scale_n'],1e-5)
                    else:self.assertIsNone(report['virtual_work']);self.assertIsNone(report['stress_virtual_work_comparison'])
                    self.assertNotIn('force_r_n',report['force'])

    def test_modified_force_units_quadrature_weights_psi_and_displaced_potential_reject(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source,request,ref=fixture(root,1,True);report=saved.export_off_axis_magnetic_force(source,root/'report.json',request)
            mutations=[(('schema_version',),True),(('force','force_z_n'),0.),(('force','conventions'),'N/m'),(('force','quadrature_orders',0),4),(('force','weights',100),.01),(('force','source_relative_psi_sha256'),'wrong'),(('virtual_work','records',0,'trials',0,'stationary_potential_j'),0.),(('virtual_work','records',0,'trials',0,'case','partition','geometry','points_rz_m',0,0),0.),(('stress_virtual_work_comparison',0,'difference_n'),0.)]
            for index,(parts,value) in enumerate(mutations):
                changed=copy.deepcopy(report);target=changed
                for key in parts[:-1]:target=target[key]
                target[parts[-1]]=value;path=root/f'edited-{index}.json';path.write_text(json.dumps(changed))
                with self.assertRaises(ValueError):saved.replay_off_axis_magnetic_force(source,path)

    def test_strict_requests_and_wrong_planar_source_cannot_reinterpret_force_units(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source,request,ref=fixture(root)
            for key,value in (('schema_version',True),('origin_xy_m',[0.,0.]),('body_region_ids',['unknown']),('weights',[False]*len(request['weights'])),('virtual_work',{}),('virtual_work',dict(translation_steps_m=[1e-5,5e-6],rotation_steps_rad=[.1,.05]))):
                changed=copy.deepcopy(request);changed[key]=value
                with self.assertRaises(ValueError):saved.export_off_axis_magnetic_force(source,root/'invalid.json',changed)
                self.assertFalse((root/'invalid.json').exists())
            case,*_=current_body(order=1);planar=root/'planar';save_planar_magnetostatic_run(case,solve_planar_magnetostatic(case),planar)
            with self.assertRaises(ValueError):saved.export_off_axis_magnetic_force(planar,root/'wrong-physics.json',request)
            self.assertFalse((root/'wrong-physics.json').exists())

    def test_source_request_and_report_changes_during_analysis_reject(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source,request,ref=fixture(root);before=_snapshot(source);original=saved.off_axis_magnetic_force
            def source_changed(*args):
                result=original(*args);(source/'case.json').write_bytes(before['case.json']+b'\n');return result
            with patch.object(saved,'off_axis_magnetic_force',side_effect=source_changed):
                with self.assertRaisesRegex(ValueError,'changed during'):saved.export_off_axis_magnetic_force(source,root/'changed.json',request)
            self.assertFalse((root/'changed.json').exists());(source/'case.json').write_bytes(before['case.json']);old=copy.deepcopy(request)
            def request_changed(*args):
                result=original(*args);request['weights'][0]=.01;return result
            with patch.object(saved,'off_axis_magnetic_force',side_effect=request_changed):
                with self.assertRaisesRegex(ValueError,'request changed'):saved.export_off_axis_magnetic_force(source,root/'request.json',request)
            request=old;path=root/'report.json';saved.export_off_axis_magnetic_force(source,path,request)
            def report_changed(*args):
                result=original(*args);path.write_text(path.read_text()+'\n');return result
            with patch.object(saved,'off_axis_magnetic_force',side_effect=report_changed):
                with self.assertRaisesRegex(ValueError,'report changed'):saved.replay_off_axis_magnetic_force(source,path)

    def test_nonoverwrite_links_wrong_source_and_interrupted_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source,request,ref=fixture(root);before=_snapshot(source);path=root/'report.json';saved.export_off_axis_magnetic_force(source,path,request)
            with self.assertRaises(FileExistsError):saved.export_off_axis_magnetic_force(source,path,request)
            with self.assertRaises(ValueError):saved.export_off_axis_magnetic_force(source,source/'report.json',request)
            link=root/'linked.json';link.symlink_to(path)
            with self.assertRaises(ValueError):saved.replay_off_axis_magnetic_force(source,link)
            linked_source=root/'linked-source';linked_source.symlink_to(source,target_is_directory=True)
            with self.assertRaises(ValueError):saved.export_off_axis_magnetic_force(linked_source,root/'bad-source.json',request)
            (root/'other').mkdir();other,*_=fixture(root/'other',current=20.)
            with self.assertRaisesRegex(ValueError,'hashes disagree'):saved.replay_off_axis_magnetic_force(other,path)
            with patch.object(saved.os,'link',side_effect=OSError('interrupted')):
                with self.assertRaises(OSError):saved.export_off_axis_magnetic_force(source,root/'partial.json',request)
            self.assertFalse((root/'partial.json').exists());self.assertFalse(list(root.glob('.axial-force-report-*')));self.assertEqual(_snapshot(source),before)

    def test_cli_exact_report_and_bytes_exit_codes_and_capabilities(self):
        inventory=capabilities()['off_axis_magnetic_force'];self.assertEqual(inventory['force_unit'],'N');self.assertEqual(inventory['potential_unit'],'J');self.assertEqual(inventory['element_orders'],[1,2]);self.assertFalse(inventory['gui'])
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for index,(order,virtual,mu) in enumerate(((1,False,1.),(2,True,3.))):
                directory=root/str(index);directory.mkdir();source,request,ref=fixture(directory,order,virtual,-10.,mu);req=directory/'request.json';req.write_text(json.dumps(request));api=directory/'api.json';cli=directory/'cli.json';expected=saved.export_off_axis_magnetic_force(source,api,request);before=_snapshot(source)
                for arguments in (['analyze-off-axis-magnetic-force',str(source),'--request',str(req),'--out',str(cli)],['replay-off-axis-magnetic-force',str(source),str(cli)]):
                    out,err=io.StringIO(),io.StringIO()
                    with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):code=main(arguments)
                    self.assertEqual(code,0,err.getvalue());self.assertEqual(json.loads(out.getvalue()),expected)
                self.assertEqual(api.read_bytes(),cli.read_bytes());self.assertEqual(_snapshot(source),before)
                with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):code=main(['analyze-off-axis-magnetic-force',str(source),'--request',str(req),'--out',str(cli)])
                self.assertEqual(code,2)


if __name__=='__main__':unittest.main()
