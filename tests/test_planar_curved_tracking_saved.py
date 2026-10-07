# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch
from superfish_ng.planar_curved_saved import save_planar_curved_run
from superfish_ng.planar_curved_tracking import PlanarCurvedTrackingRequest
from superfish_ng.planar_curved_comparison import PlanarCurvedComparisonDomain
from superfish_ng.planar_curved_tracking import PlanarCurvedTrackingControls
from test_planar_curved_identity_recovery import solutions,compare
from test_planar_curved_tuning import workspace


class PlanarCurvedTrackingSavedTests(unittest.TestCase):
    def test_original_te_rank_and_all_native_bytes_survive_pair_move(self):
        from superfish_ng.planar_curved_tracking_saved import execute_owned_planar_curved_tracking,read_owned_planar_curved_tracking
        a,_,b,_=solutions()
        with workspace('pair-native') as root:
            for name,solution in [('a',a),('b',b)]:save_planar_curved_run(solution.case,solution,root/name)
            request=compare(a,b)
            original={side:{p.name:p.read_bytes() for p in (root/source).iterdir()}
                for side,source in [('previous','a'),('current','b')]}
            result=execute_owned_planar_curved_tracking(root/'a',root/'b',request,root/'pair')
            self.assertEqual(result['current_mode_ids'],['even-x','odd-x'])
            for side,files in original.items():
                for name,data in files.items():self.assertEqual((root/'pair'/side/name).read_bytes(),data)
            (root/'a').rename(root/'a-unavailable');(root/'b').rename(root/'b-unavailable')
            (root/'pair').rename(root/'moved')
            self.assertEqual(read_owned_planar_curved_tracking(root/'moved'),result)

    def test_completed_jobs_keep_original_project_claim_and_creator_metadata(self):
        from superfish_ng.planar_curved_tracking_saved import execute_owned_planar_curved_tracking,read_owned_planar_curved_tracking
        from superfish_ng.planar_project import PlanarProject
        from superfish_ng.planar_jobs import execute_planar_project
        a,_,b,_=solutions()
        with workspace('pair-jobs') as root:
            for name,solution,unit in [('a',a,'m'),('b',b,'mm')]:
                execute_planar_project(PlanarProject(solution.case,unit),root/name)
                (root/name/'log.txt').write_text('ancillary source log is not a physical operand')
            before={side:{p.relative_to(root/source).as_posix():p.read_bytes() for p in (root/source).rglob('*')
                if p.is_file() and p.name!='log.txt'} for side,source in [('previous','a'),('current','b')]}
            result=execute_owned_planar_curved_tracking(root/'a',root/'b',compare(a,b),root/'pair')
            for side,files in before.items():
                for name,data in files.items():self.assertEqual((root/'pair'/side/name).read_bytes(),data)
                self.assertFalse((root/'pair'/side/'log.txt').exists())
            for name in ('a','b'):(root/name).rename(root/(name+'-unavailable'))
            self.assertEqual(read_owned_planar_curved_tracking(root/'pair'),result)

    def test_guard_and_budget_stop_and_rehashed_pair_report_are_separate(self):
        from superfish_ng.planar_curved_tracking_saved import execute_owned_planar_curved_tracking,read_owned_planar_curved_tracking
        from superfish_ng.jobs import _digest
        a,c,_,_=solutions()
        with workspace('pair-stops') as root:
            for name,solution in [('a',a),('c',c)]:save_planar_curved_run(solution.case,solution,root/name)
            guarded=replace(compare(a,c),controls=replace(PlanarCurvedTrackingControls(),relative_cluster_gap=.9))
            report=execute_owned_planar_curved_tracking(root/'a',root/'c',guarded,root/'guard')
            self.assertEqual(report['status'],'UNVERIFIED')
            self.assertEqual(report['current_mode_ids'],[None,None])
            self.assertEqual(read_owned_planar_curved_tracking(root/'guard'),report)
            budget=replace(compare(a,c),controls=replace(PlanarCurvedTrackingControls(),max_field_sample_points=1))
            with self.assertRaises(ValueError):execute_owned_planar_curved_tracking(root/'a',root/'c',budget,root/'budget')
            self.assertFalse((root/'budget').exists())
            shutil.copytree(root/'guard',root/'corrupted')
            path=root/'corrupted/tracking-results.json';original=path.read_bytes()
            altered=json.loads(original);altered['status']='PASS';path.write_text(json.dumps(altered))
            manifest=root/'corrupted/manifest.json';data=json.loads(manifest.read_text())
            data['files']['tracking-results.json']=_digest(path);manifest.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'complete original E/H'):read_owned_planar_curved_tracking(root/'corrupted')

    def test_imported_jobs_preserve_native_bytes_without_inventing_worker_claim(self):
        from superfish_ng.planar_curved_tracking_saved import execute_owned_planar_curved_tracking,read_owned_planar_curved_tracking
        from superfish_ng.jobs import JobManager
        a,_,b,_=solutions()
        with workspace('pair-imported') as root:
            for name,solution in [('a',a),('b',b)]:save_planar_curved_run(solution.case,solution,root/name)
            manager=JobManager(root/'jobs')
            try:
                paths=[manager.directory(manager.import_planar_result(root/name)) for name in ('a','b')]
                original=[{p.relative_to(path).as_posix():p.read_bytes() for p in path.rglob('*')
                    if p.is_file() and p.name!='log.txt'} for path in paths]
                result=execute_owned_planar_curved_tracking(*paths,compare(a,b),root/'pair')
                for side,files in zip(('previous','current'),original):
                    self.assertEqual(len(files),8)
                    self.assertFalse((root/'pair'/side/'worker.claim').exists())
                    for name,data in files.items():self.assertEqual((root/'pair'/side/name).read_bytes(),data)
                self.assertEqual(result['current_mode_ids'],['even-x','odd-x'])
            finally:manager.close()
            (root/'jobs').rename(root/'jobs-unavailable')
            for name in ('a','b'):(root/name).rename(root/(name+'-unavailable'))
            self.assertEqual(read_owned_planar_curved_tracking(root/'pair'),result)

    def test_complete_operand_links_and_request_metadata_are_strict(self):
        from superfish_ng.planar_curved_tracking_saved import execute_owned_planar_curved_tracking,read_owned_planar_curved_tracking
        a,_,b,_=solutions()
        with workspace('pair-strict') as root:
            for name,solution in [('a',a),('b',b)]:save_planar_curved_run(solution.case,solution,root/name)
            alias=root/'alias';alias.symlink_to(root/'a',target_is_directory=True)
            with self.assertRaises(ValueError):execute_owned_planar_curved_tracking(alias,root/'b',compare(a,b),root/'rejected')
            self.assertFalse((root/'rejected').exists())
            execute_owned_planar_curved_tracking(root/'a',root/'b',compare(a,b),root/'pair')
            extra=root/'pair/previous/extra';extra.write_text('undeclared')
            with self.assertRaises(ValueError):read_owned_planar_curved_tracking(root/'pair')
            extra.unlink()
            manifest=root/'pair/manifest.json';saved=manifest.read_bytes();value=json.loads(saved)
            value['saved_version']=True;manifest.write_text(json.dumps(value))
            with self.assertRaises(ValueError):read_owned_planar_curved_tracking(root/'pair')
            manifest.write_bytes(saved)
            field=root/'pair/current/fields.npz';backup=root/'backup.npz';field.rename(backup);field.symlink_to(backup)
            with self.assertRaises(ValueError):read_owned_planar_curved_tracking(root/'pair')
            field.unlink();backup.rename(field)

    def test_earlier_source_mutated_during_later_operand_copy_is_rejected(self):
        from superfish_ng.planar_curved_tracking_saved import execute_owned_planar_curved_tracking
        a,_,b,_=solutions()
        with workspace('pair-copy-mutation') as root:
            for name,solution in [('a',a),('b',b)]:save_planar_curved_run(solution.case,solution,root/name)
            copy=shutil.copyfile;changed=False
            def mutate(src,dst,*args,**kwargs):
                nonlocal changed
                result=copy(src,dst,*args,**kwargs)
                if not changed and Path(src).parent==(root/'b').resolve():
                    path=root/'a/fields.npz';path.write_bytes(path.read_bytes()+b'changed');changed=True
                return result
            with patch('superfish_ng.planar_curved_tracking_saved.shutil.copyfile',side_effect=mutate):
                with self.assertRaisesRegex(ValueError,'source changed'):
                    execute_owned_planar_curved_tracking(root/'a',root/'b',compare(a,b),root/'pair')
            self.assertTrue(changed)
