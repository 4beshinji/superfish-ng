# SPDX-License-Identifier: Apache-2.0
"""Same-vacuum scalar mass coupling and L2 projection; never an eigenmode solve."""
from dataclasses import dataclass
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu
from .axis_connected_mesh import AxisConnectedMesh
from .axis_connected_fem import axis_connected_matrices
from .meridional_mesh import MeridionalMesh
from .meridional_overlap import meridional_overlay
from .hphi_mapped_overlap import mapped_hphi_overlay, HphiMappedOverlay
from .hphi_field_transport import mapped_transport_factors
from .hphi_mesh import HphiMeshCase, hphi_mesh_matrices
from .config import integer
from .fem import triangle_quadrature


@dataclass(frozen=True)
class HphiMassCoupling:
    previous_space: object
    current_space: object
    previous_mass: object
    cross_mass: object
    current_mass: object
    diagnostic: dict


@dataclass(frozen=True)
class HphiProjection:
    coefficients: np.ndarray
    diagnostic: dict


def _basis(bary, order):
    return bary if order == 1 else np.column_stack((bary*(2*bary-1),
        4*bary[:, 0]*bary[:, 1], 4*bary[:, 1]*bary[:, 2], 4*bary[:, 2]*bary[:, 0]))


def _space(mesh, order, quadrature_order):
    if type(mesh) is AxisConnectedMesh:
        space, _, mass = axis_connected_matrices(mesh, order)
    else:
        space, _, mass, _ = hphi_mesh_matrices(HphiMeshCase(mesh, element_order=order,
            quadrature_order=quadrature_order, modes=1))
    return space, mass


def _integrate(spaces, overlay, orders, integration_order, regular):
    dofs = [space.cell_dofs[cells] for space, cells in zip(spaces,
        (overlay.previous_cells, overlay.current_cells))]
    pairs = ((0, 0), (0, 1), (1, 1))
    blocks = [np.zeros((len(overlay.determinants), dofs[i].shape[1], dofs[j].shape[1])) for i, j in pairs]
    for bary, weight in triangle_quadrature(integration_order):
        values = [_basis(np.einsum('i,tij->tj', bary, vertices), order) for vertices, order in zip(
            (overlay.previous_vertex_barycentric, overlay.current_vertex_barycentric), orders)]
        if isinstance(overlay, HphiMappedOverlay):
            values[0] = values[0]*mapped_transport_factors(overlay, bary, regular=regular)[1][:, None]
        r = np.einsum('i,ti->t', bary, overlay.vertices_rz_m[:, :, 0])
        measure = overlay.determinants*weight*(r**3 if regular else 1/r)
        for block, (i, j) in zip(blocks, pairs):
            block += measure[:, None, None]*values[i][:, :, None]*values[j][:, None, :]
    matrices = []
    for block, (i, j) in zip(blocks, pairs):
        row = np.repeat(dofs[i], dofs[j].shape[1], axis=1).ravel()
        col = np.tile(dofs[j], (1, dofs[i].shape[1])).ravel()
        matrix = coo_matrix((block.ravel(), (row, col)),
            shape=(len(spaces[i].dof_points), len(spaces[j].dof_points))).tocsr()
        if not np.isfinite(matrix.data).all():
            raise ValueError('Hphi scalar mass integral is outside finite SI arithmetic')
        matrices.append(matrix)
    return matrices


def _difference(a, b, left, right):
    delta = (a-b).tocoo()
    return float(np.max(abs(delta.data)/left[delta.row]/right[delta.col], initial=0.))


