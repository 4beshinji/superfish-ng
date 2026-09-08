# SPDX-License-Identifier: Apache-2.0
"""Mapped strong/flux TM residual priorities; never physical error bounds."""
import math
import numpy as np
from .fem import triangle_quadrature
from .quadratic_geometry import _REFERENCE_GRAD, _REFERENCE_NODES

# Reference-coordinate Hessians of the six quadratic Lagrange functions.
_HESSIANS = np.array([4*np.outer(g, g) for g in _REFERENCE_GRAD] +
    [4*(np.outer(_REFERENCE_GRAD[i], _REFERENCE_GRAD[j])+
        np.outer(_REFERENCE_GRAD[j], _REFERENCE_GRAD[i])) for i,j in ((0,1),(1,2),(2,0))])


def _field_derivatives(mapping, coefficients, reference_points):
    mapped = mapping.evaluate(reference_points)
    shifted = coefficients-coefficients[0]
    gradient = np.einsum('qia,i->qa', mapped['basis_gradients'], shifted)
    reference_hessian = np.einsum('i,iab->ab', shifted, _HESSIANS)
    map_hessians = np.einsum('ic,iab->cab', mapping.points_rz_m-mapping.points_rz_m[0], _HESSIANS)
    corrected = reference_hessian-np.einsum('qc,cab->qab', gradient, map_hessians)
    inverse = np.linalg.inv(mapped['jacobian'])
    laplacian = np.einsum('qai,qab,qbi->q', inverse, corrected, inverse)
    return mapped, mapped['basis_values']@coefficients, gradient, laplacian


def _diameter_squared(mapping):
    p = mapping.points_rz_m-mapping.points_rz_m[0]
    controls = np.concatenate((p[:3], 2*p[3:]-.5*(p[:3]+p[[1,2,0]])))
    return float(np.max(np.sum((controls[:,None]-controls[None,:])**2, axis=2)))


def _components(space, u, eigenvalue, quadrature_order=12):
    geometry = space.geometry
    maps = geometry.local_maps
    cells = geometry.cell_nodes
    rule = list(triangle_quadrature(order=quadrature_order))
    references = np.array([n[1:] for n,_ in rule]); weights = np.array([w for _,w in rule])
    volume = np.zeros(len(cells)); interior = np.zeros(len(cells)); boundary = np.zeros(len(cells))
    owners = {}
    for cell, (nodes, mapping) in enumerate(zip(cells, maps)):
        mapped, value, gradient, laplacian = _field_derivatives(mapping, u[nodes], references)
        radius = mapped['points_rz_m'][:,0]
        residual = radius*laplacian+3*gradient[:,0]+eigenvalue*radius*value
        volume[cell] = _diameter_squared(mapping)*float(weights@(mapped['determinant_m2']*radius*residual**2))
        for i,j in ((0,1),(1,2),(2,0)):
            owners.setdefault(tuple(sorted((int(nodes[i]), int(nodes[j])))), []).append((cell,i,j))
    tags = {tuple(sorted(map(int, edge[:2]))): tag for edge,tag in zip(geometry.boundary_nodes, space.boundary_tags)}
    x,w = np.polynomial.legendre.leggauss(quadrature_order); x=(x+1)/2; w=w/2
    for edge, adjacent in owners.items():
        if tags.get(edge) in ('axis', 'magnetic_symmetry'):
            continue
        flux = np.zeros(len(x))
        for index, (cell,i,j) in enumerate(adjacent):
            a,b = _REFERENCE_NODES[[i,j]]
            t = x if cells[cell,i] == edge[0] else 1-x
            mapped = maps[cell].evaluate((1-t[:,None])*a+t[:,None]*b)
            tangent = np.einsum('qab,b->qa', mapped['jacobian'], b-a)
            speed = np.linalg.norm(tangent, axis=1)
            normal = np.column_stack((tangent[:,1],-tangent[:,0]))/speed[:,None]
            coefficients = u[cells[cell]]
            gradient = np.einsum('qia,i->qa', mapped['basis_gradients'], coefficients-coefficients[0])
            radius = mapped['points_rz_m'][:,0]
            flux += radius*np.sum(gradient*normal,axis=1)
            if len(adjacent) == 1:
                flux += 2*normal[:,0]*(mapped['basis_values']@coefficients)
            if index == 0:
                measure = speed; radii = radius
        length = float(w@measure)
        contribution = length*float(w@(measure*radii*flux**2))
        target = interior if len(adjacent) == 2 else boundary
        for cell,_,_ in adjacent:
            target[cell] += contribution/len(adjacent)
    return volume, interior, boundary


