# SPDX-License-Identifier: Apache-2.0
"""Report-derived finite RF-goal hits and costs, keeping failed trials visible.

This layer recomputes scalar/ancestry decisions, not fields. Full saved-field
replay and independent similarity audits remain separate acceptance evidence.
"""
from copy import deepcopy
import math

from .adaptive_efficiency_accuracy import LIMITS
from .curved_rf_goal_efficiency_metrics import assess_rf_goal_history
from .curved_rf_goal_efficiency_saved import _same_saved


METHODS=('uniform','rf_goal','uniform_when_rf_passes')


def _seconds(value):
    if type(value) not in (int,float) or not math.isfinite(value) or value<0:
        raise ValueError('RF measurement requires finite nonnegative seconds')
    return value


def event_solver_costs(record):
    """Inclusive solve and eigensolver intervals, each same-name root counted once.

    Solve includes assembly/normalization/observer overhead. Eigenproblem is a
    subset and must not be added to it. Absent intervals stay UNKNOWN/null.
    """
    n=len(record['events']);unknown=[dict(native_solve_cumulative_seconds=None,eigenproblem_cumulative_seconds=None) for _ in range(n)]
    if record.get('schema_version')!=1 or 'observed_cost' not in record:return unknown
    phases=record['observed_cost']['phases'];roots=[p['index'] for p in phases if p['name']=='native_event' and p['parent_index'] is None]
    if len(roots)!=n:return unknown
    root_to_event={index:i for i,index in enumerate(roots)};costs=[[0.,0.] for _ in range(n)];counts=[[0,0] for _ in range(n)]
    for index,p in enumerate(phases):
        if type(p['index']) is not int or p['index']!=index:raise ValueError('RF phase indices must remain ordered')
        parent=p['parent_index']
        if parent is not None and (type(parent) is not int or not 0<=parent<index):raise ValueError('RF phase parent must precede its child')
        if p['name'] not in ('native_solve_and_normalization','eigenproblem'):continue
        column=0 if p['name']=='native_solve_and_normalization' else 1
        ancestor=parent;duplicate=False;owner=None
        while ancestor is not None:
            if phases[ancestor]['name']==p['name']:duplicate=True
            if ancestor in root_to_event:owner=root_to_event[ancestor]
            ancestor=phases[ancestor]['parent_index']
        if owner is None or duplicate:continue
        counts[owner][column]+=1
        value=p.get('inclusive_seconds')
        if value is None:costs[owner][column]=None
        elif costs[owner][column] is not None:costs[owner][column]+=_seconds(value)
    cumulative=[0.,0.];result=[]
    for values,observed in zip(costs,counts):
        for k in (0,1):
            if not observed[k] or values[k] is None:cumulative[k]=None
            elif cumulative[k] is not None:cumulative[k]+=values[k]
        result.append(dict(native_solve_cumulative_seconds=cumulative[0],eigenproblem_cumulative_seconds=cumulative[1]))
    return result


def summarize_execution(execution, bundle, record):
    process=bundle['process'];wall=None if process is None else _seconds(process['wall_seconds'])
    row=dict(execution_id=execution['id'],case_id=execution['case_id'],method=execution['method'],repetition=execution['repetition'],
        process_status=None if process is None else process['status'],process_exit_code=None if process is None else process['exit_code'],
        bundle_status=bundle['status'],benchmark_status=None if record is None else record['status'],
        native_status=None if record is None else record['native_status'],confirmed=False,
        first_accuracy_hit=None,first_rejected_accuracy_hit=None,confirmed_accuracy_hit=None,confirmation_event_indices=None,
        process_wall_seconds=wall,peak_rss_bytes=None if process is None else process['peak_rss_bytes'],
        event_count=0,maximum_event_dofs=None,final_dofs=None,observed_phase_totals=None,
        physical_error_bound=None,full_saved_replay_status='NOT_RUN_06_REQUIRED')
    if record is None:return row
    _same_saved(record['execution'],execution,'RF measured fixed execution')
    assessment=assess_rf_goal_history(record['events'],record['observations'])
    _same_saved(record['assessment'],assessment,'RF measured actual ancestry assessment')
    events=record['events'];records=record['event_records']
    if not events or len(records)!=len(events):raise ValueError('RF report needs one complete record per event')
    for i,(event,item) in enumerate(zip(events,records)):
        if type(item['index']) is not int or item['index']!=i:raise ValueError('RF event records must retain their indices')
        if any(type(event[k]) is not int or event[k]<=0 for k in ('dofs','triangles')):raise ValueError('RF event sizes require positive integer counts')
        for key,value in item['observed_prefix_cost'].items():
            if key.endswith('_seconds') and value is not None:_seconds(value)
    costs=event_solver_costs(record)
    def hit(key):
        index=assessment[key]
        if index is None:return None
        event=events[index]
        return dict(event_index=index,dofs=event['dofs'],triangles=event['triangles'],
                    **deepcopy(records[index]['observed_prefix_cost']),**costs[index])
    row.update(event_count=len(events),maximum_event_dofs=max(e['dofs'] for e in events),final_dofs=events[-1]['dofs'],
               first_accuracy_hit=hit('first_accuracy_hit_index'),first_rejected_accuracy_hit=hit('first_rejected_accuracy_hit_index'))
    fresh=(record.get('schema_version')==1 and 'resume_origin' not in record and record.get('development_event_limit') is None)
    confirmed=bool(fresh and bundle['status']=='PROCESS_EXITED' and bundle['source_audit']['status']=='UNCHANGED' and
        process is not None and process['status']=='PROCESS_EXITED' and type(process['exit_code']) is int and process['exit_code']==0 and
        record['status']=='TARGETS_MET' and assessment['status']=='CONFIRMED')
    row['confirmed']=confirmed
    if confirmed:
        row['confirmed_accuracy_hit']=hit('confirmed_accuracy_hit_index');row['confirmation_event_indices']=assessment['confirmation_event_indices']
    if 'observed_cost' in record:
        totals={}
        for p in record['observed_cost']['phases']:
            value=p.get('exclusive_seconds');name=p['name']
            if value is None:totals[name]=None
            elif totals.get(name,0.) is not None:totals[name]=totals.get(name,0.)+_seconds(value)
        row['observed_phase_totals']=totals
    return row