def _coupling(previous, current, previous_order, current_order, quadrature_order,
              max_candidate_tests, max_overlay_triangles, max_dofs, geometry_mapping=None):
    for name, value in (('previous_order', previous_order), ('current_order', current_order),
            ('quadrature_order', quadrature_order), ('max_candidate_tests', max_candidate_tests),
            ('max_overlay_triangles', max_overlay_triangles), ('max_dofs', max_dofs)):
        integer(value, name)
    if previous_order not in (1, 2) or current_order not in (1, 2) or not 4 <= quadrature_order <= 32:
        raise ValueError('Hphi mass coupling requires P1/P2 and quadrature_order from 4 to 32')
    if type(previous) not in (AxisConnectedMesh, MeridionalMesh) or type(previous) is not type(current):
        raise ValueError('Hphi mass coupling requires two explicit meshes with the same regular-u or positive-radius-q unknown')
    previous, current = [type(mesh).from_dict(mesh.to_dict()) for mesh in (previous, current)]
    orders = previous_order, current_order
    for mesh, order in zip((previous, current), orders):
        count = len(mesh.points_rz_m)
        if order == 2:
            count += len(np.unique(np.sort(mesh.triangles[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2), axis=1), axis=0))
        if count > max_dofs:
            raise ValueError('Hphi mass coupling exceeds max_dofs')
    options = dict(max_candidate_tests=max_candidate_tests, max_overlay_triangles=max_overlay_triangles)
    overlay = (meridional_overlay(previous, current, **options) if geometry_mapping is None
               else mapped_hphi_overlay(previous, current, geometry_mapping, **options))
    regular = type(previous) is AxisConnectedMesh
    spaces, masses = zip(*(_space(mesh, order, quadrature_order) for mesh, order in zip((previous, current), orders)))
    norms = [np.sqrt(mass.diagonal()) for mass in masses]
    if any(not np.isfinite(n).all() or np.any(n <= 0) for n in norms):
        raise ValueError('Hphi scalar mass norms must be finite positive')
    integration_orders = [5, 7] if regular and geometry_mapping is None else [quadrature_order+4, quadrature_order+8]
    low, high = [_integrate(spaces, overlay, orders, n, regular) for n in integration_orders]
    differences = [_difference(a, b, norms[i], norms[j]) for a, b, (i, j) in zip(low, high, ((0, 0), (0, 1), (1, 1)))]
    reproduction = [_difference(a, b, n, n) for a, b, n in zip((high[0], high[2]), masses, norms)]
    if max(differences) > 1e-10 or max(reproduction) > 1e-8:
        raise ValueError('Hphi mass coupling quadrature is unresolved; refine or increase quadrature_order')
    for matrix in (*masses, high[1]):
        for array in (matrix.data, matrix.indices, matrix.indptr):
            array.setflags(write=False)
    diagnostic = dict(unknown='u=Hphi/r' if regular else 'q=r*Hphi',
        measure='r^3 dr dz' if regular else 'dr dz/r',
        physical_relation='2*pi times scalar mass is the full 3D Hphi inner product',
        previous_order=previous_order, current_order=current_order, integration_orders=integration_orders,
        normalized_quadrature_differences=differences, integration_tolerance=1e-10,
        normalized_source_mass_differences=reproduction, source_mass_tolerance=1e-8,
        overlay_triangles=len(overlay.determinants), previous_dofs=len(norms[0]), current_dofs=len(norms[1]),
        scope='original scalar-space inner products only; no eigenmode, frequency or mode identity')
    if geometry_mapping is not None:
        diagnostic.update(mapping='explicit_piecewise_affine',
            transport='unitary cylindrical-component L2 transport; scalar factor derived from H=r*u or H=q/r')
    return HphiMassCoupling(*spaces, masses[0], high[1], masses[1], diagnostic), overlay


def hphi_mass_coupling(previous, current, *, previous_order=2, current_order=2, quadrature_order=12,
                       max_candidate_tests=2000000, max_overlay_triangles=250000, max_dofs=250000, geometry_mapping=None):
    """Assemble C[i,j]=<previous basis i,current basis j> on exact common vacuum.

    The scalar unknown is u on an axis-connected mesh, q on a positive-radius
    mesh. Axis DOFs and the q constant field remain in their complete spaces.
    The two P1/P2 meshes need not be nested. Optional geometry_mapping uses
    density-normalized Hphi transport between declared physical domains;
    otherwise no physical boundary is moved.
    """
    return _coupling(previous, current, previous_order, current_order, quadrature_order,
        max_candidate_tests, max_overlay_triangles, max_dofs, geometry_mapping)[0]


