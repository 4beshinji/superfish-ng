# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path
import unittest
from unittest.mock import Mock,patch
from superfish_ng.gui_rf_optimization import rf_optimization_response


class GUIRFOptimizationTests(unittest.TestCase):
    def test_prepare_strict_json_and_start_keep_complete_request(self):
        request=json.loads(Path('examples/optimization/curved_rf.json').read_text());manager=Mock()
        result=rf_optimization_response(manager,'prepare-rf-optimization',dict(request=json.dumps(request)))
        self.assertEqual(result['request'],request);self.assertEqual(json.loads(result['serialized']),request)
        manager.start_rf_optimization.return_value='job'
        self.assertEqual(rf_optimization_response(manager,'start-rf-optimization',dict(request=result['serialized'],max_new_trials=1)),dict(id='job'))
        manager.start_rf_optimization.assert_called_once_with(request,max_new_trials=1)
        for data in (dict(request='{"schema_version":1,"schema_version":1}'),dict(request=request,extra=True)):
            with self.assertRaises(ValueError):rf_optimization_response(manager,'prepare-rf-optimization',data)

    def test_selected_field_uses_verified_rank_and_has_no_rank_fallback(self):
        manager=Mock();manager.import_result.return_value='imported'
        result=dict(request=dict(mode_id='A'),trials=[dict(assessment=dict(assessment=dict(rows=[dict(mode_index=3),dict(mode_index=2),dict(mode_index=4)])))],trial_directories=['/native/trial-001'])
        with patch('superfish_ng.gui_rf_optimization.replay_rf_optimization',return_value=result):
            output=rf_optimization_response(manager,'rf-optimization-field',dict(document={},trial=0,level=2))
            self.assertEqual(output,dict(id='imported',mode=4,mode_id='A',trial=0,level=2))
            manager.import_result.assert_called_once_with(Path('/native/trial-001/level-2'))
            for trial,level in ((1,0),(0,3),(True,0),(0,-1)):
                with self.assertRaises(ValueError):rf_optimization_response(manager,'rf-optimization-field',dict(document={},trial=trial,level=level))
            result['trials'][0]['assessment']=None
            with self.assertRaisesRegex(ValueError,'individual'):rf_optimization_response(manager,'rf-optimization-field',dict(document={},trial=0,level=0))
            self.assertEqual(manager.import_result.call_count,1)
