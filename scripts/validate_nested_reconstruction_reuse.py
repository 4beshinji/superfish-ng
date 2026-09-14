# SPDX-License-Identifier: Apache-2.0
"""Compare native ancestry reconstruction against archived project code."""
import argparse
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import statistics
import sys
import time
from unittest.mock import patch
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng.saved import read_solution
from superfish_ng.curved_saved import geometry_arrays
from superfish_ng.curved_fem import assemble_curved
from superfish_ng.curved_reflection import reflect_curved_solution
from superfish_ng import nested_curved_tracking as tracking
from validate_curved_rf_goal_reuse import fingerprints

goal=importlib.import_module('superfish_ng.curved_rf_goal_indicator')
CONTROLS=dict(mapping='nested_curved',minimum_overlap=.95,minimum_assignment_margin=.05,
              relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)


def equal_transfers(first,second):
    p,space,a,b,ancestry=first;q,other,c,d,history=second
    if p.shape!=q.shape or (p-q).nnz or ancestry!=history:
        raise ValueError('transfer or ancestry changed')
    left,right=geometry_arrays(space),geometry_arrays(other)
    if (set(left)!=set(right) or any(not np.array_equal(left[k],right[k]) for k in left)
            or not np.array_equal(a,c) or not np.array_equal(b,d)):
        raise ValueError('reconstructed geometry or coefficients changed')


def alternating(functions,expected,check):
    times={name:[] for name in functions}
    for repetition in range(3):
        names=list(functions)
        if repetition%2:names.reverse()
        for name in names:
            start=time.perf_counter();actual=functions[name]();times[name].append(time.perf_counter()-start)
            check(expected,actual)
    return dict(seconds=times,median_speedup=statistics.median(times['baseline'])/statistics.median(times['reuse']),
                exactly_equal=True)


def equal_reports(expected,actual):
    if actual!=expected:raise ValueError('canonical report changed')


def write_json(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True,help='native RF-goal validator output with checks and uniform runs')
    parser.add_argument('--baseline-module',type=Path,required=True,help='archived independent project nested_curved_tracking.py; never legacy solver code')
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    before=fingerprints();started=time.perf_counter()
    baseline_path=args.baseline_module.resolve();baseline_hash=hashlib.sha256(baseline_path.read_bytes()).hexdigest()
    spec=importlib.util.spec_from_file_location('superfish_ng._nested_before_reuse',baseline_path)
    baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
    evidence=json.loads((args.evidence/'validation.json').read_text());rows=[];sources={}
    for index,record in enumerate(evidence['checks']):
        old_run=Path(record['run']);new_run=args.evidence/f'case-{index:03d}'/'uniform'
        for directory in (old_run,new_run):
            for path in sorted(directory.iterdir()):
                if path.is_file():sources[str(path.resolve())]=hashlib.sha256(path.read_bytes()).hexdigest()
        a,b=read_solution(old_run),read_solution(new_run)
        directory=out/f'case-{index:03d}';directory.mkdir()
        row=dict(case_index=index,previous_run=str(old_run.resolve()),current_run=str(new_run.resolve()),
                 dofs=[len(a.u),len(b.u)])
        reference=baseline._nested_transfer(a,b)
        row['transfer']=alternating(dict(baseline=lambda:baseline._nested_transfer(a,b),
            reuse=lambda:tracking._nested_transfer(a,b)),reference,equal_transfers)
        p=reference[0]
        # Independent higher-order integration tests preservation of the whole
        # coarse mass form, not only the available eigenfields or their residuals.
        coarse_mass=assemble_curved(a.space,quadrature_order=12)[1]
        fine_mass=assemble_curved(b.space,quadrature_order=12)[1]
        delta=p.T@fine_mass@p-coarse_mass
        error=float(np.linalg.norm(delta.data)/np.linalg.norm(coarse_mass.data))
        constant_error=float(np.max(abs(p@np.ones(p.shape[1])-1)))
        if error>1e-11 or constant_error>1e-13:raise ValueError('nested polynomial mass invariant failed')
        row['mass_form_relative_difference']=error;row['constant_transfer_max_error']=constant_error
        ids=[f'previous-{i}' for i in range(len(a.frequencies_hz))]
        expected=baseline.track_nested_curved_modes(a,b,ids,**CONTROLS)
        row['tracking']=alternating(dict(baseline=lambda:baseline.track_nested_curved_modes(a,b,ids,**CONTROLS),
            reuse=lambda:tracking.track_nested_curved_modes(a,b,ids,**CONTROLS)),expected,equal_reports)
        write_json(directory/'tracking.json',expected)
        def old_goal():
            # Only the ancestry module differs. The RF/adjoint code, loaded
            # native fields and numerical libraries are identical in both runs.
            with patch.object(goal,'_nested_transfer',baseline._nested_transfer):
                return goal.curved_rf_goal_indicator(a,b)
        expected=old_goal()
        row['rf_goal']=alternating(dict(baseline=old_goal,reuse=lambda:goal.curved_rf_goal_indicator(a,b)),expected,equal_reports)
        write_json(directory/'rf-goal.json',expected)
        if a.case.z_min!='pec' or a.case.z_max!='pec':
            _,ra=reflect_curved_solution(a.case,a);_,rb=reflect_curved_solution(b.case,b)
            equal_transfers(baseline._nested_transfer(ra,rb),tracking._nested_transfer(ra,rb))
            reflected=baseline.track_nested_curved_modes(ra,rb,ids,**CONTROLS)
            equal_reports(reflected,tracking.track_nested_curved_modes(ra,rb,ids,**CONTROLS))
            write_json(directory/'reflected-tracking.json',reflected)
            row['reflected_transfer_and_report_exactly_equal']=True
        rows.append(row);print(f'case {index} PASS, RF median speedup {row["rf_goal"]["median_speedup"]:.3f}',flush=True)
    unchanged=before==fingerprints() and hashlib.sha256(baseline_path.read_bytes()).hexdigest()==baseline_hash
    inputs_unchanged=all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest for path,digest in sources.items())
    report=dict(passed=unchanged and inputs_unchanged,checks=rows,source_sha256=before,source_unchanged=unchanged,
        native_sha256=sources,native_unchanged=inputs_unchanged,baseline_module=str(baseline_path),baseline_sha256=baseline_hash,
        seconds=time.perf_counter()-started,
        scope='three alternating same-process observations per native pair; archived ancestry code with current RF/adjoint and libraries; no new eigensolve, no general speed guarantee')
    write_json(out/'validation.json',report)
    print('nested reconstruction reuse '+('PASS' if report['passed'] else 'FAIL'),flush=True)
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
