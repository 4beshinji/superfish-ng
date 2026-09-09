# SPDX-License-Identifier: Apache-2.0
"""Reflect fixed quadratic geometry and parity coefficients without reprojection."""
from dataclasses import dataclass
from types import MappingProxyType
import numpy as np
from scipy.sparse import coo_matrix
from .curved_space import CurvedSpace, check_curved_edges
from .curved_refinement import RestrictedGeometry
from .quadratic_geometry import QuadraticTriangle
from .quadratic_boundary import check_quadratic_boundary


@dataclass(frozen=True)
class CurvedReflection:
    space: CurvedSpace
    coefficient_map: object
    reflected_contour: object
    side: str
    parity: int
    seam_dofs: np.ndarray

    def apply(self, coefficients):
        """Transfer finite scalar/multimode coefficients with exact odd seam zeros."""
        values = np.asarray(coefficients)
        if (values.dtype.kind not in 'iuf' or values.ndim not in (1, 2)
                or values.shape[0] != self.coefficient_map.shape[1]
                or not np.isfinite(values).all()):
            raise ValueError('reflection coefficients require finite matching node rows')
        if self.parity == -1 and np.any(values[self.seam_dofs] != 0):
            raise ValueError('magnetic symmetry requires zero u at the reflection plane')
        return self.coefficient_map@values


def reflect_curved_space(case, parent, *, coefficient_parity=None):
    """Join a half space to its mirror, retaining every quadratic cell map.

    Coefficients on a magnetic seam must be zero before applying coefficient_map.
    Boundary primitive indices refer to reflected_contour; mirrored primitive
    parameters reverse because the full analytic contour retains orientation.
    This transformation does not solve or normalize an eigenmode.
    """
    if not isinstance(parent, CurvedSpace) or case.curved_contour is None:
        raise ValueError('curved reflection requires a native Case and CurvedSpace')
    sides = [side for side in ('z_min', 'z_max') if getattr(case, side) != 'pec']
    if len(sides) != 1:
        raise ValueError('curved reflection requires exactly one symmetry end and one PEC end')
    side = sides[0]
    tag = getattr(case, side)
    if coefficient_parity is not None and (type(coefficient_parity) is not int or coefficient_parity not in (-1, 1)):
        raise ValueError('reflection coefficient_parity must be -1 or 1')
    parity = (1 if tag == 'electric_symmetry' else -1) if coefficient_parity is None else coefficient_parity
    contour = case.curved_contour
    full_contour = contour.reflected()  # Validates a complete connected seam.
    geometry = parent.geometry
    plane = 0. if side == 'z_min' else case.length
    shift = case.length if side == 'z_min' else 0.
    points = geometry.points_rz_m
    seam = parent.boundary_tags == tag
    on_plane = np.zeros(len(points), dtype=bool)
    on_plane[geometry.boundary_nodes[seam].ravel()] = True
    tolerance = 512*np.finfo(float).eps*float(np.max(np.ptp(points, axis=0)))
    if (not np.any(seam) or np.any(abs(points[on_plane, 1]-plane) > tolerance)
            or np.any((points[:, 1] == plane) & ~on_plane)
            or np.any((parent.boundary_tags != tag) & np.char.endswith(parent.boundary_tags, '_symmetry'))):
        raise ValueError('curved space must have exactly the Case symmetry seam')
    original = points.copy()
    original[:, 1] += shift
    # Fixed-map subdivision can round a constant plane by one ulp. Identify
    # shared DOFs by boundary topology, then restore only that roundoff.
    original[on_plane, 1] = plane+shift
    mirrored = points.copy()
    mirrored[:, 1] = 2*plane-points[:, 1]+shift
    mapping = np.arange(len(points))
    mapping[~on_plane] = np.arange(len(points), len(points)+np.count_nonzero(~on_plane))
    joined = np.vstack((original, mirrored[~on_plane]))
    cells = np.vstack((geometry.cell_nodes, mapping[geometry.cell_nodes][:, [0, 2, 1, 5, 4, 3]]))
    keep = ~seam
    boundary = np.vstack((geometry.boundary_nodes[keep], mapping[geometry.boundary_nodes[keep]][:, [1, 0, 2]]))
    tags = np.tile(parent.boundary_tags[keep], 2)
    # Match CurvedContour.reflected's traversal from the end of the seam.
    symmetry = {i for i, t in enumerate(contour.edge_tags) if t.endswith('_symmetry')}
    start = next(i for i in range(len(contour.curves)) if i not in symmetry and (i-1)%len(contour.curves) in symmetry)
    remaining = []
    i = start
    while i not in symmetry:
        remaining.append(i)
        i = (i+1)%len(contour.curves)
    original_indices = {owner: index for index, owner in enumerate(remaining)}
    owners = geometry.boundary_curve_indices[keep]
    indices = np.array([original_indices[int(owner)] for owner in owners], dtype=int)
    indices = np.r_[indices, 2*len(remaining)-1-indices]
    parameters = np.vstack((geometry.boundary_parameters[keep], 1-geometry.boundary_parameters[keep][:, ::-1]))
    # Affine axis midpoint convention is exact in the RF integrator.
    for a, b, mid in boundary[tags == 'axis']:
        joined[mid] = (joined[a]+joined[b])/2
    maps = tuple(QuadraticTriangle(joined[nodes]) for nodes in cells)
    boundary_check = MappingProxyType(check_quadratic_boundary(joined, boundary))
    edge_check = MappingProxyType(check_curved_edges(joined, cells, boundary))
    axis = np.unique(boundary[tags == 'axis'])
    axis = axis[np.argsort(joined[axis, 1])]
    constrained = np.array([], dtype=int)
    for array in (joined, cells, boundary, tags, indices, parameters, axis, constrained):
        array.setflags(write=False)
    full_geometry = RestrictedGeometry(joined, cells, boundary, indices, parameters, maps, boundary_check)
    space = CurvedSpace(full_geometry, tags, axis, constrained, edge_check)
    columns = np.r_[np.arange(len(points)), np.flatnonzero(~on_plane)]
    values = np.r_[np.ones(len(points)), np.full(np.count_nonzero(~on_plane), parity)]
    transfer = coo_matrix((values, (np.arange(len(joined)), columns)), shape=(len(joined), len(points))).tocsr()
    seam_dofs = np.flatnonzero(on_plane)
    seam_dofs.setflags(write=False)
    return CurvedReflection(space, transfer, full_contour, side, parity, seam_dofs)


