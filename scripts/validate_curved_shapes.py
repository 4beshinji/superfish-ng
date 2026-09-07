# SPDX-License-Identifier: Apache-2.0
"""Exercise native ellipse/hyperbola P2 refinement and hyperbola reflection."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import numpy as np
from superfish_ng import Case, solve
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution
from superfish_ng.project import Project
from superfish_ng.studies import Study, execute_study
from superfish_ng.symmetry import reflect_solution
from superfish_ng.curved_rf import quantities_curved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[1]
    studies, reflections = {}, []
    for name in ('ellipse', 'hyperbola'):
        case = replace(Case.load(root/f'examples/curved_{name}.json'), geometry_order=2, quadrature_order=12)
        study = Study(Project.from_dict(case.to_dict()), 'fixed_geometry_convergence',
                      '/case/mesh/curved_refinement_levels', [0, 1])
        report = execute_study(study, args.out/f'{name}-fixed')
        studies[name] = dict(status=report['numerical_status'], comparisons=report['comparisons'])
        print(name, report['numerical_status'], flush=True)
        if name != 'hyperbola':
            continue
        for side, edge in (('z_min', 3), ('z_max', 1)):
            for tag in ('electric_symmetry', 'magnetic_symmetry'):
                tags = list(case.curved_contour.edge_tags)
                tags[edge] = tag
                half_case = replace(case, contour=None,
                                    curved_contour=replace(case.curved_contour, edge_tags=tuple(tags)))
                half = solve(half_case)
                full_case, full = reflect_solution(half_case, half)
                directory = args.out/f'hyperbola-{side}-{tag}'
                save_run(full_case, full, directory)
                restored = read_solution(directory)
                a, b = quantities_curved(half), restored.results['modes'][0]
                ratios = {key: b[key]/a[key] for key in ('stored_energy_j', 'electric_energy_j', 'magnetic_energy_j', 'wall_loss_w')}
                residual = float(max(restored.residuals))
                parity = 1 if tag == 'electric_symmetry' else -1
                errors = []
                for i in range(len(half.space.geometry.cell_nodes)):
                    old = half.fields_in_cell(i, [[.2, .3]])
                    new = restored.fields_in_cell(i+len(half.space.geometry.cell_nodes), [[.3, .2]])
                    for key, sign in (('Hphi_A_per_m', parity), ('Er_quadrature_V_per_m', -parity), ('Ez_quadrature_V_per_m', parity)):
                        errors.append(float(np.max(abs(new[key]-sign*old[key])))/max(1., float(np.max(abs(old[key])))))
                passed = residual < 1e-7 and max(errors) < 1e-8 and all(abs(v/2-1) < 1e-10 for v in ratios.values())
                reflections.append(dict(side=side, tag=tag, status='PASS' if passed else 'FAIL',
                                        residual=residual, parity_relative_error=max(errors), ratios=ratios,
                                        corner_diagnostics=restored.results['surface_corner_diagnostics']))
                print(side, tag, reflections[-1]['status'], flush=True)
    passed = all(s['status']=='PASS' for s in studies.values()) and all(r['status']=='PASS' for r in reflections)
    report = dict(status='PASS' if passed else 'FAIL', studies=studies, reflections=reflections,
                  scope='fixed quadratic geometry FEM convergence and portable hyperbola reflection invariants',
                  physical_peak_convergence='UNVERIFIED',
                  geometric_convergence='not assessed by fixed geometry refinement')
    (args.out/'comparison.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(report['status'], flush=True)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
