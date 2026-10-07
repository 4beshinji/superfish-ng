# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from pathlib import Path
from copy import deepcopy
import json
import shutil
import unittest
import numpy as np
from unittest.mock import patch
from superfish_ng.planar_curved_saved import save_planar_curved_run
from superfish_ng.planar_curved_identity_recovery import PlanarCurvedIdentityRecoveryRequest
from test_planar_curved_identity_recovery import solutions,compare
from test_planar_curved_tuning import workspace


def native_chain(root):
    paths=[]
    for index,solution in enumerate(solutions()):
        path=root/f'native-{index}';save_planar_curved_run(solution.case,solution,path);paths.append(path)
    return paths


class PlanarCurvedTrackingHistoryTests(unittest.TestCase):
    def test_real_circle_subspace_anchor_rank_recovery_and_following_inheritance(self):
        from superfish_ng.planar_curved_tracking_saved import execute_owned_planar_curved_tracking
        from superfish_ng.planar_curved_tracking_history import (PlanarCurvedTrackingHistoryRequest,
            execute_owned_planar_curved_history,extend_owned_planar_curved_history,read_owned_planar_curved_history)
        a,c,b,later=solutions()
        with workspace('history-recovery') as root:
            sources=native_chain(root)
            execute_owned_planar_curved_tracking(sources[0],sources[1],compare(a,c),root/'pair-0')
            execute_owned_planar_curved_tracking(sources[1],sources[2],compare(c,b,True),root/'pair-1')
            recovery=PlanarCurvedIdentityRecoveryRequest(0,compare(a,b))
            request=PlanarCurvedTrackingHistoryRequest(2,4,[dict(after_step_index=1,request=recovery.to_dict())])
            history=execute_owned_planar_curved_history([root/'pair-0',root/'pair-1'],request,root/'history')
            self.assertEqual(history['status'],'PASS')
            self.assertEqual(history['steps'][1]['current_mode_ids'],[None,None])
            self.assertEqual(history['current_mode_ids'],['even-x','odd-x'])
            self.assertEqual(history['identity_recoveries'][0]['recovered_frequencies_hz'],
                dict(zip(['even-x','odd-x'],b.frequencies_hz[:2])))
            next_request=replace(compare(b,later),previous_mode_ids=['even-x','odd-x'])
            execute_owned_planar_curved_tracking(sources[2],sources[3],next_request,root/'next')
            extended=extend_owned_planar_curved_history(root/'history',root/'next',root/'extended')
            self.assertEqual(extended['current_mode_ids'],['even-x','odd-x'])
            self.assertEqual(extended['steps'][:2],history['steps'])
            for path in sources:path.rename(path.with_name(path.name+'-unavailable'))
            for path in [root/'pair-0',root/'pair-1',root/'history',root/'next']:
                path.rename(path.with_name(path.name+'-unavailable'))
            (root/'extended').rename(root/'moved')
            self.assertEqual(read_owned_planar_curved_history(root/'moved'),extended)

    def test_recover_last_owned_subspace_then_extend_and_enforce_max_steps(self):
        from superfish_ng.planar_curved_tracking_saved import execute_owned_planar_curved_tracking
        from superfish_ng.planar_curved_tracking_history import (PlanarCurvedTrackingHistoryRequest,
            execute_owned_planar_curved_history,recover_owned_planar_curved_history,extend_owned_planar_curved_history)
        a,c,b,later=solutions()
        with workspace('history-recover-last') as root:
            paths=native_chain(root)
            for index,request in enumerate([compare(a,c),compare(c,b,True)]):
                execute_owned_planar_curved_tracking(paths[index],paths[index+1],request,root/f'pair-{index}')
            history=execute_owned_planar_curved_history([root/'pair-0',root/'pair-1'],
                PlanarCurvedTrackingHistoryRequest(2,3),root/'unresolved')
            self.assertFalse(history['individual_ids_complete']);self.assertEqual(history['current_mode_ids'],[None,None])
            before={str(p):p.read_bytes() for p in (root/'unresolved').rglob('*') if p.is_file()}
            recovered=recover_owned_planar_curved_history(root/'unresolved',
                PlanarCurvedIdentityRecoveryRequest(0,compare(a,b)),root/'recovered')
            self.assertEqual(recovered['current_mode_ids'],['even-x','odd-x'])
            for path,data in before.items():self.assertEqual(Path(path).read_bytes(),data)
            execute_owned_planar_curved_tracking(paths[2],paths[3],
                replace(compare(b,later),previous_mode_ids=['even-x','odd-x']),root/'next')
            final=extend_owned_planar_curved_history(root/'recovered',root/'next',root/'final')
            self.assertEqual(final['status'],'PASS');self.assertFalse(final['can_extend'])
            with self.assertRaisesRegex(ValueError,'max_steps'):
                extend_owned_planar_curved_history(root/'final',root/'next',root/'rejected')
            self.assertFalse((root/'rejected').exists())

    def test_wrong_anchor_ids_and_native_or_unresolved_id_discontinuity_rejected(self):
        from superfish_ng.planar_curved_tracking_saved import execute_owned_planar_curved_tracking
        from superfish_ng.planar_curved_tracking_history import PlanarCurvedTrackingHistoryRequest,execute_owned_planar_curved_history
        a,c,b,_=solutions()
        with workspace('history-invalid-chain') as root:
            paths=native_chain(root)
            execute_owned_planar_curved_tracking(paths[0],paths[1],compare(a,c),root/'first')
            execute_owned_planar_curved_tracking(paths[1],paths[2],compare(c,b),root/'replaced-ids')
            execute_owned_planar_curved_tracking(paths[0],paths[2],compare(a,b),root/'disconnected')
            for name,reason in [('replaced-ids','unresolved ID set'),('disconnected','native continuity')]:
                with self.assertRaisesRegex(ValueError,reason):
                    execute_owned_planar_curved_history([root/'first',root/name],PlanarCurvedTrackingHistoryRequest(2),root/(name+'-rejected'))
                self.assertFalse((root/(name+'-rejected')).exists())
            execute_owned_planar_curved_tracking(paths[1],paths[2],compare(c,b,True),root/'second')
            for index,comparison in [(1,replace(compare(c,b),previous_mode_ids=['odd-x','even-x'])),
                                      (0,replace(compare(a,b),previous_mode_ids=['outside','even-x']))]:
                request=PlanarCurvedTrackingHistoryRequest(2,3,[dict(after_step_index=1,
                    request=PlanarCurvedIdentityRecoveryRequest(index,comparison).to_dict())])
                destination=root/f'anchor-{index}'
                with self.assertRaisesRegex(ValueError,'actual earlier resolved IDs'):
                    execute_owned_planar_curved_history([root/'first',root/'second'],request,destination)
                self.assertFalse(destination.exists())

    def test_true_doublet_failed_recovery_and_guard_stop_block_extension(self):
        from superfish_ng.planar_curved_tracking_saved import execute_owned_planar_curved_tracking
        from superfish_ng.planar_curved_tracking import PlanarCurvedTrackingControls
        from superfish_ng.planar_curved_tracking_history import (PlanarCurvedTrackingHistoryRequest,
            execute_owned_planar_curved_history,extend_owned_planar_curved_history)
        a,c,_,_=solutions()
        with workspace('history-stops') as root:
            paths=native_chain(root)
            for name,request in [('doublet',compare(a,c)),('guard',replace(compare(a,c),
                    controls=replace(PlanarCurvedTrackingControls(),relative_cluster_gap=.9)))]:
                execute_owned_planar_curved_tracking(paths[0],paths[1],request,root/name)
            recovery=PlanarCurvedIdentityRecoveryRequest(0,compare(a,c))
            for name in ('doublet','guard'):
                events=[dict(after_step_index=0,request=recovery.to_dict())] if name=='doublet' else []
                history=execute_owned_planar_curved_history([root/name],PlanarCurvedTrackingHistoryRequest(1,3,
                    events),root/(name+'-history'))
                self.assertEqual(history['status'],'UNVERIFIED');self.assertFalse(history['can_extend'])
                if name=='doublet':self.assertIsNone(history['identity_recoveries'][0]['recovered_frequencies_hz'])
                else:self.assertEqual(history['identity_recoveries'],[])
                with self.assertRaisesRegex(ValueError,'UNVERIFIED'):
                    extend_owned_planar_curved_history(root/(name+'-history'),root/name,root/(name+'-rejected'))
                self.assertFalse((root/(name+'-rejected')).exists())

    def test_rehashed_history_result_is_rebuilt_and_strict_request_roundtrips(self):
        from superfish_ng.planar_curved_tracking_saved import execute_owned_planar_curved_tracking
        from superfish_ng.planar_curved_tracking_history import (PlanarCurvedTrackingHistoryRequest,
            execute_owned_planar_curved_history,read_owned_planar_curved_history)
        from superfish_ng.jobs import _digest
        a,_,b,_=solutions()
        request=PlanarCurvedTrackingHistoryRequest(1,2)
        for key,value in [('history_version',True),('step_count',True),('max_steps',0),('extra',0),('identity_recoveries',{})]:
            bad=request.to_dict();bad[key]=value
            with self.assertRaises(ValueError):PlanarCurvedTrackingHistoryRequest.from_dict(bad)
        self.assertEqual(PlanarCurvedTrackingHistoryRequest.from_dict(request.to_dict()).to_dict(),request.to_dict())
        with workspace('history-tamper') as root:
            sources=native_chain(root)
            execute_owned_planar_curved_tracking(sources[0],sources[2],compare(a,b),root/'pair')
            original=execute_owned_planar_curved_history([root/'pair'],request,root/'history')
            shutil.copytree(root/'history',root/'corrupted')
            path=root/'corrupted/history-results.json';bad=json.loads(path.read_text());bad['current_mode_ids'].reverse();path.write_text(json.dumps(bad))
            manifest=root/'corrupted/manifest.json';value=json.loads(manifest.read_text())
            value['files']['history-results.json']=_digest(path);manifest.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError,'complete original ancestry'):read_owned_planar_curved_history(root/'corrupted')
            self.assertEqual(read_owned_planar_curved_history(root/'history'),original)
            alias=root/'alias';alias.symlink_to(root/'history',target_is_directory=True)
            with self.assertRaises(ValueError):read_owned_planar_curved_history(alias)

    def test_independent_native_reflection_parity_survives_owned_history(self):
        from superfish_ng.planar_curved_tracking_saved import execute_owned_planar_curved_tracking,_read_verified
        from superfish_ng.planar_curved_tracking_history import PlanarCurvedTrackingHistoryRequest,execute_owned_planar_curved_history
        a,_,b,_=solutions()
        angle=np.pi/7;r=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
        reflection=r@np.diag([-1.,1.])@r.T
        with workspace('history-parity') as root:
            sources=native_chain(root)
            execute_owned_planar_curved_tracking(sources[0],sources[2],compare(a,b),root/'pair')
            result=execute_owned_planar_curved_history([root/'pair'],PlanarCurvedTrackingHistoryRequest(1),root/'history')
            _,operands=_read_verified(root/'history/step-0000')
            for solution,expected in zip(operands,[[-1.,1.],[1.,-1.]]):
                points=solution.case.domain.points_xy_m;reflected=points@reflection.T
                distances=np.linalg.norm(reflected[:,None]-points[None,:],axis=2);permutation=np.argmin(distances,axis=1)
                self.assertLess(float(max(distances[np.arange(len(points)),permutation])),1e-16)
                c=solution.coefficients[:,:2];parity=np.sum(c*c[permutation],axis=0)/np.sum(c*c,axis=0)
                np.testing.assert_allclose(parity,expected,rtol=0,atol=1e-10)
            self.assertEqual(result['current_mode_ids'],['even-x','odd-x'])

    def test_earlier_pair_mutated_during_later_step_copy_is_rejected(self):
        from superfish_ng.planar_curved_tracking_saved import execute_owned_planar_curved_tracking
        from superfish_ng.planar_curved_tracking_history import PlanarCurvedTrackingHistoryRequest,execute_owned_planar_curved_history
        a,_,b,later=solutions()
        with workspace('history-copy-mutation') as root:
            sources=native_chain(root)
            execute_owned_planar_curved_tracking(sources[0],sources[2],compare(a,b),root/'first')
            execute_owned_planar_curved_tracking(sources[2],sources[3],
                replace(compare(b,later),previous_mode_ids=['even-x','odd-x']),root/'second')
            copy=shutil.copyfile;changed=False
            def mutate(src,dst,*args,**kwargs):
                nonlocal changed
                result=copy(src,dst,*args,**kwargs)
                if not changed and Path(src).is_relative_to((root/'second').resolve()):
                    path=root/'first/tracking-results.json';path.write_bytes(path.read_bytes()+b' ');changed=True
                return result
            with patch('superfish_ng.planar_curved_tracking_history.shutil.copyfile',side_effect=mutate):
                with self.assertRaisesRegex(ValueError,'source changed'):
                    execute_owned_planar_curved_history([root/'first',root/'second'],PlanarCurvedTrackingHistoryRequest(2),root/'history')
            self.assertTrue(changed)
