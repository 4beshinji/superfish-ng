# SPDX-License-Identifier: Apache-2.0
"""A terminated process may resume only its last completely published prefix."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

from superfish_ng.completion import digest
from superfish_ng.curved_rf_goal_efficiency_bundle import file_inventory, verify_bundle
from superfish_ng.curved_rf_goal_efficiency_plan import build_curved_rf_goal_efficiency_plan
from superfish_ng.curved_rf_goal_efficiency_resume import _verify_interruption


ROOT = Path(__file__).resolve().parents[1]


class RFGoalTerminationMetadataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name);self.native = self.root/'native';self.native.mkdir()
        self.execution = build_curved_rf_goal_efficiency_plan()['executions'][0]
        self.parent = dict(execution=self.execution, development_event_limit=None,
                           level_runs=[str(self.native/'event-001')], events=[dict(index=0)])
        self.checkpoint = self.native/'checkpoint-001.json';self.write(self.checkpoint, self.parent)
        self.invocation = dict(schema_version=1, action='run', execution=self.execution,
                               max_new_events=None, source_archives={})
        self.write(self.root/'invocation.json', self.invocation)
        (self.root/'process').mkdir()
        self.process = dict(schema_version=1, document_type='adaptive_efficiency_process_cost',
            status='PROCESS_FAILED', exit_code=-15, wall_seconds=2., peak_rss_bytes=1024,
            request=dict(argv=[sys.executable,str(ROOT/'scripts/run_curved_rf_goal_efficiency.py'),
                '_worker','--invocation',str(self.root/'invocation.json'),'--sha256',digest(self.root/'invocation.json'),
                '--out',str(self.native),'--submission-origin','1.0'], cwd=str(ROOT)))
        source = {'scripts/run_curved_rf_goal_efficiency.py':digest(ROOT/'scripts/run_curved_rf_goal_efficiency.py')}
        for name in ('sources-before.json','sources-after.json'):self.write(self.root/name, source)
        self.write(self.root/'process/process.json', self.process)
        for name in ('stdout.log','stderr.log'):(self.root/'process'/name).write_text('')
        self.manifest = self.root/'manifest.json';self.rebind()

    def write(self, path, value):path.write_text(json.dumps(value))

    def rebind(self):
        (self.root/'process/process.json').write_text(json.dumps(self.process))
        self.write(self.root/'invocation.json', self.invocation)
        self.bundle = dict(schema_version=1, document_type='curved_rf_goal_efficiency_process_bundle',
            status=self.process['status'], source_audit=dict(status='UNCHANGED',changed=[],added=[],deleted=[],scope='endpoint'),
            process=self.process, numerical_status=None, files=file_inventory(self.root),physical_error_bound=None,scope='fixture')
        self.write(self.manifest, self.bundle)
        self.origin = dict(journal_path=str(self.checkpoint), journal_sha256=digest(self.checkpoint), event_count=1,
                           interruption_files={str(self.manifest):digest(self.manifest)})

    def test_term_and_kill_without_failure_receipt_retain_partial_bytes_and_only_complete_prefix(self):
        (self.native/'event-002').mkdir();(self.native/'event-002/fields.npz').write_bytes(b'unpublished native')
        (self.native/'.checkpoint-002-staging').mkdir()
        (self.native/'.checkpoint-002-staging/staged.json').write_bytes(b'{"incomplete":')
        for signal in (-15,-9):
            self.process['exit_code']=signal;self.rebind();bound={}
            _verify_interruption(self.parent, self.origin, bound)
            self.assertEqual(bound[str(self.manifest)], digest(self.manifest))
            self.assertIn(str(self.native/'event-002/fields.npz'), bound)
            self.assertFalse((self.native/'checkpoint-002.json').exists())
            self.assertFalse((self.native/'failure.json').exists())

    def test_unrelated_or_stale_terminal_process_and_wrong_execution_are_rejected_even_after_rehash(self):
        original = deepcopy(self.process)
        for name in ('wrong_output','wrong_invocation_hash','wrong_action','wrong_cwd','positive_exit','boolean_exit','successful_status','wrong_document'):
            self.process=deepcopy(original)
            if name=='wrong_output':self.process['request']['argv'][8]='/unrelated/native'
            elif name=='wrong_invocation_hash':self.process['request']['argv'][6]='0'*64
            elif name=='wrong_action':self.process['request']['argv'][2]='other-worker'
            elif name=='wrong_cwd':self.process['request']['cwd']='/unrelated/repository'
            elif name=='positive_exit':self.process['exit_code']=7
            elif name=='boolean_exit':self.process['exit_code']=True
            elif name=='successful_status':self.process['status']='PROCESS_EXITED'
            else:self.process['document_type']='other-process'
            self.rebind()
            with self.subTest(name=name),self.assertRaises(ValueError):_verify_interruption(self.parent,self.origin,{})
        self.process=original;self.invocation['execution']=deepcopy(self.execution);self.invocation['execution']['method']='rf_goal'
        self.rebind();self.process['request']['argv'][6]=digest(self.root/'invocation.json');self.rebind()
        with self.assertRaises(ValueError):_verify_interruption(self.parent,self.origin,{})

    def test_newer_complete_checkpoint_or_foreign_journal_cannot_use_the_older_prefix(self):
        self.write(self.native/'checkpoint-002.json', dict(self.parent,events=[{},{}]))
        self.rebind()
        with self.assertRaises(ValueError):_verify_interruption(self.parent,self.origin,{})
        (self.native/'checkpoint-002.json').unlink();self.rebind()
        other=self.root/'foreign-checkpoint.json';self.write(other,self.parent)
        origin=dict(self.origin,journal_path=str(other),journal_sha256=digest(other))
        with self.assertRaises(ValueError):_verify_interruption(self.parent,origin,{})

    def test_resource_terminal_stop_is_preserved_and_changed_bundle_bytes_fail(self):
        for status in ('WALL_LIMIT','MEMORY_LIMIT','INTERRUPTED'):
            self.process['status']=status;self.rebind()
            _verify_interruption(self.parent,self.origin,{})
        (self.root/'process/stderr.log').write_text('changed after closure')
        with self.assertRaises(ValueError):verify_bundle(self.manifest,digest(self.manifest))

    def test_source_changed_terminal_bundle_cannot_resume(self):
        self.write(self.root/'sources-after.json', {'new':'0'*64})
        self.rebind();self.bundle['source_audit']=dict(status='CHANGED',changed=[],added=['new'],deleted=['scripts/run_curved_rf_goal_efficiency.py'],scope='endpoint')
        self.bundle['status']='SOURCE_CHANGED';self.write(self.manifest,self.bundle)
        self.origin['interruption_files'][str(self.manifest)]=digest(self.manifest)
        with self.assertRaises(ValueError):_verify_interruption(self.parent,self.origin,{})

    def test_killed_resume_before_first_new_checkpoint_uses_only_explicit_original_verified_journal(self):
        self.checkpoint.unlink();previous=self.root/'previous';previous.mkdir();journal=previous/'result.json'
        parent=dict(self.parent,development_event_limit=1,observed_cost={});self.write(journal,parent);self.checkpoint=journal
        self.invocation=dict(schema_version=1,action='resume',max_new_events=None,journal=str(journal),sha256=digest(journal),implementation_archives={},interruption_files={})
        self.rebind();self.process['request']['argv'][6]=digest(self.root/'invocation.json');self.rebind()
        _verify_interruption(parent,self.origin,{})
        for field,value in (('journal','/wrong/original.json'),('sha256','0'*64),('max_new_events',True)):
            original=self.invocation[field];self.invocation[field]=value;self.rebind();self.process['request']['argv'][6]=digest(self.root/'invocation.json');self.rebind()
            with self.subTest(field=field),self.assertRaises(ValueError):_verify_interruption(parent,self.origin,{})
            self.invocation[field]=original


    def test_first_resumed_checkpoint_binds_its_actual_original_resume_inputs(self):
        self.invocation=dict(schema_version=1,action='resume',max_new_events=None,journal='/previous/result.json',sha256='a'*64,implementation_archives={},interruption_files={})
        parent=dict(self.parent,resume_origin=dict(journal_path=self.invocation['journal'],journal_sha256=self.invocation['sha256'],implementation_archives={},interruption_files={}))
        self.write(self.checkpoint,parent);self.rebind();self.process['request']['argv'][6]=digest(self.root/'invocation.json');self.rebind()
        _verify_interruption(parent,self.origin,{})
        wrong=dict(parent,resume_origin=dict(parent['resume_origin'],journal_sha256='b'*64))
        self.write(self.checkpoint,wrong);self.rebind()
        with self.assertRaises(ValueError):_verify_interruption(wrong,self.origin,{})




if __name__ == '__main__':unittest.main()
