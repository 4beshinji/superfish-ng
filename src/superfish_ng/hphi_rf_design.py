# SPDX-License-Identifier: Apache-2.0
"""Typed Hphi RF observations; a single saved FEM never establishes convergence."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
from .config import integer, keys
from .project import parse_json
from .rf_design import _number
from .hphi_native import hphi_case_from_dict, read_hphi_run, hphi_result


UNITS = dict(frequency_hz='Hz', geometry_factor_ohm='ohm', q0='1',
             wall_loss_w='W', r_over_q_accelerator_ohm='ohm', r_over_q_circuit_ohm='ohm')
_NATIVE_FILES = {'case.json', 'mesh.npz', 'fields.npz', 'results.json', 'manifest.json'}
_SCOPE = ('one fully reconstructed dedicated Hphi native observation; all PEC walls and original '
          'material regions retained; q0 means wall-loss-only Q; no individual mode identity, '
          'refinement acceptance, peak accuracy, search or continuum error certification')


def hphi_rf_capabilities(case):
    """Validate the original Case without FEM and disclose unavailable quantities."""
    case = hphi_case_from_dict(case.to_dict())
    has_axis_path = getattr(case, 'acceleration', None) is not None
    available = {name: unit for name, unit in UNITS.items()
                 if has_axis_path or not name.startswith('r_over_q_')}
    reason = 'no declared vacuum-axis acceleration path; the axis may be outside the RF domain'
    unavailable = {name: reason for name in UNITS if name not in available}
    unavailable.update(epk_over_eacc='converged dedicated surface peak evaluation is not implemented',
        bpk_over_eacc_mt_per_mv_per_m='converged dedicated surface peak evaluation is not implemented',
        total_q='only normal-metal wall loss is implemented; volume/complex loss is not accepted',
        volume_loss_w='lossless-material input does not implement an additional volume-loss model',
        stored_energy_j='stored energy is fixed input normalization, not a free design objective')
    return dict(available=available, unavailable=unavailable, q0_loss_model='wall_only',
                normalization_j=case.normalization_j)


def validate_hphi_rf_criteria(case, criteria):
    """Reject inapplicable or unimplemented quantities before any solve/replay."""
    capability = hphi_rf_capabilities(case)
    keys(criteria, ('schema_version', 'objective', 'constraints'),
         ('schema_version', 'objective', 'constraints'), 'Hphi RF criteria')
    if type(criteria['schema_version']) is not int or criteria['schema_version'] != 1:
        raise ValueError('Hphi RF criteria require schema_version 1')
    def quantity(value):
        if type(value) is not str or value not in capability['available']:
            reason = capability['unavailable'].get(value, 'unknown quantity') if type(value) is str else 'quantity must be a string'
            raise ValueError(f'Hphi RF quantity {value!r}: {reason}; available: '+', '.join(capability['available']))
    objective = criteria['objective']
    keys(objective, ('quantity', 'direction'), ('quantity', 'direction'), 'Hphi RF objective')
    quantity(objective['quantity'])
    if objective['direction'] not in ('minimize', 'maximize'):
        raise ValueError('Hphi RF objective requires explicit minimize or maximize')
    constraints = criteria['constraints']
    if type(constraints) is not list or not constraints:
        raise ValueError('Hphi RF constraints must be a nonempty list')
    seen = set()
    for constraint in constraints:
        keys(constraint, ('quantity', 'lower', 'upper'), ('quantity',), 'Hphi RF constraint')
        name = constraint['quantity']; quantity(name)
        if name in seen: raise ValueError('Hphi RF constraints require distinct quantities')
        seen.add(name)
        bounds = [constraint[k] for k in ('lower', 'upper') if k in constraint]
        if not bounds or any(not _number(x) or x < 0 for x in bounds):
            raise ValueError('Hphi RF constraints require finite nonnegative inclusive bounds')
        if len(bounds) == 2 and bounds[0] > bounds[1]:
            raise ValueError('Hphi RF constraint lower must not exceed upper')
    return deepcopy(criteria)


def _snapshot(directory):
    if directory.is_symlink() or not directory.is_dir() or {p.name for p in directory.iterdir()} != _NATIVE_FILES:
        raise ValueError('Hphi RF observation requires a complete regular five-file native directory')
    result = {}
    for name in sorted(_NATIVE_FILES):
        path = directory/name
        if path.is_symlink() or not path.is_file(): raise ValueError('Hphi RF native files must be regular, not linked')
        result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def observe_hphi_rf_design(directory, criteria, mode_rank=1):
    """Reconstruct FEM and all RF; report every constraint as numerically unverified."""
    directory = Path(directory)
    before = _snapshot(directory)
    directory = directory.resolve()
    case = hphi_case_from_dict(parse_json((directory/'case.json').read_text(encoding='utf-8')))
    criteria = validate_hphi_rf_criteria(case, criteria)
    integer(mode_rank, 'Hphi RF positive frequency rank', 1)
    if mode_rank > case.modes: raise ValueError('Hphi RF mode_rank exceeds the saved positive spectrum')
    # Capability/rank errors above do not enter matrix reconstruction or RF evaluation.
    solution = read_hphi_run(directory)
    if solution.case.to_dict() != case.to_dict(): raise ValueError('Hphi RF Case changed before reconstruction')
    native = hphi_result(solution); rf = native['modes'][mode_rank-1]
    capabilities = hphi_rf_capabilities(case)
    observations = {}
    for name, unit in capabilities['available'].items():
        value = rf[name]
        if not _number(value) or value < 0 or (name in ('frequency_hz', 'q0', 'geometry_factor_ohm', 'wall_loss_w') and value == 0):
            raise ValueError('Hphi RF reconstructed quantity is invalid: '+name)
        observations[name] = dict(value=value, unit=unit)
    if before != _snapshot(directory): raise ValueError('Hphi RF native changed during observation')
    return dict(schema_version=1, document_type='hphi_rf_design_observation', native_run=str(directory),
        native_sha256=before, case=case.to_dict(), criteria=criteria, mode_rank=mode_rank,
        mode_identity=None, capabilities=capabilities, observations=observations, rf=rf,
        conventions=native['conventions'], status='UNVERIFIED', refinement_status='UNVERIFIED',
        constraints=[dict(constraint=deepcopy(c), unit=UNITS[c['quantity']], observed_envelope=None,
                          status='UNVERIFIED') for c in criteria['constraints']],
        objective=dict(**criteria['objective'], unit=UNITS[criteria['objective']['quantity']],
                       observed_envelope=None, eligible_value=None),
        reason='a single native has no independently verified three-level field/identity/RF convergence',
        physical_error_bound=None, scope=_SCOPE)


def save_hphi_rf_design(directory, criteria, path, mode_rank=1):
    """Save an observation with a relative native reference; never overwrite a file."""
    path = Path(path)
    if path.parent.resolve() == Path(directory).resolve():
        raise ValueError('Hphi RF observation must be saved outside the immutable native directory')
    report = observe_hphi_rf_design(directory, criteria, mode_rank)
    report['native_run'] = os.path.relpath(report['native_run'], path.parent.resolve())
    if report['native_sha256'] != _snapshot(Path(directory)):
        raise ValueError('Hphi RF native changed before observation publication')
    with path.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False, allow_nan=False); stream.write('\n')
    return report


def read_hphi_rf_design(path):
    """Reconstruct every native quantity and compare the entire saved observation."""
    path = Path(path); document = parse_json(path.read_text(encoding='utf-8'))
    if not isinstance(document, dict) or type(document.get('native_run')) is not str:
        raise ValueError('expected a Hphi RF observation with a native_run reference')
    expected = observe_hphi_rf_design(path.parent/document['native_run'], document.get('criteria'), document.get('mode_rank'))
    expected['native_run'] = document['native_run']
    canonical = lambda value: json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)
    if canonical(expected) != canonical(document):
        raise ValueError('Hphi RF observation differs from fully reconstructed native evidence')
    return expected
