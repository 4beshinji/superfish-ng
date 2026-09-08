# SPDX-License-Identifier: Apache-2.0
"""Check sparse adjoint reciprocity on saved native curved eigenfields."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng.saved import read_solution
from superfish_ng.curved_rf_sensitivity import r_over_q_gradient
from superfish_ng.curved_rf_adjoint import r_over_q_adjoint


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--runs',nargs='+',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();rows=[]
    for run in args.runs:
        with patch('superfish_ng.curved_solution.eigsh',side_effect=AssertionError('must not solve native modes')):
            s=read_solution(run)
        a=r_over_q_adjoint(s);g=r_over_q_gradient(s).accelerator_gradient
        rng=np.random.default_rng(113);errors=[];u=s.u[:,0];mu=s.mass@u
        for _ in range(3):
            du=rng.normal(size=len(u));du[s.space.constrained_dofs]=0
            du-=u*(mu@du)/(mu@u)
            force=s.stiffness@du-s.eigenvalues[0]*(s.mass@du)
            direct=float(g@du);dual=float(a.accelerator_adjoint@force)
            errors.append(abs(direct-dual)/max(abs(direct),abs(dual),np.finfo(float).tiny))
        rows.append(dict(run=str(run.resolve()),dofs=len(u),relative_residual=a.relative_residual,
                         relative_gauge_error=a.relative_gauge_error,reciprocity_errors=errors,
                         passed=max(errors)<1e-7 and a.relative_residual<1e-8 and a.relative_gauge_error<1e-10))
    unchanged=before==fingerprints();passed=unchanged and all(r['passed'] for r in rows)
    (out/'validation.json').write_text(json.dumps(dict(passed=passed,checks=rows,source_sha256=before,
        source_unchanged=unchanged,scope='fixed-frequency coefficient adjoint reciprocity; no discretization error bound or total frequency derivative'),indent=2,allow_nan=False)+'\n')
    print('RF adjoint '+('PASS' if passed else 'FAIL'),flush=True);return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
