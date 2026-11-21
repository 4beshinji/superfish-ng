# SPDX-License-Identifier: Apache-2.0
"""Fixed RF-goal metrics and accepted-parent confirmation, without native solves.

These functions derive finite-sample gates. They neither authenticate saved
sources nor assign physical mode IDs. A worker must construct the observations
from verified full fields and replay the original native branches separately.
"""
from copy import deepcopy
import math

import numpy as np

from .adaptive_efficiency_accuracy import LIMITS, PEAKS, assess_efficiency_samples
from .surface_convergence import _interval_change


def _result(errors, sign=None, reason=None):
    if reason is not None:
        errors={key:None for key in LIMITS}
    gates={key:errors[key] is not None and errors[key]<=limit for key,limit in LIMITS.items()}
    return dict(status='UNVERIFIED' if reason is not None else 'PASS' if all(gates.values()) else 'FAIL',
                relative_errors=errors,gates=gates,limits=dict(LIMITS),common_hphi_sign=sign,
                unverified_reason=reason,physical_error_bound=None,
                scope='actual parent-to-child native sample changes; previous field norm, current/previous RF, both peak intervals; source/domain/ID verification remains external')


def assess_rf_goal_pair(previous, current):
    """Compare both native events on the same complete physical Gauss grid.

    Inputs contain fields (N,3), axis_ez (A,), weights (N,), axis_weights (A,),
    quantities and peak_intervals. All fields are already in the shared volume
    density convention. Never compare different quadrature grids pointwise.
    """
    try:
        for key in ('weights','axis_weights'):
            a=np.asarray(previous[key]);b=np.asarray(current[key])
            if (a.dtype.kind not in 'iuf' or b.dtype.kind not in 'iuf' or
                    not np.array_equal(a,b)):
                raise ValueError('native parent/child require identical full-grid '+key)
        for key in PEAKS:
            for entry in (previous,current):
                interval=entry['peak_intervals'][key]
                if (type(interval) not in (tuple,list) or len(interval)!=2 or
                        any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in interval) or
                        interval[0]>interval[1]):
                    raise ValueError('parent/child peak change requires both ordered finite positive endpoints')
        # The original sample metric supplies the common sign and original
        # parent field norm. RF scalars use current/previous instead. Its peak
        # diagnostic is replaced by the two-interval upper bound below.
        reference_quantities=dict(previous['quantities'])
        for key in PEAKS:
            reference_quantities[key]=previous['peak_intervals'][key][0]
        row=assess_efficiency_samples(previous['fields'],current['fields'],previous['weights'],
            previous['axis_ez'],current['axis_ez'],previous['axis_weights'],
            current['quantities'],reference_quantities,current['peak_intervals'])
        if row['status']=='UNVERIFIED':
            return _result({},row['common_hphi_sign'],row['unverified_reason'])
        errors=deepcopy(row['relative_errors'])
        for key in PEAKS:
            errors[key]=_interval_change(previous['peak_intervals'][key],current['peak_intervals'][key])
            if errors[key] is None:raise ValueError('parent/child peak interval change is unresolved')
        # A zero current field has a defined difference but cannot identify a
        # physical mode or supply a meaningful reciprocal confirmation.
        if (not np.any(current['fields']) or not np.any(current['axis_ez'])):
            raise ValueError('zero current field/physical axis leaves confirmation unverified')
        return _result(errors,row['common_hphi_sign'])
    except (ValueError,TypeError,KeyError,OverflowError) as error:
        return _result({},reason=str(error))


def assess_rf_goal_orders(orders):
    """Require both Gauss orders and consistent original nine scalar gates.

    Errors are recombined, never trusted from a supplied PASS flag alone. Field
    provenance and the underlying arrays are the caller's separate obligation.
    """
    if (type(orders) is not list or len(orders)!=2 or any(type(o) is not dict for o in orders) or
            any(type(o.get('order')) is not int for o in orders) or [o['order'] for o in orders]!=[16,24]):
        raise ValueError('RF goal assessment requires both ordered Gauss16/24 observations')
    verified=True;passed=True;errors=[]
    for order in orders:
        row=order.get('accuracy')
        if (type(row) is not dict or row.get('limits')!=LIMITS or
                type(row.get('relative_errors')) is not dict or set(row['relative_errors'])!=set(LIMITS) or
                type(row.get('gates')) is not dict or set(row['gates'])!=set(LIMITS) or
                any(type(v) is not bool for v in row['gates'].values())):
            raise ValueError('RF goal assessment requires complete original limits/errors/gates')
        values=row['relative_errors']
        if row.get('status')=='UNVERIFIED':
            if any(v is not None for v in values.values()) or any(row['gates'].values()):
                raise ValueError('UNVERIFIED RF goal observation must retain null errors and failed gates')
            verified=False;passed=False
        else:
            if any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in values.values()):
                raise ValueError('verified RF goal observations require finite nonnegative errors')
            gates={key:values[key]<=limit for key,limit in LIMITS.items()}
            expected='PASS' if all(gates.values()) else 'FAIL'
            if row.get('status')!=expected or row['gates']!=gates:
                raise ValueError('RF goal observation status/gates differ from actual errors')
            passed=passed and expected=='PASS'
        errors.append(values)
    differences={key:abs(errors[0][key]-errors[1][key]) for key in LIMITS} if verified else None
    order_gates={key:differences is not None and differences[key]<=limit for key,limit in LIMITS.items()}
    passed=passed and all(order_gates.values())
    return dict(status='UNVERIFIED' if not verified else 'PASS' if passed else 'FAIL',
                order_error_differences=differences,order_difference_gates=order_gates,
                orders=deepcopy(orders),limits=dict(LIMITS),physical_error_bound=None)


