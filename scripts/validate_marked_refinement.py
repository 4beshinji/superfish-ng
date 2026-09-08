# SPDX-License-Identifier: Apache-2.0
"""Local restrictions, Ritz monotonicity, Bessel reference and Maxwell scaling."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng import Case,solve
from superfish_ng.analytic import pillbox_spectrum
from superfish_ng.io import save_run
from superfish_ng.mesh import element_geometry
from superfish_ng.mesh_input import mesh_to_dict
from superfish_ng.marked_refinement import refine_marked_cells


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    before=hashes();checks={}
    for kind in ('cylinder','folded'):
        for order in (1,2):
            series=[];identities=[];volume_errors=[];monotonic=[];analytic_errors=[]
            for scale in (1.,2.):
                if kind=='cylinder':
                    case=Case(((0.,.1*scale),(.2*scale,.1*scale)),nr=6,nz=8,modes=2,element_order=order)
                    volume=np.pi*(.1*scale)**2*(.2*scale)
                    exact=np.array([row[0] for row in pillbox_spectrum(.1*scale,.2*scale,2)])
                else:
                    data=Case.load(ROOT/'examples/contour_folded.json').to_dict()
                    data['geometry']['vertices_zr_m']=(np.array(data['geometry']['vertices_zr_m'])*scale).tolist()
                    data['mesh']['contour_mesh']['max_edge_m']*=scale;data['solver']['element_order']=order
                    case=Case.from_dict(data);volume=case.contour.volume_m3
                base=solve(case);branches={}
                for selection in ('local','uniform'):
                    solution=base;rows=[]
                    for level in range(3):
                        seconds=0.;requested=[];quality=None
                        if level:
                            centre=solution.mesh.points[solution.mesh.triangles].mean(axis=1)
                            requested=list(range(len(centre))) if selection=='uniform' else np.flatnonzero((centre[:,0]>=.6*np.max(solution.mesh.points[:,0])) & (centre[:,1]<=.75*case.length)).tolist()
                            start=time.perf_counter();refined=refine_marked_cells(case,solution.mesh,requested)
                            current=solve(case,mesh_data=mesh_to_dict(refined.mesh));seconds=time.perf_counter()-start;quality=refined.quality
                            for a,b in ((solution.stiffness,current.stiffness),(solution.mass,current.mass)):
                                difference=refined.prolongation.T@b@refined.prolongation-a
                                identities.append(float(np.linalg.norm(difference.data)/np.linalg.norm(a.data)))
                            monotonic.append(float(np.max(current.frequencies_hz/solution.frequencies_hz-1)))
                            solution=current
                        name=f'{kind}-p{order}-s{int(scale)}-{selection}-{level}';save_run(case,solution,out/name)
                        p,det,_=element_geometry(solution.mesh);measured=float(np.pi*np.sum(det*p[:,:,0].mean(axis=1)))
                        volume_errors.append(abs(measured/volume-1));quantities=json.loads((out/name/'results.json').read_text())['modes']
                        row=dict(run=name,level=level,triangles=len(solution.mesh.triangles),dofs=len(solution.u),refine_and_solve_seconds=seconds,
                            requested_cells=requested,quality=quality,modes=quantities)
                        if kind=='cylinder':
                            row['analytical_frequency_relative_errors']=(solution.frequencies_hz/exact-1).tolist()
                            analytic_errors.extend(row['analytical_frequency_relative_errors'])
                        rows.append(row)
                    branches[selection]=rows
                series.append(branches)
            similarity={key:max(abs(y[key]*(2 if key=='frequency_hz' else 1)/x[key]-1)
                for branch in ('local','uniform') for a,b in zip(series[0][branch],series[1][branch]) for x,y in zip(a['modes'],b['modes']))
                for key in ('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm')}
            less_work=all(s['local'][-1]['triangles']<s['uniform'][-1]['triangles'] for s in series)
            analytic_ok=not analytic_errors or (min(analytic_errors)>-2e-11 and max(analytic_errors)<(.02 if order==1 else .001))
            passed=max(identities)<1e-11 and max(volume_errors)<2e-12 and max(monotonic)<2e-12 and max(similarity.values())<2e-9 and less_work and analytic_ok
            checks[f'{kind}-p{order}']=dict(passed=bool(passed),series=series,maximum_galerkin_relative_difference=max(identities),
                maximum_volume_relative_error=max(volume_errors),maximum_frequency_relative_increase=max(monotonic),similarity_relative_errors=similarity,
                analytic_frequency_error_range=[min(analytic_errors),max(analytic_errors)] if analytic_errors else None,
                note='local selection is an explicitly prescribed physical region, not an error indicator; lower DOF does not imply smaller error than uniform refinement')
    unchanged=before==hashes();passed=unchanged and all(c['passed'] for c in checks.values())
    report=dict(passed=passed,checks=checks,source_sha256=before,source_changed_during_run=not unchanged,
        scope='straight P1/P2 local and uniform two-pass subdivision; fixed domains, Galerkin energy identity, Ritz monotonicity, cylinder analytical spectrum and f/RQ/G similarity; no adaptive-error estimator or physical RF convergence acceptance')
    (out/'validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print(f'Marked refinement {"PASS" if passed else "FAIL"}: {out}');return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
