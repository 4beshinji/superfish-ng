# SPDX-License-Identifier: Apache-2.0
"""Prepare GUI fixtures and verify real boundary-remesh worker cancellation/resume."""
import argparse
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import signal
import sys
import time
from unittest.mock import patch
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'tests')]
from superfish_ng.curved_remesh_generation import build_curved_remesh_generation
from superfish_ng.project import Project,parse_json
from superfish_ng.jobs import JobManager
from superfish_ng.saved import read_solution
from superfish_ng.adaptive_study import replay_adaptive_study
from test_curved_remesh_study import remesh_study_document
from test_curved_harmonic_study import controls
from validate_large_curved_mesh_selection import fingerprints


def write(path,value):
    with path.open('x') as stream:stream.write(json.dumps(value,indent=2,allow_nan=False)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--checkpoint',type=Path,help='Reuse a completed two-point PAUSED checkpoint without repeating its FEM solves')
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();before=fingerprints();write(out/'source-sha256.json',before)
    fixtures=out/'fixtures';fixtures.mkdir()
    source=Project.load(ROOT/'examples/curved_boundary_remesh/nonaffine-project.json')
    write(fixtures/'source-project.json',source.to_dict())
    studies={}
    for version,path in [(1,'examples/curved_remesh_generation/settings.json'),(2,'examples/curved_boundary_remesh/nonaffine-settings.json')]:
        settings=parse_json((ROOT/path).read_text());document=build_curved_remesh_generation(source,settings)
        write(fixtures/f'v{version}-settings.json',settings);write(fixtures/f'v{version}-generation.json',document)
        write(fixtures/f'v{version}-plan.json',document['plan'])
        study=remesh_study_document();study['mesh_schedule']['plans'][1]['plan']=document['plan'];studies[version]=study
        write(fixtures/f'study-v{version}.json',study)
    request=dict(schema_version=1,study=studies[2],initial_ids=['A'],step_controls=[dict(controls(),minimum_overlap=1.)],
                 adaptive=dict(max_depth=1,max_attempts=4,minimum_parameter_step=.001))
    write(out/'request.json',request)
    manager=JobManager(out/'workspace');processes=[]
    def wait(identifier):
        deadline=time.monotonic()+600
        while time.monotonic()<deadline:
            state=manager.status(identifier)
            if state['status'] not in ('queued','running'):
                state=manager.status(identifier,verify=True);assert state['status']=='complete',state
                return state
            time.sleep(.1)
        raise AssertionError(f'worker still active: {identifier}')
    try:
        if args.checkpoint:
            checkpoint=parse_json(args.checkpoint.read_text())
            with patch('superfish_ng.curved_solution.solve_curved',side_effect=AssertionError('checkpoint replay must not solve')):
                assert replay_adaptive_study(checkpoint)==checkpoint
            assert checkpoint['request']==request and checkpoint['status']=='PAUSED'
            first=str(args.checkpoint.resolve())
        else:
            first=manager.start_adaptive_study(request,max_new_attempts=1);processes.append(manager.processes[first])
            state=wait(first);assert state['tracking_status']=='PAUSED',state
            checkpoint=parse_json((manager.directory(first)/'adaptive-study-results.json').read_text())
        assert checkpoint['attempts'][0]['decision']=='BISECT' and len(checkpoint['points'])==2
        protected={str(p):sha256(p.read_bytes()).hexdigest() for point in checkpoint['points']
                   for p in Path(point['run']).rglob('*') if p.is_file()}
        arrays=[]
        for point in checkpoint['points']:
            with np.load(Path(point['run'])/'solution'/'fields.npz') as saved:arrays.append({k:saved[k].copy() for k in saved.files})
        manager.close();manager=JobManager(out/'workspace')
        cancelled=manager.start_adaptive_study(request,checkpoint=checkpoint);process=manager.processes[cancelled];processes.append(process)
        # Suspend this owned newly spawned process while still queued so the
        # real cancel API is deterministic and does not start a disposable FEM.
        os.kill(process.pid,signal.SIGSTOP)
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            state_line=next(line for line in Path(f'/proc/{process.pid}/status').read_text().splitlines() if line.startswith('State:'))
            if 'T (stopped)' in state_line:break
            time.sleep(.01)
        else:raise AssertionError('owned queued worker did not stop')
        queued=manager.status(cancelled)
        assert queued['status']=='queued' and not (manager.directory(cancelled)/'execution').exists(),queued
        stopped=manager.cancel(cancelled);assert stopped['status']=='cancelled' and process.poll() is not None,stopped
        manager.close();manager=JobManager(out/'workspace')
        assert manager.status(cancelled)['status']=='cancelled'
        resumed=manager.start_adaptive_study(request,checkpoint=checkpoint);processes.append(manager.processes[resumed])
        state=wait(resumed);result=parse_json((manager.directory(resumed)/'adaptive-study-results.json').read_text())
        assert state['tracking_status']=='UNVERIFIED' and result['points'][:2]==checkpoint['points']
        assert result['points'][2]['value']==.5 and result['attempts'][1]['decision']=='STOP'
        assert result['request']==request
        manager.close();manager=JobManager(out/'workspace')
        assert manager.status(resumed,verify=True)['tracking_status']=='UNVERIFIED'
        with patch('superfish_ng.curved_solution.solve_curved',side_effect=AssertionError('saved replay must not solve')):
            assert replay_adaptive_study(result)==result
            natives=[read_solution(Path(point['run'])/'solution') for point in result['points']]
        assert [len(n.source_mesh_data['triangles']) for n in natives]==[26,8,26]
        for index,point in enumerate(result['points'][:2]):
            with np.load(Path(point['run'])/'solution'/'fields.npz') as saved:
                assert set(saved.files)==set(arrays[index])
                for key in saved.files:np.testing.assert_array_equal(saved[key],arrays[index][key])
        assert all(sha256(Path(p).read_bytes()).hexdigest()==value for p,value in protected.items())
        write(out/'completed-adaptive-study.json',result);write(out/'protected-native-sha256.json',protected)
        report=dict(status='PASS',first_job=first,cancelled_job=cancelled,resumed_job=resumed,
            cancelled_before_execution=True,completed_fem_solves=1 if args.checkpoint else 3,
            reused_fem_solves=2 if args.checkpoint else 0,cancelled_fem_solves=0,
            scope='real queued-worker cancellation followed by manager recreation and resume of a completed checkpoint; not recovery of an interrupted FEM or an abnormal crash',
            protected_files=len(protected),protected_arrays=[len(a) for a in arrays],
            initial_cell_counts=[len(n.source_mesh_data['triangles']) for n in natives],
            final_cell_counts=[len(n.space.geometry.cell_nodes) for n in natives],
            final_boundary_counts=[len(n.space.geometry.boundary_nodes) for n in natives],
            full_rf=[n.results['modes'] for n in natives],final_status=state['tracking_status'])
    finally:
        manager.close()
        assert all(process.poll() is not None for process in processes)
    assert fingerprints()==before
    report.update(source_files_unchanged=len(before),seconds=time.monotonic()-started,
                  process_returncodes=[p.returncode for p in processes])
    write(out/'report.json',report)
    print(json.dumps({key:report[key] for key in ('status','completed_fem_solves','cancelled_fem_solves','seconds')}))


if __name__=='__main__':main()
