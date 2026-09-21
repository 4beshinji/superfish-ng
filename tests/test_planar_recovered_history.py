# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from pathlib import Path
import json
import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from superfish_ng.planar_identity_recovery import PlanarIdentityRecoveryRequest
from superfish_ng.planar_tracking import PlanarTrackingRequest
from superfish_ng.planar_tracking_jobs import execute_planar_tracking
from superfish_ng.planar_tracking_history import PlanarTrackingHistoryRequest
from superfish_ng.planar_tracking_history_saved import (execute_planar_history, recover_planar_history,
    extend_planar_history, read_planar_history, history_snapshot)
from superfish_ng.jobs import JobManager
import test_planar_tracking_history as fixtures


class PlanarRecoveredHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.PlanarTrackingHistoryTests.setUpClass()
        cls.source = fixtures.PlanarTrackingHistoryTests.root
        cls.recovery = PlanarIdentityRecoveryRequest(0, PlanarTrackingRequest())
        execute_planar_tracking(cls.source/'right', cls.source/'right',
                               PlanarTrackingRequest(2,2,['mode-2','mode-1']), cls.source/'continue')

    @classmethod
    def tearDownClass(cls): fixtures.PlanarTrackingHistoryTests.tearDownClass()

    def initial(self, root, square_only=False):
        paths = [self.source/'merge'] + ([] if square_only else [self.source/'split'])
        return execute_planar_history(paths, PlanarTrackingHistoryRequest(len(paths)), root)

    def test_owned_recovery_move_extension_and_anchor_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self.initial(root/'initial'); before=history_snapshot(root/'initial')
            result=recover_planar_history(root/'initial',self.recovery,root/'recovered')
            self.assertEqual(result['history_version'],2)
            self.assertEqual(result['current_mode_ids'],['mode-2','mode-1'])
            self.assertEqual(result['steps'][-1]['current_mode_ids'],[None,None])
            self.assertEqual(len(result['identity_recoveries']),1)
            self.assertEqual(before,history_snapshot(root/'initial'))
            self.assertEqual(before['step-0000/previous/fields.npz'],
                             result['identity_recoveries'][0]['anchor_native_sha256']['fields.npz'])
            shutil.move(root/'recovered',root/'moved'); shutil.rmtree(root/'initial')
            self.assertEqual(read_planar_history(root/'moved'),result)
            extended=extend_planar_history(root/'moved',self.source/'continue',root/'extended')
            self.assertEqual(extended['current_mode_ids'],['mode-2','mode-1'])
            self.assertEqual(len(extended['identity_recoveries']),1)
            self.assertTrue(extended['individual_ids_complete'])
            self.assertEqual(read_planar_history(root/'extended'),extended)

    def test_true_degeneracy_and_unresolved_anchor_are_not_adopted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self.initial(root/'square',True)
            failed=recover_planar_history(root/'square',self.recovery,root/'failed')
            self.assertEqual(failed['status'],'UNVERIFIED');self.assertFalse(failed['can_extend'])
            self.assertIsNone(failed['identity_recoveries'][0]['recovered_frequencies_hz'])
            with self.assertRaisesRegex(ValueError,'UNVERIFIED'):
                extend_planar_history(root/'failed',self.source/'split',root/'bad-extension')
            self.assertFalse((root/'bad-extension').exists())
            self.initial(root/'initial')
            for recovery in (replace(self.recovery,anchor_snapshot_index=1),
                             replace(self.recovery,comparison=PlanarTrackingRequest(2,2,['wrong','mode-2']))):
                with self.assertRaisesRegex(ValueError,'earlier resolved IDs'):
                    recover_planar_history(root/'initial',recovery,root/'bad-anchor')
                self.assertFalse((root/'bad-anchor').exists())

    def test_rehashed_recovery_event_and_invalid_placement_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.initial(root/'initial')
            recover_planar_history(root/'initial',self.recovery,root/'recovered')
            path=root/'recovered/history-results.json';data=json.loads(path.read_text())
            data['identity_recoveries'][0]['assessment']['current_mode_ids'].reverse()
            path.write_text(json.dumps(data))
            manifest=root/'recovered/manifest.json';metadata=json.loads(manifest.read_text())
            metadata['files']['history-results.json']=hashlib.sha256(path.read_bytes()).hexdigest()
            manifest.write_text(json.dumps(metadata))
            with self.assertRaisesRegex(ValueError,'ancestry replay'):read_planar_history(root/'recovered')
        for events in ([dict(after_step_index=1,request=self.recovery.to_dict())]*2,
                       [dict(after_step_index=2,request=self.recovery.to_dict())],
                       [dict(after_step_index=0,request=replace(self.recovery,anchor_snapshot_index=1).to_dict())]):
            with self.assertRaises(ValueError):PlanarTrackingHistoryRequest(2,100,events)

    def test_cli_recovery_worker_extension_and_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.initial(root/'initial')
            request=root/'recovery.json';request.write_text(json.dumps(self.recovery.to_dict()))
            run=subprocess.run([sys.executable,'-m','superfish_ng','recover-planar-history',
                str(root/'initial'),str(request),'--out',str(root/'cli')],capture_output=True,text=True,timeout=240)
            self.assertEqual(run.returncode,0,run.stderr)
            result=json.loads(run.stdout);self.assertEqual(result['current_mode_ids'],['mode-2','mode-1'])
            manager=JobManager(root/'workspace')
            try:
                identifier=manager.recover_planar_history(root/'initial',self.recovery)
                self.assertEqual(manager.processes[identifier].wait(timeout=240),0)
                recovered=read_planar_history(manager.directory(identifier))
                self.assertEqual(recovered['current_mode_ids'],result['current_mode_ids'])
                extended=manager.extend_planar_history(manager.directory(identifier),self.source/'continue')
                self.assertEqual(manager.processes[extended].wait(timeout=240),0)
                before=history_snapshot(manager.directory(identifier))
                manager.close();manager=JobManager(root/'workspace')
                self.assertEqual(manager.status(extended,verify=True)['status'],'complete')
                self.assertEqual(before,history_snapshot(manager.directory(identifier)))
            finally: manager.close()


class PlanarAffineSavedMappingTests(unittest.TestCase):
    def test_polynomial_affine_pair_entry_and_portable_replay(self):
        from superfish_ng.planar import PlanarCase,solve_planar
        from superfish_ng.planar_project import PlanarProject
        from superfish_ng.planar_affine_shape import PlanarAffineShapeLaw,explicit_planar_project
        from superfish_ng.planar_affine_shape_mapping import PlanarAffineShapeMapping
        from superfish_ng.planar_saved import save_planar_run
        from superfish_ng.planar_tracking_jobs import read_planar_tracking
        original=explicit_planar_project(PlanarProject(PlanarCase(.18,.2,nx=3,ny=3,modes=3)))
        law=PlanarAffineShapeLaw([[[1,.25],[0]],[[0],[1,.25]]],[[0],[0]],[0,1])
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,value in [('a',0.),('b',1.)]:
                case=law.project(original,value).case
                save_planar_run(case,solve_planar(case),root/name)
            request=PlanarTrackingRequest(mapping=PlanarAffineShapeMapping(original,law,0.,1.))
            result=execute_planar_tracking(root/'a',root/'b',request,root/'pair')
            self.assertEqual(result['result_version'],8)
            shutil.move(root/'pair',root/'moved');shutil.rmtree(root/'a');shutil.rmtree(root/'b')
            self.assertEqual(read_planar_tracking(root/'moved'),result)


if __name__=='__main__':unittest.main()
