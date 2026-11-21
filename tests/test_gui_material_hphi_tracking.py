# SPDX-License-Identifier: Apache-2.0
from contextlib import ExitStack
import json,tempfile,threading,unittest
from pathlib import Path
from superfish_ng.gui_hphi import hphi_response
from superfish_ng.jobs import JobManager
from superfish_ng.hphi_native import save_hphi_run
from test_material_hphi_tracking_jobs import pair
from superfish_ng.material_hphi_tracking_history import MaterialHphiTrackingHistoryRequest


class MaterialHphiTrackingGuiTests(unittest.TestCase):
    def test_strict_gui_start_restore_original_side_and_repeat_from_owned_sources(self):
        with tempfile.TemporaryDirectory() as t,ExitStack() as cleanup:
            root=Path(t);manager=JobManager(root/'jobs');cleanup.callback(manager.close);(a,b),q=pair();sources=[];lock=threading.Lock()
            def api(action,**data):return hphi_response(manager,action,data,lock,root/'cache')[0]
            for i,solution in enumerate((a,b)):
                native=root/f'native-{i}';save_hphi_run(solution.case,solution,native);sources.append(manager.import_hphi_result(native))
            self.assertEqual(api('hphi-normalize-tracking',document=json.dumps(q.to_dict())),q.to_dict())
            identifier=api('hphi-start-tracking',previous_id=sources[0],current_id=sources[1],document=q.to_dict())['id']
            self.assertEqual(manager.processes[identifier].wait(timeout=120),0);reply=api('hphi-tracking-result',id=identifier)
            self.assertEqual(reply['result']['status'],'PASS');self.assertEqual(reply['request'],q.to_dict())
            imported=api('hphi-tracking-side',id=identifier,side='previous')['id']
            original=manager.directory(identifier)/'previous';target=manager.directory(imported)
            self.assertEqual((original/'project.json').read_bytes(),(target/'project.json').read_bytes())
            self.assertEqual({p.name:p.read_bytes() for p in (original/'solution').iterdir()},{p.name:p.read_bytes() for p in (target/'solution').iterdir()})
            for i,source in enumerate(sources):manager.directory(source).rename(root/f'moved-source-{i}')
            rerun=api('hphi-repeat-tracking',id=identifier,document=q.to_dict())['id'];self.assertNotEqual(rerun,identifier)
            self.assertEqual(manager.processes[rerun].wait(timeout=120),0);self.assertEqual(api('hphi-tracking-result',id=rerun)['result'],reply['result'])
            history_request=MaterialHphiTrackingHistoryRequest(1).to_dict()
            self.assertEqual(api('hphi-normalize-history',document=history_request),history_request)
            history_id=api('hphi-start-history',document=history_request,step_ids=[rerun])['id']
            self.assertEqual(manager.processes[history_id].wait(timeout=180),0)
            history_reply=api('hphi-history-result',id=history_id)
            self.assertEqual(history_reply['result']['status'],'PASS')
            self.assertEqual(history_reply['step_requests'],[q.to_dict()])
            side_id=api('hphi-history-source',id=history_id,index=0,side='current')['id']
            saved=manager.directory(history_id)/'step-0000/current'
            target=manager.directory(side_id)
            self.assertEqual((saved/'project.json').read_bytes(),(target/'project.json').read_bytes())
            self.assertEqual({p.name:p.read_bytes() for p in (saved/'solution').iterdir()},
                             {p.name:p.read_bytes() for p in (target/'solution').iterdir()})
            before=len(manager.list())
            for action,data in (('hphi-tracking-side',dict(id=identifier,side=True)),
                    ('hphi-start-tracking',dict(previous_id=identifier,current_id=imported,document=q.to_dict())),
                    ('hphi-repeat-tracking',dict(id=identifier,document={**q.to_dict(),'unsupported':True}))):
                with self.assertRaises(ValueError):api(action,**data)
            self.assertEqual(len(manager.list()),before)

    def test_invalid_control_document_rejected_without_allocating_a_job(self):
        with tempfile.TemporaryDirectory() as t,ExitStack() as cleanup:
            manager=JobManager(Path(t)/'jobs');cleanup.callback(manager.close);lock=threading.Lock()
            with self.assertRaises(ValueError):hphi_response(manager,'hphi-normalize-tracking',dict(document={'format':'superfish_ng_planar_tracking_request'}),lock,Path(t)/'cache')
            with self.assertRaises(ValueError):hphi_response(manager,'hphi-start-tracking',dict(document={}),lock,Path(t)/'cache')
            self.assertEqual(manager.list(),[])


if __name__=='__main__':unittest.main()
