# SPDX-License-Identifier: Apache-2.0
"""Adjacent nested FEM comparisons using physical area integrals and one phase."""
import numpy as np
from .fem import triangle_quadrature
from .planar import PlanarSolution, planar_matrices, planar_quantities, _restore
from .planar_refinement import planar_refinement_relation, _transfer_matrix
from .planar_convergence import PlanarConvergence


def _verified_solution(solution, project):
    if not isinstance(solution, PlanarSolution) or solution.case.to_dict() != project.case.to_dict():
        raise ValueError('planar convergence solution does not match the declared level case')
    space, stiffness, mass, free = planar_matrices(project.case)
    for name in space.__dataclass_fields__:
        if not np.array_equal(getattr(space, name), getattr(solution.space, name)):
            raise ValueError('planar convergence solution mesh differs from the declared level')
    return _restore(project.case, space, stiffness, mass, free,
                    solution.coefficients, solution.frequencies_hz, verify_spectrum=True)


def _adjacent(coarse, fine, coarse_mesh, fine_mesh, ranks, thresholds):
    parents, child_bary = planar_refinement_relation(coarse_mesh, fine_mesh)
    transfer = _transfer_matrix(coarse.space, fine.space, parents, child_bary, coarse.case.element_order)
    old, new = coarse.coefficients, fine.coefficients
    cross = old.T @ (transfer.T @ (fine.mass @ new))
    old_norm = np.sqrt(np.sum(old * (coarse.mass @ old), axis=0))
    new_norm = np.sqrt(np.sum(new * (fine.mass @ new), axis=0))
    overlaps = cross / np.outer(old_norm, new_norm)
    if not np.isfinite(overlaps).all() or np.max(abs(overlaps)) > 1 + 1e-10:
        raise ValueError('invalid physical scalar overlap on planar refinement')
    absolute = np.minimum(abs(overlaps), 1.)
    rows = []
    for rank in ranks:
        mode = rank - 1
        reasons = []
        if rank == coarse.case.modes:
            reasons.append('upper spectral neighbor was not computed')
        gaps = []
        for solution in (coarse, fine):
            f = solution.frequencies_hz
            neighbors = [i for i in (mode - 1, mode + 1) if 0 <= i < len(f)]
            gaps.extend(abs(float(f[i]/f[mode] - 1)) for i in neighbors)
        neighborhood = [i for i in (mode - 1, mode, mode + 1) if 0 <= i < coarse.case.modes]
        drift = max(abs(float(coarse.frequencies_hz[i]/fine.frequencies_hz[i] - 1)) for i in neighborhood)
        required_gap = max(thresholds.spectral_gap_relative, 2*drift)
        if not gaps or min(gaps) <= required_gap:
            reasons.append('spectral separation is unresolved or near-degenerate')
        other_row = np.delete(absolute[mode], mode)
        other_column = np.delete(absolute[:, mode], mode)
        competitor = max(np.max(other_row, initial=0.), np.max(other_column, initial=0.))
        overlap = float(absolute[mode, mode])
        margin = float(overlap - competitor)
        if overlap < thresholds.minimum_overlap or margin < thresholds.overlap_margin:
            reasons.append('same-rank scalar overlap is not uniquely dominant')
        phase = 1 if cross[mode, mode] >= 0 else -1
        errors = dict(E=0., H=0.)
        norms = dict(E=0., H=0.)
        cells = np.arange(len(fine.space.triangles))
        for bary, weight in triangle_quadrature(5):
            fine_bary = np.broadcast_to(bary, (len(cells), 3))
            old_bary = np.einsum('j,njk->nk', bary, child_bary)
            a = coarse.fields_in_cells(parents, old_bary, mode)
            b = fine.fields_in_cells(cells, fine_bary, mode)
            weights = weight * fine.space.determinants
            for key in a:
                field = key[0]
                errors[field] += float(weights @ (phase*a[key] - b[key])**2)
                norms[field] += float(weights @ b[key]**2)
        if not np.isfinite(list(errors.values()) + list(norms.values())).all() or min(norms.values()) <= 0:
            raise ValueError('invalid planar field difference integral')
        qa, qb = (planar_quantities(s, mode) for s in (coarse, fine))
        rf_names = ('stored_energy_j_per_m', 'electric_energy_j_per_m', 'magnetic_energy_j_per_m',
                    'wall_loss_w_per_m', 'surface_resistance_ohm', 'q0', 'geometry_factor_ohm')
        rf = {name: abs(float(qa[name]/qb[name] - 1)) for name in rf_names}
        delta = float(coarse.frequencies_hz[mode]/fine.frequencies_hz[mode] - 1)
        if delta < -1e-10:
            reasons.append('frequency increased under conforming refinement beyond roundoff')
        rows.append(dict(mode_rank=rank, correspondence='UNVERIFIED' if reasons else 'same_rank_overlap_verified',
                         reasons=reasons, scalar_overlap=overlap, overlap_margin=margin,
                         minimum_spectral_gap_relative=min(gaps) if gaps else None,
                         neighborhood_frequency_drift_relative=drift,
                         required_spectral_gap_relative=required_gap,
                         coarse_phase_multiplier=phase, frequency_relative=abs(delta),
                         electric_field_relative=float(np.sqrt(errors['E']/norms['E'])),
                         magnetic_field_relative=float(np.sqrt(errors['H']/norms['H'])),
                         rf_relative=rf, rf_max_relative=max(rf.values()),
                         r_over_q_accelerator_ohm=None, r_over_q_circuit_ohm=None))
    return dict(scalar_overlap_matrix=overlaps.tolist(), modes=rows)


