# SPDX-License-Identifier: Apache-2.0
"""Actual curved tuning against independent TM011 and Maxwell scaling laws."""
import argparse,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng import Case
from superfish_ng.conics import LineSegment
from superfish_ng.curved_contour import CurvedContour
from superfish_ng.mesh_controls import ContourMeshControls
from superfish_ng.project import Project
from superfish_ng.constants import C0
from superfish_ng.tuning import execute_tune,replay_tune
from superfish_ng.saved import read_solution
from superfish_ng.rf import quantities
from validate_curved_rf_adaptive import fingerprints


def request(scale=1.,unit='m'):
    points=((0.,0.),(.1*scale,0.),(.1*scale,.1*scale),(0.,.1*scale))
    curves=tuple(LineSegment(p,q) for p,q in zip(points,points[1:]+points[:1]))
    case=Case((),curved_contour=CurvedContour(curves,('axis','pec','pec','pec'),1e-14*scale),
        curve_chord_tolerance_m=.001*scale,contour_mesh=ContourMeshControls(.02*scale,min_angle_deg=5.),
        element_order=2,geometry_order=2,quadrature_order=12,modes=3)
    return dict(schema_version=4,project=Project(case).to_dict(),parameter='length' if unit=='m' else 'length_factor',parameter_unit=unit,
        affine_coefficients=dict(radial_scale=[1.],axial_scale=[0.,10./scale if unit=='m' else 1.],axial_shear=[0.]),rf_coordinates='axial',
        bounds=[.06*scale,.1*scale] if unit=='m' else [.6,1.],
        target_hz=C0/(2*math.pi)*math.hypot(2.404825557695773/(.1*scale),math.pi/(.08*scale)),
        frequency_tolerance_hz=1e5/scale,parameter_tolerance=1e-9,max_trials=20,initial_ids=['TM010','TM020','TM011'],mode_id='TM011',
        controls=dict(mapping='affine_remesh',sample_order=8,minimum_overlap=.95,minimum_assignment_margin=.05,
            relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8),refinement_scale=2,mesh_frequency_tolerance_hz=1e5/scale)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();rows=[];references={}
    for scale,unit in ((1.,'m'),(1.,'1'),(2.,'m'),(2.,'1')):
        r=request(scale,unit);directory=out/f'scale-{scale:g}-unit-{unit}'
        first=execute_tune(r,directory/'first',max_new_trials=2)
        final=execute_tune(r,directory/'resumed',checkpoint=first);assert final['status']=='TUNED'
        assert replay_tune(final)==final
        ranks=[t['current_mode_ids'].index('TM011') for t in first['trials']];assert ranks==[2,1]
        errors=[]
        for trial in final['trials']:
            length=trial['value'] if unit=='m' else .1*scale*trial['value']
            exact=C0/(2*math.pi)*math.hypot(2.404825557695773/(.1*scale),math.pi/length)
            errors.append(abs(trial['frequency_hz']/exact-1))
        assert max(errors)<1e-4 and errors[-1]<1e-5
        solution=read_solution(Path(final['trial_runs'][-1])/'solution')
        q=quantities(solution.case,solution,mode=final['trials'][-1]['current_mode_ids'].index('TM011'))
        length_error=abs(solution.case.length/(.08*scale)-1);assert length_error<1e-4
        references[(scale,unit)]=q
        rows.append(dict(scale=scale,parameter_unit=unit,trials=len(final['trials']),status=final['status'],first_ranks=ranks,
            max_analytic_frequency_error=max(errors),final_analytic_frequency_error=errors[-1],length_relative_error=length_error))
    comparisons=[]
    base=references[(1.,'m')]
    for (scale,unit),q in references.items():
        error=max(abs(q[k]*(scale if k=='frequency_hz' else 1)/base[k]-1)
            for k in ('frequency_hz','r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm'))
        assert error<1e-9;comparisons.append(dict(scale=scale,unit=unit,max_maxwell_or_unit_error=error))
    assert before==fingerprints()
    (out/'validation.json').write_text(json.dumps(dict(passed=True,rows=rows,comparisons=comparisons,source_sha256=before,source_unchanged=True,
        scope='four actual curved-P2 affine tunes, two units/two physical scales, analytical TM011 with rank crossing, native pause/resume/replay and final fixed-geometry refinement; not arbitrary shape convergence or global root certification'),indent=2)+'\n')
    print('Curved tuning PASS')


if __name__=='__main__':main()
