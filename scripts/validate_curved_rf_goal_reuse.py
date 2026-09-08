# SPDX-License-Identifier: Apache-2.0
"""Compare native RF selection reports and measured reconstruction reuse costs."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng.saved import read_solution
from superfish_ng.curved_rf_goal_indicator import curved_rf_goal_indicator


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--baseline-module',type=Path,required=True,help='archived independent project module, never legacy solver code')
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints()
    baseline_path=args.baseline_module.resolve();baseline_hash=hashlib.sha256(baseline_path.read_bytes()).hexdigest()
    spec=importlib.util.spec_from_file_location('superfish_ng._rf_goal_before_reuse',baseline_path)
    baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
    evidence=json.loads((args.evidence/'validation.json').read_text());rows=[]
    for index,record in enumerate(evidence['checks']):
        a=read_solution(record['run']);directory=args.evidence/f'case-{index:03d}';b=read_solution(directory/'uniform')
        expected=json.loads((directory/'indicator.json').read_text());times={'baseline':[],'reuse':[]}
        for repetition in range(3):
            order=['baseline','reuse'] if repetition%2==0 else ['reuse','baseline']
            for name in order:
                function=baseline.curved_rf_goal_indicator if name=='baseline' else curved_rf_goal_indicator
                start=time.perf_counter();actual=function(a,b);times[name].append(time.perf_counter()-start)
                if actual!=expected:raise ValueError(f'{name} changed canonical RF goal report for case {index}')
        rows.append(dict(case_index=index,report_exactly_equal=True,seconds=times,
                         median_speedup=statistics.median(times['baseline'])/statistics.median(times['reuse'])))
    unchanged=before==fingerprints() and hashlib.sha256(baseline_path.read_bytes()).hexdigest()==baseline_hash
    report=dict(passed=unchanged,checks=rows,source_sha256=before,source_unchanged=unchanged,
        baseline_module=str(baseline_path),baseline_sha256=baseline_hash,
        scope='exact report equality and alternating same-process timings; archived goal module uses current public tracking wrapper, whose mathematics and reconstruction are unchanged')
    (out/'validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print('RF goal reuse '+('PASS' if unchanged else 'FAIL'),flush=True);return 0 if unchanged else 1

if __name__=='__main__':raise SystemExit(main())
