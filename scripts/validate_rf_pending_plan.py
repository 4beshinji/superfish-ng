# SPDX-License-Identifier: Apache-2.0
"""Compare old/new incremental native replay, including complete checkpoint data."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics
import sys
import time
from unittest.mock import patch
from validate_curved_rf_adaptive import fingerprints
from superfish_ng import curved_rf_adaptive_refinement as current


def incremental(module, document):
    cache_type=getattr(module,'_VerifiedRFPrefix',module._VerifiedPrefix)
    cache=cache_type();results=[];start=time.perf_counter()
    with patch.object(module,'curved_rf_goal_indicator',wraps=module.curved_rf_goal_indicator) as selection:
        module.assemble(document['request'],[],_cache=cache)
        for count in range(1,len(document['level_runs'])+1):
            result,_=module.assemble(document['request'],document['level_runs'][:count],_cache=cache)
            results.append(result)
    return results,time.perf_counter()-start,selection.call_count


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--baseline-module',type=Path,required=True)
    parser.add_argument('--checkpoint',type=Path,action='append',required=True)
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    baseline=args.baseline_module.resolve();old_bytes=baseline.read_bytes()
    spec=importlib.util.spec_from_file_location('superfish_ng._previous_rf_engine',baseline)
    old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
    before=fingerprints();reports=[]
    with patch('superfish_ng.curved_solution.eigsh',side_effect=AssertionError('native comparison must not solve')):
        for path in args.checkpoint:
            raw=path.read_bytes();document=json.loads(raw);samples=[];reference=None
            for trial in range(3):
                measured={}
                for label,module in (('old',old),('new',current)) if trial%2==0 else (('new',current),('old',old)):
                    results,seconds,calls=incremental(module,document)
                    if reference is None:reference=results
                    if results!=reference or results[-1]!=document:
                        raise AssertionError('incremental checkpoint differs from old/native reference')
                    measured[label]=dict(seconds=seconds,rf_selection_calls=calls)
                    print(f'{path.name} trial {trial+1} {label}: {seconds:.6f}s, {calls} selections',flush=True)
                if measured['new']['rf_selection_calls']>=measured['old']['rf_selection_calls']:
                    raise AssertionError('fixture must exercise eliminated repeated RF selection')
                samples.append(measured)
            medians={label:statistics.median(s[label]['seconds'] for s in samples) for label in ('old','new')}
            if path.read_bytes()!=raw:raise AssertionError('input checkpoint changed during comparison')
            reports.append(dict(checkpoint=str(path.resolve()),sha256=hashlib.sha256(raw).hexdigest(),
                event_triangles=[r['triangles'] for r in document['levels']],samples=samples,
                median_seconds=medians,median_ratio_old_over_new=medians['old']/medians['new'],
                all_incremental_documents_identical=True,final_document_identical_to_input=True))
    unchanged=before==fingerprints() and baseline.read_bytes()==old_bytes
    report=dict(passed=unchanged,source_sha256=before,source_unchanged=unchanged,cases=reports,
        baseline_module=str(baseline),baseline_sha256=hashlib.sha256(old_bytes).hexdigest(),
        scope='Three alternating same-process native incremental-assembly trials; no solve/save timing, no generic speed claim. Entire old/new checkpoints and native input match exactly. Other local numerical work may run concurrently.')
    (out/'validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print('Pending plan '+('PASS' if unchanged else 'FAIL'),flush=True)
    return 0 if unchanged else 1


if __name__=='__main__':raise SystemExit(main())
