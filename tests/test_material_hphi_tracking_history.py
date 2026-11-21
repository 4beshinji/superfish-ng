# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from pathlib import Path
from copy import deepcopy
import json,tempfile,unittest
import numpy as np
from test_material_hphi_tracking_crossing import material,tracking
from superfish_ng.hphi_geometry_mapping import HphiGeometryMapping
from superfish_ng.material_hphi import MaterialHphiCase,solve_material_hphi
from superfish_ng.hphi_native import save_hphi_run
from superfish_ng.material_hphi_tracking_jobs import execute_material_hphi_tracking
from superfish_ng.material_hphi_identity_recovery import MaterialHphiIdentityRecoveryRequest
from superfish_ng.material_hphi_tracking_history import MaterialHphiTrackingHistoryRequest,verify_material_hphi_history_steps
from superfish_ng.material_hphi_tracking_history_saved import execute_material_hphi_history,read_material_hphi_history
from superfish_ng.jobs import JobManager


class MaterialHphiHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)
        a,b=[solve_material_hphi(MaterialHphiCase(material(length),modes=3)) for length in (.05859375,.0703125)]
        for name,s in (('a',a),('b',b)):save_hphi_run(s.case,s,cls.root/name)
        mapping=HphiGeometryMapping(a.case.partition.mesh,b.case.partition.mesh)
        cls.comparison=replace(tracking(a,b,mapping),previous_mode_ids=['radial','TEM'])
        grouped=replace(cls.comparison,controls=replace(cls.comparison.controls,relative_cluster_gap=.15))
        reverse=replace(tracking(b,a,mapping.inverse()),previous_mode_ids=['TEM','radial'])
        cls.first=execute_material_hphi_tracking(cls.root/'a',cls.root/'b',grouped,cls.root/'enter')
        execute_material_hphi_tracking(cls.root/'b',cls.root/'a',reverse,cls.root/'continue')
        cls.placement=dict(after_step_index=0,request=MaterialHphiIdentityRecoveryRequest(0,cls.comparison).to_dict())
        # Independent TEM field shape in uniform epsilon_r=4, mu_r=9 material.
        for solution,rank in ((a,1),(b,0)):
            r,z=solution.space.dof_points.T
            length=.05859375 if rank==1 else .0703125
            exact=np.cos(np.pi*z/length);actual=solution.coefficients[:,rank];mass=solution.mass
            overlap=abs(actual@(mass@exact))/np.sqrt((actual@(mass@actual))*(exact@(mass@exact)))
            if overlap<=.999:raise AssertionError('TEM-like physical branch is not independently resolved')

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def history_request(self,n=1):return MaterialHphiTrackingHistoryRequest(n,3,[self.placement])

    def test_owned_recovery_extension_and_source_move(self):
        self.assertEqual(self.first['status'],'PASS');self.assertFalse(self.first['individual_ids_complete'])
        paths=[self.root/'enter',self.root/'continue']
        with self.assertRaisesRegex(ValueError,'individual IDs'):
            verify_material_hphi_history_steps(paths,MaterialHphiTrackingHistoryRequest(2))
        history=self.root/'history';result=execute_material_hphi_history(paths[:1],self.history_request(),history)
        self.assertEqual(result['current_mode_ids'],['TEM','radial'])
        self.assertTrue(result['can_extend'])
        event=result['identity_recoveries'][0]
        self.assertEqual(event['status'],'PASS')
        self.assertEqual(event['anchor_native_sha256'],{k.removeprefix('previous/solution/'):v for k,v in result['step_sha256'][0].items() if k.startswith('previous/solution/')})
        (self.root/'enter').rename(self.root/'enter-moved')
        try:
            self.assertEqual(read_material_hphi_history(history),result)
            manager=JobManager(self.root/'workers')
            try:
                identifier=manager.extend_material_hphi_history(history,self.root/'continue')
                self.assertEqual(manager.processes[identifier].wait(timeout=600),0)
                directory=manager.directory(identifier)
                final=read_material_hphi_history(directory)
                self.assertEqual(final['current_mode_ids'],['radial','TEM'])
                self.assertEqual(final['identity_recoveries'],result['identity_recoveries'])
                for path in (history/'step-0000').rglob('*'):
                    if path.is_file():self.assertEqual(path.read_bytes(),(directory/'step-0000'/path.relative_to(history/'step-0000')).read_bytes())
            finally:manager.close()
            manager=JobManager(self.root/'workers')
            try:self.assertEqual(manager.status(identifier,verify=True)['status'],'complete')
            finally:manager.close()
            path=history/'history-results.json';raw=path.read_bytes();bad=json.loads(raw)
            bad['identity_recoveries'][0]['assessment']['current_mode_ids'].reverse();path.write_text(json.dumps(bad))
            try:
                with self.assertRaises(ValueError):read_material_hphi_history(history)
            finally:path.write_bytes(raw)
        finally:(self.root/'enter-moved').rename(self.root/'enter')

    def test_strict_anchor_and_guard_refusal(self):
        raw=self.history_request().to_dict()
        self.assertEqual(MaterialHphiTrackingHistoryRequest.from_dict(raw).to_dict(),raw)
        for change in ({'history_version':True},{'recoveries':None},{'recoveries':[]},{'recoveries':[self.placement,self.placement]}):
            with self.assertRaises(ValueError):MaterialHphiTrackingHistoryRequest.from_dict({**raw,**change})
        future=deepcopy(self.placement);future['request']['anchor_snapshot_index']=1
        with self.assertRaises(ValueError):MaterialHphiTrackingHistoryRequest(1,3,[future])
        wrong=deepcopy(self.placement);wrong['request']['comparison']['previous_mode_ids']=['TEM','radial']
        with self.assertRaisesRegex(ValueError,'anchor IDs differ'):
            verify_material_hphi_history_steps([self.root/'enter'],MaterialHphiTrackingHistoryRequest(1,3,[wrong]))
        bad=deepcopy(self.placement);bad['request']['comparison']['controls']['relative_cluster_gap']=.9
        result=verify_material_hphi_history_steps([self.root/'enter'],MaterialHphiTrackingHistoryRequest(1,3,[bad]))
        self.assertEqual(result['status'],'UNVERIFIED');self.assertFalse(result['can_extend'])
        with self.assertRaisesRegex(ValueError,'UNVERIFIED'):
            verify_material_hphi_history_steps([self.root/'enter',self.root/'continue'],MaterialHphiTrackingHistoryRequest(2,3,[bad]))

    def test_native_continuity_and_unrecovered_group_budget(self):
        limited=verify_material_hphi_history_steps([self.root/'enter'],MaterialHphiTrackingHistoryRequest(1,1))
        self.assertEqual(limited['status'],'PASS');self.assertFalse(limited['can_extend'])
        self.assertFalse(limited['individual_ids_complete'])
        self.assertEqual(limited['current_mode_ids'],[None,None])
        self.assertEqual(limited['current_identity_groups'],[dict(indices=[1,2],ids=['TEM','radial'])])
        with self.assertRaisesRegex(ValueError,'native spectrum'):
            verify_material_hphi_history_steps([self.root/'enter',self.root/'enter'],MaterialHphiTrackingHistoryRequest(2))


