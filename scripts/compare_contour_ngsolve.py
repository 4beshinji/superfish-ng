# SPDX-License-Identifier: Apache-2.0
"""G02 generated polygon meshes against independent Netgen/Hphi P3 fields."""
import argparse
import importlib.metadata
import json
import time
from pathlib import Path
import numpy as np
from compare_ngsolve import reference, acceptance, fingerprints, probe_points, Case, LIMITS
from superfish_ng import solve
from superfish_ng.contour import Contour
from superfish_ng.contour_mesh import quality_contour_mesh, contour_mesh_quality
from superfish_ng.mesh_input import mesh_to_dict
from superfish_ng.rf import quantities
from superfish_ng.sampling import FieldSampler


def electric_difference(a,b):
    h1,h2 = np.asarray(a['hphi_probes_a_per_m']),np.asarray(b['hphi_probes_a_per_m'])
    sign = 1 if np.dot(h1,h2)>=0 else -1
    e1,e2 = np.asarray(a['electric_probes_v_per_m']),np.asarray(b['electric_probes_v_per_m'])
    return float(np.linalg.norm(sign*e1-e2)/np.linalg.norm(e2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--sizes',type=float,nargs='+',default=[.012,.006,.003])
    parser.add_argument('--cases',choices=['frustum','folded'],nargs='+',default=['frustum','folded'])
    args = parser.parse_args()
    if (len(args.sizes)<3 or any(not np.isfinite(h) or h<=0 for h in args.sizes)
            or any(a<=b for a,b in zip(args.sizes,args.sizes[1:]))):
        parser.error('sizes require at least three strictly decreasing positive finite values')
    args.out.mkdir(parents=True,exist_ok=False)
    frustum = Case(((0.,.08),(.12,.10)),modes=1)
    polygon = Case((),contour=Contour.from_profile(frustum),modes=1,element_order=2)
    folded = Case((),contour=Contour(tuple((z*.03,r*.03) for z,r in
                  ((0,0),(3,0),(3,2),(1,2),(1,1),(2,1),(2,.5),(0,.5))),
                  ('axis',)+('pec',)*7),modes=1,element_order=2)
    probes = np.array([[r,z] for z in (.015,.045,.075) for r in (.003,.009)]
                      +[[r,z] for z in (.045,.075) for r in (.036,.051)]
                      +[[.0225,.075]])
    report = dict(passed=False,source_sha256=fingerprints(),limits_relative=LIMITS,
                  environment={name:importlib.metadata.version(name) for name in
                               ('numpy','scipy','ngsolve','netgen-mesher')},cases={},
                  not_verified=['surface peaks at singular corners','higher modes','measured structures',
                                'fully independent eigensolver','CLI/GUI automatic mesh configuration'])
    try:
        for name,case,positions in [('frustum',polygon,probe_points(frustum)),('folded',folded,probes)]:
            if name not in args.cases:
                continue
            entry = dict(case=case.to_dict(),probe_points_rz_m=positions.tolist(),native=[],reference=[])
            report['cases'][name]=entry
            for size in args.sizes:
                start = time.perf_counter()
                mesh = quality_contour_mesh(case,size)
                solution = solve(case,mesh_data=mesh_to_dict(mesh))
                row = quantities(case,solution)
                samples = FieldSampler.from_solution(solution).evaluate(positions)
                row.update(hphi_probes_a_per_m=samples['Hphi_A_per_m'].tolist(),
                           electric_probes_v_per_m=np.column_stack((samples['Er_quadrature_V_per_m'],
                                                                  samples['Ez_quadrature_V_per_m'])).tolist(),
                           max_edge_m=size,mesh_quality=contour_mesh_quality(mesh),
                           dofs=len(solution.u),seconds=time.perf_counter()-start)
                entry['native'].append(row)
                print(name,'native',size,row['frequency_hz'],flush=True)
            for size in args.sizes:
                row = reference(case,size,probes=positions)
                entry['reference'].append(row)
                print(name,'reference',size,row['frequency_hz'],flush=True)
            entry['acceptance'] = acceptance(entry['native'],entry['reference'])
            entry['electric_relative_l2'] = {
                'native_last_refinement':electric_difference(entry['native'][-1],entry['native'][-2]),
                'reference_last_refinement':electric_difference(entry['reference'][-1],entry['reference'][-2]),
                'cross_solver':electric_difference(entry['native'][-1],entry['reference'][-1])}
            entry['electric_limit'] = .01
            entry['passed'] = entry['acceptance']['passed'] and all(
                np.isfinite(x) and x<=.01 for x in entry['electric_relative_l2'].values())
        report['source_unchanged'] = report['source_sha256']==fingerprints()
        report['passed'] = report['source_unchanged'] and all(e['passed'] for e in report['cases'].values())
    finally:
        (args.out/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS' if report['passed'] else 'FAIL')
    return 0 if report['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
