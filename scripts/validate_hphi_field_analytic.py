# SPDX-License-Identifier: Apache-2.0
"""Separated vacuum fields check Hphi frequency, E/H and common-volume differences."""
import argparse,json,sys,time
from pathlib import Path
import numpy as np
from scipy.special import jn_zeros,jv
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from validate_meridional_overlap import mesh
from validate_hphi_field_overlap import common_rule,independent_fields,fingerprints
from superfish_ng.axis_hphi import AxisHphiCase,solve_axis_hphi
from superfish_ng.hphi_mesh import HphiMeshCase,solve_hphi_mesh
from superfish_ng.hphi_field_overlap import hphi_field_grams
from superfish_ng.constants import C0,EPS0,MU0,TAU


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();started=time.monotonic();records=[]
    for axis in (False,True):
        for order in (1,2):
            previous=None;old=None
            for n in (2,4):
                transform=({(1,0):1/32,(0,0):0. if axis else 1/32},{(0,1):2/32})
                geometry,_=mesh(n,0,axis,transform,17 if n==2 else 31)
                case=AxisHphiCase(geometry,element_order=order,modes=3) if axis else HphiMeshCase(geometry,element_order=order,modes=3,quadrature_order=12)
                solution=solve_axis_hphi(case) if axis else solve_hphi_mesh(case)
                centers,points,weights=common_rule(geometry,12);fields=independent_fields(solution,centers,points)
                r,z=points.reshape(-1,2).T;weight=weights.ravel();a=geometry.outer_rz_m[0,0];b,length=geometry.outer_rz_m[2]
                if axis:
                    root=jn_zeros(0,1)[0];wave=root/b;omega=C0*wave;mass=length*b*b/2*jv(1,root)**2;amplitude=np.sqrt(1/(MU0*np.pi*mass))
                    h=amplitude*jv(1,wave*r);er=np.zeros_like(r);ez=-amplitude*wave/(omega*EPS0)*jv(0,wave*r)
                else:
                    wave=np.pi/length;omega=C0*wave;amplitude=np.sqrt(1/(MU0*np.pi*np.log(b/a)*length/2))
                    h=amplitude*np.cos(wave*z)/r;er=-amplitude*wave/(omega*EPS0)*np.sin(wave*z)/r;ez=np.zeros_like(r)
                projection=h@(weight[:,None]*fields[1][0]);norm=np.sqrt(np.dot(weight,h*h)*np.sum(weight[:,None]*fields[1][0]**2,axis=0));overlaps=projection/norm
                ranking=np.argsort(-abs(overlaps));mode=int(ranking[0]);margin=abs(overlaps[mode])-abs(overlaps[ranking[1]])
                assert abs(overlaps[mode])>.9 and margin>.4
                sign=float(np.sign(overlaps[mode]));errors={}
                for name,reference,samples in (('electric',[er,ez],fields[0]),('magnetic',[h],fields[1])):
                    errors[name]=float(np.sqrt(sum(np.dot(weight,(sign*f[:,mode]-exact)**2) for f,exact in zip(samples,reference))/sum(np.dot(weight,exact**2) for exact in reference)))
                errors['frequency']=float(abs(solution.frequencies_hz[mode]/(omega/TAU)-1))
                record=dict(axis=axis,order=order,subdivision=n,rank=mode+1,sign=sign,magnetic_projection=float(overlaps[mode]),projection_margin=float(margin),errors=errors)
                if previous is not None:
                    grams=hphi_field_grams(previous,solution)
                    changes={}
                    for name,matrices in (('electric',grams.electric),('magnetic',grams.magnetic)):
                        aa,ab,bb=matrices;i=old['rank']-1;j=mode
                        cross=old['sign']*sign*ab[i,j]/np.sqrt(aa[i,i]*bb[j,j]);change=np.sqrt(max(0.,2-2*cross));changes[name]=float(change)
                        assert change<=old['errors'][name]+errors[name]+1e-8
                        assert change>=abs(old['errors'][name]-errors[name])-1e-8
                    assert all(errors[k]<old['errors'][k] for k in errors)
                    gates=dict(frequency=.02,electric=.2,magnetic=.02) if order==1 else dict(frequency=.0005,electric=.015,magnetic=.002)
                    assert all(errors[k]<v for k,v in gates.items()),(axis,order,errors)
                    record.update(field_change=changes,fixed_final_gates=gates,gram_diagnostic=grams.diagnostic)
                records.append(record);previous,old=solution,record
                (out/'progress.json').write_text(json.dumps(records,indent=2)+'\n');print('DONE',axis,order,n,errors,flush=True)
    assert fingerprints()==before
    report=dict(status='PASS',scope='synthetic no-hole cylinder TEM / axis TM010 analytical fields; local field comparison verification, not general convergence acceptance',fem=8,records=records,source_sha256=before,seconds=time.monotonic()-started)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
