# SPDX-License-Identifier: Apache-2.0
"""Scalar expression tuning on value-selected native mesh partitions."""
from copy import deepcopy
from .curved_partition_schedule import build_partition_schedule,partition_index,partition_comparison_mesh
from .expression_tuning import trial_project as expression_project
from .saved_mode_tracking import validate_tracking_controls


def validate_request(request,project):
    if request['geometry_kind']!='curved_harmonic':
        raise ValueError('partition tune requires geometry_kind curved_harmonic')
    scale=request['refinement_scale']
    if scale & (scale-1):raise ValueError('partition tune refinement_scale must be a power of two')
    controls=request['controls']
    if not isinstance(controls,dict) or controls.get('mapping')!='piecewise_remesh' or 'comparison_meshes' in controls:
        raise ValueError('partition tune requires piecewise_remesh controls without comparison_meshes')
    # All alternatives must be valid even if the current bounds skip an interval.
    candidates=build_partition_schedule(project,request['mesh_schedule'])
    schedule=request['mesh_schedule']
    first=partition_comparison_mesh(candidates[0],schedule['partitions'][0],schedule['max_pair_tests'])
    validate_tracking_controls(dict(controls,comparison_meshes=[first,first]))


def trial_project(request,project,value,phase):
    schedule=request['mesh_schedule']
    candidates=build_partition_schedule(project,schedule)
    seed=candidates[partition_index(schedule,value)]
    # The selected seed supplies chord counts and its explicitly new history.
    # Expression evaluation starts with that seed, never the original counts.
    return expression_project(request,seed,value,phase)


def pair_controls(request,previous_value,current_value,previous,current):
    """Bind charts to the actual two native Projects, including refinement.

    An accepted endpoint or identity-recovery anchor can use a different initial
    partition from the preceding trial. Values select each side independently.
    Each comparison reproduces that side's actual full quadratic history.
    """
    schedule=request['mesh_schedule'];result=deepcopy(request['controls'])
    result['comparison_meshes']=[partition_comparison_mesh(project,
        schedule['partitions'][partition_index(schedule,value)],schedule['max_pair_tests'])
        for project,value in ((previous,previous_value),(current,current_value))]
    validate_tracking_controls(result)
    return result
