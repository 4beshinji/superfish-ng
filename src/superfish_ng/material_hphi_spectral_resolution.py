# SPDX-License-Identifier: Apache-2.0
"""Nearby finite-space material Hphi spectra via projected shifted inverse residuals."""
import numpy as np
from scipy.sparse.linalg import splu
from .material_hphi import MaterialHphiSolution
from .material_hphi_comparison import MaterialHphiComparison
from .material_hphi_field_overlap import verified_material_hphi_solution
from .material_hphi_mass_projection import project_material_hphi_coefficients
from .material_hphi_fem import material_hphi_matrices
from .config import integer, positive
from .constants import C0, TAU


def _maximum_edge(mesh):
    vertices = mesh.points_rz_m[mesh.triangles]
    return float(np.max(np.linalg.norm(vertices-np.roll(vertices,-1,axis=1),axis=2)))


def material_hphi_spectral_resolution(solution, comparison, *, comparison_order=2, quadrature_order=12,
        maximum_relative_projection_error=.01, max_candidate_tests=2000000,
        max_overlay_triangles=250000, max_dofs=250000, max_sample_points=2000000,
        max_interface_tests=2000000, max_interface_pieces=250000, max_modes=256):
    """Locate a nearby eigenvalue of an explicitly supplied comparison FEM space.

    With T=(K+sM)^-1 M, mu=1/(lambda+s), dist(mu,spectrum(T)) is at
    most ||T v-mu v||_M/||v||_M in exact arithmetic. v is the original
    scalar eigenfield's L2 projection. The interval identifies neither an
    eigenvalue rank nor a continuous-spectrum enclosure. Floating residuals
    and an explicit roundoff padding give a numerical diagnostic, not a
    certified interval bound. No comparison eigensolve is used by this API.
    """
    integer(comparison_order,'comparison_order')
    limit=positive(maximum_relative_projection_error,'maximum_relative_projection_error')
    if comparison_order not in (1,2) or limit>=1:
        raise ValueError('comparison requires P1/P2 and a projection error limit below 1')
    integer(max_modes,'max_modes')
    if type(solution) is not MaterialHphiSolution or max_modes <= 0 or solution.case.modes > max_modes:
        raise ValueError('material comparison requires an original spectrum within max_modes')
    if type(comparison) is not MaterialHphiComparison or comparison.mapping != 'same_domain':
        raise ValueError('material spectral comparison requires an explicit same_domain declaration')
    comparison=MaterialHphiComparison.from_dict(comparison.to_dict())
    if comparison.previous_partition.to_dict()!=solution.case.partition.to_dict():
        raise ValueError('material spectral comparison previous partition differs from original case')
    solution=verified_material_hphi_solution(solution)
    mesh=solution.case.partition.mesh
    comparison_mesh=comparison.current_partition.mesh
    if (comparison_order<solution.case.element_order or len(comparison_mesh.triangles)<=len(mesh.triangles)
            or _maximum_edge(comparison_mesh)>=_maximum_edge(mesh)):
        raise ValueError('comparison requires at least the original order, more triangles and a smaller maximum edge')
    projection=project_material_hphi_coefficients(comparison,solution.coefficients,
        previous_order=solution.case.element_order,current_order=comparison_order,quadrature_order=quadrature_order,
        max_candidate_tests=max_candidate_tests,max_overlay_triangles=max_overlay_triangles,max_dofs=max_dofs,
        max_interface_tests=max_interface_tests,max_interface_pieces=max_interface_pieces,
        max_sample_points=max_sample_points,max_columns=max_modes)
    _,stiffness,mass,_=material_hphi_matrices(comparison.current_partition,comparison_order,quadrature_order=quadrature_order)
    regular=solution.case.axis_connected
    vectors=projection.coefficients
    shift=1/comparison_mesh.area_m2
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
    return dict(method='explicit_material_comparison_space_projected_shifted_inverse_residual',
        status='UNVERIFIED' if reasons else 'PASS',modes=rows,
        original_frequencies_hz=solution.frequencies_hz.tolist(),comparison=comparison.to_dict(),comparison_partition=comparison.current_partition.to_dict(),
        comparison_order=comparison_order,comparison_triangles=len(comparison_mesh.triangles),
        comparison_dofs=mass.shape[0],shift_per_m2=shift,shift_geometry='inverse_material_domain_meridional_area',
        projection=projection.diagnostic,maximum_relative_projection_error=limit,
        relative_inverse_residual=(delta/mu).tolist(),inverse_residual_m2=delta.tolist(),
        roundoff_relative_padding=1e-10,linear_solve_relative_residual=equation_error.tolist(),
        linear_solve_tolerance=1e-10,nearby_comparison_frequency_intervals_hz=[
            [float(a),float(b) if np.isfinite(b) else None] for a,b in zip(lower_hz,upper_hz)],
        zero_mode='absent in regular-axis space' if regular else 'constant q retained in comparison operator',
        scope='nearby finite comparison eigenvalue only; numerical residual with padding, not a certified enclosure, rank isolation, continuum error bound or mode identity')
