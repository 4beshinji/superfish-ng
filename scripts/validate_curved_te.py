# SPDX-License-Identifier: Apache-2.0
"""Independent spherical TE validation; analytical formulas are test-only."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from scipy.optimize import brentq
from scipy.special import spherical_jn
from numpy.polynomial.legendre import Legendre
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from superfish_ng import Case,solve
from superfish_ng.constants import C0,EPS0,MU0,TAU
from superfish_ng.te import te_quantities,TEFieldSampler
from superfish_ng.te_curved import wall_integral
from superfish_ng.te_saved import read_te_run
from superfish_ng.io import save_run


def fingerprint():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def sphere(scale=1.,half=False):
    data=json.loads((ROOT/'examples/optimization/curved_rf.json').read_text())['project']['case']
    data['model']['polarization']='te';data['solver']['modes']=3
    g=data['geometry'];r=.08*scale
    g['curves'][0]['start_zr_m']=[0.,0.]
    g['curves'][0]['end_zr_m']=[r if half else 2*r,0.]
    g['curves'][1]['center_zr_m']=[0. if half else r,0.];g['curves'][1]['semiaxes_m']=[r,r]
    g['curves'][1]['sweep_rad']=np.pi/2 if half else np.pi
    if half:
        g['curves'].append(dict(type='line',start_zr_m=[0.,r],end_zr_m=[0.,0.]))
        g['edge_tags'].append('magnetic_symmetry');data['rf']['normalization_j']=.5
    g['chord_tolerance_m']*=scale;g['join_tolerance_m']*=scale
    data['mesh']['contour_mesh']['max_edge_m']*=scale
    return Case.from_dict(data)


def reference(points,radius,ell,energy=1.):
    root=brentq(lambda x:spherical_jn(ell,x),ell+3.,ell+5.,xtol=1e-14)
    omega=C0*root/radius;k=root/radius
    amplitude=np.sqrt(energy*(2*ell+1)/(EPS0*np.pi*radius**3*ell*(ell+1)*spherical_jn(ell,root,True)**2))
    r=points[:,0];z=points[:,1]-radius;rho=np.hypot(r,z)
    if np.any(rho==0):raise ValueError('validation probes exclude the spherical coordinate singularity')
    u=z/rho;j=spherical_jn(ell,k*rho);dj=spherical_jn(ell,k*rho,True)
    pol=Legendre.basis(ell);p=pol.deriv()(u);dp=pol.deriv(2)(u)
    value=amplitude*j/rho*p
    radial=(k*rho*dj-j)/rho**2
    dr=amplitude*(radial*r/rho*p-j*z*r/rho**4*dp)
    dz=amplitude*(radial*z/rho*p+j*r*r/rho**4*dp)
    return omega/TAU,np.sqrt(MU0/EPS0)*root/2,dict(Ephi_V_per_m=r*value,Hr_quadrature_A_per_m=-r*dz/(omega*MU0),Hz_quadrature_A_per_m=(2*value+r*dr)/(omega*MU0))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False);initial=fingerprint();rows=[];finals={}
    for scale in (1.,2.):
        previous=None
        for level in range(5):
            case=replace(sphere(scale),curved_refinement_levels=level)
            solution=solve(case);r=.08*scale
            points=np.array([(a,b+r) for a in np.linspace(0,.75*r,11) for b in np.linspace(-.5*r,.5*r,12) if a*a+b*b<(.94*r)**2])
            fields=[TEFieldSampler(solution).evaluate(points,i) for i in range(3)];modes=[]
            for mode in range(3):
                f,g,exact=reference(points,r,mode+1)
                sign=np.sign(fields[mode]['Ephi_V_per_m']@exact['Ephi_V_per_m'])
                errors={key:float(max(abs(sign*fields[mode][key]-value))/max(abs(value))) for key,value in exact.items()}
                q=te_quantities(solution,mode);quadrature=abs(wall_integral(solution,mode,16)/wall_integral(solution,mode)-1)
                modes.append(dict(frequency_error=abs(q['frequency_hz']/f-1),geometry_factor_error=abs(q['geometry_factor_ohm']/g-1),field_errors=errors,energy_balance=abs(q['electric_energy_j']/q['magnetic_energy_j']-1),wall_quadrature_difference=quadrature,quantities=q))
            if previous is not None:assert np.all(solution.frequencies_hz<previous)
            previous=solution.frequencies_hz.copy()
            row=dict(scale=scale,level=level,coefficients=len(solution.coefficients_v_per_m2),modes=modes);rows.append(row)
            (args.out/'partial.json').write_text(json.dumps(rows,indent=2));print(json.dumps({k:v for k,v in row.items() if k!='modes'}),flush=True)
            if level==4:
                for item in modes:
                    assert item['frequency_error']<1e-4,item
                    assert item['geometry_factor_error']<.005,item
                    assert max(item['field_errors'].values())<.01,item
                    assert item['energy_balance']<1e-9,item
                    assert item['wall_quadrature_difference']<1e-9,item
                folder=args.out/f'scale-{scale:g}';save_run(case,solution,folder);saved=read_te_run(folder)
                np.testing.assert_array_equal(saved.coefficients_v_per_m2,solution.coefficients_v_per_m2)
                finals[scale]=(solution,modes,fields)
    a,qa,fa=finals[1.];b,qb,fb=finals[2.];similarity=[]
    for mode in range(3):
        for key,factor in (('frequency_hz',.5),('geometry_factor_ohm',1.),('q0',np.sqrt(2.))):
            similarity.append(abs(qb[mode]['quantities'][key]/qa[mode]['quantities'][key]/factor-1))
        for key in ('Ephi_V_per_m','Hr_quadrature_A_per_m','Hz_quadrature_A_per_m'):
            sign=np.sign(fa[mode]['Ephi_V_per_m']@fb[mode]['Ephi_V_per_m'])
            similarity.append(float(max(abs(sign*fb[mode][key]*2**1.5-fa[mode][key]))/max(abs(fa[mode][key]))))
    assert max(similarity)<1e-8,similarity
    half=replace(sphere(1.,half=True),modes=1,curved_refinement_levels=4)
    half_solution=solve(half);half_q=te_quantities(half_solution)
    symmetry={key:abs(half_q[key]/qa[0]['quantities'][key]/factor-1) for key,factor in
              (('frequency_hz',1.),('geometry_factor_ohm',1.),('wall_loss_w',.5),('stored_energy_j',.5))}
    assert max(symmetry.values())<.005,symmetry
    save_run(half,half_solution,args.out/'half')
    np.testing.assert_array_equal(read_te_run(args.out/'half').coefficients_v_per_m2,half_solution.coefficients_v_per_m2)
    assert initial==fingerprint()
    (args.out/'validation.json').write_text(json.dumps(dict(passed=True,rows=rows,half_symmetry=symmetry,max_similarity=max(similarity),source_sha256=initial),indent=2))
    print('PASS',flush=True)


if __name__=='__main__':main()
