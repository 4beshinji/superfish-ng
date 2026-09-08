# SPDX-License-Identifier: Apache-2.0
"""Real adaptive workers: partial completion, resumption and physical references."""
import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys
import time
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng import Case
from superfish_ng.analytic import pillbox_tm010
from superfish_ng.jobs import JobManager
from superfish_ng.adaptive_refinement import read_adaptive_refinement


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    before=hashes();checks={};manager=JobManager(out/'jobs')
    def wait(identifier):
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            if manager.status(identifier)['status'] not in ('queued','running'):return manager.status(identifier,verify=True)
            time.sleep(.05)
        raise TimeoutError('adaptive worker exceeded 60 seconds')
    try:
        for version,name in ((1,'pillbox.json'),(2,'pillbox_confirmed.json')):
            rows=[]
            for scale in (1.,2.):
                request=json.loads((ROOT/'examples/adaptive_refinement'/name).read_text());case=Case.from_dict(request['case'])
                case=replace(case,profile=tuple((z*scale,r*scale) for z,r in case.profile),normalization_j=scale**2)
                request['case']=case.to_dict();first=manager.start_adaptive_refinement(request,max_new_levels=1);partial=wait(first)
                checkpoint=read_adaptive_refinement(manager.directory(first)/'adaptive-refinement-results.json')
                second=manager.start_adaptive_refinement(request,checkpoint=checkpoint);state=wait(second)
                result=read_adaptive_refinement(manager.directory(second)/'adaptive-refinement-results.json')
                q=result['levels'][-1]['quantities'];reference=pillbox_tm010(.1*scale,.2*scale)
                errors={key:abs(q[key]/reference[key]-1) for key in ('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm')}
                modes=[row['current_mode_ids'][row['mode_index']] for row in result['levels']]
                no_recomputed_first=not (manager.directory(second)/'execution/level-001').exists()
                passed=(partial['status']=='complete' and partial['refinement_status']=='PAUSED' and partial['can_resume']
                    and state['status']=='complete' and state['refinement_status']=='TARGETS_MET' and not state['can_resume']
                    and state['numerical_validation']=='not_checked' and state['surface_status']=='UNASSESSED'
                    and result['sources'][:1]==checkpoint['sources'] and no_recomputed_first and all(mode==request['mode_id'] for mode in modes)
                    and errors['frequency_hz']<1e-4 and errors['r_over_q_accelerator_ohm']<.005 and errors['geometry_factor_ohm']<.005)
                rows.append(dict(passed=passed,scale=scale,first_job=first,resumed_job=second,partial_state=partial,final_state=state,
                    no_recomputed_first=no_recomputed_first,analytical_relative_errors=errors,final_quantities=q,checkpoint=result))
            similarity={key:abs(rows[1]['final_quantities'][key]*(2 if key=='frequency_hz' else 1)/rows[0]['final_quantities'][key]-1)
                for key in ('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm')}
            checks[f'version-{version}']=dict(passed=all(row['passed'] for row in rows) and max(similarity.values())<2e-8,series=rows,similarity_relative_errors=similarity)
        # Re-open the manager and verify completion from disk, without worker handles.
        manager.close();manager=JobManager(out/'jobs')
        reopened=all(manager.status(row['resumed_job'],verify=True)['refinement_status']=='TARGETS_MET' for check in checks.values() for row in check['series'])
    finally:manager.close()
    unchanged=before==hashes();passed=reopened and unchanged and all(c['passed'] for c in checks.values())
    report=dict(passed=passed,checks=checks,reopened_completion_verified=reopened,source_sha256=before,source_changed_during_run=not unchanged,
        scope='real isolated workers for version 1/2 P2 cylinder, preserved ancestral level, complete replay, manager reopen, analytical f/RQ/G and length/energy scaling; no hosted CI, GUI or general geometry accuracy acceptance')
    (out/'validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print(f'Adaptive refinement jobs {"PASS" if passed else "FAIL"}: {out}');return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
