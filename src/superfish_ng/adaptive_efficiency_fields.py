# SPDX-License-Identifier: Apache-2.0
"""N06 full supplied-point lookup with unchanged native TM field evaluators.

Curved candidates use the original padded Bernstein boxes and inverse limits.
The tree only accelerates box enumeration; sorted containing candidates, the
original inverse and original physical fields decide every point. This leaf
does not establish full-domain sampling, source provenance or individual IDs.
"""
import numpy as np
from scipy.spatial import cKDTree

from .curved_solution import CurvedSolution
from .sampling import FieldSampler
from .solver import Solution


COMPONENTS = ('Er_quadrature_V_per_m', 'Ez_quadrature_V_per_m', 'Hphi_A_per_m')


class EfficiencyFieldSampler:
    """Address each supplied point once, then evaluate all requested real modes.

No smoothing, fitting, outside-node removal, altered inverse tolerances or
analytic replacement occurs. Affine P2 uses FieldSampler unchanged. Curved
P2 batches fields_in_cell at the original inverse coordinates for each mode.
The caller must bind saved sources, whole Case/domain and actual mode IDs.
"""
    def __init__(self, solution):
        if type(solution) not in (Solution, CurvedSolution) or solution.element_order != 2:
            raise ValueError('efficiency samples require native vacuum axisymmetric TM P2 Solution or CurvedSolution')
        if isinstance(solution, CurvedSolution):
            model = solution.case.model
            if (model is None or (model.physics, model.coordinates, model.polarization, model.azimuthal_index) !=
                    ('rf_eigenmode', 'axisymmetric', 'tm', 0) or solution.case.z_min != 'pec' or
                    solution.case.z_max != 'pec' or model.to_dict()['materials'] != [dict(id='vacuum', type='vacuum')] or
                    model.to_dict()['regions'] != [dict(id='cavity', material='vacuum', domain='interior')]):
                raise ValueError('efficiency samples require closed vacuum axis-connected m=0 TM P2')
        u = np.asarray(solution.u)
        frequencies = np.asarray(solution.frequencies_hz)
        if (u.dtype.kind not in 'iuf' or frequencies.dtype.kind not in 'iuf' or
                frequencies.ndim != 1 or not len(frequencies) or u.ndim != 2 or
                u.shape[1] != len(frequencies) or not np.isfinite(u).all() or
                not np.isfinite(frequencies).all() or np.any(frequencies <= 0)):
            raise ValueError('efficiency samples require finite real native coefficients and positive frequencies')
        if isinstance(solution, CurvedSolution) and (
                u.shape[0] != len(solution.space.geometry.points_rz_m) or len(frequencies) != solution.case.modes):
            raise ValueError('curved efficiency coefficients and mode count must match the original P2 space and Case')
        self.solution = solution
        self.native_sampler = FieldSampler.from_solution(solution)
        self.curved = isinstance(solution, CurvedSolution)
        if self.curved:
            low, high = self.native_sampler.lower, self.native_sampler.upper
            # An infinity-norm ball conservatively contains each original
            # padded box. Guard the centre/subtraction rounding separately;
            # the final box check is exactly the old one, without enlargement.
            centres = low/2 + high/2
            half_width = np.maximum(centres-low, high-centres)
            scale = float(np.max(np.abs(np.concatenate((low, high)))))
            self.radius = float(np.nextafter(np.max(half_width)+8*np.finfo(float).eps*scale, np.inf))
            if not np.isfinite(centres).all() or not np.isfinite(self.radius) or self.radius <= 0:
                raise ValueError('curved candidate tree geometry UNVERIFIED: nonfinite radius or centres')
            self.tree = cKDTree(centres)

    def candidate_cells(self, point):
        """Return exactly the original containing curved boxes, in cell order."""
        raw = np.asarray(point)
        if not self.curved or raw.dtype.kind not in 'iuf' or raw.shape != (2,) or not np.isfinite(raw).all():
            raise ValueError('candidate_cells requires a curved sampler and two finite real coordinates')
        # Exact search: no nearest-k truncation or approximate KD-tree epsilon.
        candidates = np.array(sorted(self.tree.query_ball_point(raw, self.radius, p=np.inf, eps=0)), dtype=np.int64)
        low, high = self.native_sampler.lower[candidates], self.native_sampler.upper[candidates]
        return candidates[np.all(raw >= low, axis=1) & np.all(raw <= high, axis=1)]

    def evaluate(self, points_rz_m, *, modes=None):
        """Return N by selected-mode by (Er,Ez,Hphi), or fail without dropping.

        ALL_SUPPLIED_POINTS_LOCATED is a lookup claim, not a whole-domain
        accuracy/ID claim. Inverse exhaustion remains UNVERIFIED; an original
        BaseException propagates. No partial array is returned after a failure.
        """
        raw = np.asarray(points_rz_m)
        if (raw.dtype.kind not in 'iuf' or raw.ndim != 2 or raw.shape[1] != 2 or not len(raw) or
                not np.isfinite(raw).all() or np.any(raw[:,0] < 0)):
            raise ValueError('efficiency probes require nonempty finite real N by 2 (r,z) metres with r>=0')
        modes = list(range(len(self.solution.frequencies_hz))) if modes is None else modes
        if (type(modes) not in (tuple, list) or not modes or
                any(type(m) is not int or not 0 <= m < len(self.solution.frequencies_hz) for m in modes) or
                len(set(modes)) != len(modes)):
            raise ValueError('efficiency modes require unique valid zero-based integers')
        points = raw.astype(float)
        fields = np.empty((len(points), len(modes), 3))
        if not self.curved:
            for output, mode in enumerate(modes):
                values = self.native_sampler.evaluate(points, mode=mode, outside='raise')
                if not np.asarray(values['inside']).all():
                    raise ValueError('affine efficiency samples UNVERIFIED: missing native points')
                fields[:,output] = np.column_stack([values[key] for key in COMPONENTS])
        else:
            cells = np.empty(len(points), dtype=np.int64)
            coordinates = np.empty_like(points)
            for index, point in enumerate(points):
                unresolved = []
                for cell in self.candidate_cells(point):
                    try:
                        reference = self.native_sampler.locators[int(cell)].inverse(point, max_iterations=30, max_boxes=1024)
                    except ValueError as error:
                        unresolved.append(str(error))
                        continue
                    if reference is None:
                        continue
                    cells[index], coordinates[index] = cell, reference
                    break
                else:
                    if unresolved:
                        raise ValueError(f'curved efficiency point {index} UNVERIFIED: {unresolved[0]}')
                    raise ValueError(f'curved efficiency point {index} lies outside the mapped mesh')
            # Sort point addresses once. No repeated full N mask per cell; each
            # field batch still uses the original native evaluator unchanged.
            ordered = np.argsort(cells, kind='stable')
            cuts = np.flatnonzero(np.r_[True, np.diff(cells[ordered]) != 0, True])
            for start, stop in zip(cuts[:-1], cuts[1:]):
                indices = ordered[start:stop]
                cell = int(cells[indices[0]])
                for output, mode in enumerate(modes):
                    values = self.solution.fields_in_cell(cell, coordinates[indices], mode=mode)
                    fields[indices,output] = np.column_stack([values[key] for key in COMPONENTS])
        if not np.isfinite(fields).all():
            raise ValueError('efficiency samples UNVERIFIED: nonfinite native fields')
        return dict(fields=fields, mode_indices=list(modes), sample_count=len(points),
                    component_order=list(COMPONENTS), coverage_status='ALL_SUPPLIED_POINTS_LOCATED',
                    physical_error_bound=None,
                    scope='original native fields at every supplied point; no source/domain/individual-ID or physical accuracy acceptance')
