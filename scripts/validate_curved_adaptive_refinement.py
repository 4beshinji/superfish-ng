# SPDX-License-Identifier: Apache-2.0
"""Independent sphere and Maxwell checks of version 4 adaptive stopping."""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng.adaptive_refinement import execute_adaptive_refinement,read_adaptive_refinement
from superfish_ng.analytic_sphere import SphereTM
from superfish_ng.constants import MU0


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);out=parser.parse_args().out.resolve();out.mkdir(parents=True,exist_ok=False)
    def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    before=hashes();checks={};finals=[]
    for scale in (1,2):
        request=json.loads((ROOT/'examples/adaptive_refinement/curved_sphere_confirmed.json').read_text())
        request.update(max_levels=8,max_triangles=20000)
        request['relative_tolerances']=dict(frequency_hz=1e-4,r_over_q_accelerator_ohm=.005,geometry_factor_ohm=.005)
        request['surface_relative_tolerances']=dict(epk_over_eacc=.01,bpk_over_eacc_mt_per_mv_per_m=.01)
        case=request['case'];g=case['geometry']
        for curve in g['curves']:
            for key in ('start_zr_m','end_zr_m','center_zr_m','semiaxes_m'):
                if key in curve:curve[key]=[scale*v for v in curve[key]]
        for key in ('chord_tolerance_m','join_tolerance_m','minimum_gap_m'):
            if key in g:g[key]*=scale
        case['mesh']['contour_mesh']['max_edge_m']*=scale;case['rf']['normalization_j']=float(scale**2)
        code=0
        if scale==1:
            path=out/'cli-request.json';path.write_text(json.dumps(request,indent=2)+'\n');first=out/'cli-first'
            commands=[[sys.executable,'-m','superfish_ng','adaptive-refine',str(path),'--out',str(first),'--max-new-levels','3']]
            result=subprocess.run(commands[0],cwd=ROOT,capture_output=True,text=True,env=dict(os.environ,PYTHONPATH=str(ROOT/'src')))
            (out/'cli-first.log').write_text(result.stdout+result.stderr);code=result.returncode
            checkpoints=sorted(first.glob('checkpoint-*.json'));final_path=checkpoints[-1]
            checkpoint=read_adaptive_refinement(final_path)
            if checkpoint['can_resume']:
                second=out/'cli-resumed';command=[sys.executable,'-m','superfish_ng','resume-adaptive-refinement',str(final_path),'--out',str(second)]
                result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,env=dict(os.environ,PYTHONPATH=str(ROOT/'src')))
                (out/'cli-resumed.log').write_text(result.stdout+result.stderr);code=max(code,result.returncode)
                final_path=sorted(second.glob('checkpoint-*.json'))[-1]
        else:
            folder=out/'scale-2';result=execute_adaptive_refinement(request,folder)
            final_path=sorted(folder.glob('checkpoint-*.json'))[-1]
        with patch('superfish_ng.curved_solution.eigsh',side_effect=AssertionError('checkpoint replay must not solve')):
            final=read_adaptive_refinement(final_path)
        last=final['levels'][-1];radius=.08*scale;reference=SphereTM(radius,normalization_j=float(scale**2));q=reference.quantities()
        eacc=abs(complex(q['voltage_real_v'],q['voltage_imag_v']))/(2*radius)
        exact={k:q[k] for k in ('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm')}
        exact.update(epk_over_eacc=abs(float(reference.fields([[0.,0.]])['Ez_quadrature_V_per_m'][0]))/eacc,
            bpk_over_eacc_mt_per_mv_per_m=MU0*abs(float(reference.fields([[radius,radius]])['Hphi_A_per_m'][0]))/eacc*1e9)
        intervals={k:[last['quantities'][k]]*2 for k in ('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm')}
        intervals.update(last['surface']['intervals'])
        errors={k:max(abs(v/exact[k]-1) for v in values) if values else None for k,values in intervals.items()}
        limits=dict(frequency_hz=1e-4,r_over_q_accelerator_ohm=.005,geometry_factor_ohm=.005,epk_over_eacc=.01,bpk_over_eacc_mt_per_mv_per_m=.01)
        passed=(code==0 and final['status']=='TARGETS_MET' and final['surface_status']=='TARGETS_MET'
            and all(v is not None and v<=limits[k] for k,v in errors.items())
            and all(row['quadrature_check']['passed'] for row in final['levels'])
            and [row['refinement_kind'] for row in final['levels'][-2:]]==['uniform_confirmation']*2)
        checks[str(scale)]=dict(passed=passed,status=final['status'],checkpoint=str(final_path),analytical_errors=errors,
            triangles=[row['triangles'] for row in final['levels']],quadrature_checks=[row['quadrature_check'] for row in final['levels']],
            intervals=intervals,decisions=final['decision'],mode_indices=[row['mode_index'] for row in final['levels']])
        finals.append(final)
    similarity={k:max(abs(b*(2 if k=='frequency_hz' else 1)/a-1) for a,b in zip(checks['1']['intervals'][k],checks['2']['intervals'][k])) for k in exact}
    unchanged=before==hashes();passed=unchanged and all(c['passed'] for c in checks.values()) and max(similarity.values())<2e-8
    (out/'validation.json').write_text(json.dumps(dict(passed=passed,checks=checks,similarity_relative_errors=similarity,source_sha256=before,
        source_changed_during_run=not unchanged,scope='actual version 4 adaptive sphere FEM and CLI resume, independent analytical five quantities including both peak endpoints, integration checks and Maxwell scaling; no general geometry approximation or physical error bound'),indent=2,allow_nan=False)+'\n')
    print(f'Curved adaptive refinement {"PASS" if passed else "FAIL"}: {out}');return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
