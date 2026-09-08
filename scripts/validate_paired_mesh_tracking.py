# SPDX-License-Identifier: Apache-2.0
"""Saved folded/curved FEM similarity under explicit permuted mesh pairing."""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
from superfish_ng import Case,solve
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution
from superfish_ng.mesh_input import mesh_to_dict
from superfish_ng.curved_solution import CurvedSolution
from superfish_ng.paired_mesh_tracking import track_paired_mesh_modes,_geometry
from superfish_ng.saved_mode_tracking import save_mode_tracking
from superfish_ng.mode_tracking_history import start_mode_history,extend_mode_history,save_mode_history


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    files=[p for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
    def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    before=hashes();checks={}
    for kind in ('folded','ellipse'):
        data=Case.load(ROOT/'examples'/('contour_folded.json' if kind=='folded' else 'curved_ellipse.json')).to_dict()
        data['mesh']['contour_mesh'].update(max_edge_m=.025 if kind=='folded' else .08,min_angle_deg=5.)
        if kind=='ellipse':data['mesh']['geometry_order']=2;data['geometry']['chord_tolerance_m']=.008
        case=Case.from_dict(data);solution=solve(case)
        mesh=deepcopy(solution.source_mesh_data) if isinstance(solution,CurvedSolution) else mesh_to_dict(solution.mesh)
        scaled=deepcopy(data)
        if kind=='folded':scaled['geometry']['vertices_zr_m']=[[2*z,2*r] for z,r in data['geometry']['vertices_zr_m']]
        else:
            for curve in scaled['geometry']['curves']:
                for key in ('start_zr_m','end_zr_m','center_zr_m','semiaxes_m'):
                    if key in curve:curve[key]=[2*x for x in curve[key]]
            scaled['geometry']['chord_tolerance_m']*=2;scaled['geometry']['join_tolerance_m']*=2
        scaled_case=Case.from_dict(scaled);perm=np.arange(len(mesh['points'])-1,-1,-1)
        mesh['points']=(2*np.array(mesh['points'])[perm]).tolist()
        mesh['triangles']=perm[np.array(mesh['triangles'])[::-1]][:,[1,2,0]].tolist()
        mesh['boundary_edges']=perm[np.array(mesh['boundary_edges'])].tolist()
        new=solve(scaled_case,mesh_data=mesh)
        for name,c,s in [('a',case,solution),('b',scaled_case,new)]:save_run(c,s,out/f'{kind}-{name}')
        a,b=[read_solution(out/f'{kind}-{name}') for name in ('a','b')]
        pairs=[[i,int(perm[i])] for i in sorted(set(map(int,_geometry(a)[1].ravel())))]
        controls=dict(mapping='paired_mesh',vertex_pairs=pairs,minimum_overlap=.98,minimum_assignment_margin=.05,relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)
        reports=[track_paired_mesh_modes(a,b,['A'],sample_order=q,**controls) for q in (3,5)]
        old_results,new_results=[json.loads((out/f'{kind}-{name}'/'results.json').read_text())['modes'][0] for name in ('a','b')]
        errors={key:abs(new_results[key]*scale/old_results[key]-1) for key,scale in [('frequency_hz',2.),('r_over_q_accelerator_ohm',1.),('geometry_factor_ohm',1.)]}
        request=dict(schema_version=1,previous_run=f'{kind}-a',current_run=f'{kind}-b',previous_ids=['A'],controls=dict(controls,sample_order=5))
        (out/f'{kind}-request.json').write_text(json.dumps(request,indent=2)+'\n')
        pair=save_mode_tracking(request,out/f'{kind}-pair.json',base_directory=out)
        history=extend_mode_history(start_mode_history(pair),dict(current_run=f'{kind}-a',controls=dict(controls,sample_order=5,vertex_pairs=[[j,i] for i,j in pairs])),base_directory=out)
        save_mode_history(history,out/f'{kind}-history.json')
        checks[kind]=dict(passed=max(errors.values())<2e-9 and all(r['status']=='PASS' and r['current_mode_ids']==['A'] for r in reports) and history['status']=='PASS',similarity_relative_errors=errors,tracking=reports)
    passed=all(c['passed'] for c in checks.values()) and before==hashes()
    result=dict(passed=passed,checks=checks,source_sha256=before,source_changed_during_run=before!=hashes(),scope='synthetic folded and native curved meshes; explicit topology pairing and similarity; no automatic mesh matching or general continuous branch proof')
    (out/'paired_tracking.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(f'Paired mesh tracking {"PASS" if passed else "FAIL"}: {out}');return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
