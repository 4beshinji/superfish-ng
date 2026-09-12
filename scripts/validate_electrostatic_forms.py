# SPDX-License-Identifier: Apache-2.0
"""Independent full-SI electrostatic forms, volume charge and polynomial work."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
from scipy.linalg import eigvalsh
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.curved_meridional_reference import fixture
from superfish_ng.dielectrics import LinearDielectric,DielectricRegion,AxisymmetricDielectricPartition
from superfish_ng.electrostatic_fem import axisymmetric_electrostatic_forms
from superfish_ng.constants import EPS0,TAU


def make_partition(axis,holes,pattern,scale):
    mesh=fixture(axis,holes,scale=scale,shear=0.)[0]['base_mesh'];count=len(mesh.triangles)
    labels=(np.zeros(count,dtype=int) if pattern==0 else
            (mesh.points_rz_m[mesh.triangles][:,:,1].mean(axis=1)>=scale/16).astype(int) if pattern==1 else np.arange(count)%3)
    eps=np.array([2.,5.,11.])[:int(labels.max())+1];rho=np.array([2.,-3.,7.])[:len(eps)]
    materials=[LinearDielectric(f'dielectric-{i}',e) for i,e in enumerate(eps)]
    regions=[DielectricRegion(f'region-{i}',materials[i].id,np.flatnonzero(labels==i).tolist()) for i in range(len(eps))]
    return AxisymmetricDielectricPartition(mesh,materials,regions),{r.id:float(v) for r,v in zip(regions,rho)},eps[labels],rho[labels]


def dense_reference(mesh,epsilon,rho,order):
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
        stiffness=sum(gradient[:,:,i].T@((measure*EPS0*epsilon[index])[:,None]*gradient[:,:,i]) for i in (0,1))
        k[np.ix_(cells[index],cells[index])]+=stiffness;f[cells[index]]+=basis.T@(measure*rho[index])
    return points,cells,k,f


def rectangle_moment(mesh,a,b,region,pattern,scale):
    result=0.
    for polygon,sign in [(mesh.outer_rz_m,1),*((h,-1) for h in mesh.holes_rz_m)]:
        r0,z0=polygon.min(axis=0);r1,z1=polygon.max(axis=0)
        if pattern==1:
            if region==0:z1=min(z1,scale/16)
            else:z0=max(z0,scale/16)
        if z1>z0:result+=sign*TAU*(r1**(a+2)-r0**(a+2))/(a+2)*(z1**(b+1)-z0**(b+1))/(b+1)
    return result


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples')
            for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();start=time.monotonic();records=[];pairs={};preserved={}
    maximum_matrix=maximum_load=maximum_scale=maximum_polynomial=maximum_charge=maximum_kernel=0.;polynomial_checks=0
    for axis in (False,True):
        for holes in (0,1,2):
            for order in (1,2):
                for pattern in (0,1,2):
                    for scale in (.5,2.):
                        name=f'axis-{int(axis)}-holes-{holes}-p-{order}-pattern-{pattern}-scale-{scale}'
                        p,rho,epsilon,cell_rho=make_partition(axis,holes,pattern,scale)
                        space,k,f,report=axisymmetric_electrostatic_forms(p,rho,order)
                        points,cells,rk,rf=dense_reference(p.mesh,epsilon,cell_rho,order)
                        np.testing.assert_array_equal(points,space.dof_points);np.testing.assert_array_equal(cells,space.cell_dofs)
                        kd=float(np.linalg.norm(k.toarray()-rk)/np.linalg.norm(rk));fd=float(np.linalg.norm(f-rf)/np.linalg.norm(rf))
                        assert max(kd,fd)<1e-12;maximum_matrix=max(maximum_matrix,kd);maximum_load=max(maximum_load,fd)
                        kernel=float(np.linalg.norm(k@np.ones(k.shape[0]))/np.linalg.norm(k.data));assert kernel<1e-12;maximum_kernel=max(maximum_kernel,kernel)
                        eigen=eigvalsh(rk);assert abs(eigen[0])/eigen[-1]<1e-12 and eigen[1]/eigen[-1]>1e-6
                        key=axis,holes,order,pattern
                        if key not in pairs:pairs[key]=k,f
                        else:
                            old_k,old_f=pairs[key];diff=[np.linalg.norm((k/4-old_k).data)/np.linalg.norm(old_k.data),np.linalg.norm(f/64-old_f)/np.linalg.norm(old_f)]
                            assert max(diff)<1e-12;maximum_scale=max(maximum_scale,*map(float,diff))
                        permuted=AxisymmetricDielectricPartition(p.mesh,p.materials[::-1],p.regions[::-1])
                        _,pk,pf,_=axisymmetric_electrostatic_forms(permuted,rho,order)
                        np.testing.assert_array_equal(k.toarray(),pk.toarray());np.testing.assert_array_equal(f,pf)
                        if pattern in (0,1):
                            def moment(a,b,index):return rectangle_moment(p.mesh,a,b,index,pattern,scale)
                            materials={m.id:m.epsilon_r for m in p.materials}
                            charge=sum(rho[region.id]*moment(0,0,i) for i,region in enumerate(p.regions))
                            charge_difference=abs(f.sum()/charge-1);assert charge_difference<1e-12;maximum_charge=max(maximum_charge,float(charge_difference))
                            r,z=points.T;polynomials=[(np.ones(len(points)),0,0,[]),(r,1,0,[(1,0,0)]),(z,0,1,[(1,0,0)])]
                            if order==2:polynomials += [(r*r,2,0,[(4,2,0)]),(r*z,1,1,[(1,2,0),(1,0,2)]),(z*z,0,2,[(4,0,2)])]
                            for c,a,b,gradient_square in polynomials:
                                expected=EPS0*sum(materials[region.material]*sum(v*moment(x,y,i) for v,x,y in gradient_square) for i,region in enumerate(p.regions))
                                work=sum(rho[region.id]*moment(a,b,i) for i,region in enumerate(p.regions))
                                wd=float(abs(c@f/work-1));ed=float(abs(c@k@c/expected-1)) if expected else kernel
                                assert max(wd,ed)<1e-11;maximum_polynomial=max(maximum_polynomial,wd,ed);polynomial_checks+=1
                        path=out/(name+'.json');path.write_text(json.dumps(dict(partition=p.to_dict(),charge_density_c_per_m3=rho),indent=2)+'\n')
                        assert AxisymmetricDielectricPartition.from_dict(json.loads(path.read_text())['partition']).to_dict()==p.to_dict()
                        preserved[path.name]=hashlib.sha256(path.read_bytes()).hexdigest();records.append(dict(name=name,stiffness_relative_difference=kd,load_relative_difference=fd,kernel_relative_residual=kernel,quadrature=report))
            print('DONE',axis,holes,flush=True)
    assert fingerprints()==before
    for path,digest in preserved.items():assert hashlib.sha256((out/path).read_bytes()).hexdigest()==digest
    result=dict(status='PASS',cases=len(records),partition_permutations=len(records),partition_roundtrips=len(preserved),constant_kernel_spectra=len(records),
        independent_polynomial_checks=polynomial_checks,maximum_stiffness_relative_difference=maximum_matrix,maximum_load_relative_difference=maximum_load,
        maximum_spatial_scale_relative_difference=maximum_scale,maximum_polynomial_relative_difference=maximum_polynomial,
        maximum_total_charge_relative_difference=maximum_charge,maximum_kernel_relative_residual=maximum_kernel,
        interpretation='full-SI axisymmetric electrostatic K and volume load only; no boundary/gauge, solution, capacitance or field accuracy acceptance',
        records=records,source_sha256=before,seconds=time.monotonic()-start)
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k not in ('records','source_sha256')})


if __name__=='__main__':main()
