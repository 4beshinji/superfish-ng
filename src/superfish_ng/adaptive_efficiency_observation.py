# SPDX-License-Identifier: Apache-2.0
"""Serial worker-only observation of selected existing function bindings.

Functions receive their original arguments and return their original objects.
Observation overhead is measured, not subtracted or presented as solver-only
performance. This context changes no function code or persisted scientific data.
"""
from contextlib import contextmanager
from functools import wraps
import types


def _wrapper(recorder, original, phase_name):
    @wraps(original)
    def observed(*args, **kwargs):
        with recorder.phase(phase_name):
            return original(*args, **kwargs)
    observed._adaptive_efficiency_observer = True
    return observed


@contextmanager
def observe_selected_calls(recorder, bindings):
    """Observe explicitly selected (module, attribute, phase) bindings, then restore.

    Use only in a fresh serial N06 worker. Every alias must be explicitly listed;
    this is not a profiler or a claim that unlisted calls have been measured.
    Conflicting outside replacements are preserved and make closure unverified.
    """
    recorder._require_owner()
    if type(bindings) not in (tuple, list) or not bindings:
        raise ValueError('bindings require a nonempty list of module/attribute/phase tuples')
    selected = []
    keys = set()
    names = {}
    for row in bindings:
        if type(row) not in (tuple, list) or len(row) != 3:
            raise ValueError('each observed binding requires module, attribute and phase name')
        module, attribute, phase = row
        if not isinstance(module, types.ModuleType) or type(attribute) is not str or not attribute:
            raise ValueError('observed binding requires a module and named existing attribute')
        if type(phase) is not str or not phase or phase.strip() != phase:
            raise ValueError('phase name must be nonempty without surrounding whitespace')
        key = (id(module), attribute)
        if key in keys:
            raise ValueError('duplicate observed module/attribute binding')
        keys.add(key)
        original = getattr(module, attribute, None)
        if not callable(original) or getattr(original, '_adaptive_efficiency_observer', False):
            raise ValueError('observed attribute must be an original callable, without nested observers')
        identity = id(original)
        if identity in names and names[identity] != phase:
            raise ValueError('aliases of one callable must use the same observed phase name')
        names[identity] = phase
        selected.append((module, attribute, original, _wrapper(recorder, original, phase)))
    installed = []
    failure = None
    try:
        for module, attribute, original, observed in selected:
            setattr(module, attribute, observed)
            installed.append((module, attribute, original, observed))
        yield
    except BaseException as error:
        failure = error
        raise
    finally:
        recorder._require_owner()
        conflicts = []
        for module, attribute, original, observed in reversed(installed):
            if getattr(module, attribute, None) is observed:
                setattr(module, attribute, original)
            else:
                conflicts.append(module.__name__ + '.' + attribute)
        if conflicts:
            message = 'observed binding changed outside its serial context: ' + ', '.join(conflicts)
            if failure is None:
                raise ValueError(message)
            if hasattr(failure, 'add_note'):
                failure.add_note(message)
