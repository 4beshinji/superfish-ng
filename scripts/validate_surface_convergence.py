# SPDX-License-Identifier: Apache-2.0
"""Independent sphere errors and scaling for tracked peak refinement assessment."""
import argparse
from dataclasses import replace
import hashlib
import json
import math
import os
from pathlib import Path
import sys
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng import Case,solve
from superfish_ng.constants import MU0
from superfish_ng.conics import LineSegment,EllipseArc
from superfish_ng.curved_contour import CurvedContour
from superfish_ng.mesh_controls import ContourMeshControls
from superfish_ng.analytic_sphere import SphereTM
from superfish_ng.io import save_run
from superfish_ng.saved_mode_tracking import build_saved_mode_tracking
from superfish_ng.mode_tracking_history import start_mode_history,extend_mode_history,save_mode_history
from superfish_ng.surface_convergence import save_surface_convergence,read_surface_convergence


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    before=hashes();checks={};assessments=[]
    for scale in (1,2):
        radius=.08*scale;normalization=float(scale**2)
        case=Case((),name='synthetic_sphere_peak_refinement',curved_contour=CurvedContour(
            (LineSegment((0,0),(2*radius,0)),EllipseArc((radius,0),(radius,radius),0,math.pi)),('axis','pec'),1e-14*scale),
            curve_chord_tolerance_m=.0016*scale,contour_mesh=ContourMeshControls(.064*scale,min_angle_deg=5.),
            element_order=2,geometry_order=2,modes=1,normalization_j=normalization)
        paths=[]
        for level in range(3):
            c=replace(case,curved_refinement_levels=level);path=out/f'sphere-{scale}-{level}'
            save_run(c,solve(c),path);paths.append(str(path))
        controls=dict(mapping='curved_same_domain',sample_order=3,minimum_overlap=.98,minimum_assignment_margin=.05,
            relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)
        pair=build_saved_mode_tracking(dict(schema_version=1,previous_run=paths[0],current_run=paths[1],previous_ids=['fundamental'],controls=controls))
        history=extend_mode_history(start_mode_history(pair),dict(current_run=paths[2],controls=controls))
        save_mode_history(history,out/f'history-{scale}.json')
        path=out/f'assessment-{scale}.json';assessment=save_surface_convergence(history,'fundamental',path)
        assert read_surface_convergence(path)==assessment
        reference=SphereTM(radius,normalization_j=normalization);quantities=reference.quantities()
        eacc=abs(complex(quantities['voltage_real_v'],quantities['voltage_imag_v']))/(2*radius)
        expected={k:quantities[k] for k in ('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm')}
        expected.update(epk_over_eacc=abs(float(reference.fields([[0.,0.]])['Ez_quadrature_V_per_m'][0]))/eacc,
            bpk_over_eacc_mt_per_mv_per_m=MU0*abs(float(reference.fields([[radius,radius]])['Hphi_A_per_m'][0]))/eacc*1e9)
        errors={k:max(abs(v/exact-1) for v in assessment['rows'][-1]['intervals'][k]) for k,exact in expected.items()}
        # Independent development targets, not imported from the implementation.
        limits=dict(frequency_hz=1e-4,r_over_q_accelerator_ohm=.005,geometry_factor_ohm=.005,epk_over_eacc=.01,bpk_over_eacc_mt_per_mv_per_m=.01)
        checks[str(scale)]=dict(passed=assessment['status']=='TARGETS_MET' and all(errors[k]<=limits[k] for k in errors),
            assessment_status=assessment['status'],analytical_relative_errors=errors,analytical_limits=limits,
            normalization_j=normalization,triangle_counts=[r['triangles'] for r in assessment['rows']])
        assessments.append(assessment)
    similarity={k:max(abs(v*(2 if k=='frequency_hz' else 1)/u-1) for a,b in zip(assessments[0]['rows'],assessments[1]['rows'])
        for u,v in zip(a['intervals'][k],b['intervals'][k])) for k in expected}
    unchanged=before==hashes();passed=unchanged and all(c['passed'] for c in checks.values()) and max(similarity.values())<2e-9
    report=dict(passed=passed,checks=checks,similarity_relative_errors=similarity,source_sha256=before,source_changed_during_run=not unchanged,
        scope='sphere analytical frequency, R/Q, G and surface peak ratios; fixed quadratic geometry refinement, length and energy normalization scaling; not general curved geometry approximation or a physical error bound')
    (out/'validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print(f'Surface convergence {"PASS" if passed else "FAIL"}: {out}');return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
