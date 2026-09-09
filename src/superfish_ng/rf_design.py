# SPDX-License-Identifier: Apache-2.0
"""RF design criteria on replayed, tracked fixed-geometry refinement evidence."""
from copy import deepcopy
import json
import math
from pathlib import Path
from .config import keys
from .project import parse_json
from .saved_mode_tracking import _canonical
from .surface_convergence import assess_surface_convergence, _ratio_interval


UNITS = dict(frequency_hz='Hz', r_over_q_accelerator_ohm='ohm',
    r_over_q_circuit_ohm='ohm', geometry_factor_ohm='ohm',
    epk_over_eacc='1', bpk_over_eacc_mt_per_mv_per_m='mT/(MV/m)')


def _number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def validate_design_criteria(criteria):
    """One explicitly directed objective and distinct inclusive RF constraints."""
    keys(criteria, ('schema_version', 'objective', 'constraints'),
         ('schema_version', 'objective', 'constraints'), 'RF design criteria')
    if type(criteria['schema_version']) is not int or criteria['schema_version'] != 1:
        raise ValueError('RF design criteria require schema_version 1')
    objective = criteria['objective']
    keys(objective, ('quantity', 'direction'), ('quantity', 'direction'), 'RF objective')
    if type(objective['quantity']) is not str or objective['quantity'] not in UNITS or objective['direction'] not in ('minimize', 'maximize'):
        raise ValueError('RF objective requires a supported quantity and minimize or maximize')
    constraints = criteria['constraints']
    if type(constraints) is not list or not constraints:
        raise ValueError('RF constraints must be a nonempty list')
    seen = set()
    for constraint in constraints:
        keys(constraint, ('quantity', 'lower', 'upper'), ('quantity',), 'RF constraint')
        quantity = constraint['quantity']
        if type(quantity) is not str or quantity not in UNITS or quantity in seen:
            raise ValueError('RF constraints require distinct supported quantities')
        seen.add(quantity)
        bounds = [constraint[name] for name in ('lower', 'upper') if name in constraint]
        if not bounds or any(not _number(v) or v < 0 for v in bounds):
            raise ValueError('RF constraint requires a finite nonnegative lower and/or upper bound')
        if len(bounds) == 2 and bounds[0] > bounds[1]:
            raise ValueError('RF constraint lower must not exceed upper')
    return deepcopy(criteria)


def _evaluate_design(criteria, assessment):
    """Internal predicate; public entry always reconstructs assessment from fields."""
    criteria = validate_design_criteria(criteria)
    recent = assessment['rows'][-3:]
    quantities = [criteria['objective']['quantity'], *[c['quantity'] for c in criteria['constraints']]]
    envelopes = {}
    for quantity in dict.fromkeys(quantities):
        values = []
        for row in recent:
            if quantity == 'r_over_q_circuit_ohm':
                source = row['intervals'].get('r_over_q_accelerator_ohm')
                interval = None if source is None else _ratio_interval(*source, 2.)
            else:
                interval = row['intervals'].get(quantity)
            if (interval is None or len(interval) != 2 or
                    any(not _number(v) or v < 0 for v in interval) or interval[0] > interval[1]):
                values = []
                break
            values.append(interval)
        envelopes[quantity] = ([min(v[0] for v in values), max(v[1] for v in values)]
                               if len(values) == 3 else None)
    checks = []
    for constraint in criteria['constraints']:
        interval = envelopes[constraint['quantity']]
        # The whole observed enclosure must fit. An overlapping enclosure is unresolved.
        if interval is None:
            status = 'UNVERIFIED'
        elif (('lower' not in constraint or interval[0] >= constraint['lower']) and
              ('upper' not in constraint or interval[1] <= constraint['upper'])):
            status = 'MET'
        elif (('lower' in constraint and interval[1] < constraint['lower']) or
              ('upper' in constraint and interval[0] > constraint['upper'])):
            status = 'VIOLATED'
        else:
            status = 'UNRESOLVED'
        checks.append(dict(constraint=deepcopy(constraint), unit=UNITS[constraint['quantity']],
                           observed_envelope=interval, status=status))
    objective = criteria['objective']; interval = envelopes[objective['quantity']]
    evidence_met = assessment['status'] == 'TARGETS_MET'
    if not evidence_met or interval is None or any(c['status'] == 'UNVERIFIED' for c in checks):
        status = 'UNVERIFIED'
    elif any(c['status'] == 'VIOLATED' for c in checks):
        status = 'CONSTRAINTS_VIOLATED'
    elif any(c['status'] == 'UNRESOLVED' for c in checks):
        status = 'CONSTRAINTS_UNRESOLVED'
    else:
        status = 'CRITERIA_MET'
    # Ineligible trials never receive an objective value that a search can prefer.
    value = None if status != 'CRITERIA_MET' else interval[1 if objective['direction'] == 'minimize' else 0]
    return dict(status=status, refinement_status=assessment['status'], constraints=checks,
        objective=dict(**objective, unit=UNITS[objective['quantity']], observed_envelope=interval,
                       eligible_value=value), observed_envelopes=envelopes)


def assess_rf_design(history, mode_id, criteria):
    """Assess one shape using three native mesh levels, not a claimed optimum."""
    criteria = validate_design_criteria(criteria)
    assessment = assess_surface_convergence(history, mode_id)
    decision = _evaluate_design(criteria, assessment)
    return dict(schema_version=1, document_type='rf_design_assessment', criteria=criteria,
        assessment=assessment, **decision, physical_error_bound=None,
        geometry_approximation_assessed=False,
        scope='one tracked native curved P2 shape; last three observed mesh enclosures and existing two-change RF/peak gates; empirical design criteria, not physical error certification, optimizer convergence or global optimality')


def save_rf_design(history, mode_id, criteria, path):
    result = assess_rf_design(history, mode_id, criteria)
    with Path(path).open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)+'\n')
    return result


def replay_rf_design(document):
    fields = ('schema_version', 'document_type', 'criteria', 'assessment', 'status',
              'refinement_status', 'constraints', 'objective', 'observed_envelopes',
              'physical_error_bound', 'geometry_approximation_assessed', 'scope')
    keys(document, fields, fields, 'RF design assessment')
    assessment = document['assessment']
    result = assess_rf_design(assessment['history'], assessment['mode_id'], document['criteria'])
    if _canonical(result) != _canonical(document):
        raise ValueError('RF design replay differs from saved data or sources')
    return result


def read_rf_design(path):
    return replay_rf_design(parse_json(Path(path).read_text(encoding='utf-8')))
