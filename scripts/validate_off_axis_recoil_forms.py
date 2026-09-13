# SPDX-License-Identifier: Apache-2.0
"""Independent positive-radius recoil tensor forms, gauge and remanent work."""
import argparse,hashlib,json,math,sys,time
from pathlib import Path
import numpy as np
from scipy.linalg import eigvalsh
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.curved_meridional_reference import fixture
from superfish_ng.recoil_materials import LinearRecoilMaterial,OrientedMagneticRegion
from superfish_ng.off_axis_recoil_materials import OffAxisRecoilPartition
from superfish_ng.meridional_mesh import MeridionalMesh
from superfish_ng.off_axis_recoil_fem import off_axis_recoil_forms
from superfish_ng.constants import MU0,TAU


def make_partition(holes,pattern,scale,shift):
    mesh=fixture(False,holes,scale=scale,shear=0.)[0]['base_mesh'];vertices=mesh.points_rz_m[mesh.triangles]
    labels=(np.zeros(len(vertices),dtype=int) if pattern==0 else
            (vertices[:,:,1].mean(axis=1)>=scale/16).astype(int) if pattern==1 else
            np.arange(len(vertices))%3)
    t=np.array([0.,shift]);mesh=MeridionalMesh(mesh.outer_rz_m+t,[h+t for h in mesh.holes_rz_m],mesh.points_rz_m+t,mesh.triangles)
    principal=[(2.,5.),(3.,11.),(7.,4.)];remanent=[(0.,.1),(.04,-.1),(-.03,.08)]
    angles=[0.,.3,-.6];count=int(labels.max())+1
    materials=[LinearRecoilMaterial(f'm{i}',principal[i],remanent[i]) for i in range(count)]
    regions=[OrientedMagneticRegion(f'r{i}',m.id,np.flatnonzero(labels==i).tolist(),angles[i]) for i,m in enumerate(materials)]
    # Independent component formula, without product tensor arrays or rotation helper.
    nu=[];br=[]
    for (first,second),(radial,axial),angle in zip(principal[:count],remanent[:count],angles[:count]):
        c=math.cos(angle);s=math.sin(angle);u=1/(MU0*first);v=1/(MU0*second)
        nu.append([[u*c*c+v*s*s,(u-v)*s*c],[(u-v)*s*c,u*s*s+v*c*c]])
        br.append([c*radial-s*axial,s*radial+c*axial])
    nu=np.array(nu);br=np.array(br);h=np.einsum('tij,tj->ti',nu,br);current=np.array([2.,-3.,7.])[:count]
    return OffAxisRecoilPartition(mesh,materials,regions),{r.id:float(v) for r,v in zip(regions,current)},nu,h,br,current,labels


def dense_reference(mesh,nu,source_h,current,order):
    # Independent nodal interpolation, Duffy/Gauss integration and DOF map.
    nodes=np.array([[0.,0.],[1.,0.],[0.,1.],[.5,0.],[.5,.5],[0.,.5]])[:3 if order==1 else 6]
    def monomials(x,y):
        value=np.column_stack((np.ones(len(x)),x,y))
        return value if order==1 else np.column_stack((value,x*x,x*y,y*y))
    inverse=np.linalg.inv(monomials(*nodes.T));g,w=np.polynomial.legendre.leggauss(24);g=(g+1)/2;w=w/2
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
    k=np.zeros((len(points),len(points)));f=np.zeros(len(points));m=np.zeros(len(points))
    for index,triangle in enumerate(mesh.triangles):
        vertices=mesh.points_rz_m[triangle];jac=(vertices[1:]-vertices[0]).T
        gradient=derivative@np.linalg.inv(jac);radius=vertices[0,0]+x*jac[0,0]+y*jac[0,1]
        measure=TAU*radius*weights*np.linalg.det(jac)
        br=-gradient[:,:,1]/radius[:,None];bz=gradient[:,:,0]/radius[:,None]
        stiffness=(br.T@((measure*nu[index,0,0])[:,None]*br)+bz.T@((measure*nu[index,1,1])[:,None]*bz)
            +br.T@((measure*nu[index,0,1])[:,None]*bz)+bz.T@((measure*nu[index,1,0])[:,None]*br))
        m[cells[index]]+=br.T@(measure*source_h[index,0])+bz.T@(measure*source_h[index,1])
        k[np.ix_(cells[index],cells[index])]+=stiffness;f[cells[index]]+=basis.T@(measure*current[index]/radius)
    return points,cells,k,f,m


