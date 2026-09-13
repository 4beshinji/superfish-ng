# SPDX-License-Identifier: Apache-2.0
"""Deterministic damped Newton controls and retained nonlinear magnetic failures."""
from dataclasses import dataclass
import copy
import numpy as np
from scipy.sparse.linalg import spsolve
from .config import keys,integer,positive


@dataclass(frozen=True)
class MagneticNewtonControls:
    max_iterations: int=40
    relative_residual_tolerance: float=1e-11
    max_backtracks: int=30
    backtrack_factor: float=.5
    armijo_factor: float=1e-4

    def __post_init__(self):
        for name in ('max_iterations','max_backtracks'):
            integer(getattr(self,name),name)
            if not 1<=getattr(self,name)<=1000:raise ValueError(name+' must be from 1 to 1000')
        for name in ('relative_residual_tolerance','backtrack_factor','armijo_factor'):
            object.__setattr__(self,name,positive(getattr(self,name),name))
        if self.relative_residual_tolerance>1e-10:raise ValueError('magnetic relative_residual_tolerance must be at most 1e-10 to retain discrete physical checks')
        if not self.backtrack_factor<1.:raise ValueError('backtrack_factor must be less than 1')
        if not self.armijo_factor<.5:raise ValueError('armijo_factor must be less than 0.5')

    def to_dict(self):return dict(max_iterations=self.max_iterations,relative_residual_tolerance=self.relative_residual_tolerance,max_backtracks=self.max_backtracks,backtrack_factor=self.backtrack_factor,armijo_factor=self.armijo_factor)

    @classmethod
    def from_dict(cls,data):
        names=['max_iterations','relative_residual_tolerance','max_backtracks','backtrack_factor','armijo_factor'];keys(data,names,names,'magnetic Newton controls');return cls(**data)


class MagneticNonlinearFailure(ValueError):
    def __init__(self,reason,detail,context,controls,history,last_valid,*,coefficient_field=None):
        super().__init__('nonlinear magnetic solve failed: '+reason+'; '+detail)
        self.report=dict(format='superfish_ng_magnetic_nonlinear_failure',schema_version=1,status='failed',reason=reason,detail=detail,
            context=copy.deepcopy(context),controls=controls.to_dict(),history=copy.deepcopy(history))
        values=None if last_valid is None else np.asarray(last_valid).tolist()
        if coefficient_field is None:
            # Preserve the existing planar relative-Az failure format exactly.
            self.report['last_valid_relative_coefficients']=values
        elif coefficient_field=='aphi_over_r_t':
            self.report.update(schema_version=2,coefficient_field=coefficient_field,last_valid_coefficients=values)
        else:raise ValueError('unsupported nonlinear failure coefficient_field')


def damped_magnetic_newton(assemble,initial,free,load,controls,*,energy_key,context,coefficient_field=None):
    """Solve free-DOF internal_load=load using the true material tangent.

    The caller supplies physical coefficient/residual/energy units in context.
    Failed trial states never replace the last valid coefficients. Accepted
    objectives include a roundoff allowance; residual convergence is separate.
    No elapsed times enter the reproducible iteration history.
    """
    if type(controls) is not MagneticNewtonControls:raise ValueError('explicit MagneticNewtonControls required')
    if coefficient_field not in (None,'aphi_over_r_t'):raise ValueError('unsupported nonlinear failure coefficient_field')
    coefficients=np.asarray(initial,dtype=float).copy();history=[];last_valid=None
    def fail(reason,detail):raise MagneticNonlinearFailure(reason,detail,context,controls,history,last_valid,coefficient_field=coefficient_field)
    def evaluate(values):
        k,g,q=assemble(values);energy=float(q[energy_key]);objective=energy-float(values@load)
        scale=float(np.linalg.norm(g)+np.linalg.norm(load));norm=float(np.linalg.norm((g-load)[free]));residual=norm/scale if scale else norm
        if not np.isfinite([energy,objective,scale,norm,residual]).all():raise ValueError('nonlinear objective or residual exceeds finite arithmetic')
        return k,g,q,energy,objective,scale,norm,residual
    try:state=evaluate(coefficients)
    except ValueError as exc:fail('invalid_initial_field',str(exc)+'; supply a feasible initial field or a valid wider material table')
    last_valid=coefficients.copy()
    for iteration in range(controls.max_iterations+1):
        k,g,q,energy,objective,scale,norm,residual=state
        history.append(dict(event='iterate',iteration=iteration,energy=energy,objective=objective,residual_norm=norm,residual_scale=scale,relative_residual=residual))
        if residual<=controls.relative_residual_tolerance:
            return coefficients,k,g,q,residual,dict(status='converged',iterations=iteration,controls=controls.to_dict(),history=history,
                residual_unit=context['residual_unit'],coefficient_unit=context['coefficient_unit'],energy_unit=context['energy_unit'],
                interpretation='algebraic convergence of the declared nonlinear FEM; no field discretization-error bound')
        if iteration==controls.max_iterations:fail('iteration_limit','residual tolerance was not reached')
        direction=np.zeros_like(coefficients)
        try:direction[free]=spsolve(k[free][:,free],-(g-load)[free])
        except (ValueError,RuntimeError) as exc:fail('tangent_solve',str(exc))
        descent=float((g-load)@direction)
        if not np.isfinite(direction).all() or not np.isfinite(descent) or descent>=0.:fail('invalid_newton_direction','finite descent with the material tangent was not obtained')
        alpha=1.;accepted=False
        for attempt in range(controls.max_backtracks):
            trial=coefficients+alpha*direction
            if not np.isfinite(trial).all():
                history.append(dict(event='trial',iteration=iteration+1,attempt=attempt,step_fraction=alpha,accepted=False,reason='nonfinite_coefficients'))
                alpha*=controls.backtrack_factor;continue
            if np.array_equal(trial,coefficients):fail('stagnation','Newton update is not representable before residual convergence')
            try:trial_state=evaluate(trial)
            except ValueError as exc:
                history.append(dict(event='trial',iteration=iteration+1,attempt=attempt,step_fraction=alpha,accepted=False,reason='invalid_material_trial',detail=str(exc)))
                alpha*=controls.backtrack_factor;continue
            _,_,_,trial_energy,trial_objective,_,_,trial_residual=trial_state
            # Subtract source work on the increment, avoiding a large fixed
            # reference contribution in the objective difference.
            delta=trial-coefficients;difference=trial_energy-energy-float(delta@load)
            rounding=32*np.finfo(float).eps*(abs(trial_energy)+abs(energy)+float(abs(delta)@abs(load)))
            sufficient=controls.armijo_factor*alpha*descent
            if not np.isfinite([difference,rounding,sufficient]).all():fail('line_search_arithmetic','objective decrease or its rounding scale is nonfinite')
            accepted=bool(difference<=sufficient+rounding)
            history.append(dict(event='trial',iteration=iteration+1,attempt=attempt,step_fraction=alpha,accepted=accepted,
                reason='armijo_with_roundoff' if accepted else 'insufficient_objective_decrease',objective=trial_objective,
                objective_difference=difference,armijo_bound=sufficient,roundoff_allowance=rounding,relative_residual=trial_residual))
            if accepted:coefficients=trial;state=trial_state;last_valid=coefficients.copy();break
            alpha*=controls.backtrack_factor
        if not accepted:fail('line_search_limit','no feasible trial met the objective decrease condition; inspect material range and retained trials')
    raise AssertionError('unreachable Newton state')