def compare_planar_convergence(request, solutions):
    """Reverify every solution; judge the last two pairs, never a true error bound.

    Near degeneracy is conservatively UNVERIFIED. This routine does not assign
    persistent mode identities or infer uncomputed neighboring eigenmodes.
    """
    if not isinstance(request, PlanarConvergence):
        raise ValueError('expected a PlanarConvergence request')
    projects = request.projects()
    if not isinstance(solutions, (list, tuple)) or len(solutions) != request.levels:
        raise ValueError('planar convergence requires every declared refinement level')
    verified = [_verified_solution(solution, project) for solution, project in zip(solutions, projects)]
    # The first solution may retain rectangle schema 1; its explicit boundary is
    # exactly the polygon declaration retained by the subsequent schema 2 levels.
    from .planar_mesh import PlanarMesh
    meshes = [PlanarMesh.create(projects[1].case.mesh.polygon_xy_m,
                               solution.space.points_xy_m, solution.space.triangles)
              for solution in verified]
    comparisons = [_adjacent(a, b, ma, mb, request.mode_ranks, request.thresholds)
                   for a, b, ma, mb in zip(verified[:-1], verified[1:], meshes[:-1], meshes[1:])]
    decisions = []
    for index, rank in enumerate(request.mode_ranks):
        previous, last = (pair['modes'][index] for pair in comparisons[-2:])
        correspondence = all(row['correspondence'] == 'same_rank_overlap_verified' for row in (previous, last))
        checks = {}
        for name, limit in (
                ('frequency_relative', request.thresholds.frequency_relative),
                ('electric_field_relative', request.thresholds.electric_field_relative),
                ('magnetic_field_relative', request.thresholds.magnetic_field_relative),
                ('rf_max_relative', request.thresholds.rf_relative)):
            stable = last[name] <= previous[name] + max(1e-12, previous[name]*1e-8)
            checks[name] = dict(passed=bool(correspondence and stable and last[name] <= limit),
                                last=last[name], previous=previous[name], threshold=limit,
                                nonincreasing=bool(stable))
        decisions.append(dict(mode_rank=rank, status='PASS' if all(c['passed'] for c in checks.values()) else 'UNVERIFIED',
                              correspondence_verified=correspondence, checks=checks))
    return dict(format='superfish_ng_planar_convergence_result', result_version=1,
                request=request.to_dict(), status='PASS' if all(d['status'] == 'PASS' for d in decisions) else 'UNVERIFIED',
                comparisons=comparisons, decisions=decisions,
                interpretation='three-finest-level difference diagnostic; not a true discretization error bound',
                surface_peak_accuracy='not_checked', mode_tracking='not_performed')
