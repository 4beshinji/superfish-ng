# SPDX-License-Identifier: Apache-2.0
"""Curved-P2 solve and mapped-cell field evaluation."""
from dataclasses import dataclass,replace
import numpy as np
from scipy.sparse import diags
from scipy.sparse.linalg import eigsh,ArpackNoConvergence
from .constants import C0,MU0,EPS0,TAU
from .curved_space import case_curved_space
from .curved_fem import assemble_curved
from .mesh import make_mesh
from .mesh_input import mesh_from_dict,mesh_to_dict


@dataclass
class CurvedSolution:
    case: object
    space: object
    stiffness: object
    mass: object
    eigenvalues: np.ndarray
    frequencies_hz: np.ndarray
    u: np.ndarray
    residuals: np.ndarray
    orthogonality_error: float
    quadrature_order: int
    source_mesh_data: object
    reflection_source_case: object = None

    @property
    def element_order(self):
        return 2

    def fields_in_cell(self,cell,reference_points,mode=0):
        """Evaluate the physical fields at supplied reference coordinates."""
        if type(cell) is not int or not 0<=cell<len(self.space.geometry.local_maps):
            raise ValueError('cell must be a valid zero-based integer')
        if type(mode) is not int or not 0<=mode<len(self.frequencies_hz):
            raise ValueError('mode must be a valid zero-based integer')
        mapping = self.space.geometry.local_maps[cell]
        result = mapping.evaluate(reference_points)
        coefficients = self.u[self.space.geometry.cell_nodes[cell],mode]
        value = result['basis_values']@coefficients
        gradient = np.einsum('qia,i->qa',result['basis_gradients'],coefficients)
        radius = result['points_rz_m'][:,0]
        omega = TAU*self.frequencies_hz[mode]
        return dict(points_rz_m=result['points_rz_m'],
                    Hphi_A_per_m=radius*value,
                    Er_quadrature_V_per_m=-radius*gradient[:,1]/(omega*EPS0),
                    Ez_quadrature_V_per_m=(2*value+radius*gradient[:,0])/(omega*EPS0))


def solve_curved(case,*,quadrature_order=None,mesh_data=None):
    """Solve on a validated curved space, promoting an explicit experimental call."""
    from .te import is_te
    if is_te(case):
        from .te import solve_te
        quadrature_order=case.quadrature_order if quadrature_order is None else quadrature_order
        return solve_te(replace(case,geometry_order=2,quadrature_order=quadrature_order),mesh_data=mesh_data)
    if case.element_order!=2:
        raise ValueError('experimental curved solve requires element_order=2')
    quadrature_order=case.quadrature_order if quadrature_order is None else quadrature_order
    case=replace(case,geometry_order=2,quadrature_order=quadrature_order)
    mesh = make_mesh(case) if mesh_data is None else mesh_from_dict(case,mesh_data)
    space = case_curved_space(case,mesh)
    k,m = assemble_curved(space,quadrature_order=quadrature_order)
    count = k.shape[0]
    free = np.setdiff1d(np.arange(count),space.constrained_dofs)
    if case.modes>=len(free)-1:
        raise ValueError('modes must be smaller than free curved node count minus one')
    kr,mr = k[free][:,free],m[free][:,free]
    d = 1/np.sqrt(mr.diagonal())
    scale = diags(d)
    a,b = scale@kr@scale,scale@mr@scale
    try:
        values,vectors = eigsh(a,k=case.modes,M=b,sigma=0.,which='LM',tol=1e-10,
                              maxiter=10000,v0=np.random.default_rng(20260905).normal(size=len(free)))
    except ArpackNoConvergence as exc:
        raise RuntimeError('curved eigensolver did not converge') from exc
    order = np.argsort(values)
    values = values[order]
    if not np.isfinite(values).all() or np.any(values<=0):
        raise RuntimeError('curved eigensolve returned nonpositive/nonfinite eigenvalues')
    u = np.zeros((count,case.modes))
    u[free] = d[:,None]*vectors[:,order]
    u /= np.sqrt(np.sum(u*(m@u),axis=0))
    orthogonality = float(np.max(abs(u.T@(m@u)-np.eye(case.modes))))
    residuals = []
    for i,value in enumerate(values):
        ku,mu = (k@u[:,i])[free],(m@u[:,i])[free]
        residuals.append(np.linalg.norm(ku-value*mu)/(np.linalg.norm(ku)+value*np.linalg.norm(mu)))
        if u[np.argmax(abs(u[:,i])),i]<0:
            u[:,i]*=-1
    if not np.isfinite(residuals).all() or max(residuals)>1e-7:
        raise RuntimeError('curved eigenpair residual exceeds 1e-7')
    u *= np.sqrt(case.normalization_j/(MU0*np.pi))
    return CurvedSolution(case,space,k,m,values,C0*np.sqrt(values)/TAU,u,
                          np.asarray(residuals),orthogonality,quadrature_order,mesh_to_dict(mesh))
