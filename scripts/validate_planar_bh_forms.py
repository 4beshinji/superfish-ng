# SPDX-License-Identifier: Apache-2.0
"""Independent P1 nonlinear magnetic weak forms, Decimal work and variations."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.planar_electrostatic_reference import rectangle
from scripts.validate_bh_curve import decimal_reference
from superfish_ng.bh_curve import MonotoneBHCurve
from superfish_ng.magnetic_materials import MagneticRegion
from superfish_ng.planar_bh_materials import PlanarBHPartition
from superfish_ng.planar_bh_fem import planar_bh_forms
from superfish_ng.planar_mesh import PlanarMesh


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def fixture(geometry,pattern,amplitude,scale,hscale):
    mesh,local,width,height,_,_=rectangle(4,scale,concave=geometry=='concave');shape=np.array([[1.,.2],[.1,1.]]) if geometry=='sheared' else np.eye(2)
    angle=.713 if hscale==7. else 0.;q=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]]);shift=np.array([-.25,.125]) if hscale==7. else np.zeros(2)
    mesh=PlanarMesh.create(mesh.polygon_xy_m@shape.T@q.T+shift,mesh.points_xy_m@shape.T@q.T+shift,mesh.triangles)
    labels=np.zeros(len(mesh.triangles),dtype=int) if pattern=='uniform' else np.arange(len(mesh.triangles))%2
    tables=[[0.,100.,250.,1500.,100000.],[0.,80.,500.,1800.,50000.]];materials=[MonotoneBHCurve(f'm{i}',[0.,.25,.5,1.,4.],tuple(np.array(tables[i])*hscale),'Synthetic monotone table; no measured or legacy material') for i in range(labels.max()+1)]
    regions=[MagneticRegion(f'r{i}',f'm{i}',np.flatnonzero(labels==i).tolist()) for i in range(len(materials))];p=PlanarBHPartition(mesh,materials,regions)
    sign=-1. if hscale==7. else 1.;x,y=(local/scale).T;w=width/scale;hh=height/scale
    a=sign*amplitude*scale*(.3*x+.7*y+1.1*x*x/w-.45*x*y/w+.2*y*y/hh)
    current={v.id:sign*(2. if i==0 else -3.)*hscale/scale for i,v in enumerate(regions)}
    return p,a,current,sign


def independent(p,coefficients,current):
    n=len(coefficients);k=np.zeros((n,n));g=np.zeros(n);f=np.zeros(n);energy=coenergy=bdoth=0.;indices={m.id:i for i,m in enumerate(p.materials)}
    for index,cell in enumerate(p.mesh.triangles):
        vertices=p.mesh.points_xy_m[cell];v=np.column_stack((np.ones(3),vertices));inverse=np.linalg.inv(v);gradient=inverse[1:,:].T
        curls=np.column_stack((gradient[:,1],-gradient[:,0]));b=(coefficients[cell]-coefficients[cell[0]])@curls;magnitude=float(np.hypot.reduce(b));area=abs(float(np.linalg.det(v)))/2
        region=p.regions[p.cell_region_indices[index]];material=p.materials[indices[region.material]];h,w,ws,slope,secant=decimal_reference(material,magnitude);direction=b/magnitude if magnitude else np.zeros(2)
        intensity=h*direction;tangent=secant*np.eye(2)+(slope-secant)*np.outer(direction,direction)
        np.add.at(g,cell,area*(curls@intensity));np.add.at(f,cell,np.full(3,current[region.id]*area/3));np.add.at(k,(cell[:,None],cell[None,:]),area*curls@tangent@curls.T)
        energy+=area*w;coenergy+=area*ws;bdoth+=area*float(b@intensity)
    return k,g,f,np.array([energy,coenergy,bdoth])


def relative(a,b):
    a=np.asarray(a);b=np.asarray(b);scale=np.linalg.norm(b);return float(np.linalg.norm(a-b)/scale) if scale else float(np.linalg.norm(a-b))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    before=fingerprints();start=time.monotonic();records=[];preserved={};baselines={};maxima=dict(tangent=0.,internal_load=0.,current_load=0.,potentials=0.,covariance=0.,energy_gradient=0.,load_derivative=0.);minimum_ratio=1.;used=set()
    for geometry in ('rectangle','concave','sheared'):
        for pattern in ('uniform','checkerboard'):
            for amplitude in (.173,.557):
                for scale in (.5,2.):
                    for hscale in (1.,3.,7.):
                        name=f'{geometry}-{pattern}-a{amplitude}-s{scale}-h{hscale}';p,a,current,sign=fixture(geometry,pattern,amplitude,scale,hscale)
                        _,k,g,f,q=planar_bh_forms(p,a,current);rk,rg,rf,rq=independent(p,a,current);values=np.array([q['energy_j_per_m'],q['coenergy_j_per_m'],q['bdoth_integral_j_per_m']])
                        errors={label:relative(actual,expected) for label,actual,expected in zip(('tangent','internal_load','current_load','potentials'),(k.toarray(),g,f,values),(rk,rg,rf,rq))}
                        assert max(errors.values())<1e-10,errors
                        eigenvalues=np.linalg.eigvalsh(k.toarray());assert abs(eigenvalues[0])/eigenvalues[-1]<1e-12 and eigenvalues[1]/eigenvalues[-1]>1e-5;minimum_ratio=min(minimum_ratio,float(eigenvalues[1]/eigenvalues[-1]))
                        key=geometry,pattern,amplitude;normalized=(k.toarray()/hscale,g/(scale*hscale*sign),f/(scale*hscale*sign),values/(scale**2*hscale))
                        if key not in baselines:baselines[key]=normalized
                        covariance=max(relative(x,y) for x,y in zip(normalized,baselines[key]));assert covariance<1e-10
                        direction=np.sin(np.arange(len(a))+.37);step=1e-8*scale
                        _,_,gp,_,qp=planar_bh_forms(p,a+step*direction,current);_,_,gm,_,qm=planar_bh_forms(p,a-step*direction,current)
                        energy_gradient=relative((qp['energy_j_per_m']-qm['energy_j_per_m'])/(2*step),float(direction@g));load_derivative=relative((gp-gm)/(2*step),k@direction)
                        assert energy_gradient<1e-6 and load_derivative<2e-6,(energy_gradient,load_derivative)
                        for value in q['table_intervals_used'].values():used.update(value)
                        errors.update(covariance=covariance,energy_gradient=energy_gradient,load_derivative=load_derivative)
                        for label,value in errors.items():maxima[label]=max(maxima[label],value)
                        path=out/(name+'.json');path.write_text(json.dumps(dict(partition=p.to_dict(),az_wb_per_m=a.tolist(),current_density_z_a_per_m2=current,element_order=1,quantities=q),indent=2)+'\n');preserved[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
                        records.append(dict(name=name,geometry=geometry,pattern=pattern,amplitude=amplitude,scale=scale,h_scale=hscale,errors=errors));print('DONE',name,flush=True)
    assert len(records)==72 and len(used)>=3 and fingerprints()==before
    for name,digest in preserved.items():assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest
    report=dict(status='PASS',cases=len(records),independent_form_comparisons=4*len(records),variation_checks=2*len(records),material_intervals_used=sorted(used),max_errors=maxima,min_nonconstant_eigenvalue_ratio=minimum_ratio,records=records,source_sha256=before,seconds=time.monotonic()-start,
        interpretation='P1 cell-constant original B/H. Independent Vandermonde gradients and Decimal interval potentials, global g/K/source, positive tangent/gauge, energy/load derivatives and geometric/material covariance. No nonlinear solve or mesh-accuracy claim.')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('records','source_sha256')})


if __name__=='__main__':main()
