# SPDX-License-Identifier: Apache-2.0
"""Magnetic half-domain stopping, extra fixed-domain reference and scaling."""
import argparse
from dataclasses import replace
import json
import math
import os
from pathlib import Path
import sys
from unittest.mock import patch
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng.adaptive_refinement import execute_adaptive_refinement,read_adaptive_refinement
from superfish_ng import solve
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution
from superfish_ng.curved_refinement_steps import CurvedRefinementStep as Step
from superfish_ng.curved_adaptive_refinement import _surface,_quadrature
from superfish_ng.curved_residual_indicator import curved_residual_indicator
from superfish_ng.surface_convergence import _interval_change
from superfish_ng.saved_mode_tracking import build_saved_mode_tracking
from validate_curved_adaptive_symmetry import fingerprints


def intervals(q,surface):
    return {**{key:[q[key]]*2 for key in ('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm')},**surface['intervals']}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--electric-evidence',type=Path,required=True,help='directory containing the independently tested hemisphere requests')
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    before=fingerprints();checks={}
    limits=dict(frequency_hz=1e-4,r_over_q_accelerator_ohm=.005,geometry_factor_ohm=.005,
                epk_over_eacc=.01,bpk_over_eacc_mt_per_mv_per_m=.01)
    for scale in (1,2):
        request=json.loads((args.electric_evidence/f'request-{scale}.json').read_text())
        radius=.08*scale
        expected_curves=[dict(type='line',start_zr_m=[0.,0.],end_zr_m=[radius,0.]),
                         dict(type='ellipse_arc',center_zr_m=[0.,0.],semiaxes_m=[radius,radius],
                              start_rad=0.,sweep_rad=math.pi/2,rotation_rad=0.),
                         dict(type='line',start_zr_m=[0.,radius],end_zr_m=[0.,0.])]
        geometry=request['case']['geometry']
        if (geometry['curves']!=expected_curves or geometry['edge_tags']!=['axis','pec','electric_symmetry']
                or request['case']['solver']['modes']!=1
                or len(request['initial_ids'])!=1 or request['mode_id']!=request['initial_ids'][0]
                or request['relative_tolerances']!={k:limits[k] for k in ('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm')}
                or request['surface_relative_tolerances']!={k:limits[k] for k in ('epk_over_eacc','bpk_over_eacc_mt_per_mv_per_m')}):
            raise ValueError('magnetic verification requires the specified electric hemisphere, one target mode, and unchanged five-quantity tolerances')
        request['case']['geometry']['edge_tags'][-1]='magnetic_symmetry'
        request['case']['name']='synthetic_magnetic_symmetry_hemisphere'
        (out/f'request-{scale}.json').write_text(json.dumps(request,indent=2)+'\n')
        directory=out/f'scale-{scale}';result=execute_adaptive_refinement(request,directory)
        checkpoint=sorted(directory.glob('checkpoint-*.json'))[-1]
        with patch('superfish_ng.curved_solution.eigsh',side_effect=AssertionError('replay must not solve')):
            verified=read_adaptive_refinement(checkpoint)
            previous=read_solution(verified['level_runs'][-1])
        assert result==verified
        rows=[intervals(level['quantities'],level['surface']) for level in verified['levels']]
        extra=None
        if result['status']=='TARGETS_MET':
            case=replace(previous.case,curved_refinement_steps=previous.case.curved_refinement_steps+(Step('uniform'),))
            reference=solve(case,mesh_data=previous.source_mesh_data)
            reference_dir=out/f'reference-{scale}';save_run(case,reference,reference_dir)
            restored=read_solution(reference_dir)
            q=restored.results['modes'][0];surface=_surface(restored,0,q)
            indicator=curved_residual_indicator(case,restored,mode=0,quadrature_order=case.quadrature_order)
            quadrature=_quadrature(restored,request,0,indicator)
            tracking=build_saved_mode_tracking(dict(schema_version=1,previous_run=verified['level_runs'][-1],
                 current_run=str(reference_dir),previous_ids=verified['levels'][-1]['current_mode_ids'],controls=request['controls']))
            changes={key:_interval_change(rows[-1][key],intervals(q,surface)[key]) for key in limits}
            extra=dict(differences=changes,quadrature=quadrature,tracking_status=tracking['tracking']['status'],
                       triangles=len(restored.space.geometry.cell_nodes),dofs=len(restored.u),
                       passed=quadrature['passed'] and tracking['tracking']['status']=='PASS' and all(v is not None and v<=limits[k] for k,v in changes.items()))
        passed=result['status']=='TARGETS_MET' and extra is not None and extra['passed']
        checks[str(scale)]=dict(passed=passed,status=result['status'],checkpoint=str(checkpoint),intervals=rows,
                               triangles=[level['triangles'] for level in result['levels']],extra_reference=extra)
        (out/f'scale-{scale}.json').write_text(json.dumps(checks[str(scale)],indent=2,allow_nan=False)+'\n')
        print(f'magnetic scale {scale}: {result["status"]}, additional reference pass {passed}',flush=True)
    a,b=checks['1'],checks['2'];same=a['triangles']==b['triangles']
    similarity={key:max(abs(y*(2 if key=='frequency_hz' else 1)/x-1)
                         for aa,bb in zip(a['intervals'],b['intervals']) for x,y in zip(aa[key],bb[key])) for key in limits}
    unchanged=before==fingerprints();passed=unchanged and same and all(c['passed'] for c in checks.values()) and max(similarity.values())<2e-8
    report=dict(passed=passed,checks=checks,similarity_relative_differences=similarity,same_mesh_counts=same,
                source_sha256=before,source_changed_during_run=not unchanged,
                scope='magnetic symmetry hemisphere: actual adaptive stopping, eigensolve-free replay, additional same-domain uniform reference and Maxwell scaling; reference differences are not absolute RF errors')
    (out/'validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print('Magnetic validation '+('PASS' if passed else 'FAIL'),flush=True);return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
