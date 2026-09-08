# SPDX-License-Identifier: Apache-2.0
"""Actual FEM/reference and dimensional-invariant checks for RF peak reports."""
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
from superfish_ng.io import save_run
from superfish_ng.analytic import pillbox_tm010
from superfish_ng.rf_peak_assessment import save_rf_peaks,read_rf_peaks


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    before=hashes();checks={}
    def evaluate(case,name):
        run=out/name;save_run(case,solve(case),run);path=out/(name+'-peaks.json');r=save_rf_peaks(run,path);assert read_rf_peaks(path)==r
        assert r['status']=='DISCRETE_BOUNDS_ONLY' and r['mesh_convergence']=='UNASSESSED' and r['physical_error_bound'] is None
        return r
    for order in (1,2):
        rows=[]
        for scale in (1.,2.):
            case=Case(((0.,.1*scale),(.08*scale,.1*scale)),nr=32,nz=16,modes=1,element_order=order,normalization_j=scale**2)
            r=evaluate(case,f'p{order}-s{scale:g}');ref=pillbox_tm010(.1*scale,.08*scale)
            errors={k:abs(r['rf'][k]/ref[k]-1) for k in ('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm')}
            for k,target in (('epk_over_eacc','epk_over_eacc_estimate'),('bpk_over_eacc_mt_per_mv_per_m','bpk_over_eacc_estimate_mt_per_mv_per_m')):
                errors[k]=max(abs(v/ref[target]-1) for v in r['intervals'][k])
            passed=errors['frequency_hz']<1e-4 and max(errors[k] for k in ('r_over_q_accelerator_ohm','geometry_factor_ohm'))<.005 and max(errors[k] for k in ('epk_over_eacc','bpk_over_eacc_mt_per_mv_per_m'))<.01
            rows.append(dict(passed=passed,scale=scale,analytical_interval_endpoint_errors=errors,assessment=r))
        a,b=[row['assessment'] for row in rows]
        similarity={k:abs(b['rf'][k]*(2 if k=='frequency_hz' else 1)/a['rf'][k]-1) for k in ('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm')}
        similarity.update({k:max(abs(y/x-1) for x,y in zip(a['intervals'][k],b['intervals'][k])) for k in ('epk_over_eacc','bpk_over_eacc_mt_per_mv_per_m')})
        checks[f'P{order}']=dict(passed=all(row['passed'] for row in rows) and max(similarity.values())<2e-8,series=rows,similarity_relative_errors=similarity)
    case=replace(Case.load(ROOT/'examples/curved_ellipse.json'),geometry_order=2)
    a=evaluate(case,'curve-u1');b=evaluate(replace(case,normalization_j=case.normalization_j*4),'curve-u4')
    scaling={k:max(abs(y/(x*(2 if k in ('epk_v_per_m','hpk_a_per_m','bpk_t') else 1))-1) for x,y in zip(a['intervals'][k],b['intervals'][k])) for k in a['intervals']}
    checks['curved_energy_normalization']=dict(passed=max(scaling.values())<2e-8,relative_errors=scaling,assessments=[a,b])
    unchanged=before==hashes();passed=unchanged and all(c['passed'] for c in checks.values())
    (out/'validation.json').write_text(json.dumps(dict(passed=passed,checks=checks,source_sha256=before,source_changed_during_run=not unchanged,
        scope='actual FEM cylinder analytical f/RF/peak endpoint checks, size scaling, curved peak energy normalization, native replay; no physical error bound or general convergence acceptance'),indent=2,allow_nan=False)+'\n')
    print(f'RF peak assessment {"PASS" if passed else "FAIL"}: {out}');return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