class MaterialHphiHistoryCliTests(unittest.TestCase):
    def test_execute_replay_and_budget_refusal(self):
        import contextlib,io
        from superfish_ng.cli import main
        from test_material_hphi_tracking_jobs import sources
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            previous,current,comparison=sources(root)
            pair=root/'pair'
            execute_material_hphi_tracking(previous,current,comparison,pair)
            request=root/'history-request.json'
            MaterialHphiTrackingHistoryRequest(1,1).save(request)
            output=root/'history'
            stream=io.StringIO()
            with contextlib.redirect_stdout(stream):
                code=main(['execute-material-hphi-history',str(request),'--steps',str(pair),'--out',str(output)])
            self.assertEqual(code,0)
            result=json.loads(stream.getvalue())
            self.assertEqual(result['status'],'PASS');self.assertFalse(result['can_extend'])
            stream=io.StringIO()
            with contextlib.redirect_stdout(stream):
                code=main(['replay-material-hphi-history',str(output)])
            self.assertEqual(code,0);self.assertEqual(json.loads(stream.getvalue()),result)
            with contextlib.redirect_stderr(io.StringIO()):
                code=main(['extend-material-hphi-history',str(output),str(pair),'--out',str(root/'forbidden')])
            self.assertNotEqual(code,0);self.assertFalse((root/'forbidden').exists())
