#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exercise shape-tuning cancellation, owned resume and native GUI transport."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from scripts.validate_hphi_shape_tuning import request as general_request
from superfish_ng.gui_hphi import hphi_response
from superfish_ng.jobs import JobManager


def validate(out):
    out.mkdir(parents=True, exist_ok=False)
    records = []
    sources = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in (ROOT/'src').rglob('*')
               if p.is_file() and p.suffix in ('.py','.html','.js','.css')}
    requests = [('coaxial', json.loads((ROOT/'examples/hphi_tune_coaxial_length.json').read_text())),
                ('holed', general_request())]
    for name, request in requests:
        workspace = out/name
        manager = JobManager(workspace)
        lock = threading.Lock()
        def api(action, **data):
            return hphi_response(manager, action, data, lock, out/'cache')[0]
        def wait(identifier):
            deadline = time.monotonic()+600
            while time.monotonic() < deadline:
                state = manager.status(identifier)
                if state['status'] not in ('queued','running'):
                    manager.processes[identifier].wait(timeout=10)
                    assert state['status']=='complete', state
                    return
                time.sleep(.05)
            raise TimeoutError(identifier)
        try:
            assert api('hphi-normalize-tune', request=json.dumps(request)) == request
            first = api('hphi-start-tune', request=request)['id']
            checkpoint = workspace/first/'execution/checkpoint-001.json'
            deadline = time.monotonic()+600
            while not checkpoint.is_file() and time.monotonic()<deadline:
                assert manager.status(first)['status'] in ('queued','running')
                time.sleep(.01)
            assert checkpoint.is_file(), 'first checkpoint not reached'
            assert manager.cancel(first)['status']=='cancelled'
            initial = api('hphi-open-tune-checkpoint', id=first, index=1)
            assert initial['document']['request']==request
            assert initial['document']['status']=='PAUSED'
            resumed = api('hphi-resume-tune', document=initial['serialized'], max_new_trials=1)['id']
            wait(resumed)
            result = api('hphi-tune-result', id=resumed)
            doc = result['document']
            assert doc['request']==request and len(doc['trials'])==2
            assert doc['status']=='PAUSED'
            assert doc['trials'][:1]==initial['document']['trials']
            assert doc['trial_sources_sha256'][:1]==initial['document']['trial_sources_sha256']
            manager.close()
            (workspace/first).rename(out/(name+'-archived-source'))
            manager = JobManager(workspace)
            assert api('hphi-tune-result', id=resumed)==result
            assert api('hphi-replay-tune', document=result['serialized'])==result
            imports = []
            for index, path in enumerate(doc['trial_runs'],1):
                imported = api('hphi-tune-trial', document=result['serialized'], index=index)
                expected_rank = doc['trials'][index-1]['current_mode_ids'].index(request['mode_id'])+1
                assert imported['mode']==expected_rank
                for filename in ('case.json','mesh.npz','fields.npz','results.json','manifest.json'):
                    assert api('hphi-download',id=imported['id'],file=filename)==(Path(path)/'solution'/filename).read_bytes()
                imports.append(imported)
            records.append(dict(case=name,cancelled_job=first,resumed_job=resumed,
                                imports=imports,trials=doc['trials'],status='PASS'))
            print('PASS', name, flush=True)
        finally:
            manager.close()
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in sources.items())
    (out/'report.json').write_text(json.dumps(dict(status='PASS',records=records,source_sha256=sources),indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    validate(parser.parse_args().out.resolve())
