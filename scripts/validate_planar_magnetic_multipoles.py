# SPDX-License-Identifier: Apache-2.0
"""Independent Decimal polynomial fields and Fourier multipole frame checks."""
import argparse,hashlib,json,math,sys,time
from decimal import Decimal,localcontext
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from superfish_ng.planar_magnetic_multipoles import PlanarMagneticMultipoleFrame as Frame,PlanarMagneticMultipoleSeries as Series


def reference_field(series,points):
    # Real Cartesian powers and binomial coefficients, accumulated at 60
    # decimal digits. No production Horner or coefficient-transform calls.
    with localcontext() as context:
        context.prec=60;D=lambda v:Decimal(str(float(v)));angle=series.frame.rotation_rad;co=D(math.cos(angle));si=D(math.sin(angle));radius=D(series.frame.reference_radius_m);cx,cy=map(D,series.frame.center_xy_m);result=[]
        for x,y in points:
            dx,dy=D(x)-cx,D(y)-cy;xx=(co*dx+si*dy)/radius;yy=(-si*dx+co*dy)/radius;real=imag=Decimal(0)
            for k,(normal,skew) in enumerate(zip(series.normal_t,series.skew_t)):
                pr=pi=Decimal(0)
                for j in range(k+1):
                    term=Decimal(math.comb(k,j))*(xx**(k-j) if k-j else Decimal(1))*(yy**j if j else Decimal(1))
                    if j%4==0:pr+=term
                    elif j%4==1:pi+=term
                    elif j%4==2:pr-=term
                    else:pi-=term
                real+=D(normal)*pr-D(skew)*pi;imag+=D(normal)*pi+D(skew)*pr
            result.append([float(co*imag-si*real),float(si*imag+co*real)])
    return np.array(result)


def fourier_reference(series,frame):
    count=8*len(series.normal_t);angle=2*np.pi*np.arange(count)/count;co,si=np.cos(frame.rotation_rad),np.sin(frame.rotation_rad)
    xx,yy=frame.reference_radius_m*np.cos(angle),frame.reference_radius_m*np.sin(angle);points=np.column_stack((frame.center_xy_m[0]+co*xx-si*yy,frame.center_xy_m[1]+si*xx+co*yy));b=reference_field(series,points)
    local_x=co*b[:,0]+si*b[:,1];local_y=-si*b[:,0]+co*b[:,1];field=local_y+1j*local_x
    return np.array([np.mean(field*np.exp(-1j*k*angle)) for k in range(len(series.normal_t))])


def relative(a,b):
    a=np.asarray(a);b=np.asarray(b);scale=max(np.linalg.norm(a),np.linalg.norm(b));return float(np.linalg.norm(a-b)/scale) if scale else 0.


def fingerprints():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);start=time.monotonic();before=fingerprints();records=[];preserved={};maxima=dict(fields=0.,transformed_fields=0.,fourier_coefficients=0.,inverse=0.,composition=0.,divergence=0.,curl=0.)
    for count in (1,2,3,5,8,16,32):
        for angle in (0.,.3,-.7):
            for radius in (.01,.2):
                for amplitude in (1.,-7.):
                    name=f'multipoles-n{count}-theta{angle}-r{radius}-a{amplitude}';frame=Frame((.25,-.125),radius,angle);series=Series(frame,tuple(amplitude*(-.3)**k/(k+1) for k in range(count)),tuple(amplitude*.2**(k+1) for k in range(count)),'Synthetic finite polynomial for independent SI/frame validation; not a solved or measured field')
                    theta=np.linspace(0.,2*np.pi,33,endpoint=False);points=np.column_stack((.25+radius*.6*np.cos(theta),-.125+radius*.6*np.sin(theta)));reference=reference_field(series,points);field_error=relative(series.evaluate(points),reference);assert field_error<1e-11;maxima['fields']=max(maxima['fields'],field_error)
                    targets=[Frame((.25+.125*radius,-.125-.0625*radius),.75*radius,angle+.2),Frame((.25-.07*radius,-.125+.04*radius),.5*radius,angle-.45)];converted=[];rows=[]
                    for target in targets:
                        changed=series.in_frame(target);converted.append(changed);field_difference=relative(changed.evaluate(points),reference);coefficients=np.asarray(changed.normal_t)+1j*np.asarray(changed.skew_t);coefficient_difference=relative(coefficients,fourier_reference(series,target));inverse=changed.in_frame(frame);inverse_difference=relative(np.r_[inverse.normal_t,inverse.skew_t],np.r_[series.normal_t,series.skew_t])
                        assert max(field_difference,coefficient_difference,inverse_difference)<1e-11
                        for key,value in [('transformed_fields',field_difference),('fourier_coefficients',coefficient_difference),('inverse',inverse_difference)]:maxima[key]=max(maxima[key],value)
                        rows.append(dict(frame=target.to_dict(),field_error=field_difference,fourier_error=coefficient_difference,inverse_error=inverse_difference))
                    composed=converted[0].in_frame(targets[1]);composition=relative(np.r_[composed.normal_t,composed.skew_t],np.r_[converted[1].normal_t,converted[1].skew_t]);assert composition<1e-11;maxima['composition']=max(maxima['composition'],composition)
                    step=radius*1e-6;dx=(series.evaluate(points+[step,0.])-series.evaluate(points-[step,0.]))/(2*step);dy=(series.evaluate(points+[0.,step])-series.evaluate(points-[0.,step]))/(2*step);scale=abs(amplitude)/radius
                    divergence=float(np.max(abs(dx[:,0]+dy[:,1]))/scale);curl=float(np.max(abs(dx[:,1]-dy[:,0]))/scale);assert max(divergence,curl)<2e-6
                    maxima['divergence']=max(maxima['divergence'],divergence);maxima['curl']=max(maxima['curl'],curl)
                    path=out/(name+'.json');path.write_text(json.dumps(series.to_dict(),indent=2)+'\n');preserved[path.name]=hashlib.sha256(path.read_bytes()).hexdigest();assert Series.from_dict(json.loads(path.read_text())).to_dict()==series.to_dict()
                    records.append(dict(name=name,field_error=field_error,transforms=rows,composition_error=composition,divergence=divergence,curl=curl));print('DONE',name,flush=True)
    assert len(records)==84 and fingerprints()==before
    for name,digest in preserved.items():assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest
    report=dict(status='PASS',cases=84,decimal_field_comparisons=84,fourier_frame_comparisons=168,inverse_comparisons=168,composition_comparisons=84,divergence_and_curl_checks=168,max_errors=maxima,records=records,source_sha256=before,seconds=time.monotonic()-start,
        interpretation='Finite planar harmonic polynomial representation and SI/frame transforms only. Independent Decimal Cartesian powers and Fourier coefficients; no FEM extraction, source-free-domain certification, force, torque, or omitted-order error bound.')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('records','source_sha256')})


if __name__=='__main__':main()