def _direct_errors(coupling, overlay, coefficients, projected, orders, integration_order, regular):
    error = np.zeros(coefficients.shape[1])
    for bary, weight in triangle_quadrature(integration_order):
        fields = []
        for space, cells, vertices, order, values in zip(
                (coupling.previous_space, coupling.current_space), (overlay.previous_cells, overlay.current_cells),
                (overlay.previous_vertex_barycentric, overlay.current_vertex_barycentric), orders, (coefficients, projected)):
            basis = _basis(np.einsum('i,tij->tj', bary, vertices), order)
            fields.append(np.einsum('ti,tim->tm', basis, values[space.cell_dofs[cells]]))
        r = np.einsum('i,ti->t', bary, overlay.vertices_rz_m[:, :, 0])
        measure = overlay.determinants*weight*(r**3 if regular else 1/r)
        if isinstance(overlay, HphiMappedOverlay):
            fields[0] = fields[0]*mapped_transport_factors(overlay, bary, regular=regular)[1][:, None]
        error += np.sum(measure[:, None]*(fields[0]-fields[1])**2, axis=0)
    return error


def project_hphi_coefficients(previous, current, coefficients, *, previous_order=2, current_order=2,
        quadrature_order=12, max_candidate_tests=2000000, max_overlay_triangles=250000, max_dofs=250000, geometry_mapping=None):
    """Return the scalar L2 projection and directly integrated loss for each column.

    This operation fully rebuilds its declared spaces and coupling. Projected
    coefficients are not a solved eigenfield and carry no frequency or RF data.
    """
    raw = np.asarray(coefficients)
    if raw.ndim != 2 or raw.dtype.kind not in 'iuf' or not raw.shape[1] or not np.isfinite(raw).all():
        raise ValueError('Hphi projection coefficients require a finite real matrix with nonempty columns')
    coefficients = np.array(raw, dtype=float, copy=True)
    coupling, overlay = _coupling(previous, current, previous_order, current_order, quadrature_order,
        max_candidate_tests, max_overlay_triangles, max_dofs, geometry_mapping)
    if coefficients.shape[0] != coupling.previous_mass.shape[0]:
        raise ValueError('Hphi projection coefficient rows differ from the declared original scalar space')
    mass = coupling.current_mass
    rhs = coupling.cross_mass.T @ coefficients
    projected = splu(mass.tocsc()).solve(rhs)
    residual = np.linalg.norm(mass @ projected-rhs, axis=0)
    rhs_norm = np.linalg.norm(rhs, axis=0)
    relative_residual = np.divide(residual, rhs_norm, out=np.zeros_like(residual), where=rhs_norm > 0)
    source_norm = np.sum(coefficients*(coupling.previous_mass @ coefficients), axis=0)
    projected_norm = np.sum(projected*(mass @ projected), axis=0)
    if not np.isfinite(source_norm).all() or np.any((source_norm <= 0) & np.any(coefficients != 0, axis=0)):
        raise ValueError('nonzero Hphi projection columns require finite positive mass norms; rescale the coefficients')
    integration_order = coupling.diagnostic['integration_orders'][-1]
    errors = [_direct_errors(coupling, overlay, coefficients, projected, (previous_order, current_order),
        n, type(previous) is AxisConnectedMesh) for n in (integration_order, integration_order+2)]
    relative_errors = [np.sqrt(np.divide(e, source_norm, out=np.zeros_like(e), where=source_norm > 0)) for e in errors]
    pythagoras = np.divide(abs(source_norm-projected_norm-errors[-1]), source_norm,
        out=np.zeros_like(source_norm), where=source_norm > 0)
    if (not all(np.isfinite(x).all() for x in (projected, relative_residual, source_norm, projected_norm, *errors, *relative_errors, pythagoras))
            or np.any(source_norm < 0) or np.max(relative_residual) > 1e-10 or np.max(pythagoras) > 1e-8
            or np.any(projected_norm > source_norm*(1+1e-8)) or np.max(abs(relative_errors[0]-relative_errors[1])) > 1e-10):
        raise ValueError('Hphi L2 projection or its directly integrated error is numerically unresolved')
    projected.setflags(write=False)
    return HphiProjection(projected, dict(coupling=coupling.diagnostic,
        relative_linear_residual=relative_residual.tolist(), linear_residual_tolerance=1e-10,
        source_squared_mass_norm=source_norm.tolist(), projected_squared_mass_norm=projected_norm.tolist(),
        direct_squared_mass_error=errors[-1].tolist(), relative_mass_error=relative_errors[-1].tolist(),
        relative_pythagoras_defect=pythagoras.tolist(), pythagoras_tolerance=1e-8,
        difference_integration_orders=[integration_order, integration_order+2],
        scope='orthogonal projection of original scalar coefficients only; not a new FEM eigenmode or a continuum error bound'))
