# SPDX-License-Identifier: Apache-2.0
"""Observe the original adjoint's SuperLU C call without changing its objects."""
from contextlib import contextmanager
from functools import wraps
import sys

from scipy.sparse.linalg import SuperLU

from . import curved_rf_adjoint


C_CALLS=[dict(module='superfish_ng.curved_rf_adjoint',function='r_over_q_adjoint',
              c_type='SuperLU',method='solve',phase='adjoint_linear_solve',
              scope='current serial Python thread; original C-call entry/return/exception plus observer overhead; C exception class unavailable')]


class C_EXCEPTION_TYPE_UNAVAILABLE(BaseException):
    """Timing metadata sentinel only; never raised into the original caller."""


@contextmanager
def _profile_selected_callers(recorder, *, callers):
    """Use CPython C-call events in named original Python caller frames only.

    No SuperLU instance or method is replaced. Other solvers and threads are
    outside this scope. Existing or conflicting profilers are never overwritten.
    """
    recorder._require_owner()
    if sys.getprofile() is not None:raise ValueError('RF C-call observation requires a serial thread without an existing profiler')
    if type(callers) not in (list,tuple) or not callers or any(not hasattr(f,'__code__') for f in callers):
        raise ValueError('RF C-call observation requires explicit original Python caller functions')
    codes={f.__code__ for f in callers};active=[];failure=None
    def profile(frame,event,argument):
        if (frame.f_code not in codes or event not in ('c_call','c_return','c_exception') or
                getattr(argument,'__name__',None)!='solve' or not isinstance(getattr(argument,'__self__',None),SuperLU)):
            return
        if event=='c_call':
            phase=recorder.phase('adjoint_linear_solve');phase.__enter__();active.append(phase)
        else:
            if not active:raise ValueError('RF C-call return lacks its original observed entry')
            phase=active.pop()
            if event=='c_exception':
                marker=C_EXCEPTION_TYPE_UNAVAILABLE('Python profiler does not expose the C exception object')
                phase.__exit__(type(marker),marker,None)
            else:phase.__exit__(None,None,None)
    sys.setprofile(profile)
    try:yield
    except BaseException as error:
        failure=error;raise
    finally:
        recorder._require_owner()
        conflict=sys.getprofile() is not profile
        if not conflict:sys.setprofile(None)
        while active:
            phase=active.pop();marker=C_EXCEPTION_TYPE_UNAVAILABLE('C-call observation ended without a terminal event')
            phase.__exit__(type(marker),marker,None)
        if conflict:
            message='RF C-call profiler changed outside its serial observation context'
            if failure is None:raise ValueError(message)
            if hasattr(failure,'add_note'):failure.add_note(message)


@contextmanager
def observe_adjoint_linear_solves(recorder, *, callers=None):
    """Enable the C profiler only while an actual original adjoint is running.

    The explicit callers option is for isolated boundary tests. Production
    observes both original adjoint aliases without profiling unrelated FEM,
    full-field sampling, serialization or reference preparation.
    """
    if callers is not None:
        with _profile_selected_callers(recorder,callers=callers):yield
        return
    from . import curved_rf_goal_indicator
    recorder._require_owner()
    if sys.getprofile() is not None:raise ValueError('RF C-call observation requires a serial thread without an existing profiler')
    originals=[(m,m.r_over_q_adjoint) for m in (curved_rf_adjoint,curved_rf_goal_indicator)]
    wrappers={}
    for _,original in originals:
        if (not hasattr(original,'__code__') or getattr(original,'_rf_c_call_observer',False) or
                getattr(original,'_adaptive_efficiency_observer',False)):
            raise ValueError('RF C-call observation requires original adjoint aliases before other observers')
        if original in wrappers:continue
        def wrap(function):
            @wraps(function)
            def observed(*args,**kwargs):
                with _profile_selected_callers(recorder,callers=(function,)):return function(*args,**kwargs)
            observed._rf_c_call_observer=True
            return observed
        wrappers[original]=wrap(original)
    installed=[];failure=None
    try:
        for module,original in originals:
            module.r_over_q_adjoint=wrappers[original];installed.append((module,original))
        yield
    except BaseException as error:
        failure=error;raise
    finally:
        recorder._require_owner();conflicts=[]
        for module,original in reversed(installed):
            if module.r_over_q_adjoint is wrappers[original]:module.r_over_q_adjoint=original
            else:conflicts.append(module.__name__+'.r_over_q_adjoint')
        if sys.getprofile() is not None:conflicts.append('current thread profiler')
        if conflicts:
            message='RF C-call observation changed outside its serial context: '+', '.join(conflicts)
            if failure is None:raise ValueError(message)
            if hasattr(failure,'add_note'):failure.add_note(message)
