# SPDX-License-Identifier: Apache-2.0
"""Independent regular axis magnetic forms, energy and azimuthal current work."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
from scipy.linalg import eigvalsh
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.curved_meridional_reference import fixture
from superfish_ng.magnetic_materials import LinearMagneticMaterial,MagneticRegion
from superfish_ng.axis_magnetic_materials import AxisMagneticPartition
from superfish_ng.axis_connected_mesh import AxisConnectedMesh
from superfish_ng.magnetostatic_fem import axis_magnetostatic_forms
from superfish_ng.constants import MU0,TAU


def make_partition(holes,pattern,scale,shift):
    mesh=fixture(True,holes,scale=scale,shear=0.)[0]['base_mesh'];count=len(mesh.triangles)
    labels=(np.zeros(count,dtype=int) if pattern==0 else
            (mesh.points_rz_m[mesh.triangles][:,:,1].mean(axis=1)>=scale/16).astype(int) if pattern==1 else np.arange(count)%3)
    translation=np.array([0.,shift]);mesh=AxisConnectedMesh(mesh.outer_rz_m+translation,[h+translation for h in mesh.holes_rz_m],mesh.points_rz_m+translation,mesh.triangles)
    mu=np.array([2.,5.,11.])[:int(labels.max())+1];current=np.array([2.,-3.,7.])[:len(mu)]
    materials=[LinearMagneticMaterial(f'magnetic-{i}',v) for i,v in enumerate(mu)]
    regions=[MagneticRegion(f'region-{i}',materials[i].id,np.flatnonzero(labels==i).tolist()) for i in range(len(mu))]
    return AxisMagneticPartition(mesh,materials,regions),{r.id:float(v) for r,v in zip(regions,current)},mu[labels],current[labels]


def dense_reference(mesh,mu,current,order):
    # Independent nodal interpolation, Duffy/Gauss integration and DOF map.
    nodes=np.array([[0.,0.],[1.,0.],[0.,1.],[.5,0.],[.5,.5],[0.,.5]])[:3 if order==1 else 6]
    def monomials(x,y):
        value=np.column_stack((np.ones(len(x)),x,y))
        return value if order==1 else np.column_stack((value,x*x,x*y,y*y))
    inverse=np.linalg.inv(monomials(*nodes.T));g,w=np.polynomial.legendre.leggauss(18);g=(g+1)/2;w=w/2
    x=np.repeat(g,len(g));y=np.tile(g,len(g))*(1-x);weights=np.repeat(w,len(w))*np.tile(w,len(w))*(1-x)
    basis=monomials(x,y)@inverse;dx=np.column_stack((0*x,0*x+1,0*x));dy=np.column_stack((0*x,0*x,0*x+1))
    if order==2:dx=np.column_stack((dx,2*x,y,0*x));dy=np.column_stack((dy,0*x,x,2*y))
    derivative=np.stack((dx@inverse,dy@inverse),axis=-1)
    cells=mesh.triangles.copy();points=mesh.points_rz_m
    if order==2:
        edges=sorted({tuple(sorted((int(t[a]),int(t[b])))) for t in cells for a,b in ((0,1),(1,2),(2,0))})
        indices={edge:len(points)+i for i,edge in enumerate(edges)}
        cells=np.array([[*t,*(indices[tuple(sorted((int(t[a]),int(t[b]))))] for a,b in ((0,1),(1,2),(2,0)))] for t in cells])
        points=np.vstack((points,np.array([(mesh.points_rz_m[a]+mesh.points_rz_m[b])/2 for a,b in edges])))
    k=np.zeros((len(points),len(points)));f=np.zeros(len(points))
    for index,triangle in enumerate(mesh.triangles):
        vertices=mesh.points_rz_m[triangle];jac=(vertices[1:]-vertices[0]).T
        gradient=derivative@np.linalg.inv(jac);radius=vertices[0,0]+x*jac[0,0]+y*jac[0,1]
        measure=TAU*radius*weights*np.linalg.det(jac)
        br=-radius[:,None]*gradient[:,:,1];bz=2*basis+radius[:,None]*gradient[:,:,0]
        stiffness=sum(component.T@((measure*((1./MU0)/mu[index]))[:,None]*component) for component in (br,bz))
        k[np.ix_(cells[index],cells[index])]+=stiffness;f[cells[index]]+=basis.T@(measure*radius*current[index])
    return points,cells,k,f


def rectangle_moment(mesh,a,b,region,pattern,scale,shift):
    result=0.
    for polygon,sign in [(mesh.outer_rz_m,1),*((h,-1) for h in mesh.holes_rz_m)]:
        r0,z0=polygon.min(axis=0);r1,z1=polygon.max(axis=0)
        if pattern==1:
            if region==0:z1=min(z1,scale/16+shift)
            else:z0=max(z0,scale/16+shift)
        if z1>z0:result+=sign*TAU*(r1**(a+2)-r0**(a+2))/(a+2)*(z1**(b+1)-z0**(b+1))/(b+1)
    return result


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples')
            for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();start=time.monotonic();records=[];pairs={};preserved={}
    maximum_matrix=maximum_load=maximum_scale=maximum_polynomial=maximum_work=maximum_mu=maximum_uniform=0.;polynomial_checks=0;minimum_eigen_ratio=1.
    for holes in (0,1,2):
        for order in (1,2):
            for pattern in (0,1,2):
                for scale in (.5,2.):
                    for shift in (0.,-.25):
                        name=f'axis-holes{holes}-p{order}-pattern{pattern}-scale{scale}-shift{shift}'
                        p,current,mu,cell_current=make_partition(holes,pattern,scale,shift)
                        space,k,f,report=axis_magnetostatic_forms(p,current,order);points,cells,rk,rf=dense_reference(p.mesh,mu,cell_current,order)
                        np.testing.assert_array_equal(points,space.dof_points);np.testing.assert_array_equal(cells,space.cell_dofs)
                        kd=float(np.linalg.norm(k.toarray()-rk)/np.linalg.norm(rk));fd=float(np.linalg.norm(f-rf)/np.linalg.norm(rf))
                        assert max(kd,fd)<1e-11;maximum_matrix=max(maximum_matrix,kd);maximum_load=max(maximum_load,fd)
                        eigen=eigvalsh(rk);ratio=float(eigen[0]/eigen[-1]);assert ratio>1e-9;minimum_eigen_ratio=min(minimum_eigen_ratio,ratio)
                        assert len(space.axis_dofs)>0 and report['constant_a_is_gauge'] is False
                        uniform_expected=4*sum(((1./MU0)/material.mu_r)*volume for material,volume in zip(p.materials,p.region_volume_m3))
                        ones=np.ones(len(points));uniform=float(abs(ones@k@ones/uniform_expected-1));assert uniform<1e-11;maximum_uniform=max(maximum_uniform,uniform)
                        key=holes,order,pattern,shift
                        if scale==.5:pairs[key]=k,f
                        else:
                            old_k,old_f=pairs[key];diff=[np.linalg.norm((k/64-old_k).data)/np.linalg.norm(old_k.data),np.linalg.norm(f/256-old_f)/np.linalg.norm(old_f)]
                            assert max(diff)<1e-11;maximum_scale=max(maximum_scale,*map(float,diff))
                        motion=holes,order,pattern,scale,'motion'
                        if shift==0.:pairs[motion]=k,f
                        else:
                            old_k,old_f=pairs[motion];diff=[np.linalg.norm((k-old_k).data)/np.linalg.norm(old_k.data),np.linalg.norm(f-old_f)/np.linalg.norm(old_f)]
                            assert max(diff)<1e-11;maximum_scale=max(maximum_scale,*map(float,diff))
                        permuted=AxisMagneticPartition(p.mesh,p.materials[::-1],p.regions[::-1]);_,pk,pf,_=axis_magnetostatic_forms(permuted,current,order)
                        np.testing.assert_array_equal(k.toarray(),pk.toarray());np.testing.assert_array_equal(f,pf)
                        _,_,negative,_=axis_magnetostatic_forms(p,{name:-value for name,value in current.items()},order);np.testing.assert_array_equal(negative,-f)
                        raw=p.to_dict()
                        for material in raw['materials']:material['mu_r']*=7
                        _,scaled,unchanged,_=axis_magnetostatic_forms(AxisMagneticPartition.from_dict(raw),current,order)
                        md=float(np.linalg.norm((7*scaled-k).data)/np.linalg.norm(k.data));assert md<1e-11;maximum_mu=max(maximum_mu,md);np.testing.assert_array_equal(unchanged,f)
                        if pattern in (0,1):
                            def moment(a,b,index):return rectangle_moment(p.mesh,a,b,index,pattern,scale,shift)
                            materials={m.id:m.mu_r for m in p.materials}
                            work_sum=sum(current[region.id]*moment(1,0,i) for i,region in enumerate(p.regions))
                            source_current=sum(current[region.id]*moment(-1,0,i)/TAU for i,region in enumerate(p.regions))
                            wd=max(abs(f.sum()/work_sum-1),abs(report['total_source_current_a']/source_current-1));assert wd<1e-11;maximum_work=max(maximum_work,float(wd))
                            r,z=points.T;polynomials=[(0,0),(1,0),(0,1)]+([(2,0),(1,1),(0,2)] if order==2 else [])
                            for a,b in polynomials:
                                c=r**a*z**b
                                expected=sum(((1./MU0)/materials[region.material])*((a+2)**2*moment(2*a,2*b,i)+(b*b*moment(2*a+2,2*b-2,i) if b else 0.)) for i,region in enumerate(p.regions))
                                work=sum(current[region.id]*moment(a+1,b,i) for i,region in enumerate(p.regions))
                                wd=float(abs(c@f/work-1));ed=float(abs(c@k@c/expected-1));assert max(wd,ed)<1e-11;maximum_polynomial=max(maximum_polynomial,wd,ed);polynomial_checks+=1
                        path=out/(name+'.json');path.write_text(json.dumps(dict(partition=p.to_dict(),current_density_phi_a_per_m2=current),indent=2)+'\n')
                        assert AxisMagneticPartition.from_dict(json.loads(path.read_text())['partition']).to_dict()==p.to_dict()
                        preserved[path.name]=hashlib.sha256(path.read_bytes()).hexdigest();records.append(dict(name=name,stiffness_relative_difference=kd,load_relative_difference=fd,positive_spectrum_ratio=ratio,uniform_B_energy_relative_difference=uniform,quadrature=report))
    assert len(records)==72 and polynomial_checks==216 and fingerprints()==before
    for path,digest in preserved.items():assert hashlib.sha256((out/path).read_bytes()).hexdigest()==digest
    result=dict(status='PASS',cases=len(records),partition_permutations=len(records),partition_roundtrips=len(preserved),positive_spectra=len(records),
        mu_scaling_cases=len(records),current_sign_cases=len(records),uniform_B_energy_cases=len(records),
        independent_polynomial_checks=polynomial_checks,maximum_stiffness_relative_difference=maximum_matrix,maximum_load_relative_difference=maximum_load,
        maximum_scale_translation_relative_difference=maximum_scale,maximum_polynomial_relative_difference=maximum_polynomial,
        maximum_current_work_relative_difference=maximum_work,maximum_mu_scaling_relative_difference=maximum_mu,
        maximum_uniform_B_energy_relative_difference=maximum_uniform,minimum_positive_eigenvalue_ratio=minimum_eigen_ratio,
        interpretation='regular axis-connected a=Aphi/r[T], magnetic K[m^4/H], current work load[A m^2], full 3D energy[J]. Constant a is uniform axial B, not gauge. No boundary solve, off-axis gauge or field-accuracy acceptance.',
        records=records,source_sha256=before,seconds=time.monotonic()-start)
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k not in ('records','source_sha256')})


if __name__=='__main__':main()
