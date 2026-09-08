# SPDX-License-Identifier: Apache-2.0
"""Actual native curved residual-driven refinement and independent invariants."""
import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys
import time
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng import solve
from superfish_ng.analytic import pillbox_tm010
from superfish_ng.curved_refinement_steps import CurvedRefinementStep
from superfish_ng.curved_residual_indicator import curved_residual_indicator
from superfish_ng.curved_rf import quantities_curved
from superfish_ng.io import save_run
from superfish_ng.residual_indicator import mark_bulk
from validate_curved_marked_refinement import scaled_case


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);out=parser.parse_args().out.resolve()
    out.mkdir(parents=True,exist_ok=False)
    def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    before=hashes();checks={}
    rf_keys=('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm','epk_over_eacc_estimate','bpk_over_eacc_estimate_mt_per_mv_per_m')
    for kind in ('cylinder','ellipse','hyperbola'):
        series=[]
        for scale in (1.,2.):
            case=replace(scaled_case(kind,scale),quadrature_order=12);rows=[]
            for level in range(3):
                start=time.perf_counter();solution=solve(case);solve_seconds=time.perf_counter()-start
                run=out/f'{kind}-s{scale:g}-level{level}'
                save_run(case,solution,run)
                start=time.perf_counter();indicator=curved_residual_indicator(case,solution);indicator_seconds=time.perf_counter()-start
                check=curved_residual_indicator(case,solution,quadrature_order=24)
                # Aggregate component differences: tiny individual zero jumps are not relative denominators.
                denominator=sum(check['cell_relative_squared'])
                quadrature={k:float(np.sum(np.abs(np.array(indicator[k])-check[k]))/denominator) for k in ('volume_relative_squared','interior_relative_squared','boundary_relative_squared')}
                marked=mark_bulk(indicator['cell_relative_squared'],.5)
                q=quantities_curved(solution)
                exact=pillbox_tm010(.1*scale,.08*scale) if kind=='cylinder' else None
                errors={k:abs(q[k]/exact[k]-1) for k in rf_keys} if exact else None
                gap=float(solution.frequencies_hz[1]/solution.frequencies_hz[0]-1)
                passed=(max(quadrature.values())<1e-6 and indicator['relative_indicator']>1e-8 and max(solution.residuals)<1e-7 and gap>.05 and bool(marked))
                if errors:passed=passed and errors[rf_keys[0]]<1e-4 and max(errors[k] for k in rf_keys[1:3])<.005 and max(errors[k] for k in rf_keys[3:])<.01
                row=dict(passed=bool(passed),level=level,triangles=len(solution.space.geometry.cell_nodes),dofs=len(solution.u),
                    indicator=indicator,quadrature_component_relative_l1=quadrature,marked_cells=marked,rf=q,cylinder_analytical_errors=errors,
                    eigenpair_residuals=solution.residuals.tolist(),first_mode_relative_gap=gap,solve_seconds=solve_seconds,indicator_seconds=indicator_seconds)
                rows.append(row);(out/(run.name+'-indicator.json')).write_text(json.dumps(row,indent=2,allow_nan=False)+'\n')
                if level<2:
                    case=replace(case,curved_refinement_steps=case.curved_refinement_steps+(CurvedRefinementStep('marked',tuple(marked),5.),))
            ritz=[rows[i+1]['rf']['frequency_hz']/rows[i]['rf']['frequency_hz']-1 for i in range(2)]
            series.append(dict(scale=scale,levels=rows,ritz_frequency_relative_changes=ritz,
                               passed=all(r['passed'] for r in rows) and max(ritz)<2e-9 and rows[-1]['indicator']['relative_indicator']<rows[0]['indicator']['relative_indicator']))
        similarities=[]
        for a,b in zip(series[0]['levels'],series[1]['levels']):
            similarities.append(dict(rf={k:abs(b['rf'][k]*(2 if k=='frequency_hz' else 1)/a['rf'][k]-1) for k in rf_keys},
                indicator=abs(b['indicator']['relative_indicator']/a['indicator']['relative_indicator']-1),same_priority_order=a['marked_cells']==b['marked_cells'],same_selected_cell_set=sorted(a['marked_cells'])==sorted(b['marked_cells'])))
        passed=all(s['passed'] for s in series) and all(max(s['rf'].values())<2e-8 and s['indicator']<2e-8 and s['same_selected_cell_set'] for s in similarities)
        checks[kind]=dict(passed=passed,series=series,similarity=similarities)
    unchanged=before==hashes();passed=unchanged and all(c['passed'] for c in checks.values())
    (out/'validation.json').write_text(json.dumps(dict(passed=passed,checks=checks,source_sha256=before,source_changed_during_run=not unchanged,
        scope='isolated lowest modes of synthetic native cases; residual-based local selection, quadrature comparison, Ritz/cylinder/Maxwell invariants; no automatic stopping, general efficiency or physical error bound'),indent=2,allow_nan=False)+'\n')
    print(f'Curved residual indicator {"PASS" if passed else "FAIL"}: {out}');return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
