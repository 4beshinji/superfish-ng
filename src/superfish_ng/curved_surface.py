# SPDX-License-Identifier: Apache-2.0
"""One-sided curved boundary traces and explicitly sampled surface estimates."""
import numpy as np
from .curved_solution import CurvedSolution

_REFERENCE = np.array([[0., 0.], [1., 0.], [0., 1.]])


class CurvedSurfaceSampler:
    def __init__(self, solution):
        if not isinstance(solution, CurvedSolution):
            raise ValueError('curved surface sampling requires a CurvedSolution')
        self.solution = solution
        geometry = solution.space.geometry
        incidence = {}
        for cell, nodes in enumerate(geometry.cell_nodes):
            for edge, (a, b) in enumerate(((0, 1), (1, 2), (2, 0))):
                key = tuple(sorted((int(nodes[a]), int(nodes[b]))))
                incidence.setdefault(key, []).append((cell, a, b, int(nodes[3+edge])))
        self.owners = []
        for start, end, mid in geometry.boundary_nodes:
            entries = incidence.get(tuple(sorted((int(start), int(end)))), [])
            if len(entries) != 1 or entries[0][3] != mid:
                raise ValueError('surface edge must have exactly one conforming adjacent cell')
            cell, a, b, _ = entries[0]
            direction = 1 if geometry.cell_nodes[cell, a] == start else -1
            self.owners.append((cell, a, b, direction))

    def evaluate(self, boundary_index, parameters, mode=0):
        """Parameters follow stored endpoints; unit tangent follows cell CCW order.

        Outward normal in (r,z) is (t_z,-t_r). At a corner, each adjacent
        boundary edge keeps its own cell derivative; no averaging is applied.
        """
        if type(boundary_index) is not int or not 0 <= boundary_index < len(self.owners):
            raise ValueError('boundary_index must be a valid zero-based integer')
        raw = np.asarray(parameters)
        if (raw.dtype.kind not in 'iuf' or raw.ndim != 1 or not len(raw)
                or not np.isfinite(raw).all() or np.any(raw < 0) or np.any(raw > 1)):
            raise ValueError('surface parameters must be finite one-dimensional fractions in [0,1]')
        cell, a, b, direction = self.owners[boundary_index]
        t = raw.astype(float) if direction == 1 else 1-raw.astype(float)
        reference = (1-t[:, None])*_REFERENCE[a]+t[:, None]*_REFERENCE[b]
        mapping = self.solution.space.geometry.local_maps[cell]
        mapped = mapping.evaluate(reference)
        tangent = mapped['jacobian']@(_REFERENCE[b]-_REFERENCE[a])
        lengths = np.linalg.norm(tangent, axis=1)
        if not np.isfinite(lengths).all() or np.any(lengths <= 0):
            raise ValueError('surface tangent is zero or nonfinite')
        tangent = tangent/lengths[:, None]
        normal = np.column_stack((tangent[:, 1], -tangent[:, 0]))
        fields = self.solution.fields_in_cell(cell, reference, mode)
        electric = np.column_stack((fields['Er_quadrature_V_per_m'], fields['Ez_quadrature_V_per_m']))
        return dict(**fields, normal_rz=normal, tangent_rz=tangent,
                    arc_length_derivative_m=lengths,
                    En_quadrature_V_per_m=np.sum(electric*normal, axis=1),
                    Et_quadrature_V_per_m=np.sum(electric*tangent, axis=1),
                    E_abs_V_per_m=np.linalg.norm(electric, axis=1))


def sampled_surface_summary(solution, mode=0, *, samples_per_edge=17):
    """PEC-only sample maxima; these are not continuous extrema or error bounds."""
    if type(samples_per_edge) is not int or samples_per_edge < 2:
        raise ValueError('samples_per_edge must be an integer >= 2')
    sampler = CurvedSurfaceSampler(solution)
    parameters = np.linspace(0, 1, samples_per_edge)
    indices = np.flatnonzero(solution.space.boundary_tags == 'pec')
    if not len(indices):
        raise ValueError('surface estimates require a PEC boundary')
    fields = [sampler.evaluate(int(i), parameters, mode) for i in indices]
    result = dict(status='sampled estimates; continuous extrema and mesh convergence not certified',
                  samples_per_edge=samples_per_edge, pec_edges=len(indices),
                  corner_convention='one-sided cell derivatives; every edge endpoint retained')
    for key in ('E_abs_V_per_m', 'Hphi_A_per_m', 'Et_quadrature_V_per_m'):
        values = np.concatenate([abs(field[key]) for field in fields])
        index = int(np.argmax(values))
        edge, sample = divmod(index, samples_per_edge)
        result[key] = dict(value=float(values[index]), boundary_index=int(indices[edge]),
                           parameter=float(parameters[sample]),
                           points_rz_m=fields[edge]['points_rz_m'][sample].tolist())
    return result
