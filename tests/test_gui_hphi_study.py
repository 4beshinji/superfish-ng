# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
from contextlib import ExitStack
import tempfile,threading,unittest
from unittest.mock import patch
from superfish_ng.coaxial import CoaxialCase
from superfish_ng.hphi_project import HphiProject
from superfish_ng.hphi_study import HphiStudy
from superfish_ng.jobs import JobManager
from superfish_ng.gui_hphi import hphi_response


class HphiStudyGuiTests(unittest.TestCase):
    def test_definition_worker_result_and_owned_point(self):
        with tempfile.TemporaryDirectory() as temp, ExitStack() as cleanup:
            root=Path(temp);manager=JobManager(root/'jobs');cleanup.callback(manager.close);lock=threading.Lock()
            def request(action,**data):return hphi_response(manager,action,data,lock,root/'cache')[0]
            study=HphiStudy(HphiProject(CoaxialCase(.025,.05,.18,nr=3,nz=8,modes=2)),'uniform_scale',[1,2])
            self.assertEqual(request('hphi-normalize-study',document=study.to_dict()),study.to_dict())
            for data in ({'document':study.to_dict(),'extra':0},{'document':dict(study.to_dict(),study_version=True)}):
                with self.assertRaises(ValueError):request('hphi-start-study',**data)
            identifier=request('hphi-start-study',document=study.to_dict())['id'];self.assertEqual(manager.processes[identifier].wait(timeout=30),0)
            reply=request('hphi-study-result',id=identifier);self.assertEqual(reply['study'],study.to_dict());self.assertEqual(reply['result']['mode_tracking'],'not_performed')
            source=manager.directory(identifier)/'point-0001/solution';before={p.name:p.read_bytes() for p in source.iterdir()}
            imported=request('hphi-study-point',id=identifier,index=1)['id'];self.assertEqual(before,{p.name:p.read_bytes() for p in (manager.directory(imported)/'solution').iterdir()})
            self.assertEqual(request('hphi-result',id=imported)['project'],study.projects()[1].to_dict())
            for index in (-1,True,2):
                with self.assertRaises(ValueError):request('hphi-study-point',id=identifier,index=index)
            import superfish_ng.hphi_study_jobs as module
            original=module.read_hphi_study
            def mutate(path):
                result=original(path);(path/'study.json').write_text((path/'study.json').read_text()+' ');return result
            with patch.object(module,'read_hphi_study',side_effect=mutate):
                with self.assertRaisesRegex(ValueError,'changed'):request('hphi-study-point',id=identifier,index=1)
