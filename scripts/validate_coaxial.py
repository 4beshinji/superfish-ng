# SPDX-License-Identifier: Apache-2.0
"""Independent TEM and annular Bessel spectrum, fields, wall loss and scaling."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np
from scipy.optimize import brentq
from scipy.special import jv,yv
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng.constants import C0,TAU,MU0,EPS0
from superfish_ng.coaxial import CoaxialCase,solve_coaxial,coaxial_quantities
from superfish_ng.coaxial_saved import save_coaxial_run,read_coaxial_run
from superfish_ng.fem import triangle_quadrature


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def radial_roots(a,b,count):
    ratio=a/b
    def determinant(x):return jv(0,ratio*x)*yv(0,x)-yv(0,ratio*x)*jv(0,x)
    step=np.pi/(32*(1-ratio));left=1e-6;roots=[]
    while len(roots)<count:
        right=left+step
        if determinant(left)*determinant(right)<0:
            root=brentq(determinant,left,right,xtol=1e-13)
            assert abs(determinant(root))<1e-11
            roots.append(root/b)
        left=right
        if left>1000/(1-ratio):raise AssertionError('radial root search exhausted')
    return roots


def exact_modes(case):
    roots=[0.,*radial_roots(case.inner_radius_m,case.outer_radius_m,case.modes)]
    candidates=sorted((C0/TAU*np.hypot(kr,p*np.pi/case.length_m),n,p,kr)
                      for n,kr in enumerate(roots) for p in range(case.modes+1) if n or p)
    result=candidates[:case.modes]
    assert min(np.diff([q[0] for q in candidates[:case.modes+1]])/np.array([q[0] for q in candidates[1:case.modes+1]]))>1e-3
    return result


def radial(case,n,kr,r):
    if n==0:return np.ones_like(r),np.zeros_like(r)
    a=case.inner_radius_m
    h=yv(0,kr*a)*jv(1,kr*r)-jv(0,kr*a)*yv(1,kr*r)
    derivative=kr*r*(yv(0,kr*a)*jv(0,kr*r)-jv(0,kr*a)*yv(0,kr*r))
    return r*h,derivative


def reference(case,item):
    f,n,p,kr=item;a,b,L=case.inner_radius_m,case.outer_radius_m,case.length_m
    x,w=np.polynomial.legendre.leggauss(128);r=a+(x+1)*(b-a)/2
    value,_=radial(case,n,kr,r)
    integral=float(np.sum(w*(b-a)/2*value**2/r));axial=L if p==0 else L/2
    amplitude=np.sqrt(case.normalization_j/(MU0*np.pi*integral*axial))
    walls=np.array([TAU*amplitude**2*float(radial(case,n,kr,np.array([radius]))[0][0])**2*axial/radius for radius in (a,b)]
                   +[TAU*amplitude**2*integral]*2)
    omega=TAU*f;rs=np.sqrt(np.pi*f*MU0/case.conductivity_s_per_m);power=rs*walls.sum()/2
    quantities=dict(frequency_hz=f,stored_energy_j=case.normalization_j,geometry_factor_ohm=2*omega*case.normalization_j/walls.sum(),
                    q0=omega*case.normalization_j/power,wall_loss_w=power)
    def fields(r,z):
        value,derivative=radial(case,n,kr,r);kz=p*np.pi/L
        h=amplitude*value/r*np.cos(kz*z)
        er=-amplitude*value*kz/(r*omega*EPS0)*np.sin(kz*z)
        ez=-amplitude*derivative/(r*omega*EPS0)*np.cos(kz*z)
        return h,np.column_stack((er,ez))
    return quantities,walls,fields


def compare(case,solution):
    exact=exact_modes(case);space=solution.space;vertices=space.mesh.points[space.mesh.triangles]
    cells=np.arange(len(vertices));rows=[]
    for mode,item in enumerate(exact):
        expected,walls,analytic=reference(case,item)
        norm_h=np.zeros(3);norm_e=np.zeros(3)
        for bary,weight in triangle_quadrature(7):
            rz=np.einsum('tij,i->tj',vertices,bary)
            h,e=analytic(*rz.T)
            actual=solution.fields_in_cells(cells,np.tile(bary,(len(cells),1)),mode)
            ah=actual['Hphi_real_A_per_m'];ae=np.column_stack((actual['Er_quadrature_V_per_m'],actual['Ez_quadrature_V_per_m']))
            measure=TAU*rz[:,0]*weight*space.determinants
            norm_h+=np.array([measure@(ah*ah),measure@(h*h),measure@(ah*h)])
            norm_e+=np.array([measure@np.sum(ae*ae,axis=1),measure@np.sum(e*e,axis=1),measure@np.sum(ae*e,axis=1)])
        sign=1 if norm_h[2]>=0 else -1
        h_error=np.sqrt(max(0.,(norm_h[0]+norm_h[1]-2*sign*norm_h[2])/norm_h[1]))
        e_error=np.sqrt(max(0.,(norm_e[0]+norm_e[1]-2*sign*norm_e[2])/norm_e[1]))
        q=coaxial_quantities(solution,mode)
        errors={key:float(abs(q[key]/value-1)) for key,value in expected.items()}
        errors.update(electric_relative_l2=float(e_error),magnetic_relative_l2=float(h_error),
                      wall_components_relative_error=float(np.max(abs(np.array(list(q['wall_h2_integral_a2_by_surface'].values()))/walls-1))))
        rows.append(dict(mode_index=mode,analytic_family='TEM' if item[1]==0 else 'TM',radial_index=item[1],axial_index=item[2],
                         reference=expected,quantities=q,errors=errors))
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    before=fingerprints();start=time.monotonic();records=[]
    limits={1:dict(frequency_hz=1e-3,electric_relative_l2=.035,magnetic_relative_l2=.002,
                   geometry_factor_ohm=.005,q0=.005,wall_loss_w=.005,wall_components_relative_error=.005,stored_energy_j=1e-8),
            2:dict(frequency_hz=1e-4,electric_relative_l2=.01,magnetic_relative_l2=.001,
                   geometry_factor_ohm=.005,q0=.005,wall_loss_w=.005,wall_components_relative_error=.005,stored_energy_j=1e-8)}
    for shape,(a,b,L) in [('tem',(.025,.05,.18)),('mixed',(.025,.1,.12))]:
        for order,levels in [(1,(64,128)),(2,(24,48))]:
            for scale in (1.,2.):
                previous=None
                for level,n in enumerate(levels):
                    case=CoaxialCase(a*scale,b*scale,L*scale,nr=n,nz=n,element_order=order,modes=4,normalization_j=scale**3)
                    solution=solve_coaxial(case);rows=compare(case,solution)
                    folder=out/f'{shape}-p{order}-s{scale:g}-n{n}'
                    saved=save_coaxial_run(case,solution,folder);replayed=read_coaxial_run(folder)
                    np.testing.assert_array_equal(replayed.coefficients,solution.coefficients)
                    worst={key:max(row['errors'][key] for row in rows) for key in limits[order]}
                    record=dict(shape=shape,order=order,scale=scale,n=n,final=bool(level),dofs=len(solution.coefficients),
                        modes=rows,max_errors=worst,matrix_quadrature=solution.quadrature_diagnostic,
                        native_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()})
                    records.append(record)
                    (out/'progress.json').write_text(json.dumps(dict(records=records),indent=2)+'\n')
                    print(shape,order,scale,n,worst,flush=True)
                    if level:
                        for key,limit in limits[order].items():
                            assert worst[key]<limit,(shape,order,scale,key,worst[key],limit)
                            if key!='stored_energy_j':assert worst[key]<previous[key],(shape,order,scale,'no refinement decrease',key)
                    previous=worst
    similarity=[]
    for first in [r for r in records if r['scale']==1]:
        second=next(r for r in records if r['shape']==first['shape'] and r['order']==first['order'] and r['n']==first['n'] and r['scale']==2)
        for a,b in zip(first['modes'],second['modes']):
            for key,factor in dict(frequency_hz=.5,stored_energy_j=8.,geometry_factor_ohm=1.,q0=np.sqrt(2),wall_loss_w=2**1.5).items():
                similarity.append(abs(b['quantities'][key]/(a['quantities'][key]*factor)-1))
    assert max(similarity)<1e-8
    after=fingerprints();assert after==before
    result=dict(status='PASS',scope='two closed coaxial rectangles; TEM and positive-radial-index TM; not arbitrary inner conductors',
                records=records,limits=limits,max_similarity_relative_error=float(max(similarity)),
                source_sha256=after,source_unchanged=True,seconds=time.monotonic()-start)
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS',len(records),'FEM/native comparisons',flush=True)


if __name__=='__main__':main()
