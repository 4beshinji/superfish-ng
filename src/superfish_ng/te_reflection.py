# SPDX-License-Identifier: Apache-2.0
"""TE symmetry extension with unchanged amplitudes and explicit source provenance."""
from dataclasses import replace
import numpy as np
from .constants import EPS0
from .mesh import Mesh, element_geometry
from .te import TESolution, te_matrices, validate_te_case


def reflect_te_solution(case, solution):
    """Extend one symmetry sector without another eigenvalue solve.

    Amplitudes stay unchanged; full energy and PEC loss double. Frequencies
    retain their source order in a parity-filtered subset, not full-spectrum
    ranks. reflection_source_case records that distinction explicitly.
    """
    validate_te_case(case)
    if not isinstance(solution, TESolution) or solution.case != case:
        raise ValueError('TE reflection requires the matching solved native Case')
    if solution.reflection_source_case is not None:
        raise ValueError('TE reflection cannot reflect an already filtered spectrum')
    sides = [side for side in ('z_min', 'z_max') if getattr(case, side) != 'pec']
    if len(sides) != 1:
        raise ValueError('TE reflection requires exactly one symmetry end and one PEC end')
    side = sides[0]
    tag = getattr(case, side)
    parity = 1 if tag == 'magnetic_symmetry' else -1
    if case.geometry_order == 2:
        from .curved_reflection import reflect_curved_space, reflected_case
        from .curved_fem import assemble_curved
        reflection = reflect_curved_space(case, solution.space, coefficient_parity=parity)
        if parity == -1 and np.any(solution.coefficients_v_per_m2[reflection.seam_dofs] != 0):
            raise ValueError('TE electric symmetry requires zero Ephi/r at the reflection plane')
        v = reflection.apply(solution.coefficients_v_per_m2)
        full = reflected_case(case, reflection)
        space = reflection.space
        constrained = np.unique(space.geometry.boundary_nodes[np.isin(space.boundary_tags, ['pec', 'electric_symmetry'])])
        constrained.setflags(write=False)
        space = replace(space, constrained_dofs=constrained)
        k, m = assemble_curved(space, quadrature_order=case.quadrature_order)
        free = np.setdiff1d(np.arange(k.shape[0]), constrained)
        # Curved fields use the full fixed maps. This mesh is explicitly the source mesh.
        mesh = solution.mesh
    else:
        mesh, full, space, k, m, free, v = _straight(case, solution, side, tag, parity)
    kv, mv = (k@v)[free], (m@v)[free]
    residuals = np.linalg.norm(kv-mv*solution.eigenvalues, axis=0)/(np.linalg.norm(kv, axis=0)+solution.eigenvalues*np.linalg.norm(mv, axis=0))
    if not np.isfinite(residuals).all() or np.max(residuals) > 1e-7:
        raise ValueError('TE reflected fields fail the full-domain free-equation residual check')
    error = float(np.max(abs(EPS0*np.pi/full.normalization_j*(v.T@(m@v))-np.eye(case.modes))))
    if not np.isfinite(error) or error > 1e-7:
        raise ValueError('TE reflected normalization or orthogonality differs')
    result = TESolution(full, mesh, space, k, m, solution.eigenvalues.copy(),
                        solution.frequencies_hz.copy(), v, residuals, error,
                        solution.source_mesh_data, reflection_source_case=case,
                        reflection_source_coefficients=solution.coefficients_v_per_m2.copy())
    return full, result


def _straight(case, solution, side, tag, parity):
    mesh = solution.mesh
    plane = 0. if side == 'z_min' else case.length
    shift = case.length if side == 'z_min' else 0.
    on_plane = mesh.points[:, 1] == plane
    field_points = mesh.points if case.element_order == 1 else solution.space.dof_points
    if parity == -1 and np.any(solution.coefficients_v_per_m2[field_points[:, 1] == plane] != 0):
        raise ValueError('TE electric symmetry requires zero Ephi/r at the reflection plane')
    original = mesh.points.copy(); original[:, 1] += shift
    mirrored = mesh.points.copy(); mirrored[:, 1] = 2*plane-mirrored[:, 1]+shift
    mapping = np.arange(len(original))
    mapping[~on_plane] = np.arange(len(original), len(original)+np.count_nonzero(~on_plane))
    points = np.vstack((original, mirrored[~on_plane]))
    triangles = np.vstack((mesh.triangles, mapping[mesh.triangles][:, [0, 2, 1]]))
    keep = mesh.boundary_tags != tag
    edges = np.vstack((mesh.boundary_edges[keep], mapping[mesh.boundary_edges[keep]]))
    cells = np.r_[mesh.boundary_cells[keep], mesh.boundary_cells[keep]+len(mesh.triangles)]
    tags = np.tile(mesh.boundary_tags[keep], 2)
    axis = np.flatnonzero(points[:, 0] == 0); axis = axis[np.argsort(points[axis, 1])]
    reflected = Mesh(points, triangles, edges, tags, cells, axis)
    element_geometry(reflected)
    if side == 'z_min':
        profile = tuple((case.length-z, r) for z, r in reversed(case.profile))
        profile += tuple((case.length+z, r) for z, r in case.profile[1:])
        count = len(case.profile)
        arcs = tuple((count-i, radius, direction) for i, radius, direction in case.arcs)
        arcs += tuple((count-1+i, radius, direction) for i, radius, direction in case.arcs)
    else:
        profile = case.profile + tuple((2*case.length-z, r) for z, r in reversed(case.profile[:-1]))
        arcs = case.arcs+tuple((2*len(case.profile)-1-i, radius, direction) for i, radius, direction in case.arcs)
    contour = case.contour.reflected() if case.contour is not None else None
    curved = case.curved_contour.reflected() if case.curved_contour is not None else None
    from .curve_partitions import reflected_segments_per_curve
    full = replace(case, profile=profile, arcs=arcs, contour=None if curved is not None else contour,
                   curved_contour=curved, curve_segments_per_curve=reflected_segments_per_curve(case),
                   z_min='pec', z_max='pec', nz=2*case.nz, normalization_j=2*case.normalization_j,
                   name=case.name+' [reflected full cavity]', **case.reflected_acceleration_parameters(side))
    space, k, m, free = te_matrices(full, reflected)
    if case.element_order == 1:
        v = np.vstack((solution.coefficients_v_per_m2, parity*solution.coefficients_v_per_m2[~on_plane]))
    else:
        v = np.zeros((k.shape[0], case.modes)); count = len(mesh.triangles)
        values = solution.coefficients_v_per_m2[solution.space.cell_dofs]
        v[space.cell_dofs[:count]] = values
        v[space.cell_dofs[count:]] = parity*values[:, [0, 2, 1, 5, 4, 3]]
    return reflected, full, space, k, m, free, v
