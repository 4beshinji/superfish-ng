# SPDX-License-Identifier: Apache-2.0
"""Verify angular-frequency RF derivatives on native saved curved modes."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng.saved import read_solution
from superfish_ng.constants import TAU
from superfish_ng.curved_rf import quantities_curved
from superfish_ng.curved_rf_frequency_sensitivity import r_over_q_frequency_derivative


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
        d=r_over_q_frequency_derivative(s);h=1e-6
        plus=quantities_curved(replace(s,frequencies_hz=s.frequencies_hz*(1+h)),include_surface_peaks=False)
        minus=quantities_curved(replace(s,frequencies_hz=s.frequencies_hz*(1-h)),include_surface_peaks=False)
        errors={}
        for key,value in [('r_over_q_accelerator_ohm',d.accelerator_derivative_ohm_per_rad_s),('r_over_q_circuit_ohm',d.circuit_derivative_ohm_per_rad_s)]:
            numerical=(plus[key]-minus[key])/(2*h*TAU*s.frequencies_hz[0])
            errors[key]=float(abs(value-numerical)/max(abs(value),abs(numerical),1e-300))
        rows.append(dict(run=str(run.resolve()),dofs=len(s.u),angular_frequency_rad_s=d.angular_frequency_rad_s,
                         accelerator_derivative_ohm_per_rad_s=d.accelerator_derivative_ohm_per_rad_s,
                         relative_errors=errors,passed=max(errors.values())<2e-7))
    unchanged=before==fingerprints();passed=unchanged and all(r['passed'] for r in rows)
    (out/'validation.json').write_text(json.dumps(dict(passed=passed,checks=rows,source_sha256=before,
        source_unchanged=unchanged,scope='angular-frequency partial derivatives at fixed coefficients, matrices and geometry'),indent=2,allow_nan=False)+'\n')
    print('RF frequency derivative '+('PASS' if passed else 'FAIL'),flush=True);return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