def assess_rf_goal_history(events, observations):
    """Derive first hits and two uniform edges on the actual accepted ancestry.

    Events are original public native rows, or separately recorded uniform
    continuation rows. Each observation binds its index, source_domain_identity
    status, both reference_orders and parent_change (parent_event_index/orders).
    Native stopping labels/counters never replace these independent conditions.
    This validates bookkeeping, not saved-field provenance or native replay.
    """
    if type(events) is not list or type(observations) is not list or len(events)!=len(observations):
        raise ValueError('RF goal history requires one observation for every original event')
    rows=[];accepted=[];first=None;rejected=None;confirmed=None;chain=None
    required=('index','parent_event_index','refinement_kind','accepted','status','current_mode_ids','mode_index','quadrature_check')
    for i,(event,observation) in enumerate(zip(events,observations)):
        if (type(event) is not dict or any(k not in event for k in required) or
                type(event['index']) is not int or event['index']!=i or type(event['accepted']) is not bool or
                event['status'] not in ('INITIAL','PASS','UNVERIFIED')):
            raise ValueError('RF goal history requires original ordered event indices and typed native status/acceptance')
        parent=event['parent_event_index'];kind=event['refinement_kind']
        if i==0:
            if parent is not None or kind!='initial':raise ValueError('initial RF event must have no parent')
        else:
            if type(parent) is not int or not accepted or parent!=accepted[-1]:
                raise ValueError('RF goal event must name the actual last accepted parent')
            if kind not in ('uniform_probe','rf_local','uniform_confirmation'):
                raise ValueError('RF goal event requires a known original refinement kind')
            last=events[i-1]
            rejected_probe=last['refinement_kind']=='uniform_probe' and not last['accepted']
            if rejected_probe != (kind=='rf_local') or (rejected_probe and parent!=last['parent_event_index']):
                raise ValueError('rejected uniform probe must branch locally from its original accepted parent')
        ids=event['current_mode_ids'];mode=event['mode_index']
        labels=[] if type(ids) is not list else [v for v in ids if v is not None]
        if (type(ids) is not list or not ids or any(type(v) is not str or not v for v in labels) or
                len(set(labels))!=len(labels) or
                (event['status']=='UNVERIFIED' and (mode is not None or event['accepted'])) or
                (event['status']!='UNVERIFIED' and (len(labels)!=len(ids) or type(mode) is not int or not 0<=mode<len(ids)))):
            raise ValueError('RF goal history requires explicit complete mode labels or an unaccepted UNVERIFIED event')
        if (type(observation) is not dict or set(observation)!=set(('index','source_domain_identity_status','reference_orders','parent_change')) or
                type(observation['index']) is not int or observation['index']!=i or
                observation['source_domain_identity_status'] not in ('PASS','UNVERIFIED')):
            raise ValueError('RF goal history observations must retain original indices and verification status')
        accuracy=assess_rf_goal_orders(observation['reference_orders'])
        change=observation['parent_change']
        if parent is None:
            if change is not None:raise ValueError('initial RF observation has no parent change')
            change_result=None
        else:
            if (type(change) is not dict or set(change)!=set(('parent_event_index','orders')) or
                    type(change['parent_event_index']) is not int or change['parent_event_index']!=parent):
                raise ValueError('RF goal change must compare its actual original parent')
            change_result=assess_rf_goal_orders(change['orders'])
        quadrature=event['quadrature_check']
        if quadrature is not None and (type(quadrature) is not dict or type(quadrature.get('passed')) is not bool):
            raise ValueError('RF goal history quadrature requires a typed passed result or null')
        accurate=(accuracy['status']=='PASS' and observation['source_domain_identity_status']=='PASS' and
                  event['status']!='UNVERIFIED' and quadrature is not None and quadrature['passed'])
        if accurate:
            if event['accepted'] and first is None:first=i
            if not event['accepted'] and rejected is None:rejected=i
        edge_pass=(event['accepted'] and kind in ('uniform_probe','uniform_confirmation') and
                   change_result is not None and change_result['status']=='PASS')
        candidate=None
        if edge_pass and parent is not None and rows[parent]['uniform_edge_passed']:
            grandparent=events[parent]['parent_event_index']
            if grandparent is not None and all(rows[k]['independent_accuracy_passed'] for k in (grandparent,parent)) and accurate:
                candidate=[grandparent,parent,i]
                if confirmed is None:confirmed=i;chain=candidate
        rows.append(dict(index=i,parent_event_index=parent,independent_accuracy_passed=accurate,
                         reference_accuracy=accuracy,parent_change=change_result,uniform_edge_passed=bool(edge_pass),
                         confirmation_event_indices=candidate))
        if event['accepted']:accepted.append(i)
    return dict(status='CONFIRMED' if confirmed is not None else 'NOT_CONFIRMED',events=rows,
                first_accuracy_hit_index=first,first_rejected_accuracy_hit_index=rejected,
                confirmed_accuracy_hit_index=confirmed,confirmation_event_indices=chain,
                accepted_event_indices=accepted,physical_error_bound=None,
                scope='finite benchmark confirmation on three accurate accepted ancestors and two uniform RF/peak/field edges; native status untouched; source/domain/ID and saved replay remain separate')
