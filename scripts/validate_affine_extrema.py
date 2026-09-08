# SPDX-License-Identifier: Apache-2.0
"""Independent cylinder peak/RF convergence and scale checks for affine bounds."""
import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng import Case,solve
from superfish_ng.analytic import pillbox_tm010
from superfish_ng.constants import MU0
from superfish_ng.io import save_run
from superfish_ng.affine_extrema import save_affine_peaks,read_affine_peaks


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    before=hashes();checks={}
    keys=('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm','epk_over_eacc_estimate','bpk_over_eacc_estimate_mt_per_mv_per_m')
    for order in (1,2):
        series=[]
        for scale in (1.,2.):
            rows=[];reference=pillbox_tm010(.1*scale,.08*scale)
            for n in (8,16,32):
                case=Case(profile=((0.,.1*scale),(.08*scale,.1*scale)),nr=n,nz=n//2,modes=1,element_order=order,normalization_j=scale**2)
                sol=solve(case);run=out/f'p{order}-s{scale:g}-n{n}';save_run(case,sol,run)
                document=save_affine_peaks(run,out/f'{run.name}-peaks.json');assert read_affine_peaks(out/f'{run.name}-peaks.json')==document
                q=json.loads((run/'results.json').read_text())['modes'][0];peaks=document['peaks'];values={k:q[k] for k in keys}
                for name,key,factor in [('electric_v_per_m','epk_over_eacc_estimate',1.),('magnetic_a_per_m','bpk_over_eacc_estimate_mt_per_mv_per_m',MU0*1e9)]:
                    b=peaks[name];values[key]=(b['lower_bound']+b['upper_bound'])/2*factor/q['eacc_v_per_m']
                    assert b['lower_bound']<=b['upper_bound']<=b['lower_bound']*(1+1.000001e-6)
                errors={k:abs(values[k]/reference[k]-1) for k in keys}
                rows.append(dict(n=n,triangles=len(sol.mesh.triangles),dofs=len(sol.u),values=values,analytical_relative_errors=errors,peaks=peaks))
            errors=rows[-1]['analytical_relative_errors']
            passed=(errors['frequency_hz']<1e-4 and all(errors[k]<.005 for k in keys[1:3]) and all(errors[k]<.01 for k in keys[3:])
                and all(a['values']['frequency_hz']>=b['values']['frequency_hz'] for a,b in zip(rows,rows[1:])))
            series.append(dict(scale=scale,passed=passed,rows=rows))
        similarity={k:max(abs(b['values'][k]*(2 if k=='frequency_hz' else 1)/a['values'][k]-1) for a,b in zip(series[0]['rows'],series[1]['rows'])) for k in keys}
        checks[f'P{order}']=dict(passed=all(s['passed'] for s in series) and max(similarity.values())<2e-8,series=series,similarity_relative_errors=similarity)
    unchanged=before==hashes();passed=unchanged and all(c['passed'] for c in checks.values())
    report=dict(passed=passed,checks=checks,source_sha256=before,source_changed_during_run=not unchanged,
        scope='P1/P2 cylinder f, RF and enclosed discrete peaks assessed against analytical values separately; length/energy scaling; native replay; no general corner or physical-error-bound acceptance')
    (out/'validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print(f'Affine extrema {"PASS" if passed else "FAIL"}: {out}');return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
