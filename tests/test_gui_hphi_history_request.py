# SPDX-License-Identifier: Apache-2.0
"""Browser form transport must retain explicit identity recovery declarations."""
from pathlib import Path
import shutil
import subprocess
import unittest


class HphiHistoryRequestFormTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node is required for the browser form transport check')
    def test_loaded_recovery_request_roundtrips_and_old_version_clears_events(self):
        source=(Path(__file__).parents[1]/'src/superfish_ng/web/hphi.js').read_text()
        functions=source[source.index('function historyFromForm()'):source.index('async function openHphiHistory')]
        # Exercise the actual form functions with the minimal DOM interface.
        # The recovery request body is opaque to this form; the API validates it.
        program='''
const assert=require('node:assert/strict');
let hphiHistoryRequest=null;
const fields={};const $=id=>fields[id]??=( {value:'',textContent:''} );
const numeric=id=>Number($(id).value);
'''+functions+'''
const recovery={format:'superfish_ng_hphi_tracking_history_request',history_version:2,
 step_count:2,max_steps:5,recoveries:[{after_step_index:1,request:{anchor_snapshot_index:0}}]};
loadHistoryRequest(recovery);assert.deepEqual(historyFromForm(),recovery);
$('history-count').value=3;assert.deepEqual(historyFromForm().recoveries,recovery.recoveries);
const old={format:recovery.format,history_version:1,step_count:1,max_steps:4};
loadHistoryRequest(old);assert.deepEqual(historyFromForm(),old);
'''
        run=subprocess.run(['node','-e',program],capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr)
