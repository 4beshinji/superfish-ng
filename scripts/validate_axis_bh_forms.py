# SPDX-License-Identifier: Apache-2.0
"""Independent axis B-H quadrature forms, constant-a physics and variations."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
from scipy.linalg import eigvalsh
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.curved_meridional_reference import fixture
from scripts.validate_bh_curve import decimal_reference
from superfish_ng.bh_curve import MonotoneBHCurve
from superfish_ng.magnetic_materials import MagneticRegion
from superfish_ng.axis_connected_mesh import AxisConnectedMesh
from superfish_ng.axis_bh_materials import AxisBHPartition
from superfish_ng.axis_bh_fem import axis_bh_forms,_assemble
from superfish_ng.constants import TAU


def partition(holes=1,pattern=1,scale=1.,shift=0.,h_scale=1.,linear=False):
    mesh=fixture(True,holes,scale=scale,shear=0.)[0]['base_mesh'];t=np.array([0.,shift]);mesh=AxisConnectedMesh(mesh.outer_rz_m+t,[h+t for h in mesh.holes_rz_m],mesh.points_rz_m+t,mesh.triangles)
    labels=np.arange(len(mesh.triangles))%2 if pattern else np.zeros(len(mesh.triangles),dtype=int)
    b=np.array([0.,.25,.5,1.,4.]);curves=[400*b,1200*b] if linear else [np.array([0.,100.,250.,1500.,100000.]),np.array([0.,80.,500.,1800.,50000.])]
    materials=[MonotoneBHCurve(f'm{i}',tuple(b),tuple(h*h_scale),'Synthetic SI curve for axis validation; no measured or legacy material') for i,h in enumerate(curves[:int(labels.max())+1])]
    regions=[MagneticRegion(f'r{i}',m.id,np.flatnonzero(labels==i).tolist()) for i,m in enumerate(materials)]
    return AxisBHPartition(mesh,materials,regions)


def reference_forms(p,coefficients,current,order):
    # Physical-coordinate Vandermonde interpolation, independent Duffy rule,
    # and Decimal interval integration; no production shape/state arrays.
    nodes,weights=np.polynomial.legendre.leggauss(order);nodes=(nodes+1)/2;weights=weights/2
    x=np.repeat(nodes,len(nodes));y=np.tile(nodes,len(nodes))*(1-x);w=np.repeat(weights,len(weights))*np.tile(weights,len(weights))*(1-x)
    bary=np.column_stack((1-x-y,x,y));n=len(p.mesh.points_rz_m);k=np.zeros((n,n));g=np.zeros(n);f=np.zeros(n);u=co=work=0.
    for index,dofs in enumerate(p.mesh.triangles):
        points=p.mesh.points_rz_m[dofs];inverse=np.linalg.inv(np.column_stack((np.ones(3),points)));q=points[0]+np.column_stack((x,y))@(points[1:]-points[0]);values=np.column_stack((np.ones(len(q)),q))@inverse
        dr,dz=inverse[1],inverse[2];radius=q[:,0];measure=TAU*radius*w*np.linalg.det((points[1:]-points[0]).T)
        br=-radius[:,None]*dz;bz=2*values+radius[:,None]*dr;bi=np.stack((br,bz),axis=-1);b=bi.transpose(0,2,1)@coefficients[dofs];magnitude=np.linalg.norm(b,axis=1)
        material=p.materials[p.cell_material_indices[index]];assert np.all(magnitude<=material.b_t[-1])
        ref=np.array([decimal_reference(material,float(v)) for v in magnitude]);h=np.zeros_like(b);direction=np.zeros_like(b);positive=magnitude>0;direction[positive]=b[positive]/magnitude[positive,None];h=ref[:,0,None]*direction
        parallel=np.einsum('qia,qa->qi',bi,direction);local_k=np.einsum('q,qia,qja->ij',measure*ref[:,4],bi,bi)+parallel.T@((measure*(ref[:,3]-ref[:,4]))[:,None]*parallel)
        k[np.ix_(dofs,dofs)]+=local_k;g[dofs]+=np.einsum('q,qia,qa->i',measure,bi,h);f[dofs]+=values.T@(measure*radius*current[p.regions[p.cell_region_indices[index]].id])
        u+=float(measure@ref[:,1]);co+=float(measure@ref[:,2]);work+=float(measure@np.sum(b*h,axis=1))
    return k,g,f,np.array([u,co,work])


def relative(a,b):
    scale=max(np.linalg.norm(a),np.linalg.norm(b));return float(np.linalg.norm(np.asarray(a)-np.asarray(b))/scale) if scale else 0.


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);start=time.monotonic();before=fingerprints();records=[];preserved={};baseline={};maxima=dict(tangent=0.,internal_load=0.,current_load=0.,potentials=0.,covariance=0.,energy_variation=0.,load_variation=0.,uniform=0.);min_eigen=1.;variations=0
    for holes in (0,1,2):
        for pattern in (0,1):
            for amplitude in (.07,.17,.27,.6):
                for scale in (.5,2.):
                    for hscale in (1.,7.):
                        sign=1. if hscale==1. else -1.;shift=0. if scale==.5 else -.25;name=f'axis-bh-holes{holes}-pattern{pattern}-a{amplitude}-s{scale}-h{hscale}'
                        p=partition(holes,pattern,scale,shift,hscale);r,z=p.mesh.points_rz_m.T;coefficients=sign*amplitude*(1+.4*r/scale+.3*(z-shift)/scale);current={v.id:sign*hscale/scale*(2 if i==0 else -3) for i,v in enumerate(p.regions)}
                        space,k,g,f,q=axis_bh_forms(p,coefficients,current,quadrature_order=12);rk,rg,rf,rq=reference_forms(p,coefficients,current,12)
                        differences=[relative(k.toarray(),rk),relative(g,rg),relative(f,rf),relative([q['energy_j'],q['coenergy_j'],q['bdoth_integral_j']],rq)];assert max(differences)<1e-10,(name,differences)
                        for key,value in zip(('tangent','internal_load','current_load','potentials'),differences):maxima[key]=max(maxima[key],value)
                        eigen=eigvalsh(rk);ratio=float(eigen[0]/eigen[-1]);assert ratio>1e-8;min_eigen=min(min_eigen,ratio)
                        assert q['constant_a_is_gauge'] is False and len(space.axis_dofs)>0
                        key=holes,pattern,amplitude;normalized=[k.toarray()/(hscale*scale**3),g/(sign*hscale*scale**3),f/(sign*hscale*scale**3),np.array([q['energy_j'],q['coenergy_j']])/(hscale*scale**3)]
                        if key not in baseline:baseline[key]=normalized
                        else:
                            errors=[relative(a,b) for a,b in zip(normalized,baseline[key])];assert max(errors)<1e-10;maxima['covariance']=max(maxima['covariance'],*errors)
                        densities=np.array([current[v.id] for v in p.regions]);step=amplitude*1e-6
                        for direction in (np.ones(len(coefficients)),np.cos(np.arange(len(coefficients))+.3)):
                            _,gp,_,qp=_assemble(space,coefficients+step*direction,densities,12);_,gm,_,qm=_assemble(space,coefficients-step*direction,densities,12)
                            de=abs((qp['energy_j']-qm['energy_j'])/(2*step)-g@direction)/(np.linalg.norm(g)*np.linalg.norm(direction));dg=relative((gp-gm)/(2*step),k@direction)
                            assert de<2e-6 and dg<2e-6,(name,de,dg);maxima['energy_variation']=max(maxima['energy_variation'],float(de));maxima['load_variation']=max(maxima['load_variation'],dg);variations+=1
                        # Uniform a has a nonzero axial field. Its energies have
                        # a separate geometric volume/Decimal constitutive reference.
                        constant=sign*amplitude*np.ones(len(coefficients));_,_,_,uq=_assemble(space,constant,densities,4)
                        exact=np.zeros(2)
                        for i,m in enumerate(p.materials):
                            ref=decimal_reference(m,2*amplitude);volume=0.
                            for cell,triangle in enumerate(p.mesh.triangles):
                                if p.cell_material_indices[cell]!=i:continue
                                vertices=p.mesh.points_rz_m[triangle];volume+=TAU*np.linalg.det((vertices[1:]-vertices[0]).T)/2*float(vertices[:,0].sum())/3
                            exact+=volume*np.array(ref[1:3])
                        ue=relative([uq['energy_j'],uq['coenergy_j']],exact);assert ue<1e-10;maxima['uniform']=max(maxima['uniform'],ue)
                        path=out/(name+'.json');path.write_text(json.dumps(dict(partition=p.to_dict(),coefficients_a_t=coefficients.tolist(),current_density_phi_a_per_m2=current),indent=2)+'\n');preserved[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
                        records.append(dict(name=name,form_differences=differences,positive_spectrum_ratio=ratio,uniform_error=ue,quadrature=q['quadrature_comparison'],table_intervals=q['table_intervals_used']));print('DONE',name,flush=True)
    quadrature_studies=[]
    for pattern in (0,1):
        p=partition(0,pattern);r,z=p.mesh.points_rz_m.T;values=.1+.9*r+.6*z;current={v.id:0. for v in p.regions};rows=[]
        for order in (4,8,16,32):
            space,k,g,f,q=axis_bh_forms(p,values,current,quadrature_order=order);rk,rg,rf,rq=reference_forms(p,values,current,order)
            differences=[relative(k.toarray(),rk),relative(g,rg),relative([q['energy_j'],q['coenergy_j']],rq[:2])];assert max(differences)<1e-10
            rows.append(dict(order=order,same_rule_reference_differences=differences,comparison=q['quadrature_comparison'],table_intervals=q['table_intervals_used']))
        assert rows[0]['comparison']['tangent_relative_difference']>1e-6 and rows[0]['comparison']['energy_relative_difference']>1e-8
        quadrature_studies.append(dict(pattern=pattern,rows=rows,interpretation='table-knot crossings produce measurable integration differences; same-rule fidelity does not remove this approximation'))
    assert len(records)==96 and variations==192 and fingerprints()==before
    for name,digest in preserved.items():assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest
    report=dict(status='PASS',cases=96,independent_form_comparisons=384,variation_checks=variations,uniform_checks=96,minimum_positive_eigenvalue_ratio=min_eigen,max_errors=maxima,quadrature_studies=quadrature_studies,records=records,source_sha256=before,seconds=time.monotonic()-start,
        interpretation='axis P1 a=Aphi/r has no constant gauge kernel; original nonlinear H/tangent and full 3D potentials independently checked; fixed quadrature error remains separate from eventual nonlinear residual or mesh error; no boundary solve or legacy comparison')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('records','source_sha256','quadrature_studies')})


if __name__=='__main__':main()
