# SPDX-License-Identifier: Apache-2.0
"""Check fixed curved geometry refinement by Galerkin energy restriction."""
import argparse
import json
from pathlib import Path
import numpy as np
from superfish_ng import Case
from superfish_ng.mesh import make_mesh
from superfish_ng.curved_space import curved_space
from superfish_ng.curved_refinement import refine_curved_space
from superfish_ng.curved_fem import assemble_curved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    case = Case.load(Path(__file__).resolve().parents[1]/'examples/curved_ellipse.json')
    parent = curved_space(case, make_mesh(case))
    result = refine_curved_space(parent)
    p = result.prolongation
    errors = {}
    for order in (8, 12):
        coarse = assemble_curved(parent, quadrature_order=order)
        fine = assemble_curved(result.space, quadrature_order=order)
        errors[str(order)] = {name: float(np.linalg.norm((p.T@b@p-a).data)/np.linalg.norm(a.data))
                              for name, a, b in zip(('stiffness', 'mass'), coarse, fine)}
    passed = all(value < 1e-10 for pair in errors.values() for value in pair.values())
    report = dict(status='PASS' if passed else 'FAIL', relative_matrix_errors=errors,
                  limits=dict(stiffness=1e-10, mass=1e-10),
                  parent_cells=len(parent.geometry.cell_nodes), refined_cells=len(result.space.geometry.cell_nodes),
                  edge_check=dict(result.space.edge_check),
                  meaning='P transpose K_refined P = K_parent and same for mass; fixed quadratic geometry',
                  pending='curved GUI acceptance, surface peaks and reflection')
    (args.out/'comparison.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps(report, indent=2), flush=True)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
