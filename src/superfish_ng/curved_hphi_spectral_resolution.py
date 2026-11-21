# SPDX-License-Identifier: Apache-2.0
"""Nearby finite curved Hphi spectra using an explicit same-domain space."""
import numpy as np
from scipy.sparse.linalg import splu
from .config import integer,positive
from .constants import C0,TAU
from .curved_meridional_geometry import CurvedMeridionalGeometry
from .curved_hphi_comparison import CurvedHphiComparisonDomain
from .curved_hphi_field_overlap import verified_curved_hphi_solution
from .curved_hphi_mass_projection import project_curved_hphi_coefficients
from .curved_hphi_fem import curved_hphi_matrices


def _maximum_cell_diameter(geometry):
    """Whole-P2 Bernstein bounding-box diameter, including curved edges."""
    p=geometry.points_rz_m[geometry.cell_nodes]
    controls=np.concatenate((p[:,:3],2*p[:,3:]-(p[:,[0,1,2]]+p[:,[1,2,0]])/2),axis=1)
    return float(np.max(np.linalg.norm(np.ptp(controls,axis=1),axis=1)))


def curved_hphi_spectral_resolution(solution,comparison_geometry,domain,*,comparison_order=2,
        quadrature_order=12,original_cells=None,comparison_cells=None,
        maximum_relative_projection_error=.01,max_candidate_tests=2000000,
        max_overlay_triangles=250000,max_dofs=250000,max_sample_points=2000000):
    """Locate nearby finite-space eigenvalues, without rank or continuum claims.

    For T=(K+sM)^-1 M, the M-norm residual of a projected source vector
    bounds its distance to the finite spectrum in exact arithmetic. The
    reported floating-point diagnostic adds explicit roundoff padding;
    it is neither a certified enclosure nor an eigenmode identity. No
    comparison eigensolve is used here. Both native partitions must cover
    the same declared full quadratic vacuum, with any rounding explicit.
    """
    integer(comparison_order,'comparison_order')
    limit=positive(maximum_relative_projection_error,'maximum_relative_projection_error')
    if comparison_order not in (1,2) or limit>=1:
        raise ValueError('curved comparison requires P1/P2 and a projection error limit below 1')
    if type(domain) is not CurvedHphiComparisonDomain or domain.mapping!='same_vacuum':
        raise ValueError('curved spectral comparison requires an explicit same_vacuum quadratic domain')
    if type(comparison_geometry) is not CurvedMeridionalGeometry:
        raise ValueError('curved spectral comparison requires complete quadratic native geometry')
    solution=verified_curved_hphi_solution(solution)
    geometry=solution.case.geometry
    comparison_geometry=CurvedMeridionalGeometry.from_dict(comparison_geometry.to_dict())
    if (comparison_order<solution.case.element_order or len(comparison_geometry.cell_nodes)<=len(geometry.cell_nodes)
            or _maximum_cell_diameter(comparison_geometry)>=_maximum_cell_diameter(geometry)):
        raise ValueError('curved comparison requires at least the original order, more cells and a smaller whole-P2 bounding-box diameter')
    projection=project_curved_hphi_coefficients(geometry,comparison_geometry,solution.coefficients,domain,
        previous_order=solution.case.element_order,current_order=comparison_order,quadrature_order=quadrature_order,
        previous_cells=original_cells,current_cells=comparison_cells,max_candidate_tests=max_candidate_tests,
        max_overlay_triangles=max_overlay_triangles,max_dofs=max_dofs,max_sample_points=max_sample_points)
    _,stiffness,mass,_=curved_hphi_matrices(comparison_geometry,comparison_order,quadrature_order=quadrature_order)
    regular=solution.case.axis_connected
    vectors=projection.coefficients
    shift=1/comparison_geometry.area_m2
    if not np.isfinite(shift) or shift<=0:
        raise ValueError('Hphi comparison shift is outside finite positive SI arithmetic')
    matrix=(stiffness+shift*mass).tocsc();rhs=mass @ vectors
    norm=np.sum(vectors*rhs,axis=0)
    if not np.isfinite(norm).all() or np.any(norm<=0):
        raise ValueError('Hphi comparison projection has no finite positive norm; refine the comparison space')
    inverse=splu(matrix).solve(rhs)
    equation_error=np.linalg.norm(matrix @ inverse-rhs,axis=0)/np.linalg.norm(rhs,axis=0)
    eigenvalues=(TAU*solution.frequencies_hz/C0)**2
    mu=1/(eigenvalues+shift);residual=inverse-vectors*mu
    squared=np.sum(residual*(mass @ residual),axis=0)/norm
    if not np.isfinite(squared).all() or np.any(squared<0) or not np.isfinite(equation_error).all() or np.max(equation_error)>1e-10:
        raise ValueError('Hphi shifted inverse comparison is numerically unresolved')
    delta=np.sqrt(squared);padding=1e-10*mu;padded=delta+padding
    lower=np.maximum(0.,1/(mu+padded)-shift)
    upper=np.full(len(mu),np.inf);bounded=mu>padded
    upper[bounded]=1/(mu[bounded]-padded[bounded])-shift
    lower_hz=np.sqrt(lower)*C0/TAU;upper_hz=np.sqrt(upper)*C0/TAU
    errors=projection.diagnostic['relative_mass_error'];reasons=[];rows=[]
    for i,(a,b,error) in enumerate(zip(lower_hz,upper_hz,errors)):
        why=[]
        if error>limit:why.append('original scalar field projection loss exceeds the declared limit')
        if not np.isfinite(b):why.append('shifted inverse residual does not give a finite upper frequency')
        if not regular and a==0:why.append('comparison interval reaches the static constant-q circulation')
        rows.append(dict(mode_rank=i+1,status='UNVERIFIED' if why else 'PASS',reasons=why))
        reasons.extend(why)
    return dict(method='explicit_curved_comparison_space_projected_shifted_inverse_residual',
        status='UNVERIFIED' if reasons else 'PASS',modes=rows,
        original_frequencies_hz=solution.frequencies_hz.tolist(),comparison_geometry=comparison_geometry.to_dict(),comparison_domain=domain.to_dict(),
        comparison_order=comparison_order,comparison_triangles=len(comparison_geometry.cell_nodes),
        comparison_dofs=mass.shape[0],shift_per_m2=shift,shift_geometry='inverse_vacuum_meridional_area',
        projection=projection.diagnostic,maximum_relative_projection_error=limit,
        relative_inverse_residual=(delta/mu).tolist(),inverse_residual_m2=delta.tolist(),
        roundoff_relative_padding=1e-10,linear_solve_relative_residual=equation_error.tolist(),
        linear_solve_tolerance=1e-10,nearby_comparison_frequency_intervals_hz=[
            [float(a),float(b) if np.isfinite(b) else None] for a,b in zip(lower_hz,upper_hz)],
        zero_mode='absent in regular-axis space' if regular else 'constant q retained in comparison operator',
        scope='nearby finite comparison eigenvalue only; numerical residual with padding, not a certified enclosure, rank isolation, continuum error bound or mode identity')
