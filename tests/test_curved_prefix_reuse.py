# SPDX-License-Identifier: Apache-2.0
"""Execution reuse must preserve independent replay and reject changed ancestors."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from superfish_ng import solve
from superfish_ng import curved_adaptive_refinement as engine
from superfish_ng.adaptive_refinement import execute_adaptive_refinement, replay_adaptive_refinement
from superfish_ng.saved import read_solution
from test_curved_adaptive_refinement import request


class CurvedPrefixReuseTests(unittest.TestCase):
    def test_each_new_level_is_assessed_once_and_full_replay_agrees(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            with patch.object(engine,'read_solution',wraps=read_solution) as reads:
                result=execute_adaptive_refinement(request(),root/'run',max_new_levels=3)
            self.assertEqual(reads.call_count,3,'old native levels must not be reassessed at every append')
            self.assertEqual(result['status'],'PAUSED')
            with patch.object(engine,'read_solution',wraps=read_solution) as reads:
                replay=replay_adaptive_refinement(result)
            self.assertEqual(reads.call_count,3,'independent replay must still validate all saved levels')
            self.assertEqual(result,replay)
            with patch.object(engine,'read_solution',wraps=read_solution) as reads:
                resumed=execute_adaptive_refinement(request(),root/'resumed',checkpoint=result,max_new_levels=1)
            self.assertEqual(reads.call_count,4,'resume must validate each old level once and the new level once')
            self.assertEqual(resumed['sources'][:3],result['sources'])
            # An exported document is not trusted memory for subsequent executions.
            bad=deepcopy(result);bad['levels'][0]['quadrature_check']['passed']=False
            with self.assertRaises(ValueError):
                execute_adaptive_refinement(request(),root/'bad',checkpoint=bad,max_new_levels=1)
            self.assertFalse((root/'bad').exists())

    def test_changed_ancestor_after_new_solve_is_rejected_and_checkpoint_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'run';calls=0;checkpoint=None
            def change_ancestor(*args,**kwargs):
                nonlocal calls,checkpoint
                calls+=1
                result=solve(*args,**kwargs)
                if calls==2:
                    checkpoint=(root/'checkpoint-001.json').read_bytes()
                    path=root/'level-001/case.json'
                    # Semantically identical JSON still has different provenance bytes.
                    path.write_bytes(path.read_bytes()+b' ')
                return result
            with patch.object(engine,'solve',side_effect=change_ancestor):
                with self.assertRaises(ValueError):
                    execute_adaptive_refinement(request(),root,max_new_levels=2)
            self.assertEqual((root/'checkpoint-001.json').read_bytes(),checkpoint)
            self.assertFalse((root/'checkpoint-002.json').exists())
            failure=json.loads((root/'failure-002.json').read_text())
            self.assertEqual(failure['status'],'FAILED')
            self.assertEqual(failure['preceding_level_runs'],[str(root/'level-001')])

    def test_reuse_rejects_source_change_during_new_level_assessment(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'run';original=engine._surface;calls=0
            def change_ancestor(*args,**kwargs):
                nonlocal calls
                result=original(*args,**kwargs);calls+=1
                if calls==2:
                    path=root/'level-001/results.json';path.write_bytes(path.read_bytes()+b' ')
                return result
            with patch.object(engine,'_surface',side_effect=change_ancestor):
                with self.assertRaises(ValueError):
                    execute_adaptive_refinement(request(),root,max_new_levels=2)
            self.assertTrue((root/'checkpoint-001.json').exists())
            self.assertFalse((root/'checkpoint-002.json').exists())


if __name__=='__main__':unittest.main()