def rectangle_moment(mesh,a,b,region,pattern,scale,shift):
    result=0.
    for polygon,sign in [(mesh.outer_rz_m,1),*((h,-1) for h in mesh.holes_rz_m)]:
        r0,z0=polygon.min(axis=0);r1,z1=polygon.max(axis=0)
        if pattern==1:
            if region==0:z1=min(z1,scale/16+shift)
            else:z0=max(z0,scale/16+shift)
        if z1>z0:
            radial=np.log(r1/r0) if a==0 else (r1**a-r0**a)/a
            result+=sign*TAU*radial*(z1**(b+1)-z0**(b+1))/(b+1)
    return result


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples')
            for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();start=time.monotonic();records=[];pairs={};preserved={}
    maxima=dict(matrix=0.,current_load=0.,remanent_load=0.,transform=0.,polynomial=0.,mu_scaling=0.,zero_H=0.,constant=0.)
    polynomial_checks=zero_h=0;minimum_eigen_ratio=1.;maximum_kernel=0.
    def error(a,b):
        scale=max(np.linalg.norm(a),np.linalg.norm(b));return float(np.linalg.norm(a-b)/scale) if scale else 0.
    for holes in (0,1,2):
        for order in (1,2):
            for pattern in (0,1,2):
                for scale in (.5,2.):
                    for shift in (0.,-.25):
                        name=f'off-axis-recoil-holes{holes}-p{order}-pattern{pattern}-scale{scale}-shift{shift}'
                        p,current,nu,h,br,densities,labels=make_partition(holes,pattern,scale,shift)
                        space,k,f,m,report=off_axis_recoil_forms(p,current,order)
                        points,cells,rk,rf,rm=dense_reference(p.mesh,nu[labels],h[labels],densities[labels],order)
                        np.testing.assert_array_equal(points,space.dof_points);np.testing.assert_array_equal(cells,space.cell_dofs)
                        kd,fd,md=error(k.toarray(),rk),error(f,rf),error(m,rm)
                        assert max(kd,fd,md)<1e-11
                        for key,value in zip(('matrix','current_load','remanent_load'),(kd,fd,md)):maxima[key]=max(maxima[key],value)
                        eigen=eigvalsh(rk);ratio=float(eigen[1]/eigen[-1]);assert ratio>1e-9 and abs(eigen[0]/eigen[-1])<1e-12;minimum_eigen_ratio=min(minimum_eigen_ratio,ratio)
                        kernel=float(np.linalg.norm(k@np.ones(len(points)))/np.linalg.norm(k.data));assert kernel<1e-12;maximum_kernel=max(maximum_kernel,kernel)
                        assert not hasattr(space,'axis_dofs') and report['constant_psi_kernel_retained'] is True
                        constant=report['remanent_reference_constant_j']
                        key=holes,order,pattern,shift
                        if scale==.5:pairs[key]=k.toarray(),f,m,constant
                        else:
                            old_k,old_f,old_m,old_c=pairs[key];differences=[error(k.toarray()*4,old_k),error(f/16,old_f),error(m/4,old_m),abs(constant/(64*old_c)-1)]
                            assert max(differences)<1e-11;maxima['transform']=max(maxima['transform'],*differences)
                        motion=holes,order,pattern,scale,'motion'
                        if shift==0.:pairs[motion]=k.toarray(),f,m,constant
                        else:
                            old_k,old_f,old_m,old_c=pairs[motion];differences=[error(k.toarray(),old_k),error(f,old_f),error(m,old_m),abs(constant/old_c-1)]
                            assert max(differences)<1e-11;maxima['transform']=max(maxima['transform'],*differences)
                        permuted=OffAxisRecoilPartition(p.mesh,p.materials[::-1],p.regions[::-1]);_,pk,pf,pm,_=off_axis_recoil_forms(permuted,current,order)
                        for a,b in ((k.toarray(),pk.toarray()),(f,pf),(m,pm)):np.testing.assert_array_equal(a,b)
                        raw=p.to_dict()
                        for material in raw['materials']:material['remanent_b_local_t']=[-v for v in material['remanent_b_local_t']]
                        _,nk,nf,nm,_=off_axis_recoil_forms(OffAxisRecoilPartition.from_dict(raw),{name:-value for name,value in current.items()},order)
                        for a,b in ((k.toarray(),nk.toarray()),(-f,nf),(-m,nm)):np.testing.assert_array_equal(a,b)
                        raw=p.to_dict()
                        for material in raw['materials']:material['mu_r_principal']=[7*v for v in material['mu_r_principal']]
                        _,sk,sf,sm,sq=off_axis_recoil_forms(OffAxisRecoilPartition.from_dict(raw),current,order)
                        differences=[error(sk.toarray()*7,k.toarray()),error(sm*7,m),abs(sq['remanent_reference_constant_j']*7/constant-1)]
                        assert max(differences)<1e-11;maxima['mu_scaling']=max(maxima['mu_scaling'],*differences);np.testing.assert_array_equal(sf,f)
                        if pattern in (0,1):
                            def moment(a,b,index):return rectangle_moment(p.mesh,a,b,index,pattern,scale,shift)
                            expected_constant=.5*sum(float(br[i]@h[i])*moment(2,0,i) for i in range(len(nu)))
                            cd=abs(constant/expected_constant-1);assert cd<1e-11;maxima['constant']=max(maxima['constant'],cd)
                            radial,z=points.T;polynomials=[(0,0),(1,0),(0,1)]+([(2,0),(1,1),(0,2)] if order==2 else [])
                            for a,b in polynomials:
                                c=radial**a*z**b
                                energy=sum((nu[i,1,1]*a*a*moment(2*a-2,2*b,i) if a else 0.)+(nu[i,0,0]*b*b*moment(2*a,2*b-2,i) if b else 0.)-(2*nu[i,0,1]*a*b*moment(2*a-1,2*b-1,i) if a and b else 0.) for i in range(len(nu)))
                                work=sum(densities[i]*moment(a+1,b,i) for i in range(len(nu)))
                                rem_work=sum((a*h[i,1]*moment(a,b,i) if a else 0.)-(b*h[i,0]*moment(a+1,b-1,i) if b else 0.) for i in range(len(nu)))
                                differences=[abs(c@k@c/energy-1) if a or b else kernel,abs(c@f-work)/max(np.linalg.norm(c)*np.linalg.norm(f),abs(work)),abs(c@m-rem_work)/max(np.linalg.norm(c)*np.linalg.norm(m),abs(rem_work))]
                                assert max(differences)<1e-11;maxima['polynomial']=max(maxima['polynomial'],*differences);polynomial_checks+=1
                        if pattern==0 and order==2:
                            c=br[0,1]*points[:,0]**2/2;equilibrium=error(k@c,m)
                            u=float(c@k@c/2);work=float(c@m)
                            differences=[equilibrium,abs(u/constant-1),abs(work/constant-2),abs(u-work+constant)/constant]
                            assert max(differences)<1e-11;maxima['zero_H']=max(maxima['zero_H'],*differences);zero_h+=1
                        path=out/(name+'.json');path.write_text(json.dumps(dict(partition=p.to_dict(),current_density_phi_a_per_m2=current),indent=2)+'\n')
                        assert OffAxisRecoilPartition.from_dict(json.loads(path.read_text())['partition']).to_dict()==p.to_dict()
                        preserved[path.name]=hashlib.sha256(path.read_bytes()).hexdigest();records.append(dict(name=name,stiffness_relative_difference=kd,current_load_relative_difference=fd,remanent_load_relative_difference=md,positive_spectrum_ratio=ratio,quadrature=report))
    assert len(records)==72 and polynomial_checks==216 and zero_h==12 and fingerprints()==before
    for path,digest in preserved.items():assert hashlib.sha256((out/path).read_bytes()).hexdigest()==digest
    result=dict(status='PASS',cases=len(records),partition_permutations=len(records),partition_roundtrips=len(preserved),single_constant_kernel_spectra=len(records),
        mu_scaling_cases=len(records),source_sign_cases=len(records),uniform_zero_H_equilibria=zero_h,
        independent_polynomial_checks=polynomial_checks,maximum_relative_differences=maxima,minimum_nonconstant_eigenvalue_ratio=minimum_eigen_ratio,maximum_constant_kernel_relative_norm=maximum_kernel,
        interpretation='strictly r>0 psi=r*Aphi[Wb], tensor K[1/H], separate current/remanence loads[A], full 3D constitutive potentials[J]; constant psi kernel and P2 uniform B=Brem zero-H equilibrium; no excluded-axis absolute flux, boundary solve or discretization-error acceptance',
        records=records,source_sha256=before,seconds=time.monotonic()-start)
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k not in ('records','source_sha256')})


if __name__=='__main__':main()
