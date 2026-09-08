# SPDX-License-Identifier: Apache-2.0
"""Check coefficient sensitivities against saved native fields and finite differences."""
import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch
import numpy as np
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng.saved import read_solution
from superfish_ng.curved_rf import quantities_curved
from superfish_ng.curved_rf_sensitivity import r_over_q_gradient


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--runs',nargs='+',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();checks=[]
    for run in args.runs:
        with patch('superfish_ng.curved_solution.eigsh',side_effect=AssertionError('saved RF checks must not solve')):
            solution=read_solution(run)
        sensitivity=r_over_q_gradient(solution)
        q=solution.results['modes'][0]
        value_error=abs(sensitivity.r_over_q_accelerator_ohm/q['r_over_q_accelerator_ohm']-1)
        rng=np.random.default_rng(402);errors=[]
        for _ in range(3):
            direction=rng.normal(size=solution.u.shape);direction[solution.space.constrained_dofs]=0
            direction*=np.linalg.norm(solution.u[:,0])/np.linalg.norm(direction[:,0])
            h=1e-6
            plus=quantities_curved(replace(solution,u=solution.u+h*direction),include_surface_peaks=False)
            minus=quantities_curved(replace(solution,u=solution.u-h*direction),include_surface_peaks=False)
            numerical=(plus['r_over_q_accelerator_ohm']-minus['r_over_q_accelerator_ohm'])/(2*h)
            derivative=float(sensitivity.accelerator_gradient@direction[:,0])
            errors.append(abs(derivative-numerical)/max(abs(derivative),abs(numerical),np.finfo(float).tiny))
        orthogonality=abs(float(sensitivity.accelerator_gradient@solution.u[:,0]))/max(
            float(np.linalg.norm(sensitivity.accelerator_gradient)*np.linalg.norm(solution.u[:,0])),np.finfo(float).tiny)
        passed=value_error<1e-11 and max(errors)<2e-7 and orthogonality<1e-12
        checks.append(dict(passed=passed,run=str(run.resolve()),dofs=len(solution.u),rq_relative_error=value_error,
                           directional_difference_errors=errors,amplitude_direction_relative_dot=orthogonality))
    unchanged=before==fingerprints();passed=unchanged and all(c['passed'] for c in checks)
    (out/'validation.json').write_text(json.dumps(dict(passed=passed,checks=checks,source_sha256=before,
        source_changed_during_run=not unchanged,scope='fixed-frequency derivatives on native real coefficient spaces; not a total eigenmode/geometry sensitivity or mesh error bound'),indent=2,allow_nan=False)+'\n')
    print('RF sensitivity '+('PASS' if passed else 'FAIL'),flush=True);return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
