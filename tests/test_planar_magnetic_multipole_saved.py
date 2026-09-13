# SPDX-License-Identifier: Apache-2.0
import contextlib,copy,hashlib,io,json,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from scripts.planar_magnetic_multipole_reference import quadrupole,uniform_dipole
from superfish_ng.planar_magnetostatic import solve_planar_magnetostatic
from superfish_ng.planar_magnetostatic_saved import save_planar_magnetostatic_run,_snapshot
from superfish_ng import planar_magnetic_multipole_saved as saved
from superfish_ng.planar_magnetic_multipole_extraction import extract_planar_magnetic_multipoles
from superfish_ng.model import capabilities
from superfish_ng.cli import main


def request_for(frame):return dict(format='superfish_ng_planar_magnetic_multipole_request',schema_version=1,frame=frame.to_dict(),maximum_order=8,angular_samples=128)


def fixture(root,**kwargs):
    case,frame,ref=quadrupole(n=4,order=2,**kwargs);solution=solve_planar_magnetostatic(case);run=root/'source';save_planar_magnetostatic_run(case,solution,run);return run,solution,frame,request_for(frame)


class PlanarMagneticMultipoleSavedTests(unittest.TestCase):
    def test_original_coefficients_all_four_traces_and_source_roundtrip(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for i,(factory,order,angle) in enumerate(((uniform_dipole,1,0.),(uniform_dipole,2,.3),(quadrupole,2,-.7),(quadrupole,1,.3))):
                case,frame,ref=factory(n=8,order=order,rotation_rad=angle,offset=.125,mu_r=3.);solution=solve_planar_magnetostatic(case);run=root/str(i);save_planar_magnetostatic_run(case,solution,run);before=_snapshot(run);path=root/f'{i}.json';request=request_for(frame)
                report=saved.export_planar_magnetic_multipoles(run,path,request);self.assertEqual(report,saved.replay_planar_magnetic_multipoles(run,path));self.assertEqual(report['extraction'],extract_planar_magnetic_multipoles(solution,frame,8,128));self.assertEqual(_snapshot(run),before)
                self.assertEqual(len(report['source_native_sha256']),5);self.assertEqual([t['sample_count'] for t in report['extraction']['traces']],[128,256,128,256])
                self.assertEqual(json.loads(path.read_text()),report)
                with self.assertRaises(FileExistsError):saved.export_planar_magnetic_multipoles(run,path,request)
                self.assertEqual(json.loads(path.read_text()),report)
                with self.assertRaises(ValueError):saved.export_planar_magnetic_multipoles(run,run/'report.json',request)
                self.assertEqual(_snapshot(run),before)

    def test_edited_coefficients_original_samples_disk_diagnostics_and_types_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);run,solution,frame,request=fixture(root);path=root/'report.json';report=saved.export_planar_magnetic_multipoles(run,path,request)
            edits=(('schema_version',),('request','schema_version'),('extraction','schema_version'),('extraction','series','normal_t',1),('extraction','series','skew_t',0),('extraction','traces',0,'b_xy_t',0,0),('extraction','traces',3,'points_xy_m',0,0),('extraction','traces',2,'cell_indices',0),('extraction','traces',1,'sample_count'),('extraction','source_free_disk','mu_r'),('extraction','angular_coefficient_relative_difference'),('extraction','series','frame','rotation_rad'))
            for index,parts in enumerate(edits):
                changed=copy.deepcopy(report);parent=changed
                for key in parts[:-1]:parent=parent[key]
                parent[parts[-1]]=True if parts[-1]=='schema_version' else parent[parts[-1]]+1
                target=root/f'edited-{index}.json';target.write_text(json.dumps(changed))
                with self.assertRaises(ValueError):saved.replay_planar_magnetic_multipoles(run,target)
            changed=copy.deepcopy(report);changed['extraction']['unknown']=0;path.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):saved.replay_planar_magnetic_multipoles(run,path)

    def test_strict_request_source_identity_and_capabilities(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);run,solution,frame,request=fixture(root);path=root/'report.json';report=saved.export_planar_magnetic_multipoles(run,path,request)
            inventory=capabilities()['planar_magnetic_multipoles'];self.assertEqual(inventory['request_format'],request['format']);self.assertEqual(inventory['report_format'],report['format']);self.assertEqual(inventory['source_native_manifest_format'],json.loads((run/'manifest.json').read_text())['format']);self.assertFalse(inventory['gui']);self.assertEqual(inventory['element_orders'],[1,2])
            for key,value in (('schema_version',True),('maximum_order',True),('maximum_order',33),('angular_samples',False),('angular_samples',31),('angular_samples',8193),('unknown',1)):
                changed=copy.deepcopy(request);changed[key]=value;target=root/'invalid.json'
                with self.assertRaises(ValueError):saved.export_planar_magnetic_multipoles(run,target,changed)
                self.assertFalse(target.exists())
            changed=copy.deepcopy(request);changed['frame']['reference_radius_m']*=20
            with self.assertRaises(ValueError):saved.export_planar_magnetic_multipoles(run,root/'outside.json',changed)
            self.assertFalse((root/'outside.json').exists())
            (root/'different').mkdir();different,*_=fixture(root/'different',offset=.25)
            with self.assertRaisesRegex(ValueError,'hashes disagree'):saved.replay_planar_magnetic_multipoles(different,path)
            identical=root/'copy';shutil.copytree(run,identical);self.assertEqual(saved.replay_planar_magnetic_multipoles(identical,path),report)

    def test_links_incomplete_source_and_changed_source_or_report_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);run,solution,frame,request=fixture(root);path=root/'report.json';saved.export_planar_magnetic_multipoles(run,path,request)
            linked=root/'linked.json';linked.symlink_to(path)
            with self.assertRaises(ValueError):saved.replay_planar_magnetic_multipoles(run,linked)
            source_link=root/'source-link';source_link.symlink_to(run,target_is_directory=True)
            with self.assertRaises(ValueError):saved.export_planar_magnetic_multipoles(source_link,root/'bad.json',request)
            missing=root/'missing';shutil.copytree(run,missing);(missing/'manifest.json').unlink()
            with self.assertRaises(ValueError):saved.export_planar_magnetic_multipoles(missing,root/'bad.json',request)
            original=saved.extract_planar_magnetic_multipoles
            def changed_source(*args):
                result=original(*args);p=run/'case.json';p.write_text(p.read_text()+'\n');return result
            before=_snapshot(run)
            with patch.object(saved,'extract_planar_magnetic_multipoles',side_effect=changed_source):
                with self.assertRaisesRegex(ValueError,'changed during'):saved.export_planar_magnetic_multipoles(run,root/'changed.json',request)
            self.assertFalse((root/'changed.json').exists());(run/'case.json').write_bytes(before['case.json'])
            def changed_report(*args):
                result=original(*args);path.write_text(path.read_text()+'\n');return result
            with patch.object(saved,'extract_planar_magnetic_multipoles',side_effect=changed_report):
                with self.assertRaisesRegex(ValueError,'changed during'):saved.replay_planar_magnetic_multipoles(run,path)

    def test_request_mutation_and_interrupted_publication_leave_no_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);run,solution,frame,request=fixture(root);before=_snapshot(run);original=saved.extract_planar_magnetic_multipoles
            def changed_request(*args):
                result=original(*args);request['maximum_order']=7;return result
            with patch.object(saved,'extract_planar_magnetic_multipoles',side_effect=changed_request):
                with self.assertRaisesRegex(ValueError,'request changed'):saved.export_planar_magnetic_multipoles(run,root/'changed.json',request)
            self.assertFalse((root/'changed.json').exists())
            with patch.object(saved.os,'link',side_effect=OSError('publication interrupted')):
                with self.assertRaises(OSError):saved.export_planar_magnetic_multipoles(run,root/'partial.json',request)
            self.assertFalse((root/'partial.json').exists());self.assertFalse(list(root.glob('.planar-multipole-report-*')));self.assertEqual(_snapshot(run),before)

    def test_cli_full_json_and_exit_states(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);run,solution,frame,request=fixture(root);before=_snapshot(run);req=root/'request.json';req.write_text(json.dumps(request));api=root/'api.json';cli=root/'cli.json';report=saved.export_planar_magnetic_multipoles(run,api,request)
            def execute(args):
                out,err=io.StringIO(),io.StringIO()
                with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):status=main(args)
                return status,out.getvalue(),err.getvalue()
            status,out,err=execute(['extract-planar-magnetic-multipoles',str(run),'--request',str(req),'--out',str(cli)]);self.assertEqual(status,0,err);self.assertEqual(json.loads(out),report);self.assertEqual(cli.read_bytes(),api.read_bytes())
            status,out,err=execute(['replay-planar-magnetic-multipoles',str(run),str(cli)]);self.assertEqual(status,0,err);self.assertEqual(json.loads(out),report)
            status,_,_=execute(['extract-planar-magnetic-multipoles',str(run),'--request',str(req),'--out',str(cli)]);self.assertEqual(status,2)
            req.write_text('{"format":');status,_,_=execute(['extract-planar-magnetic-multipoles',str(run),'--request',str(req),'--out',str(root/'bad.json')]);self.assertEqual(status,2);self.assertFalse((root/'bad.json').exists());self.assertEqual(_snapshot(run),before)


if __name__=='__main__':unittest.main()
