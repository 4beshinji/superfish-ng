# SPDX-License-Identifier: Apache-2.0
"""Bound local HTTP input while admitting complete owned scientific checkpoints."""
import io,json,unittest
from superfish_ng.gui import read_api_request


class GuiRequestSizeTests(unittest.TestCase):
    def test_large_owned_checkpoint_envelopes_reach_strict_action_validation(self):
        for action in ('hphi-replay-tune','hphi-resume-tune','hphi-tune-trial'):
            document=json.dumps({'format':'superfish_ng_curved_hphi_tune_checkpoint','trials':['x'*(5*1024*1024)]})
            request={'action':action,'document':document}
            raw=json.dumps(request).encode()
            self.assertGreater(len(raw),4*1024*1024)
            self.assertEqual(read_api_request(io.BytesIO(raw),str(len(raw))),request)

    def test_unrelated_actions_keep_small_limit_and_oversize_is_not_read(self):
        raw=json.dumps({'action':'jobs','padding':'x'*(5*1024*1024)}).encode()
        with self.assertRaisesRegex(ValueError,'4 MiB'):
            read_api_request(io.BytesIO(raw),str(len(raw)))
        for size in ('0','-1','67108865','invalid'):
            stream=io.BytesIO(b'{}')
            with self.assertRaises(ValueError):read_api_request(stream,size)
            self.assertEqual(stream.tell(),0)
        with self.assertRaisesRegex(ValueError,'shorter'):
            read_api_request(io.BytesIO(b'{}'),'3')
        for raw in (b'[]',b'{',b'{"action":"jobs","action":"jobs"}'):
            with self.assertRaises(ValueError):read_api_request(io.BytesIO(raw),str(len(raw)))
        self.assertEqual(read_api_request(io.BytesIO(b'{"action":"jobs"}'),'17'),{'action':'jobs'})


if __name__=='__main__':unittest.main()
