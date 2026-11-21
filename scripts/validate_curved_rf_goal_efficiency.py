#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fixed 36 fresh RF-goal rows, serial and immutable; retain every unmet target.

Full saved-field replay/GUI is the next acceptance card. This runner records
all native bytes, worker decisions, independent errors and terminal costs.
"""
import argparse
import csv
import gc
from pathlib import Path
import os
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import run_curved_rf_goal_efficiency as transport

from superfish_ng.adaptive_efficiency_reference import _bound_file
from superfish_ng.adaptive_efficiency_timing import PhaseRecorder
from superfish_ng.curved_rf_goal_efficiency_io import publish_rf_goal_json
from superfish_ng.curved_rf_goal_efficiency_plan import build_curved_rf_goal_efficiency_plan, FIXED_PLAN_PATH
from superfish_ng.curved_rf_goal_efficiency_reference import load_curved_rf_goal_efficiency_reference, _bindings
from superfish_ng.curved_rf_goal_efficiency_summary import summarize_execution, compare_repetitions, error_rows
from superfish_ng.curved_rf_goal_efficiency_saved import _preflight, _verify_costs
from superfish_ng.project import parse_json

source_hashes=transport.source_hashes


def prepare_references(archives):
    """Validate each full fixed reference once; retain bytes/costs, not huge arrays."""
    recorder=PhaseRecorder();bound={};cases=[]
    plan=build_curved_rf_goal_efficiency_plan()
    for case in plan['cases']:
        with recorder.phase('shared_reference_verification'):
            reference=load_curved_rf_goal_efficiency_reference(case['id'],source_archives=archives)
            bound.update(reference['bound_inputs'])
            cases.append(dict(case_id=case['id'],orders=[g['order'] for g in reference['grids']],
                              kind=reference['independent_reference_kind'],status=reference['reference_status']))
            del reference
        gc.collect()
    bindings,_,_=_bindings(None);preparation={}
    for key in ('analytic_manifest','rounded_manifest','prolate_manifest'):
        binding=bindings[key];path=_bound_file(binding['path'],binding['sha256'],bound)
        document=parse_json(path.read_text())
        preparation[key]=dict(status='RECORDED' if 'shared_preparation_observed_cost' in document else 'UNKNOWN',
            original_observed_cost=document.get('shared_preparation_observed_cost'),
            original_native_reference_solve_cost_status='UNKNOWN',
            scope='original preparation cost only; reused anchor solve costs not inferred')
    for path,sha in bound.items():_bound_file(path,sha,{})
    return dict(status='VERIFIED',cases=cases,bound_inputs=bound,original_preparation=preparation,
                shared_verification_observed_cost=recorder.finish(),new_native_solves=0,
                scope='separate six-reference preflight; each fresh worker also measures its own full reference verification')


def load_record(target):
    native=target/'native';path=native/'result.json'
    if not path.is_file():
        checkpoints=sorted(native.glob('checkpoint-*.json'));path=checkpoints[-1] if checkpoints else None
    if path is None:return None,None
    record=parse_json(path.read_text());_preflight(record);_verify_costs(record)
    return record,dict(path=str(path),sha256=transport.digest(path))


def export_errors(path,records):
    columns=['execution_id','case_id','method','repetition','event_index','parent_event_index','accepted','refinement_kind',
        'dofs','triangles','gauss_order','quantity','relative_error','limit','gate','accuracy_status',
        'native_path_seconds','submission_prefix_seconds','physical_error_bound']
    with Path(path).open('x',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns);writer.writeheader()
        for execution,record in records:writer.writerows(error_rows(execution,record))


def plot_errors(out):
    """Plot actual parent edges; a rejected probe never becomes the local parent."""
    with (out/'errors-vs-dofs-and-time.csv').open() as stream:data=list(csv.DictReader(stream))
    if not data:return dict(status='NO_OBSERVATIONS',files=[])
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:return dict(status='MATPLOTLIB_UNAVAILABLE',files=[],csv_preserved=True)
    from superfish_ng.adaptive_efficiency_accuracy import LIMITS
    colors=dict(uniform='tab:blue',rf_goal='tab:orange',uniform_when_rf_passes='tab:green');files=[]
    for case in dict.fromkeys(r['case_id'] for r in data):
        for x,label in (('dofs','Native DOFs'),('submission_prefix_seconds','Submission to end of event (s)')):
            fig,axes=plt.subplots(3,3,figsize=(15,11),constrained_layout=True)
            for ax,(quantity,limit) in zip(axes.flat,LIMITS.items()):
                for method,color in colors.items():
                    for repetition in (1,2):
                        for order in (16,24):
                            group={int(r['event_index']):r for r in data if r['case_id']==case and r['quantity']==quantity and
                                r['method']==method and int(r['repetition'])==repetition and int(r['gauss_order'])==order}
                            for index,row in group.items():
                                if not row['relative_error'] or not row[x]:continue
                                parent=group.get(int(row['parent_event_index'])) if row['parent_event_index'] else None
                                if parent is not None and parent['relative_error'] and parent[x]:
                                    ax.plot([float(parent[x]),float(row[x])],[float(parent['relative_error']),float(row['relative_error'])],
                                            color=color,linestyle='-' if order==24 else '--',alpha=.55)
                                ax.scatter(float(row[x]),float(row['relative_error']),edgecolors=color,marker='o' if repetition==1 else 's',
                                    facecolors='none' if row['accepted']=='False' else color,s=16)
                ax.axhline(limit,color='black',linestyle=':');ax.set_yscale('symlog',linthresh=1e-12)
                if x=='dofs':ax.set_xscale('log')
                ax.set_title(quantity);ax.set_xlabel(label);ax.set_ylabel('Relative error');ax.grid(alpha=.2)
            fig.suptitle(case+': actual parent edges; blue uniform / orange RF goal / green RF-pass uniform; hollow rejected; rep 1 o / rep 2 s')
            name=f'{case}-errors-vs-{x}.png';fig.savefig(out/name,dpi=130);plt.close(fig);files.append(name)
    return dict(status='PLOTS_WRITTEN',files=files,scope='nine separate quantities; real parent edges, both Gauss orders and repetitions; missing values omitted visibly in CSV, zero retained on symlog; no acceptance implied')


def run_benchmark(out,archives):
    """Always the complete fixed plan; no development cap or past-native reuse."""
    out=transport.new_output(out)
    if os.environ.get('OPENBLAS_NUM_THREADS')!='1' or sys.platform!='linux':
        raise ValueError('fixed RF-goal benchmark requires Linux and OPENBLAS_NUM_THREADS=1 before startup')
    before=source_hashes();plan=build_curved_rf_goal_efficiency_plan();references=prepare_references(archives)
    if before!=source_hashes():raise ValueError('RF benchmark sources changed during reference preflight')
    out.mkdir(parents=True,exist_ok=False)
    publish_rf_goal_json(out/'plan.json',plan);publish_rf_goal_json(out/'source-archives.json',archives)
    publish_rf_goal_json(out/'environment.json',transport.environment())
    publish_rf_goal_json(out/'references.json',references);publish_rf_goal_json(out/'sources-before.json',before)
    rows=[];records=[];attempted=[];exception=None;changed=False
    try:
        for index,execution in enumerate(plan['executions']):
            print(f"START {index+1}/36 {execution['id']}",flush=True)
            target=out/execution['id']
            invocation=transport.fresh_invocation(execution['id'],source_archives=archives)
            attempted.append(execution['id'])
            bundle=transport.run_invocation(invocation,target)
            record,binding=load_record(target)
            row=summarize_execution(execution,bundle,record)
            row['bundle']=dict(path=str(target/'manifest.json'),sha256=transport.digest(target/'manifest.json'))
            row['journal']=binding
            if (target/'native/failure.json').is_file():row['failure']=parse_json((target/'native/failure.json').read_text())
            rows.append(row);records.append((execution,record))
            publish_rf_goal_json(out/f'row-{index+1:03d}.json',row)
            print(f"END {index+1}/36 {execution['id']} {row['process_status']} {row['benchmark_status']}",flush=True)
            if bundle['source_audit']['status']!='UNCHANGED' or bundle['status']=='SOURCE_CHANGED':
                changed=True;break
    except BaseException as error:
        exception=dict(type=type(error).__name__,message=str(error))
        raise
    finally:
        after=source_hashes();changed=changed or before!=after
        publish_rf_goal_json(out/'sources-after.json',after)
        missing=[e['id'] for e in plan['executions'][len(attempted):]]
        status=('SOURCE_CHANGED' if changed else 'INTERRUPTED_OR_FAILED' if exception is not None else
                'INCOMPLETE' if missing else 'FIXED_RUNS_RECORDED' if all(r['confirmed'] for r in rows) else 'FIXED_RUNS_RECORDED_WITH_UNMET_TARGETS')
        summary=dict(schema_version=1,document_type='curved_rf_goal_fixed_36_measurements',status=status,rows=rows,
            actual_native_executions=len(attempted),completed_measurement_rows=len(rows),
            not_run_execution_ids=missing,unreported_execution_ids=attempted[len(rows):],exception=exception,
            completed_journal_events=sum(r['event_count'] for r in rows),confirmed_executions=sum(r['confirmed'] for r in rows),
            comparisons=compare_repetitions(rows),source_bytes_unchanged=not changed,physical_error_bound=None,
            full_saved_replay_status='NOT_RUN_06_REQUIRED',
            scope='fixed serial 36 fresh workers; all unmet/resource/failed rows retained; no resumed or development rows; '
                  'root native path/solve/eigenproblem are nested scopes, never sum them; full process includes imports/final writes/reap')
        publish_rf_goal_json(out/'summary.json',summary)
        export_errors(out/'errors-vs-dofs-and-time.csv',records)
    for path,sha in references['bound_inputs'].items():_bound_file(path,sha,{})
    publish_rf_goal_json(out/'plots.json',plot_errors(out))
    return summary


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True);parser.add_argument('--source-archives',required=True)
    parser.add_argument('--source-archives-sha256',required=True);args=parser.parse_args(argv)
    archives=transport.read_json_binding(args.source_archives,args.source_archives_sha256)
    if type(archives) is not dict:parser.error('source archives must be a SHA256-to-absolute-path mapping')
    summary=run_benchmark(args.out,archives);print(summary['status'],flush=True)
    return 0 if summary['status'] in ('FIXED_RUNS_RECORDED','FIXED_RUNS_RECORDED_WITH_UNMET_TARGETS') else 1


if __name__=='__main__':sys.exit(main())
