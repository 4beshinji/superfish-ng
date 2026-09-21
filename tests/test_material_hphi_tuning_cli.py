# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from pathlib import Path
import json,tempfile,unittest
from unittest.mock import patch
from superfish_ng.cli import main
from superfish_ng.material_hphi_tuning_saved import read_material_hphi_tune
from superfish_ng.material_hphi_saved import read_material_hphi_run,material_hphi_result
from test_material_hphi_tuning_saved import request


class MaterialHphiTuneCliTests(unittest.TestCase):
    def test_unverified_identity_returns_failure_and_cannot_resume(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);data=request();data['controls']['relative_cluster_gap']=.9
            source=root/'request.json';source.write_text(json.dumps(data))
            self.assertEqual(main(['tune-material-hphi',str(source),'--out',str(root/'guard')]),1)
            checkpoint=root/'guard/checkpoint-001.json'
            result=read_material_hphi_tune(checkpoint)
            self.assertEqual(result['status'],'UNVERIFIED')
            self.assertIsNone(result['trials'][0]['frequency_hz'])
            self.assertEqual(main(['replay-tune-material-hphi',str(checkpoint)]),1)
            self.assertEqual(main(['resume-tune-material-hphi',str(checkpoint),'--out',str(root/'rejected')]),2)
            self.assertFalse((root/'rejected').exists())

    def test_invalid_request_rejected_without_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);data=deepcopy(request());data['parameter']='stored_energy_j'
            source=root/'request.json';source.write_text(json.dumps(data))
            self.assertEqual(main(['tune-material-hphi',str(source),'--out',str(root/'invalid')]),2)
            self.assertFalse((root/'invalid').exists())

    def test_real_cli_solve_resume_and_portable_replay(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source=root/'request.json';source.write_text(json.dumps(request()))
            self.assertEqual(main(['tune-material-hphi',str(source),'--out',str(root/'first'),'--max-new-trials','1']),0)
            self.assertEqual(main(['resume-tune-material-hphi',str(root/'first/checkpoint-001.json'),
                '--out',str(root/'second'),'--max-new-trials','1']),0)
            first=read_material_hphi_run(root/'first/trial-001/solution')
            copied=read_material_hphi_run(root/'second/trial-001/solution')
            self.assertEqual(material_hphi_result(first),material_hphi_result(copied))
            second=read_material_hphi_run(root/'second/trial-002/solution')
            # Uniform fixed-material scaling gives an independent Maxwell invariant.
            for a,b in zip(first.frequencies_hz,second.frequencies_hz):
                self.assertAlmostEqual(float(b/a),1/1.2,places=8)
            (root/'first').rename(root/'old-moved');(root/'second').rename(root/'owned-moved')
            checkpoint=root/'owned-moved/checkpoint-002.json'
            with patch('superfish_ng.material_hphi_tuning_saved.solve_material_hphi',side_effect=AssertionError('replay solved')):
                self.assertEqual(main(['replay-tune-material-hphi',str(checkpoint)]),0)
            self.assertEqual(read_material_hphi_tune(checkpoint)['status'],'PAUSED')
            # Separate format contracts must not let the old CLI accept material tuning.
            self.assertEqual(main(['replay-tune-hphi',str(checkpoint)]),2)
