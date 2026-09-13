# SPDX-License-Identifier: Apache-2.0
"""Independent decimal interval integrals and differential tests of H(B) tables."""
import argparse,hashlib,json,sys,time
from decimal import Decimal,localcontext
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from superfish_ng.bh_curve import MonotoneBHCurve


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def decimal_reference(curve,query):
    # Integrate each affine interval independently with exact binary64 inputs
    # converted to Decimal. No production slope or prefix-energy arrays reused.
    with localcontext() as context:
        context.prec=60;b=list(map(Decimal.from_float,curve.b_t));h=list(map(Decimal.from_float,curve.h_a_per_m));x=Decimal.from_float(float(query));w=Decimal(0);co=Decimal(0)
        for i in range(len(b)-1):
            slope=(h[i+1]-h[i])/(b[i+1]-b[i]);end=min(x,b[i+1]);dx=max(Decimal(0),end-b[i]);hy=h[i]+slope*dx
            w+=dx*(h[i]+hy)/2;co+=(hy-h[i])*(b[i]+end)/2
            if x<b[i+1] or i==len(b)-2:
                return float(hy),float(w),float(co),float(slope),float(hy/x) if x else float(slope)
    raise AssertionError('reference query outside table')


def relative(a,b):
    a=np.asarray(a);b=np.asarray(b);scale=np.linalg.norm(b)
    return float(np.linalg.norm(a-b)/scale) if scale else float(np.linalg.norm(a-b))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    before=fingerprints();start=time.monotonic();records=[];preserved={};scalar_count=vector_count=columns=zero_count=0
    maximum=dict(value=0.,energy=0.,coenergy=0.,inverse=0.,legendre=0.,tangent=0.,gradient=0.,reversal=0.,rotation=0.)
    base_b=np.array([0.,.25,.5,1.,2.]);shapes=dict(linear=400*base_b,saturation=np.array([0.,100.,250.,1500.,25000.]),varying_positive_slopes=np.array([0.,100.,250.,400.,600.]))
    directions=[np.array([1.,0.]),np.array([.6,-.8]),np.array([1.,0.,0.]),np.array([.3,-.4,np.sqrt(.75)])]
    def check(name,actual,expected,limit=1e-11):
        error=relative(actual,expected);assert error<=limit,(name,error,limit);maximum[name]=max(maximum[name],error)
    for shape,base_h in shapes.items():
        for bscale in (.01,1.,100.):
            for hscale in (.01,1.,100.):
                name=f'{shape}-b{bscale}-h{hscale}';curve=MonotoneBHCurve(name,tuple(base_b*bscale),tuple(base_h*hscale),'Synthetic table for independent numerical validation; no measured or legacy material')
                path=out/(name+'.json');path.write_text(json.dumps(curve.to_dict(),indent=2)+'\n');preserved[path.name]=hashlib.sha256(path.read_bytes()).hexdigest();assert MonotoneBHCurve.from_dict(json.loads(path.read_text())).to_dict()==curve.to_dict()
                inside=[a+t*(b-a) for a,b in zip(curve.b_t[:-1],curve.b_t[1:]) for t in (.17,.53,.89)]
                for value in [*curve.b_t,*inside]:
                    ref=decimal_reference(curve,value);state=curve.evaluate_magnitudes(value);scalar_count+=1
                    for label,key,expected in [('value','h_a_per_m',ref[0]),('energy','energy_density_j_per_m3',ref[1]),('coenergy','coenergy_density_j_per_m3',ref[2]),('tangent','differential_reluctivity_m_per_h',ref[3])]:check(label,state[key],expected)
                    check('inverse',curve.induction_magnitudes(state['h_a_per_m']),value);check('legendre',state['energy_density_j_per_m3']+state['coenergy_density_j_per_m3'],value*state['h_a_per_m'])
                for dim in (2,3):
                    state=curve.evaluate_vectors(np.zeros(dim));np.testing.assert_array_equal(state['h_a_per_m'],0.);np.testing.assert_array_equal(state['tangent_reluctivity_m_per_h'],np.eye(dim)*(curve.h_a_per_m[1]/curve.b_t[1]));zero_count+=1
                for value in inside:
                    for direction in directions:
                        b=value*direction;state=curve.evaluate_vectors(b);magnitude=float(np.hypot.reduce(b));h,w,co,slope,secant=decimal_reference(curve,magnitude);n=b/magnitude
                        check('value',state['h_a_per_m'],h*n);check('energy',state['energy_density_j_per_m3'],w);check('coenergy',state['coenergy_density_j_per_m3'],co)
                        # Radial and transverse eigenvalues follow independently
                        # from one-dimensional curve slope and infinitesimal rotation.
                        eig=np.linalg.eigvalsh(state['tangent_reluctivity_m_per_h']);check('tangent',eig,np.sort([slope,*([secant]*(len(b)-1))]));assert eig.min()>0.
                        inverse=curve.evaluate_vectors(-b);check('reversal',inverse['h_a_per_m'],-state['h_a_per_m']);check('reversal',inverse['energy_density_j_per_m3'],w)
                        angle=.713;rotation=np.eye(len(b));rotation[:2,:2]=[[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]];rot=curve.evaluate_vectors(rotation@b)
                        check('rotation',rot['h_a_per_m'],rotation@state['h_a_per_m']);check('rotation',rot['tangent_reluctivity_m_per_h'],rotation@state['tangent_reluctivity_m_per_h']@rotation.T)
                        step=bscale*1e-6;gradient=[];tangent=[]
                        for axis in np.eye(len(b)):
                            plus=curve.evaluate_vectors(b+step*axis);minus=curve.evaluate_vectors(b-step*axis)
                            gradient.append((plus['energy_density_j_per_m3']-minus['energy_density_j_per_m3'])/(2*step));tangent.append((plus['h_a_per_m']-minus['h_a_per_m'])/(2*step));columns+=1
                        check('gradient',gradient,state['h_a_per_m'],1e-6);check('tangent',np.array(tangent).T,state['tangent_reluctivity_m_per_h'],2e-6);vector_count+=1
                records.append(dict(name=name,shape=shape,b_scale=bscale,h_scale=hscale,scalar_checks=17,vector_checks=48));print('DONE',name,flush=True)
    assert len(records)==27 and scalar_count==459 and vector_count==1296 and columns==3240 and zero_count==54 and fingerprints()==before
    for name,digest in preserved.items():assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest
    report=dict(status='PASS',curves=len(records),scalar_checks=scalar_count,vector_checks=vector_count,finite_difference_columns=columns,zero_vector_checks=zero_count,max_errors=maximum,
        records=records,source_sha256=before,seconds=time.monotonic()-start,
        interpretation='Synthetic isotropic static H(B) only. Decimal interval integration, constitutive inversion, energy/coenergy, positive radial/transverse tangents, reversal/rotation and finite differences verified. No FEM solve, mesh-error estimate or external solver comparison.')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('records','source_sha256')})


if __name__=='__main__':main()
