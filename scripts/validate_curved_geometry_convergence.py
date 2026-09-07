# SPDX-License-Identifier: Apache-2.0
"""Separate native conic geometry convergence from fixed-geometry FEM checks."""
import argparse
from dataclasses import replace
import json
import math
from pathlib import Path
import numpy as np
from superfish_ng import Case
from superfish_ng.project import Project
from superfish_ng.studies import Study, execute_study, compare_refinement
from superfish_ng.saved import read_solution
from superfish_ng.fem import triangle_quadrature


def exact_moments(name):
    # Independent integrals of the explicit example meridians, not solver inputs.
    if name == 'ellipse':
        a, b = .1, .08
        return math.pi*a*b/2, 4*math.pi*a*b*b/3
    a, b, half_length = .05, .08, .05
    t = half_length/b
    return (a*(half_length*math.sqrt(1+t*t)+b*math.asinh(t)),
            math.pi*a*a*(2*half_length+2*half_length**3/(3*b*b)))


def mapped_moments(space):
    rule = list(triangle_quadrature(order=6))
    coordinates = [bary[1:] for bary, _ in rule]
    weights = np.array([w for _, w in rule])
    area, volume = [], []
    for mapping in space.geometry.local_maps:
        result = mapping.evaluate(coordinates)
        measure = weights*result['determinant_m2']
        area.append(float(measure.sum()))
        volume.append(float(2*math.pi*(measure*result['points_rz_m'][:, 0]).sum()))
    return math.fsum(area), math.fsum(volume)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--factors', type=float, nargs=3, default=[1., .0625, .015625],
                        help='three decreasing chord-tolerance factors; use 1 .25 .0625 to reproduce the initial failed series')
    args = parser.parse_args()
    if not all(math.isfinite(v) and v>0 for v in args.factors) or not all(a>b for a,b in zip(args.factors,args.factors[1:])):
        parser.error('--factors must be three finite positive decreasing values')
    args.out.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[1]
    shapes = {}
    for name in ('ellipse', 'hyperbola'):
        original = replace(Case.load(root/f'examples/curved_{name}.json'), geometry_order=2, quadrature_order=12)
        reference = exact_moments(name)
        analytic = (original.curved_contour.area_m2, original.curved_contour.volume_m3)
        if not np.allclose(analytic, reference, rtol=1e-12, atol=0):
            raise ValueError('example differs from independent analytic moment specification')
        levels, comparisons = [], []
        previous = None
        for i, factor in enumerate(args.factors):
            case = replace(original, contour=None, curve_chord_tolerance_m=original.curve_chord_tolerance_m*factor)
            directory = args.out/f'{name}-geometry-{i}'
            study = Study(Project.from_dict(case.to_dict()), 'fixed_geometry_convergence',
                          '/case/mesh/curved_refinement_levels', [0, 1])
            result = execute_study(study, directory)
            current = directory/'point-002'/'solution'
            print(name, i, 'revalidating saved fine space', flush=True)
            saved = read_solution(current)
            actual = mapped_moments(saved.space)
            errors = dict(zip(('area', 'volume'), (abs(a/b-1) for a,b in zip(actual,reference))))
            levels.append(dict(chord_tolerance_m=case.curve_chord_tolerance_m,
                               cells=len(saved.space.geometry.cell_nodes), moments=actual,
                               relative_moment_errors=errors, fem_comparisons=result['comparisons'],
                               fem_status=result['numerical_status']))
            if previous is not None:
                print(name, i, 'comparing adjacent geometry approximations', flush=True)
                comparisons.append(compare_refinement(previous, current))
            previous = current
            print(name, i, result['numerical_status'], errors, flush=True)
        decreasing = all(levels[i+1]['relative_moment_errors'][key] < levels[i]['relative_moment_errors'][key]
                         for i in range(2) for key in ('area', 'volume'))
        gates = dict(moment_errors_decrease=decreasing,
                     final_moments=all(e<1e-5 for e in levels[-1]['relative_moment_errors'].values()),
                     fixed_geometry_fem=all(x['fem_status']=='PASS' for x in levels),
                     final_geometry_comparison=comparisons[-1]['status']=='PASS')
        shapes[name] = dict(status='PASS' if all(gates.values()) else 'FAIL', gates=gates,
                            reference_moments=reference, levels=levels, geometry_comparisons=comparisons)
    report = dict(status='PASS' if all(x['status']=='PASS' for x in shapes.values()) else 'FAIL', shapes=shapes,
                  limits=dict(final_relative_area_and_volume=1e-5), geometry_factors=args.factors,
                  scope='three quadratic geometry approximations, each checked by independent fixed-geometry FEM refinement; final paired field/RF change',
                  interpretation='cross-geometry field/RF changes include remaining FEM error; moment convergence alone does not bound local boundary error',
                  physical_peak_convergence='UNVERIFIED')
    (args.out/'comparison.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(report['status'], flush=True)
    return 0 if report['status']=='PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
