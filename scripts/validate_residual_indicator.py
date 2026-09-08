# SPDX-License-Identifier: Apache-2.0
"""Native residual-driven and uniform refinements against physical invariants."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng import Case,solve
from superfish_ng.analytic import pillbox_spectrum
from superfish_ng.io import save_run
from superfish_ng.mesh_input import mesh_to_dict
from superfish_ng.marked_refinement import refine_marked_cells
from superfish_ng.residual_indicator import residual_indicator,mark_bulk


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    before=hashes();checks={}
    for kind in ('cylinder','folded'):
        for order in (1,2):
            series=[]
            for scale in (1.,2.):
                if kind=='cylinder':
                    case=Case(((0.,.1*scale),(.2*scale,.1*scale)),nr=6,nz=8,modes=2,element_order=order,normalization_j=scale**2)
                    exact=pillbox_spectrum(.1*scale,.2*scale,1)[0][0]
                else:
                    data=Case.load(ROOT/'examples/contour_folded.json').to_dict()
                    data['geometry']['vertices_zr_m']=(np.array(data['geometry']['vertices_zr_m'])*scale).tolist()
                    data['mesh']['contour_mesh']['max_edge_m']*=scale;data['solver']['element_order']=order;data['solver']['modes']=2
                    case=Case.from_dict(data)
                base=solve(case);branches={}
                for selection in ('residual','uniform'):
                    solution=base;rows=[]
                    for level in range(3):
                        seconds=0.;requested=[];quality=None
                        if level:
                            requested=mark_bulk(indicator['cell_relative_squared'],.5) if selection=='residual' else list(range(len(solution.mesh.triangles)))
                            start=time.perf_counter();refined=refine_marked_cells(case,solution.mesh,requested)
                            solution=solve(case,mesh_data=mesh_to_dict(refined.mesh));seconds=time.perf_counter()-start;quality=refined.quality
                        start=time.perf_counter();indicator=residual_indicator(case,solution);indicator_seconds=time.perf_counter()-start
                        name=f'{kind}-p{order}-s{int(scale)}-{selection}-{level}';save_run(case,solution,out/name)
                        (out/name/'indicator.json').write_text(json.dumps(indicator,indent=2,allow_nan=False)+'\n')
                        modes=json.loads((out/name/'results.json').read_text())['modes']
                        row=dict(run=name,level=level,triangles=len(solution.mesh.triangles),dofs=len(solution.u),refine_and_solve_seconds=seconds,
                            indicator_seconds=indicator_seconds,requested_cells=requested,quality=quality,modes=modes,
                            relative_indicator=indicator['relative_indicator'],algebraic_residual=float(solution.residuals[0]),
                            fundamental_relative_gap=float(solution.frequencies_hz[1]/solution.frequencies_hz[0]-1))
                        if kind=='cylinder':row['analytical_frequency_relative_error']=float(solution.frequencies_hz[0]/exact-1)
                        rows.append(row)
                    branches[selection]=rows
                series.append(branches)
            similarity={key:max(abs(y[key]*(2 if key=='frequency_hz' else 1)/x[key]-1)
                for branch in ('residual','uniform') for a,b in zip(series[0][branch],series[1][branch]) for x,y in zip(a['modes'],b['modes']))
                for key in ('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm')}
            indicator_scaling=max(abs(b['relative_indicator']/a['relative_indicator']-1)
                for branch in ('residual','uniform') for a,b in zip(series[0][branch],series[1][branch]))
            branches=[rows for s in series for rows in s.values()]
            reduction=all(rows[-1]['relative_indicator']<rows[0]['relative_indicator'] for rows in branches)
            monotonic=all(b['modes'][0]['frequency_hz']<=a['modes'][0]['frequency_hz']*(1+2e-12) for rows in branches for a,b in zip(rows,rows[1:]))
            isolated=all(row['fundamental_relative_gap']>.005 for rows in branches for row in rows)
            analytic=kind!='cylinder' or all(0<rows[-1]['analytical_frequency_relative_error']<rows[0]['analytical_frequency_relative_error'] for rows in branches)
            same_selection=all(a['requested_cells']==b['requested_cells'] for branch in ('residual','uniform') for a,b in zip(series[0][branch],series[1][branch]))
            passed=reduction and monotonic and isolated and analytic and same_selection and indicator_scaling<2e-8 and max(similarity.values())<2e-8
            checks[f'{kind}-p{order}']=dict(passed=bool(passed),series=series,indicator_reduced=reduction,ritz_monotonic=monotonic,
                isolated_fundamental=isolated,analytical_frequency_improved=analytic,same_scaled_selection=same_selection,
                indicator_scaling_relative_difference=indicator_scaling,similarity_relative_errors=similarity)
    unchanged=before==hashes();passed=unchanged and all(c['passed'] for c in checks.values())
    report=dict(passed=passed,checks=checks,source_sha256=before,source_changed_during_run=not unchanged,
        scope='isolated lowest TM mode, fixed straight P1/P2 cylinder and synthetic folded geometry; residual bulk fraction 0.5 versus uniform refinement, two steps; no physical error bound or general adaptive stop')
    (out/'validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print(f'Residual indicator {"PASS" if passed else "FAIL"}: {out}');return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