def curved_residual_indicator(case, solution, *, mode=0, quadrature_order=12):
    """Reconstruct a native curved field's space and evaluate its local residual.

    The Gauss rule approximates rational curved integrands. Compare quadrature
    orders separately from mesh refinement. Mode rank is not a persistent ID.
    """
    from .curved_solution import CurvedSolution
    from .curved_space import case_curved_space
    from .curved_saved import geometry_arrays
    from .curved_fem import assemble_curved
    from .mesh_input import mesh_from_dict
    if not isinstance(solution, CurvedSolution) or case.geometry_order != 2 or solution.case != case:
        raise ValueError('curved residual indicator requires a matching native curved Case and solution')
    if type(quadrature_order) is not int or not 2 <= quadrature_order <= 32:
        raise ValueError('indicator quadrature_order must be an integer from 2 to 32')
    eigenvalues = np.asarray(solution.eigenvalues)
    if eigenvalues.ndim != 1 or type(mode) is not int or not 0 <= mode < len(eigenvalues):
        raise ValueError('mode must be an available zero-based integer index')
    if solution.source_mesh_data is None:
        raise ValueError('curved residual indicator requires a native source mesh for reconstruction')
    source = solution.reflection_source_case
    if source is None:
        space = case_curved_space(case, mesh_from_dict(case, solution.source_mesh_data))
    else:
        from .curved_reflection import reflect_curved_space, reflected_case
        parent = case_curved_space(source, mesh_from_dict(source, solution.source_mesh_data))
        reflection = reflect_curved_space(source, parent)
        if reflected_case(source, reflection) != case:
            raise ValueError('curved residual reflection source differs from Case')
        space = reflection.space
    actual = geometry_arrays(solution.space)
    expected = geometry_arrays(space)
    if set(actual) != set(expected) or any(not np.array_equal(actual[k],v) for k,v in expected.items()):
        raise ValueError('curved residual geometry differs from native reconstruction')
    coefficients = np.asarray(solution.u)
    if coefficients.dtype.kind not in 'iuf' or coefficients.shape != (len(space.geometry.points_rz_m),len(eigenvalues)) or not np.isfinite(coefficients).all():
        raise ValueError('solution coefficients must be finite real values in the matching curved FEM space')
    if eigenvalues.dtype.kind not in 'iuf' or not np.isfinite(eigenvalues[mode]) or eigenvalues[mode] <= 0:
        raise ValueError('curved residual requires a positive finite eigenvalue')
    u = coefficients[:,mode].astype(float,copy=True)
    amplitude = float(np.max(np.abs(u)))
    if not amplitude > 0:
        raise ValueError('curved residual requires a nonzero field')
    if np.any(u[space.constrained_dofs] != 0):
        raise ValueError('magnetic_symmetry coefficients must satisfy the essential zero constraint')
    u /= amplitude
    with np.errstate(over='raise', invalid='raise', divide='raise'):
        try:
            stiffness,_ = assemble_curved(space, quadrature_order=quadrature_order)
            energy = float(u@(stiffness@u))
            if not math.isfinite(energy) or energy <= 0:
                raise ValueError('curved residual field energy must be positive and finite')
            parts = [part/energy for part in _components(space,u,float(eigenvalues[mode]),quadrature_order)]
        except (FloatingPointError, OverflowError) as exc:
            raise ValueError('curved residual exceeds supported numeric range') from exc
    cells = sum(parts)
    if not np.isfinite(cells).all() or np.any(cells < 0):
        raise ValueError('curved residual indicator must be finite and nonnegative')
    try:
        total = math.fsum(cells)
    except OverflowError as exc:
        raise ValueError('curved residual sum exceeds supported numeric range') from exc
    return dict(schema_version=1, mode_index=mode, element_order=2, geometry_order=2,
        quadrature_order=quadrature_order, relative_indicator=math.sqrt(total),
        cell_relative_squared=cells.tolist(), volume_relative_squared=parts[0].tolist(),
        interior_relative_squared=parts[1].tolist(), boundary_relative_squared=parts[2].tolist(),
        normalization='squared contributions divided by reconstructed u.T K u at the indicator quadrature order',
        characteristic_lengths='quadratic Bernstein control hull diameter; Gauss-integrated curved edge length',
        physical_error_bound=None,
        scope='fixed represented quadratic geometry; numerical quadrature and residual priority, not frequency/RF/peak certification')
