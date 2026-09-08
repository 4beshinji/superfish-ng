# SPDX-License-Identifier: Apache-2.0
"""Cylinder radius tuning with coupled coordinates, unit changes and Maxwell scaling."""
import argparse
import json
import math
import os
from pathlib import Path
import sys
import time
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng.constants import C0
from superfish_ng.jobs import JobManager
from superfish_ng.tuning import read_tune
from superfish_ng.project import Project
from validate_tuning import hashes


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=hashes();rows=[]
    for unit,example in [('m','pillbox_radius'),('1','pillbox_radius_factor')]:
        for scale in (1.,2.):
            request=json.loads((ROOT/f'examples/tuning/{example}.json').read_text())
            points=request['project']['case']['geometry']['points_zr_m']
            request['project']['case']['geometry']['points_zr_m']=[[z*scale,r*scale] for z,r in points]
            request['target_hz']/=scale;request['frequency_tolerance_hz']/=scale;request['mesh_frequency_tolerance_hz']/=scale
            if unit=='m':
                request['bounds']=[v*scale for v in request['bounds']];request['parameter_tolerance']*=scale
            else:
                for binding in request['bindings']:binding['multiplier']*=scale;binding['offset_m']*=scale
            name=f'unit-{unit}-scale-{int(scale)}';(out/f'{name}-request.json').write_text(json.dumps(request,indent=2)+'\n')
            manager=JobManager(out/name)
            def finished(identifier):
                deadline=time.monotonic()+60
                while time.monotonic()<deadline:
                    state=manager.status(identifier)
                    if state['status'] not in ('queued','running'):
                        checked=manager.status(identifier,verify=True)
                        if checked['status']!='complete':raise RuntimeError(f'worker failed: {checked}')
                        return read_tune(manager.directory(identifier)/'tune-results.json')
                    time.sleep(.05)
                raise RuntimeError('coupled tuning worker timeout')
            try:
                first=finished(manager.start_tune(request,max_new_trials=2))
                manager.close();manager=JobManager(out/name)
                result=finished(manager.start_tune(request,checkpoint=first))
            finally:manager.close()
            path=Path(result['trial_runs'][-1]);case=Project.load(path/'project.json').case
            radius=case.profile[0][1];analytic=C0*2.404825557695773/(2*math.pi*radius)
            quantities=json.loads((path/'solution/results.json').read_text())['modes'][0]
            rows.append(dict(unit=unit,scale=scale,status=result['status'],trial_count=len(result['trials']),
                parameter_value=result['decision'].get('value'),radius_m=radius,geometry_zr_m=case.profile,quantities=quantities,
                radius_relative_error=abs(radius/(.093*scale)-1),frequency_analytical_relative_error=abs(quantities['frequency_hz']/analytic-1),
                retained_cylinder=case.profile[0][1]==case.profile[1][1],old_sources_preserved=result['trial_sources_sha256'][:2]==first['trial_sources_sha256']))
    scaling={unit:{key:abs(rows[i+1]['quantities'][key]*(2 if key=='frequency_hz' else 1)/rows[i]['quantities'][key]-1)
        for key in ('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm')} for i,unit in [(0,'m'),(2,'1')]}
    units={key:max(abs(rows[i+2]['quantities'][key]/rows[i]['quantities'][key]-1) for i in (0,1))
        for key in ('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm')}
    passed=(all(r['status']=='TUNED' and r['retained_cylinder'] and r['old_sources_preserved'] and r['radius_relative_error']<2e-5
            and r['frequency_analytical_relative_error']<2e-6 for r in rows)
        and max(v for d in scaling.values() for v in d.values())<2e-9 and max(units.values())<2e-9 and hashes()==before)
    report=dict(passed=passed,rows=rows,similarity_relative_errors=scaling,unit_change_relative_errors=units,
        source_sha256=before,source_changed_during_run=hashes()!=before,
        scope='native P2 TM010 cylinder radius tuning with two coordinate bindings, metres/dimensionless variables, JobManager restart/resume, Bessel frequency and f/RQ/G scale invariants; not arbitrary shape or RF convergence acceptance')
    (out/'validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print(f'Coupled tuning {"PASS" if passed else "FAIL"}: {out}');return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