def compare_repetitions(rows):
    """Keep both repetitions; success ratios require all four paired successes."""
    ids=[(r['case_id'],r['method'],r['repetition']) for r in rows]
    if len(ids)!=len(set(ids)):raise ValueError('RF comparisons cannot duplicate a case/method/repetition')
    if any(r['method'] not in METHODS or type(r['repetition']) is not int or r['repetition'] not in (1,2) for r in rows):
        raise ValueError('RF comparisons require the three fixed methods and repetitions 1/2')
    result=[]
    for case in dict.fromkeys(r['case_id'] for r in rows):
        selected={method:[next((r for r in rows if r['case_id']==case and r['method']==method and r['repetition']==rep),None) for rep in (1,2)] for method in METHODS}
        methods={};ratios={}
        for method,values in selected.items():
            measures={key:[None if r is None else r[key] for r in values] for key in ('confirmed','benchmark_status','process_status','process_wall_seconds','peak_rss_bytes','maximum_event_dofs')}
            measures['confirmed_dofs']=[None if r is None or r['confirmed_accuracy_hit'] is None else r['confirmed_accuracy_hit']['dofs'] for r in values]
            measures['confirmed_native_path_seconds']=[None if r is None or r['confirmed_accuracy_hit'] is None else r['confirmed_accuracy_hit']['native_path_cumulative_seconds'] for r in values]
            measures['ranges']={key:None if any(v is None for v in data) or any(type(v) not in (int,float) for v in data) else [min(data),max(data)] for key,data in measures.items()}
            methods[method]=measures
            if method=='uniform':continue
            paired=selected['uniform']+values
            accepted=all(r is not None and r['confirmed'] for r in paired)
            if not accepted:ratios[method]=None;continue
            def divide(numerator,denominator):return None if denominator is None or numerator is None or denominator<=0 else numerator/denominator
            ratios[method]=dict(full_process_uniform_over_method=[divide(a['process_wall_seconds'],b['process_wall_seconds']) for a,b in zip(selected['uniform'],values)],
                native_path_uniform_over_method=[divide(a['confirmed_accuracy_hit']['native_path_cumulative_seconds'],b['confirmed_accuracy_hit']['native_path_cumulative_seconds']) for a,b in zip(selected['uniform'],values)])
        accepted=all(r is not None and r['confirmed'] for values in selected.values() for r in values)
        result.append(dict(case_id=case,status='PRECISION_MATCHED_REPETITIONS' if accepted else 'UNVERIFIED',methods=methods,ratios=ratios,
            scope='two fixed repetitions only; null ratios for unsuccessful/limited pairs; no general superiority or continuous error bound'))
    return result


def error_rows(execution,record):
    if record is None:return
    for event,observation,item in zip(record['events'],record['observations'],record['event_records']):
        for order in observation['reference_orders']:
            accuracy=order['accuracy']
            for quantity,limit in LIMITS.items():
                yield dict(execution_id=execution['id'],case_id=execution['case_id'],method=execution['method'],repetition=execution['repetition'],
                    event_index=event['index'],parent_event_index=event['parent_event_index'],accepted=event['accepted'],refinement_kind=event['refinement_kind'],
                    dofs=event['dofs'],triangles=event['triangles'],gauss_order=order['order'],quantity=quantity,
                    relative_error=accuracy['relative_errors'][quantity],limit=limit,gate=accuracy['gates'][quantity],accuracy_status=accuracy['status'],
                    native_path_seconds=item['observed_prefix_cost']['native_path_cumulative_seconds'],submission_prefix_seconds=item['observed_prefix_cost']['submission_prefix_wall_seconds'],
                    physical_error_bound=None)
