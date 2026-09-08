# SPDX-License-Identifier: Apache-2.0
"""Independent cylinder RF/peak checks of actual tracked affine refinements."""
import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng import Case
from superfish_ng.analytic import pillbox_tm010
from superfish_ng.adaptive_refinement import execute_adaptive_refinement
from superfish_ng.affine_surface_convergence import save_affine_surface_convergence,read_affine_surface_convergence


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    before=hashes();checks={}
    for order in (1,2):
        series=[]
        for scale in (1.,2.):
            request=json.loads((ROOT/'examples/adaptive_refinement/pillbox_confirmed.json').read_text())
            case=Case.from_dict(request['case']);case=replace(case,profile=((0.,.1*scale),(.08*scale,.1*scale)),element_order=order,nr=6,nz=4,modes=1,normalization_j=scale**2)
            request.update(case=case.to_dict(),initial_ids=['fundamental'],max_levels=8,max_triangles=150000,relative_tolerances=dict(frequency_hz=1e-4,r_over_q_accelerator_ohm=.005,geometry_factor_ohm=.005))
            checkpoint=execute_adaptive_refinement(request,out/f'p{order}-s{scale:g}')
            path=out/f'p{order}-s{scale:g}-surface.json';report=save_affine_surface_convergence(checkpoint,'fundamental',path)
            assert read_affine_surface_convergence(path)==report
            reference=pillbox_tm010(.1*scale,.08*scale)
            mapping=dict(frequency_hz='frequency_hz',r_over_q_accelerator_ohm='r_over_q_accelerator_ohm',geometry_factor_ohm='geometry_factor_ohm',epk_over_eacc='epk_over_eacc_estimate',bpk_over_eacc_mt_per_mv_per_m='bpk_over_eacc_estimate_mt_per_mv_per_m')
            final=report['rows'][-1];errors={k:max(abs(v/reference[key]-1) for v in final['intervals'][k]) for k,key in mapping.items()}
            # Assess actual physical-reference accuracy independently of changes between meshes.
            passed=(errors['frequency_hz']<1e-4 and all(errors[k]<.005 for k in ('r_over_q_accelerator_ohm','geometry_factor_ohm')) and all(errors[k]<.01 for k in ('epk_over_eacc','bpk_over_eacc_mt_per_mv_per_m'))
                and report['geometry_diagnostic']['status']=='NO_REENTRANT_CORNERS' and report['physical_error_bound'] is None
                and checkpoint['surface_status']=='UNASSESSED' and all(row['mode_index']==0 for row in report['rows']))
            if order==2:passed=passed and report['status']=='TARGETS_MET'
            series.append(dict(passed=passed,scale=scale,adaptive_status=checkpoint['status'],surface_status=report['status'],analytical_interval_endpoint_errors=errors,assessment=report))
        similarity={k:max(abs(b* (2 if k=='frequency_hz' else 1)/a-1) for a,b in zip(series[0]['assessment']['rows'][-1]['intervals'][k],series[1]['assessment']['rows'][-1]['intervals'][k])) for k in mapping}
        checks[f'P{order}']=dict(passed=all(row['passed'] for row in series) and max(similarity.values())<2e-8,series=series,similarity_relative_errors=similarity)
    unchanged=before==hashes();passed=unchanged and all(c['passed'] for c in checks.values())
    result=dict(passed=passed,checks=checks,source_sha256=before,source_changed_during_run=not unchanged,
        scope='actual P1/P2 cylinder adaptive refinements, native replay, separate analytical f/RF/peak endpoint checks, and scaling; P1 nonconvergence remains explicit if encountered; no general physical-error-bound acceptance')
    (out/'validation.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(f'Affine surface convergence {"PASS" if passed else "FAIL"}: {out}');return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