DIRECT_CONSTRUCTION = 'direct curved P2 eigensolve; indices within specified boundary conditions'
REFLECTED_CONSTRUCTION = 'curved P2 symmetry reflection; parity-filtered spectrum, indices are NOT full-spectrum ranks'


def reflected_case(case, reflection):
    from dataclasses import replace
    from .curve_partitions import reflected_segments_per_curve
    return replace(case, contour=None, curved_contour=reflection.reflected_contour,
                   curve_segments_per_curve=reflected_segments_per_curve(case),
                   curved_refinement_steps=(),
                   z_min='pec', z_max='pec', nz=2*case.nz,
                   normalization_j=2*case.normalization_j,
                   name=case.name+' [reflected full cavity]',
                   **case.reflected_acceleration_parameters(reflection.side))


def reflection_contract(case, reflection):
    return dict(version=1, side=reflection.side, parity=reflection.parity,
                source_case=case.to_dict(),
                geometry='reflect the reconstructed half-domain quadratic maps after fixed refinement',
                coefficients='unchanged amplitude with declared parity; full-domain energy is twice source energy')


def reflect_curved_solution(case, solution):
    from .curved_solution import CurvedSolution
    from .curved_fem import assemble_curved
    if not isinstance(solution, CurvedSolution) or solution.case != case or case.geometry_order != 2:
        raise ValueError('curved reflection requires the matching solved native Case')
    reflection = reflect_curved_space(case, solution.space)
    full = reflected_case(case, reflection)
    u = reflection.apply(solution.u)
    k, m = assemble_curved(reflection.space, quadrature_order=case.quadrature_order)
    ku, mu = k@u, m@u
    residuals = np.linalg.norm(ku-mu*solution.eigenvalues, axis=0)/(np.linalg.norm(ku, axis=0)+solution.eigenvalues*np.linalg.norm(mu, axis=0))
    if not np.isfinite(residuals).all() or np.max(residuals) > 1e-7:
        raise ValueError('reflected curved field fails the full-domain residual check')
    from .constants import MU0
    gram = (MU0*np.pi/full.normalization_j)*(u.T@mu)
    error = float(np.max(abs(gram-np.eye(case.modes))))
    if not np.isfinite(error) or error > 1e-7:
        raise ValueError('reflected curved normalization or orthogonality differs')
    result = CurvedSolution(full, reflection.space, k, m, solution.eigenvalues.copy(),
                            solution.frequencies_hz.copy(), u, residuals, error,
                            case.quadrature_order, solution.source_mesh_data, case)
    return full, result
