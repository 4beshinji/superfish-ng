# SPDX-License-Identifier: Apache-2.0
"""N05 quantity-specific sample metrics; source/domain/ID checks remain external.

The denominator is the original native field norm, as in N03's retained finite
Gauss diagnostics. One sign comes from Hphi and applies to both E components
and the physical axis. No amplitude fitting, cropping or missing-node removal.
"""
import math
import numpy as np


LIMITS = dict(frequency_hz=1e-4, r_over_q_accelerator_ohm=.005,
              r_over_q_circuit_ohm=.005, geometry_factor_ohm=.005,
              epk_over_eacc=.01, bpk_over_eacc_mt_per_mv_per_m=.01,
              electric_relative_l2=.005, magnetic_relative_l2=.005,
              axis_ez_relative_l2=.01)
RF = ('frequency_hz', 'r_over_q_accelerator_ohm', 'r_over_q_circuit_ohm', 'geometry_factor_ohm')
PEAKS = ('epk_over_eacc', 'bpk_over_eacc_mt_per_mv_per_m')


def _array(value, shape, name):
    array = np.asarray(value)
    if array.dtype.kind not in 'iuf' or array.shape != shape or not np.isfinite(array).all():
        raise ValueError(name + ' requires complete finite real samples in the declared shape')
    return array.astype(float, copy=False)


def _positive(value, name):
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError(name + ' requires a finite positive scalar')
    return float(value)


def _nonnegative(value, name):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError(name + ' requires a finite nonnegative scalar')
    return float(value)


def _error(native, reference, weights, sign):
    # Common scaling avoids overflow; it changes neither amplitude ratio nor
    # the native-norm denominator. Inputs are never modified or fitted.
    scale = max(float(np.max(abs(native))), float(np.max(abs(reference))))
    if not scale > 0:
        raise ValueError('zero field norm is unverified')
    a, b = native/scale, reference/scale
    w = weights/float(np.max(weights))
    if np.any(w <= 0):
        raise ValueError('weight scaling lost a supplied node; sample metric is unverified')
    denominator = float(np.sum(w*a*a))
    if not denominator > 0:
        raise ValueError('zero native field norm is unverified')
    value = float(np.sqrt(np.sum(w*(a-sign*b)**2)/denominator))
    if not math.isfinite(value):
        raise ValueError('nonfinite field difference is unverified')
    return value


def assess_efficiency_samples(native_fields, reference_fields, volume_weights,
                              native_axis_ez, reference_axis_ez, axis_weights,
                              native_quantities, reference_quantities, native_peak_intervals):
    """Compare full supplied samples (Er, Ez, Hphi), both R/Q and peak endpoints.

    PASS is a sample-metric result only. The caller must independently bind
    whole-domain coverage, original fields/units, actual IDs and reference data.
    Invalid/missing observations return UNVERIFIED/null, never fake zero error.
    """
    errors = {}
    gates = {}
    sign = None
    reason = None
    try:
        raw = np.asarray(native_fields)
        if raw.ndim != 2 or raw.shape[1] != 3 or not len(raw):
            raise ValueError('native_fields requires nonempty N by 3 (Er, Ez, Hphi) samples')
        native = _array(raw, raw.shape, 'native_fields')
        reference = _array(reference_fields, raw.shape, 'reference_fields')
        weights = _array(volume_weights, (len(raw),), 'volume_weights')
        axis = np.asarray(native_axis_ez)
        if axis.ndim != 1 or not len(axis):
            raise ValueError('physical axis requires complete nonempty Ez samples')
        own_axis = _array(axis, axis.shape, 'native_axis_ez')
        ref_axis = _array(reference_axis_ez, axis.shape, 'reference_axis_ez')
        axis_w = _array(axis_weights, axis.shape, 'axis_weights')
        if np.any(weights <= 0) or np.any(axis_w <= 0):
            raise ValueError('all volume and axis weights must be positive; no discarded nodes')
        for values in (native[:,2], reference[:,2]):
            if not np.any(values):
                raise ValueError('zero Hphi norm cannot determine a common field sign')
        hscale = max(float(np.max(abs(native[:,2]))), float(np.max(abs(reference[:,2]))))
        signed_overlap = float(np.dot(weights/np.max(weights), (native[:,2]/hscale)*(reference[:,2]/hscale)))
        if not math.isfinite(signed_overlap) or signed_overlap == 0:
            raise ValueError('zero or nonfinite Hphi overlap leaves common sign unverified')
        sign = 1 if signed_overlap > 0 else -1
        errors['electric_relative_l2'] = _error(native[:,:2], reference[:,:2], weights[:,None], sign)
        errors['magnetic_relative_l2'] = _error(native[:,2], reference[:,2], weights, sign)
        errors['axis_ez_relative_l2'] = _error(own_axis, ref_axis, axis_w, sign)
        for name in RF:
            a = _positive(native_quantities[name], 'native '+name)
            b = _positive(reference_quantities[name], 'reference '+name)
            errors[name] = abs(a/b-1)
        for source in (native_quantities, reference_quantities):
            a = _positive(source['r_over_q_accelerator_ohm'], 'accelerator R/Q')
            b = _positive(source['r_over_q_circuit_ohm'], 'circuit R/Q')
            if abs(a/(2*b)-1) > 1e-12:
                raise ValueError('both R/Q definitions must retain their factor-two convention')
        for name in PEAKS:
            target = _positive(reference_quantities[name], 'reference '+name)
            interval = native_peak_intervals[name]
            if type(interval) not in (list, tuple) or len(interval) != 2:
                raise ValueError('native '+name+' requires both discrete peak interval endpoints')
            a, b = (_nonnegative(v, 'peak interval endpoint') for v in interval)
            if a > b:
                raise ValueError('peak interval endpoints must be ordered')
            errors[name] = max(abs(a/target-1), abs(b/target-1))
        if not all(math.isfinite(v) for v in errors.values()):
            raise ValueError('nonfinite observed relative error')
        gates = {name: errors[name] <= limit for name, limit in LIMITS.items()}
        status = 'PASS' if all(gates.values()) else 'FAIL'
    except (ValueError, TypeError, KeyError, OverflowError) as error:
        status, reason = 'UNVERIFIED', str(error)
        # A partial computation must not pass absent quantities or nodes.
        errors = {name: None for name in LIMITS}
        gates = {name: False for name in LIMITS}
    return dict(status=status, relative_errors=errors, gates=gates, limits=dict(LIMITS),
                common_hphi_sign=sign, unverified_reason=reason, physical_error_bound=None,
                physical_acceptance_status='SOURCE_DOMAIN_REFERENCE_CHECKS_REQUIRED',
                scope='finite supplied full-sample diagnostic; original native-norm field denominator, '
                      'one Hphi sign for E/H/axis, both R/Q conventions, worst peak endpoints; '
                      'no fit/crop/missing-node removal; caller must verify source/domain/IDs/reference provenance')
