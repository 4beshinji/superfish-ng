# SPDX-License-Identifier: Apache-2.0
"""Exercise version 5 through CLI pause/resume and native-only replay."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng.cli import main as cli
from superfish_ng.adaptive_refinement import replay_adaptive_refinement


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--version4-request',type=Path,required=True);args=parser.parse_args()
    request=json.loads(args.version4_request.read_text())
    if request['schema_version']!=4:raise ValueError('comparison requires an existing version 4 request')
    request['schema_version']=5;out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    (out/'request.json').write_text(json.dumps(request,indent=2)+'\n');before=fingerprints();start=time.perf_counter()
    first_code=cli(['adaptive-refine',str(out/'request.json'),'--out',str(out/'first'),'--max-new-levels','2'])
    checkpoints=sorted((out/'first').glob('checkpoint-*.json'));first=checkpoints[-1]
    prefix=json.loads(first.read_text());resume_code=None
    if prefix['can_resume']:
        resume_code=cli(['resume-adaptive-refinement',str(first),'--out',str(out/'resumed')])
        checkpoints+=sorted((out/'resumed').glob('checkpoint-*.json'))
    seconds=time.perf_counter()-start;reports=[]
    with patch('superfish_ng.curved_solution.eigsh',side_effect=AssertionError('native replay must not solve')):
        for path in checkpoints:
            document=json.loads(path.read_text());assert replay_adaptive_refinement(document)==document
            reports.append(document)
    final=reports[-1];ritz=[]
    for row in final['levels']:
        parent=row['parent_event_index']
        if parent is not None:ritz.append(row['quantities']['frequency_hz']<=final['levels'][parent]['quantities']['frequency_hz']*(1+1e-9))
    unchanged=before==fingerprints();passed=unchanged and all(ritz) and final['status']=='TARGETS_MET'
    report=dict(passed=passed,status=final['status'],solve_events=len(final['levels']),accepted_event_indices=final['decision']['accepted_event_indices'],
        event_roles=[row['refinement_kind'] for row in final['levels']],parents=[row['parent_event_index'] for row in final['levels']],
        triangles=[row['triangles'] for row in final['levels']],all_checkpoints_replayed=True,ritz_monotonicity=all(ritz),
        first_cli_code=first_code,resume_cli_code=resume_code,execution_seconds=seconds,source_sha256=before,source_unchanged=unchanged,
        original_request=str(args.version4_request.resolve()),scope='same five tolerances and geometry; version 5 counts all solves including probes; one CLI resumed example, not general efficiency or absolute RF error acceptance')
    (out/'validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print('RF adaptive '+('PASS' if passed else 'FAIL'),flush=True);return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
