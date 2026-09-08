# SPDX-License-Identifier: Apache-2.0
"""Real hemisphere adaptation, reflection, sphere reference and Maxwell scaling."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from unittest.mock import patch
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng.adaptive_refinement import execute_adaptive_refinement,read_adaptive_refinement
from superfish_ng.saved import read_solution
from superfish_ng.symmetry import reflect_solution
from superfish_ng.curved_rf import quantities_curved
from superfish_ng.curved_extrema import bound_surface_peaks
from superfish_ng.analytic_sphere import SphereTM
from superfish_ng.constants import MU0


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    out=parser.parse_args().out.resolve();out.mkdir(parents=True,exist_ok=False)
    before=fingerprints();checks={}
    limits=dict(frequency_hz=1e-4,r_over_q_accelerator_ohm=.005,geometry_factor_ohm=.005,
                epk_over_eacc=.01,bpk_over_eacc_mt_per_mv_per_m=.01)
    for scale in (1,2):
        radius=.08*scale
        request=json.loads((ROOT/'examples/adaptive_refinement/curved_sphere_confirmed.json').read_text())
        case=request['case'];g=case['geometry'];case['name']='synthetic_electric_symmetry_hemisphere'
        g['curves']=[dict(type='line',start_zr_m=[0.,0.],end_zr_m=[radius,0.]),
                     dict(type='ellipse_arc',center_zr_m=[0.,0.],semiaxes_m=[radius,radius],start_rad=0.,sweep_rad=math.pi/2,rotation_rad=0.),
                     dict(type='line',start_zr_m=[0.,radius],end_zr_m=[0.,0.])]
        g['edge_tags']=['axis','pec','electric_symmetry'];g['chord_tolerance_m']*=scale;g['join_tolerance_m']*=scale
        case['mesh']['contour_mesh']['max_edge_m']*=scale;case['rf']['normalization_j']=float(scale**2)
        (out/f'request-{scale}.json').write_text(json.dumps(request,indent=2)+'\n')
        directory=out/f'scale-{scale}'
        result=execute_adaptive_refinement(request,directory)
        checkpoint=sorted(directory.glob('checkpoint-*.json'))[-1]
        with patch('superfish_ng.curved_solution.eigsh',side_effect=AssertionError('replay must not solve')):
            verified=read_adaptive_refinement(checkpoint)
            solution=read_solution(verified['level_runs'][-1])
        assert result==verified
        full_case,full=reflect_solution(solution.case,solution)
        q=quantities_curved(full);peaks=bound_surface_peaks(full)
        reference=SphereTM(radius,normalization_j=2.*scale**2);exact=reference.quantities()
        eacc=abs(complex(exact['voltage_real_v'],exact['voltage_imag_v']))/(2*radius)
        exact.update(epk_over_eacc=abs(float(reference.fields([[0.,0.]])['Ez_quadrature_V_per_m'][0]))/eacc,
                     bpk_over_eacc_mt_per_mv_per_m=MU0*abs(float(reference.fields([[radius,radius]])['Hphi_A_per_m'][0]))/eacc*1e9)
        intervals={key:[q[key]]*2 for key in ('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm')}
        intervals.update(epk_over_eacc=[peaks['electric_v_per_m'][end]/q['eacc_v_per_m'] for end in ('lower_bound','upper_bound')],
                         bpk_over_eacc_mt_per_mv_per_m=[MU0*1e9*peaks['magnetic_a_per_m'][end]/q['eacc_v_per_m'] for end in ('lower_bound','upper_bound')])
        errors={key:max(abs(value/exact[key]-1) for value in values) for key,values in intervals.items()}
        passed=(verified['status']=='TARGETS_MET' and verified['surface_status']=='TARGETS_MET'
                and all(errors[k]<=limits[k] for k in limits)
                and all(level['quadrature_check']['passed'] for level in verified['levels']))
        checks[str(scale)]=dict(passed=passed,status=verified['status'],checkpoint=str(checkpoint),
                               analytical_errors=errors,reflected_intervals=intervals,
                               half_intervals=[dict(frequency_hz=[level['quantities']['frequency_hz']]*2,
                                    r_over_q_accelerator_ohm=[level['quantities']['r_over_q_accelerator_ohm']]*2,
                                    geometry_factor_ohm=[level['quantities']['geometry_factor_ohm']]*2,
                                    **level['surface']['intervals']) for level in verified['levels']],
                               triangles=[level['triangles'] for level in verified['levels']],
                               full_normalization_j=full_case.normalization_j)
        (out/f'scale-{scale}.json').write_text(json.dumps(checks[str(scale)],indent=2)+'\n')
        print(f'hemisphere scale {scale}: {verified["status"]}, analytical pass {passed}',flush=True)
    a,b=checks['1'],checks['2'];same=a['triangles']==b['triangles']
    similarity={key:max(abs(y*(2 if key=='frequency_hz' else 1)/x-1)
                         for aa,bb in zip(a['half_intervals'],b['half_intervals']) for x,y in zip(aa[key],bb[key])) for key in limits}
    unchanged=before==fingerprints()
    passed=unchanged and same and all(c['passed'] for c in checks.values()) and max(similarity.values())<2e-8
    report=dict(passed=passed,checks=checks,similarity_relative_differences=similarity,same_mesh_counts=same,
                source_sha256=before,source_changed_during_run=not unchanged,
                scope='electric-symmetry hemisphere actual adaptive FEM; reflected full sphere analytical five quantities, original half-domain Maxwell scaling; no full-domain RF conversion inside adaptive checkpoints')
    (out/'validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print('Symmetry validation '+('PASS' if passed else 'FAIL'),flush=True)
    return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
