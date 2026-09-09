# SPDX-License-Identifier: Apache-2.0
"""RF design predicate against actual sphere FEM, analytic targets and scaling."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng.analytic_sphere import SphereTM
from superfish_ng.constants import MU0
from superfish_ng.rf_design import save_rf_design, read_rf_design, assess_rf_design
from validate_curved_rf_adaptive import fingerprints


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints()
    subprocess.run([sys.executable,str(ROOT/'scripts/validate_surface_convergence.py'),
                    '--out',str(out/'native')],check=True,cwd=ROOT)
    reports=[]
    for scale in (1,2):
        radius=.08*scale;ref=SphereTM(radius,normalization_j=float(scale**2));q=ref.quantities()
        eacc=abs(complex(q['voltage_real_v'],q['voltage_imag_v']))/(2*radius)
        exact={k:q[k] for k in ('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm')}
        exact['r_over_q_circuit_ohm']=exact['r_over_q_accelerator_ohm']/2
        exact['epk_over_eacc']=abs(float(ref.fields([[0.,0.]])['Ez_quadrature_V_per_m'][0]))/eacc
        exact['bpk_over_eacc_mt_per_mv_per_m']=MU0*abs(float(ref.fields([[radius,radius]])['Hphi_A_per_m'][0]))/eacc*1e9
        # Design band is specified before reading any computed RF result.
        criteria=dict(schema_version=1,objective=dict(quantity='r_over_q_accelerator_ohm',direction='maximize'),
            constraints=[dict(quantity=k,lower=.95*v,upper=1.05*v) for k,v in exact.items()])
        history=json.loads((out/f'native/history-{scale}.json').read_text())
        path=out/f'design-{scale}.json';report=save_rf_design(history,'fundamental',criteria,path)
        assert read_rf_design(path)==report and report['status']=='CRITERIA_MET'
        failed=deepcopy(criteria);failed['constraints'][0]['lower']=exact['frequency_hz']*1.5
        failed['constraints'][0]['upper']=exact['frequency_hz']*2
        rejected=assess_rf_design(history,'fundamental',failed)
        assert rejected['status']=='CONSTRAINTS_VIOLATED' and rejected['objective']['eligible_value'] is None
        (out/f'rejected-{scale}.json').write_text(json.dumps(rejected,indent=2)+'\n')
        reports.append(report)
    errors={k:max(abs(b*(2 if k=='frequency_hz' else 1)/a-1)
        for a,b in zip(reports[0]['observed_envelopes'][k],reports[1]['observed_envelopes'][k]))
        for k in exact}
    assert max(errors.values())<2e-9 and before==fingerprints()
    (out/'validation.json').write_text(json.dumps(dict(passed=True,similarity_relative_errors=errors,
        all_six_analytic_design_bands_met=True,infeasible_trials_have_no_objective_value=True,
        source_sha256=before,source_unchanged=True,
        scope='actual sphere FEM in two scales and energy normalizations; empirical three-level RF design criteria, not optimization or physical error certification'),indent=2)+'\n')
    print('RF design assessment PASS')


if __name__=='__main__':main()
