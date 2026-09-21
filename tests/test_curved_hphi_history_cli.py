# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from contextlib import redirect_stdout,redirect_stderr
import io,json,tempfile,unittest
from pathlib import Path
from superfish_ng.cli import main
from superfish_ng.curved_hphi import solve_curved_hphi
from superfish_ng.hphi_native import save_hphi_run
from superfish_ng.curved_hphi_tracking_history import CurvedHphiTrackingHistoryRequest
from test_curved_hphi_tracking_crossing import coax
from test_curved_hphi_tracking import request


class CurvedHphiHistoryCliTests(unittest.TestCase):
    def call(self,args,code=0):
        with redirect_stdout(io.StringIO()) as output,redirect_stderr(io.StringIO()):
            self.assertEqual(main(args),code)
        return json.loads(output.getvalue()) if code==0 else None

    def test_invalid_request_has_no_output(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);path=root/'bad.json';path.write_text('{}')
            self.call(['execute-curved-hphi-history',str(path),'--steps',str(root/'absent'),'--out',str(root/'rejected')],2)
            self.assertFalse((root/'rejected').exists())

    def test_real_pair_history_extension_and_owned_replay(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);solution=solve_curved_hphi(coax(.125,shear=1/64,n=2))
            save_hphi_run(solution.case,solution,root/'native')
            q=replace(request(solution,solution),previous_mode_count=1,current_mode_count=1,previous_mode_ids=['TEM'])
            q.save(root/'pair.json')
            pair=self.call(['execute-curved-hphi-tracking',str(root/'native'),str(root/'native'),str(root/'pair.json'),'--out',str(root/'pair')])
            self.assertEqual(pair['status'],'PASS')
            self.assertEqual(self.call(['replay-curved-hphi-tracking',str(root/'pair')]),pair)
            CurvedHphiTrackingHistoryRequest(1,2).save(root/'history.json')
            history=self.call(['execute-curved-hphi-history',str(root/'history.json'),'--steps',str(root/'pair'),'--out',str(root/'history')])
            self.assertTrue(history['can_extend'])
            final=self.call(['extend-curved-hphi-history',str(root/'history'),str(root/'pair'),'--out',str(root/'extended')])
            self.assertFalse(final['can_extend']);self.assertEqual(final['current_mode_ids'],['TEM'])
            for name in ('native','pair','history'):(root/name).rename(root/(name+'-moved'))
            self.assertEqual(self.call(['replay-curved-hphi-history',str(root/'extended')]),final)
            self.call(['extend-curved-hphi-history',str(root/'extended'),str(root/'pair-moved'),'--out',str(root/'past-limit')],2)
            self.assertFalse((root/'past-limit').exists())
            self.call(['replay-hphi-history',str(root/'extended')],2)
