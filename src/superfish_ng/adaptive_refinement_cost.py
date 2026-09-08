# SPDX-License-Identifier: Apache-2.0
"""Observed job time for the native ancestry of an already verified checkpoint.

Timing is operational metadata, never numerical evidence. Do not search outside
the active manager workspace or infer missing durations from file timestamps.
"""
import math
from pathlib import Path
from .project import parse_json


def refinement_cost_summary(manager, result):
    groups = {}; unknown = []
    stem = 'event' if result['request']['schema_version'] == 5 else 'level'
    for index, run in enumerate(result['level_runs']):
        try:
            relative = Path(run).relative_to(manager.root)
            if (len(relative.parts) != 3 or relative.parts[1:] != ('execution', f'{stem}-{index+1:03d}')
                    or str(manager.root/relative) != run):
                raise ValueError('not a managed event path')
            identifier = relative.parts[0]
            directory = manager.directory(identifier)
            if (directory/'execution').is_symlink():
                raise ValueError('execution directory is a symlink')
            groups.setdefault(identifier, []).append(index)
        except ValueError:
            unknown.append(index)
    jobs = []
    for identifier, indices in groups.items():
        seconds = None; status = 'unavailable'; reason = None
        try:
            directory = manager.directory(identifier)
            for name in ('job.json', 'adaptive-refinement-request.json'):
                if (directory/name).is_symlink():
                    raise ValueError('job metadata is a symlink')
            data = parse_json((directory/'adaptive-refinement-request.json').read_text(encoding='utf-8'))
            previous = data['checkpoint']; offset = 0 if previous is None else len(previous['level_runs'])
            if (data['request'] != result['request'] or indices != list(range(offset, offset+len(indices)))
                    or (previous is not None and
                        (previous['level_runs'] != result['level_runs'][:offset]
                         or previous['sources'] != result['sources'][:offset]))):
                raise ValueError('job ancestry differs from the verified checkpoint')
            state = parse_json((directory/'job.json').read_text(encoding='utf-8'))
            status = state['status']
            if state.get('kind') != 'adaptive_refinement' or status not in ('complete', 'cancelled', 'failed', 'interrupted'):
                raise ValueError('no terminal adaptive job time')
            value = state.get('elapsed_seconds')
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError('elapsed time was not recorded as a finite nonnegative number')
            seconds = float(value)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            reason = str(exc)
        jobs.append(dict(id=identifier, event_indices=indices, status=status, elapsed_seconds=seconds,
                         unavailable_reason=reason))
    missing = sorted(unknown+[i for job in jobs if job['elapsed_seconds'] is None for i in job['event_indices']])
    return dict(recorded_seconds=math.fsum(job['elapsed_seconds'] for job in jobs if job['elapsed_seconds'] is not None),
                jobs=jobs, unknown_event_indices=missing, all_event_owners_timed=not missing,
                scope='Observed terminal times of distinct local jobs owning checkpoint fields. Includes all work in those jobs, even after this checkpoint; excludes separate attempts with no fields in this ancestry. Missing times are unknown, not zero. Timing metadata is not independently reproducible numerical evidence.')
