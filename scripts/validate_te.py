# SPDX-License-Identifier: Apache-2.0
"""Independent cylindrical TE spectrum/fields/PEC losses and native CLI checks."""
import argparse,json,subprocess,sys,time
from pathlib import Path
import numpy as np
from scipy.special import jn_zeros,jv
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng import Case,solve
from superfish_ng.constants import EPS0,MU0,C0,TAU
from superfish_ng.model import Model
from superfish_ng.te import TEFieldSampler,te_quantities
from superfish_ng.io import save_run
from superfish_ng.te_saved import read_te_run
from validate_curved_rf_adaptive import fingerprints


def analytic(radius,length,energy,count):
    rows=sorted((C0/TAU*np.hypot(chi/radius,p*np.pi/length),i+1,p,chi)
                for i,chi in enumerate(jn_zeros(1,count)) for p in range(1,count+1))[:count]
    def evaluate(row,points):
        f,radial,axial,chi=row;kr=chi/radius;kz=axial*np.pi/length;omega=TAU*f
        a=np.sqrt(4*energy/(EPS0*np.pi*length*radius**2*jv(0,chi)**2));r,z=points.T
        fields=dict(Ephi_V_per_m=a*jv(1,kr*r)*np.sin(kz*z),
            Hr_quadrature_A_per_m=-a*kz/(omega*MU0)*jv(1,kr*r)*np.cos(kz*z),
            Hz_quadrature_A_per_m=a*kr/(omega*MU0)*jv(0,kr*r)*np.sin(kz*z))
        g=omega*MU0*(kr**2+kz**2)*length*radius/(2*(kr**2*length+2*kz**2*radius))
        return fields,g
    return rows,evaluate


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();records=[];finals={}
    limits=dict(frequency=1e-4,fields=.01,geometry_factor=.005,energy_balance=1e-9)
    for order,levels in ((1,(32,64,128,256,768)),(2,(8,16,32,64))):
        for scale in (1.,2.):
            radius,length=.1*scale,.2*scale;exact,evaluate=analytic(radius,length,1.,6);previous=None
            probes=np.array([[r,z] for r in np.linspace(0,radius,19) for z in np.linspace(0,length,23)])
            for n in levels:
                case=Case(((0.,radius),(length,radius)),nr=n,nz=3*n//2,element_order=order,modes=6,model=Model(polarization='te'))
                start=time.perf_counter();solution=solve(case);sampler=TEFieldSampler(solution);rows=[]
                frequencies=np.array([r[0] for r in exact])
                if previous is not None:assert np.all(solution.frequencies_hz<previous)
                assert np.all(solution.frequencies_hz>frequencies)
                previous=solution.frequencies_hz
                for mode,ref in enumerate(exact):
                    fields,g=evaluate(ref,probes);actual=sampler.evaluate(probes,mode)
                    sign=1 if np.dot(actual['Ephi_V_per_m'],fields['Ephi_V_per_m'])>=0 else -1
                    errors={key:float(np.max(abs(sign*actual[key]-values))/np.max(abs(values))) for key,values in fields.items()}
                    q=te_quantities(solution,mode)
                    rows.append(dict(radial_index=ref[1],axial_index=ref[2],frequency_relative_error=abs(q['frequency_hz']/ref[0]-1),
                        field_relative_errors=errors,geometry_factor_relative_error=abs(q['geometry_factor_ohm']/g-1),
                        energy_balance=abs(q['electric_energy_j']/q['magnetic_energy_j']-1),quantities=q))
                records.append(dict(order=order,scale=scale,n=n,dofs=len(solution.coefficients_v_per_m2),seconds=time.perf_counter()-start,rows=rows))
                (out/'partial.json').write_text(json.dumps(records,indent=2)+'\n')
                if n==levels[-1]:
                    assert all(r['frequency_relative_error']<limits['frequency'] and max(r['field_relative_errors'].values())<limits['fields'] and r['geometry_factor_relative_error']<limits['geometry_factor'] and r['energy_balance']<limits['energy_balance'] for r in rows),records[-1]
                    finals[order,scale]=rows
                    # Native reassembly/replay on moderate P2; P1 fine grids test the solve and physical fields above.
                    if order==2:
                        run=out/f'native-p2-scale-{int(scale)}';save_run(case,solution,run);saved=read_te_run(run)
                        np.testing.assert_array_equal(saved.coefficients_v_per_m2,solution.coefficients_v_per_m2)
                        (out/f'case-scale-{int(scale)}.json').write_text(json.dumps(case.to_dict(),indent=2)+'\n')
                        cli=out/f'cli-scale-{int(scale)}';command=[sys.executable,'-m','superfish_ng','solve',str(out/f'case-scale-{int(scale)}.json'),'--out',str(cli)]
                        result=subprocess.run(command,capture_output=True,text=True);(out/f'cli-{int(scale)}.log').write_text(result.stdout+result.stderr);assert result.returncode==0
                        other=read_te_run(cli);np.testing.assert_array_equal(other.coefficients_v_per_m2,solution.coefficients_v_per_m2)
                        assert [te_quantities(other,i) for i in range(6)]==[te_quantities(solution,i) for i in range(6)]
                print('TE',order,scale,n,'max f',max(r['frequency_relative_error'] for r in rows),flush=True)
    similarity=[]
    for order in (1,2):
        for a,b in zip(finals[order,1.],finals[order,2.]):
            x,y=a['quantities'],b['quantities'];errors=[abs(y['frequency_hz']*2/x['frequency_hz']-1),abs(y['geometry_factor_ohm']/x['geometry_factor_ohm']-1),abs(y['q0']/x['q0']/np.sqrt(2)-1)]
            assert max(errors)<1e-9;similarity.extend(errors)
    assert fingerprints()==before
    (out/'validation.json').write_text(json.dumps(dict(passed=True,limits=limits,records=records,max_similarity_error=max(similarity),source_sha256=before,source_unchanged=True,scope='six cylindrical TE modes, two scales, P1/P2 Ritz refinement, fields/axis/energy/PEC loss; P2 CLI/native replay identity; no curved TE or GUI acceptance'),indent=2)+'\n')


if __name__=='__main__':main()
