# SPDX-License-Identifier: Apache-2.0
"""Managed RF search: restart, native CLI identity and analytical final RF."""
import argparse,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng.jobs import JobManager
from superfish_ng.rf_optimization_checkpoints import open_optimization_checkpoint
from superfish_ng.rf_optimization import read_rf_optimization
from superfish_ng.project import Project
from superfish_ng.analytic_sphere import SphereTM
from superfish_ng.constants import MU0
from validate_curved_rf_adaptive import fingerprints


def wait(manager,identifier):
    deadline=time.monotonic()+600
    while manager.status(identifier)['status'] in ('queued','running') and time.monotonic()<deadline:time.sleep(.1)
    state=manager.status(identifier,verify=True)
    assert state['status']=='complete',state
    return state


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);parser.add_argument('--reference',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints()
    request=json.loads((ROOT/'examples/optimization/curved_rf.json').read_text());request['max_trials']=2
    manager=JobManager(out/'jobs')
    try:
        first=manager.start_rf_optimization(request,max_new_trials=1);assert wait(manager,first)['optimization_status']=='PAUSED'
        manager.close();manager=JobManager(out/'jobs')
        checkpoint=open_optimization_checkpoint(manager,first,1)
        second=manager.start_rf_optimization(request,checkpoint=checkpoint);state=wait(manager,second)
        assert state['optimization_status']=='SEARCH_COMPLETE' and state['computed_fem_solves']==6
        manager.close();manager=JobManager(out/'jobs')
        assert manager.status(second,verify=True)==state
        result=read_rf_optimization(out/'jobs'/second/'rf-optimization-results.json')
    finally:manager.close()
    for level in range(3):
        current=Path(result['trial_directories'][0])/f'level-{level}'
        old=args.reference/f'level-{level}'
        assert Project.load(current/'project.json').to_dict()==Project.load(old/'project.json').to_dict()
        assert json.loads((current/'solution/results.json').read_text())['modes']==json.loads((old/'solution/results.json').read_text())['modes']
    ref=SphereTM(.08);q=ref.quantities();eacc=abs(complex(q['voltage_real_v'],q['voltage_imag_v']))/.16
    expected={k:q[k] for k in ('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm')}
    expected['epk_over_eacc']=abs(float(ref.fields([[0.,0.]])['Ez_quadrature_V_per_m'][0]))/eacc
    expected['bpk_over_eacc_mt_per_mv_per_m']=MU0*abs(float(ref.fields([[.08,.08]])['Hphi_A_per_m'][0]))/eacc*1e9
    intervals=result['trials'][-1]['assessment']['assessment']['rows'][-1]['intervals']
    errors={k:max(abs(v/expected[k]-1) for v in intervals[k]) for k in expected}
    limits=dict(frequency_hz=1e-4,r_over_q_accelerator_ohm=.005,geometry_factor_ohm=.005,epk_over_eacc=.01,bpk_over_eacc_mt_per_mv_per_m=.01)
    assert all(errors[k]<=limits[k] for k in errors) and fingerprints()==before
    (out/'validation.json').write_text(json.dumps(dict(passed=True,first_id=first,resumed_id=second,
        same_native_project_and_modes_as_prior_cli=True,reference=str(args.reference.resolve()),
        restarted_manager_verified=True,analytic_final_relative_errors=errors,analytical_limits=limits,
        source_sha256=before,source_unchanged=True,
        scope='managed native FEM, complete PAUSED checkpoint resumption, restart, three-level CLI identity and final sphere RF; no new GUI verification'),indent=2)+'\n')
    print('RF optimization jobs PASS')


if __name__=='__main__':main()
