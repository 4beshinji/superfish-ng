# SPDX-License-Identifier: Apache-2.0
"""Rebuild and verify affine FEM matrices and RF quantities from saved fields."""
import numpy as np
from .constants import C0,MU0,TAU
from .fem import assemble
from .high_order import assemble_p2
from .saved import read_solution
from .solver import Solution
from .rf import quantities


def read_verified_affine_solution(directory):
    saved=read_solution(directory)
    if saved.case.geometry_order!=1:raise ValueError('verified affine reader requires straight geometry')
    case=saved.case;space=saved.space
    k,m=assemble_p2(space) if space else assemble(saved.mesh)
    values=(TAU*saved.frequencies_hz/C0)**2;u=saved.u
    boundary=space.boundary_dofs if space else saved.mesh.boundary_edges
    fixed=np.unique(boundary[saved.mesh.boundary_tags=='magnetic_symmetry'])
    if np.any(u[fixed]!=0):raise ValueError('saved magnetic_symmetry field violates the essential constraint')
    free=np.setdiff1d(np.arange(len(u)),fixed)
    error=float(np.max(abs((MU0*np.pi/case.normalization_j)*(u.T@(m@u))-np.eye(case.modes))))
    if not np.isfinite(error) or error>1e-7:raise ValueError('saved affine normalization or orthogonality differs')
    residuals=[]
    for i,value in enumerate(values):
        ku,mu=(k@u[:,i])[free],(m@u[:,i])[free]
        residuals.append(float(np.linalg.norm(ku-value*mu)/(np.linalg.norm(ku)+value*np.linalg.norm(mu))))
    if not np.all(np.isfinite(residuals)) or max(residuals)>1e-7:raise ValueError('saved affine eigenpair residual exceeds 1e-7')
    solution=Solution(saved.mesh,k,m,values,saved.frequencies_hz,u,np.asarray(residuals),error,element_order=saved.element_order,space=space)
    for i,actual in enumerate(saved.results['modes']):
        expected=quantities(case,solution,i)
        if set(actual)!=set(expected):raise ValueError('saved affine RF keys differ')
        for key,value in expected.items():
            valid=(type(actual[key]) in (int,float) and np.isfinite(actual[key]) and np.isclose(actual[key],value,rtol=1e-10,atol=1e-12)) if isinstance(value,(int,float)) else actual[key]==value
            if not valid:raise ValueError(f'saved affine RF {key} differs from coefficients')
    solution.case=case;solution.results=saved.results
    return solution
