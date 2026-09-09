# SPDX-License-Identifier: Apache-2.0
"""Compare boundary certificates and first failures with an archived own module."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from superfish_ng import quadratic_boundary as current
from validate_curved_rf_adaptive import fingerprints


def polygon(n):
    angles=np.arange(n)*2*np.pi/n
    vertices=np.column_stack((np.cos(angles),np.sin(angles)))
    return (np.vstack((vertices,(vertices+np.roll(vertices,-1,axis=0))/2)),
            np.column_stack((np.arange(n),np.roll(np.arange(n),-1),np.arange(n)+n)))


def outcome(module,points,nodes,budget=10000):
    try:return dict(report=module.check_quadratic_boundary(points,nodes,max_boxes=budget))
    except ValueError as exc:return dict(error=str(exc))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--baseline-module',type=Path,required=True)
    parser.add_argument('--native-fields',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    before=fingerprints();baseline=args.baseline_module.resolve();old_bytes=baseline.read_bytes()
    spec=importlib.util.spec_from_file_location('superfish_ng._previous_boundary',baseline)
    old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
    cases=[]
    nodes=np.array(((0,1,4),(1,2,5),(2,3,6),(3,0,7)))
    for label,bottom,top,budget in (('separated',.4,.6,10000),('crossing',.8,.2,10000),
                                   ('contact',.5,.5,10000),('budget',.4,.6,1)):
        points=np.array(((0,0),(1,0),(1,1),(0,1),(.5,bottom),(1,.5),(.5,top),(0,.5)))
        for scale in (1e-5,1.,1e5):
            for reverse in (False,True):
                order=nodes if not reverse else nodes[[2,0,3,1]][:,[1,0,2]]
                a=outcome(old,points*scale,order,budget);b=outcome(current,points*scale,order,budget)
                if a!=b:raise AssertionError((label,scale,reverse,a,b))
                if ('report' in b)!=(label=='separated'):raise AssertionError('fixture did not exercise intended outcome')
                cases.append(dict(case=label,scale=scale,reversed=reverse,outcome=b,identical=True))
    raw=args.native_fields.read_bytes()
    with np.load(args.native_fields,allow_pickle=False) as data:
        native=(data['points_rz_m'].copy(),data['boundary_nodes'].copy())
    timings=[]
    for label,(points,edges) in (('polygon-512',polygon(512)),('native-boundary',native)):
        reference=None;samples=[]
        for trial in range(3):
            sample={}
            for name,module in (('old',old),('new',current)) if trial%2==0 else (('new',current),('old',old)):
                start=time.perf_counter();report=outcome(module,points,edges);seconds=time.perf_counter()-start
                if 'report' not in report:raise AssertionError(report)
                if reference is None:reference=report
                if report!=reference:raise AssertionError('boundary certificate changed')
                sample[name]=seconds;print(f'{label} trial {trial+1} {name}: {seconds:.6f}s',flush=True)
            samples.append(sample)
        medians={name:statistics.median(s[name] for s in samples) for name in ('old','new')}
        timings.append(dict(case=label,edges=len(edges),certificate=reference,samples=samples,
                            median_seconds=medians,ratio_old_over_new=medians['old']/medians['new']))
    unchanged=before==fingerprints() and baseline.read_bytes()==old_bytes and args.native_fields.read_bytes()==raw
    (out/'validation.json').write_text(json.dumps(dict(passed=unchanged,source_sha256=before,source_unchanged=unchanged,
        baseline_module=str(baseline),baseline_sha256=hashlib.sha256(old_bytes).hexdigest(),
        native_fields=str(args.native_fields.resolve()),native_sha256=hashlib.sha256(raw).hexdigest(),
        cases=cases,timings=timings,scope='Boundary certificates and exact first-error strings only; no eigenproblem solved. Same-process alternating timing, possibly concurrent with other local validation; not a full-workflow or general speed claim.'),indent=2,allow_nan=False)+'\n')
    print('Boundary candidates '+('PASS' if unchanged else 'FAIL'),flush=True)
    return 0 if unchanged else 1


if __name__=='__main__':raise SystemExit(main())
