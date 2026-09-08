# SPDX-License-Identifier: Apache-2.0
"""Exercise RF goal marking, uniform confirmation and actual local FEM solves."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng.saved import read_solution
from superfish_ng.curved_solution import solve_curved
from superfish_ng.curved_refinement_steps import CurvedRefinementStep as Step
from superfish_ng.curved_rf_goal_indicator import curved_rf_goal_indicator
from superfish_ng.curved_rf import quantities_curved
from superfish_ng.io import save_run


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def extend(case,step):
    return replace(case,curved_refinement_levels=0,curved_refinement_steps=
                   (Step('uniform'),)*case.curved_refinement_levels+case.curved_refinement_steps+(step,))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--runs',type=Path,nargs='+',required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();rows=[]
    for index,run in enumerate(args.runs):
        directory=out/f'case-{index:03d}';directory.mkdir()
        with patch('superfish_ng.curved_solution.eigsh',side_effect=AssertionError('native input must not solve')):
            a=read_solution(run)
        start=time.perf_counter();b=solve_curved(extend(a.case,Step('uniform')),mesh_data=a.source_mesh_data)
        confirmation_seconds=time.perf_counter()-start;save_run(b.case,b,directory/'uniform')
        start=time.perf_counter();indicator=curved_rf_goal_indicator(a,b)
        indicator_seconds=time.perf_counter()-start
        (directory/'indicator.json').write_text(json.dumps(indicator,indent=2,allow_nan=False)+'\n')
        selected=indicator['marked_parent_cells']
        if not selected:raise ValueError('zero priority does not certify convergence')
        start=time.perf_counter();c=solve_curved(extend(a.case,Step('marked',tuple(selected),5.)),mesh_data=a.source_mesh_data)
        local_seconds=time.perf_counter()-start;save_run(c.case,c,directory/'local')
        qa,qb,qc=[quantities_curved(s,include_surface_peaks=False) for s in (a,b,c)]
        ritz=bool(np.all(c.frequencies_hz<=a.frequencies_hz*(1+1e-10)))
        rows.append(dict(run=str(run.resolve()),passed=ritz and indicator['local_global_relative_difference']<1e-10,
            dofs=[len(s.u) for s in (a,b,c)],selected_parent_cells=selected,
            estimated_rq_change_ohm=indicator['estimated_accelerator_change_ohm'],
            observed_rq_change_ohm=indicator['observed_accelerator_change_ohm'],
            parent_rq_relative_difference_to_uniform=float(abs(qa['r_over_q_accelerator_ohm']/qb['r_over_q_accelerator_ohm']-1)),
            local_rq_relative_difference_to_uniform=float(abs(qc['r_over_q_accelerator_ohm']/qb['r_over_q_accelerator_ohm']-1)),
            local_global_relative_difference=indicator['local_global_relative_difference'],
            ritz_monotonicity=ritz,confirmation_seconds=confirmation_seconds,indicator_seconds=indicator_seconds,local_seconds=local_seconds))
    unchanged=before==fingerprints();passed=unchanged and all(r['passed'] for r in rows)
    (out/'validation.json').write_text(json.dumps(dict(passed=passed,checks=rows,source_sha256=before,source_unchanged=unchanged,
        scope='one RF-weighted local step after uniform confirmation; reference differences are not absolute RF errors; no efficiency acceptance'),indent=2,allow_nan=False)+'\n')
    print('RF goal indicator '+('PASS' if passed else 'FAIL'),flush=True);return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
