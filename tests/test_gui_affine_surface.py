# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from superfish_ng.adaptive_refinement import execute_adaptive_refinement
from superfish_ng.gui_surface_convergence import surface_convergence_response


class GuiAffineSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup);cls.root=Path(cls.tmp.name)
        request=json.loads(Path('examples/adaptive_refinement/pillbox_confirmed.json').read_text())
        cls.checkpoint=execute_adaptive_refinement(request,cls.root/'execution')
    def action(self,action,**data):return surface_convergence_response(action,data)

    def test_evaluate_tracked_second_mode_and_exact_serialized_replay(self):
        response=self.action('assess-affine-surface-convergence',document=json.dumps(self.checkpoint),mode_id='second')
        d=response['document'];self.assertEqual(d['status'],'TARGETS_MET')
        self.assertEqual(d['checkpoint'],self.checkpoint);self.assertEqual(d['checkpoint']['surface_status'],'UNASSESSED')
        self.assertTrue(all(row['mode_index']==1 for row in d['rows']))
        self.assertEqual(json.loads(response['serialized']),d)
        self.assertEqual(self.action('replay-affine-surface-convergence',document=response['serialized']),response)

    def test_pending_short_and_strict_transport(self):
        pending=json.loads((self.root/'execution/checkpoint-004.json').read_text())
        response=self.action('assess-affine-surface-convergence',document=pending,mode_id='second')
        self.assertEqual(response['document']['status'],'CONFIRMATION_PENDING')
        short=json.loads((self.root/'execution/checkpoint-001.json').read_text())
        for action,data in [('assess-affine-surface-convergence',dict(document=short,mode_id='second')),
                ('assess-affine-surface-convergence',dict(document=pending,mode_id='missing')),
                ('assess-affine-surface-convergence',dict(document=pending,mode_id='second',unknown=True)),
                ('replay-affine-surface-convergence',dict(document={})),('unknown',dict(document=pending))]:
            with self.assertRaises(ValueError):self.action(action,**data)
        duplicate=response['serialized'].replace('"document_type": "affine_surface_convergence_assessment"','"document_type":"wrong", "document_type":"affine_surface_convergence_assessment"',1)
        with self.assertRaisesRegex(ValueError,'duplicate JSON key'):self.action('replay-affine-surface-convergence',document=duplicate)

    def test_changed_assessment_and_native_source_are_rejected(self):
        result=self.action('assess-affine-surface-convergence',document=self.checkpoint,mode_id='fundamental')
        changed=deepcopy(result['document']);changed['geometry_diagnostic']['status']='accepted'
        with self.assertRaisesRegex(ValueError,'replay'):self.action('replay-affine-surface-convergence',document=changed)
        source=Path(self.checkpoint['level_runs'][0])/'case.json';original=source.read_bytes()
        try:
            source.write_bytes(original+b'\n')
            with self.assertRaises(ValueError):self.action('replay-affine-surface-convergence',document=result['serialized'])
        finally:source.write_bytes(original)
