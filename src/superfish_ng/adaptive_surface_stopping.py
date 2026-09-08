# SPDX-License-Identifier: Apache-2.0
"""Continuous discrete peak intervals for version 3 affine adaptive stopping."""
from fractions import Fraction
from .constants import MU0
from .affine_corners import classify_affine_corners
from .affine_extrema import bound_affine_surface_peaks
from .surface_convergence import _ratio_interval,_interval_change

QUANTITIES=('epk_over_eacc','bpk_over_eacc_mt_per_mv_per_m')


def surface_intervals(case,solution,mode):
    peaks=bound_affine_surface_peaks(case,solution,mode)
    q=solution.results['modes'][mode];electric=magnetic=None
    if q['epk_over_eacc_estimate'] is not None and q['bpk_over_eacc_estimate_mt_per_mv_per_m'] is not None and q['eacc_v_per_m']>0:
        electric=_ratio_interval(peaks['electric_v_per_m']['lower_bound'],peaks['electric_v_per_m']['upper_bound'],q['eacc_v_per_m'])
        magnetic=_ratio_interval(peaks['magnetic_a_per_m']['lower_bound'],peaks['magnetic_a_per_m']['upper_bound'],q['eacc_v_per_m'],factor=Fraction(MU0)*10**9)
    return dict(intervals=dict(zip(QUANTITIES,(electric,magnetic))),peaks=peaks,geometry_diagnostic=classify_affine_corners(case))


def surface_changes(levels,limits):
    changes=[]
    for a,b in zip(levels[-3:],levels[-2:]) if len(levels)>=3 else []:
        row={}
        for key in QUANTITIES:
            value=_interval_change(a['surface']['intervals'][key],b['surface']['intervals'][key])
            row[key]=dict(relative_change_upper_bound=value,limit=limits[key],passed=value is not None and value<=limits[key])
        changes.append(row)
    return changes
