# SPDX-License-Identifier: Apache-2.0
"""N02 independent cylinder fields, RF, peaks and error per degree of freedom."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from scipy.special import j0,j1,jnp_zeros
from superfish_ng import Case,solve
from superfish_ng.analytic import pillbox_tm_mode
from superfish_ng.constants import TAU,EPS0,MU0
from superfish_ng.sampling import FieldSampler
from superfish_ng.rf import quantities


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    out=parser.parse_args().out
    out.mkdir(parents=True,exist_ok=False)
    qr,wr=np.polynomial.legendre.leggauss(41)
    qz,wz=np.polynomial.legendre.leggauss(83)
    rr,zz=np.meshgrid((qr+1)*.05,(qz+1)*.1)
    positions=np.column_stack((rr.ravel(),zz.ravel()))
    weights=(np.outer(wz,wr)*rr).ravel()
    axis_z=(qz+1)*.1
    axis_points=np.column_stack((np.zeros_like(axis_z),axis_z))
    rows=[]
    for nr in [4,8,16,32]:
        for order in [1,2]:
            case=Case(((0.,.1),(.2,.1)),nr=nr,nz=2*nr,modes=3,element_order=order)
            start=time.perf_counter();sol=solve(case);sampler=FieldSampler.from_solution(sol)
            modes=[]
            for mode in range(3):
                ref=pillbox_tm_mode(.1,.2,p=mode)
                alpha,kz=ref['radial_wave_number_per_m'],ref['axial_wave_number_per_m']
                h0,e0,omega=ref['h0_a_per_m'],ref['e0_v_per_m'],TAU*ref['frequency_hz']
                h=h0*j1(alpha*positions[:,0])*np.cos(kz*positions[:,1])
                ez=e0*j0(alpha*positions[:,0])*np.cos(kz*positions[:,1])
                er=h0*kz/(omega*EPS0)*j1(alpha*positions[:,0])*np.sin(kz*positions[:,1])
                actual=sampler.evaluate(positions,mode)
                sign=1 if np.dot(weights*h,actual['Hphi_A_per_m'])>=0 else -1
                electric_error=np.sqrt(np.dot(weights,(sign*actual['Ez_quadrature_V_per_m']-ez)**2+(sign*actual['Er_quadrature_V_per_m']-er)**2)/np.dot(weights,ez**2+er**2))
                magnetic_error=np.sqrt(np.dot(weights,(sign*actual['Hphi_A_per_m']-h)**2)/np.dot(weights,h**2))
                axial=sampler.evaluate(axis_points,mode)['Ez_quadrature_V_per_m']*sign
                expected=e0*np.cos(kz*axis_z)
                axis_error=np.sqrt(np.dot(wz,(axial-expected)**2)/np.dot(wz,expected**2))
                rf=quantities(case,sol,mode)
                epk=max(e0,abs(h0*kz*j1(alpha*.1)/(omega*EPS0)))
                bpk=MU0*h0*j1(jnp_zeros(1,1)[0])
                errors={key:abs(rf[key]/ref[key]-1) for key in ['frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm']}
                errors.update(electric_l2=float(electric_error),magnetic_l2=float(magnetic_error),axis_l2=float(axis_error),
                              epk=abs(rf['epk_surface_estimate_v_per_m']/epk-1),bpk=abs(rf['bpk_surface_estimate_t']/bpk-1))
                modes.append(errors)
            rows.append(dict(nr=nr,element_order=order,dofs=len(sol.u),seconds=time.perf_counter()-start,modes=modes))
    checks={}
    fine=rows[-1]
    for key,limit in [('frequency_hz',1e-5),('r_over_q_accelerator_ohm',1e-4),('geometry_factor_ohm',1e-4),
                      ('electric_l2',.01),('magnetic_l2',.01),('axis_l2',.01),('epk',.01),('bpk',.01)]:
        checks[f'finest_{key}']=all(m[key]<limit for m in fine['modes'])
    for key in ['frequency_hz','axis_l2','r_over_q_accelerator_ohm','electric_l2','magnetic_l2']:
        checks[f'equal_dofs_p2_improves_{key}']=all(rows[i]['dofs']==rows[i+1]['dofs'] and all(a[key]<b[key] for a,b in zip(rows[i]['modes'],rows[i+1]['modes'])) for i in [1,3,5])
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ['src','tests','scripts'] for p in sorted((ROOT/folder).rglob('*.py'))}
    report=dict(status='PASS' if all(checks.values()) else 'FAIL',checks=checks,rows=rows,source_sha256=hashes,
                scope='straight full PEC cylinder; TM010/011/012; fixed independent spatial samples; no singular-corner guarantee')
    (out/'fields.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'],checks)
    return 0 if report['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
