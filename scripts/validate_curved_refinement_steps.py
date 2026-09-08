# SPDX-License-Identifier: Apache-2.0
"""Native ordered refinement versus independent dense FEM and cylinder physics."""
import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from superfish_ng import solve
from superfish_ng.analytic import pillbox_tm010
from superfish_ng.conics import LineSegment
from superfish_ng.curved_fem import assemble_curved
from superfish_ng.curved_marked_refinement import refine_marked_curved_space
from superfish_ng.curved_refinement_steps import CurvedRefinementStep
from superfish_ng.curved_rf import quantities_curved
from superfish_ng.curved_saved import geometry_arrays
from superfish_ng.curved_space import case_curved_space
from superfish_ng.io import save_run
from superfish_ng.mesh import make_mesh
from superfish_ng.saved import read_solution
from validate_curved_marked_refinement import scaled_case, dense_solution


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    out = parser.parse_args().out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    def hashes():
        return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for folder in ('src', 'tests', 'scripts', 'examples')
                for p in sorted((ROOT/folder).rglob('*'))
                if p.is_file() and '__pycache__' not in p.parts}
    before = hashes()
    keys = ('frequency_hz', 'r_over_q_accelerator_ohm', 'geometry_factor_ohm',
            'epk_over_eacc_estimate', 'bpk_over_eacc_estimate_mt_per_mv_per_m')
    checks = {}
    for kind in ('cylinder', 'ellipse', 'hyperbola'):
        rows = []
        for scale in (1., 2.):
            base = replace(scaled_case(kind, scale), quadrature_order=12)
            parent = case_curved_space(base, make_mesh(base))
            g = parent.geometry
            edges = [i for i, (tag, owner) in enumerate(zip(parent.boundary_tags, g.boundary_curve_indices))
                     if tag == 'pec' and not isinstance(base.curved_contour.curves[int(owner)], LineSegment)]
            edge = g.boundary_nodes[edges[0] if edges else int(np.flatnonzero(parent.boundary_tags == 'pec')[0]), :2]
            marked = next(i for i, nodes in enumerate(g.cell_nodes) if all(v in nodes[:3] for v in edge))
            case = replace(base, curved_refinement_steps=(CurvedRefinementStep('marked', (marked,), 5.),))
            manual = refine_marked_curved_space(parent, [marked]).space
            dense = dense_solution(case, manual, assemble_curved(manual, quadrature_order=12))
            name = f'{kind}-s{scale:g}'
            run = out/name
            if kind == 'cylinder' and scale == 1.:
                case_path = out/'cli-case.json'
                case_path.write_text(json.dumps(case.to_dict(), indent=2)+'\n')
                command = [sys.executable, '-m', 'superfish_ng', 'solve', str(case_path), '--out', str(run)]
                completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                           env=dict(os.environ, PYTHONPATH=str(ROOT/'src')))
                (out/'cli.log').write_text(completed.stdout+completed.stderr)
                if completed.returncode:
                    raise RuntimeError(f'CLI solve failed: see {out / "cli.log"}')
            else:
                solution = solve(case)
                save_run(case, solution, run)
            with patch('superfish_ng.curved_solution.eigsh', side_effect=AssertionError('native replay must not solve')):
                native = read_solution(run)
            arrays_equal = all(np.array_equal(value, geometry_arrays(native.space)[key])
                               for key, value in geometry_arrays(manual).items())
            q = quantities_curved(native)
            reference_q = quantities_curved(dense)
            agreement = {key: abs(q[key]/reference_q[key]-1) for key in keys}
            frequencies = np.abs(native.frequencies_hz/dense.frequencies_hz-1).tolist()
            errors = None
            if kind == 'cylinder':
                analytical = pillbox_tm010(.1*scale, .08*scale)
                errors = {key: abs(q[key]/analytical[key]-1) for key in keys}
            passed = (arrays_equal and native.case == case and max(agreement.values()) < 2e-8
                      and max(frequencies) < 1e-10 and max(native.residuals) < 1e-7)
            if errors is not None:
                passed = passed and errors[keys[0]] < 1e-4 and max(errors[k] for k in keys[1:3]) < .005 and max(errors[k] for k in keys[3:]) < .01
            rows.append(dict(passed=bool(passed), scale=scale, native_run=name,
                             triangles=len(native.space.geometry.cell_nodes), geometry_arrays_exact=arrays_equal,
                             dense_fem_rf_relative_errors=agreement, dense_fem_frequency_relative_errors=frequencies,
                             cylinder_analytical_errors=errors, rf=q, eigenpair_residuals=native.residuals.tolist()))
        similarity = {key: abs(rows[1]['rf'][key]*(2 if key == 'frequency_hz' else 1)/rows[0]['rf'][key]-1) for key in keys}
        checks[kind] = dict(passed=all(row['passed'] for row in rows) and max(similarity.values()) < 2e-8,
                            series=rows, similarity_relative_errors=similarity)
    unchanged = before == hashes()
    passed = unchanged and all(check['passed'] for check in checks.values())
    (out/'validation.json').write_text(json.dumps(dict(passed=passed, checks=checks, source_sha256=before,
        source_changed_during_run=not unchanged,
        scope='native local history, actual CLI/FEM solve, no-solve verified reconstruction, independent dense FEM, cylinder five quantities and Maxwell similarity; no automatic curved adaptation or physical error bound'), indent=2, allow_nan=False)+'\n')
    print(f'Curved refinement history {"PASS" if passed else "FAIL"}: {out}')
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
