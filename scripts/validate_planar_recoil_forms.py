# SPDX-License-Identifier: Apache-2.0
"""Independent planar recoil tensor, remanent weak load and constitutive potential."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
from scipy.linalg import eigvalsh
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from superfish_ng.planar_mesh import PlanarMesh
from superfish_ng.recoil_materials import LinearRecoilMaterial,OrientedMagneticRegion,PlanarRecoilPartition
from superfish_ng.planar_recoil_fem import planar_recoil_forms
from superfish_ng.constants import MU0


def make_geometry(concave,pattern,scale,motion):
    polygon=(np.array([[-1.,-1.],[1.,-1.],[1.,0.],[0.,0.],[0.,1.],[-1.,1.]]) if concave else np.array([[-1.,-1.],[1.,-1.],[1.,1.],[-1.,1.]]))
    coordinates=[(i,j) for j in range(3) for i in range(3) if not (concave and i==j==2)]
    index={v:k for k,v in enumerate(coordinates)};points=np.asarray(coordinates,dtype=float)-1;cells=[]
    for j in range(2):
        for i in range(2):
            if concave and i==j==1:continue
            a,b,c,d=[index[v] for v in ((i,j),(i+1,j),(i+1,j+1),(i,j+1))];cells.extend(((a,b,c),(a,c,d)))
    cells=np.asarray(cells);labels=(np.zeros(len(cells),dtype=int) if pattern==0 else (points[cells][:,:,1].mean(axis=1)>=0).astype(int) if pattern==1 else np.arange(len(cells))%3)
    rotation=(np.eye(2),np.array([[0.,-1.],[1.,0.]]),np.array([[.6,-.8],[.8,.6]]))[motion]
    shift=(np.array([0.,0.]),np.array([-.375,.25]),np.array([.5,-.625]))[motion]
    mesh=PlanarMesh.create(polygon@rotation.T*scale/32+shift,points@rotation.T*scale/32+shift,cells)
    return mesh,labels,rotation,shift


def coefficients(index,angle):
    principal=((2.,5.),(3.,11.),(7.,13.))[index];remanent=((.2,-.1),(-.3,.05),(.1,.4))[index]
    c,s=np.cos(angle),np.sin(angle);u,v=1/(MU0*np.array(principal))
    nu=np.array([[c*c*u+s*s*v,c*s*(u-v)],[c*s*(u-v),s*s*u+c*c*v]])
    br=np.array([c*remanent[0]-s*remanent[1],s*remanent[0]+c*remanent[1]])
    return nu,br


def make_partition(concave,pattern,scale,motion):
    mesh,labels,rotation,shift=make_geometry(concave,pattern,scale,motion);count=int(labels.max())+1
    angle=np.arctan2(rotation[1,0],rotation[0,0]);principals=((2.,5.),(3.,11.),(7.,13.));remanents=((.2,-.1),(-.3,.05),(.1,.4))
    materials=[LinearRecoilMaterial(f'm{i}',principals[i],remanents[i]) for i in range(count)]
    regions=[OrientedMagneticRegion(f'region-{i}',f'm{i}',np.flatnonzero(labels==i).tolist(),(.2,-.4,.7)[i]+angle) for i in range(count)]
    p=PlanarRecoilPartition(mesh,materials,regions);current=np.array([2.,-3.,7.])[:count]
    expected=[coefficients(i,regions[i].orientation_rad) for i in range(count)]
    return p,{region.id:float(current[i]) for i,region in enumerate(regions)},np.array([v[0] for v in expected])[labels],np.array([v[1] for v in expected])[labels],current[labels],rotation,shift


def dense_reference(mesh,nu,remanent,current_density,order):
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
    cells=mesh.triangles.copy();points=mesh.points_xy_m
    if order==2:
        edges=sorted({tuple(sorted((int(t[a]),int(t[b])))) for t in cells for a,b in ((0,1),(1,2),(2,0))})
        indices={edge:len(points)+i for i,edge in enumerate(edges)}
        cells=np.array([[*t,*(indices[tuple(sorted((int(t[a]),int(t[b]))))] for a,b in ((0,1),(1,2),(2,0)))] for t in cells])
        points=np.vstack((points,np.array([(mesh.points_xy_m[a]+mesh.points_xy_m[b])/2 for a,b in edges])))
    k=np.zeros((len(points),len(points)));f=np.zeros(len(points));m=np.zeros(len(points));constant=0.
    for index,triangle in enumerate(mesh.triangles):
        vertices=mesh.points_xy_m[triangle];jac=(vertices[1:]-vertices[0]).T
        gradient=derivative@np.linalg.inv(jac)
        measure=weights*np.linalg.det(jac)
        curl=np.stack((gradient[:,:,1],-gradient[:,:,0]),axis=-1)
        stiffness=np.zeros((curl.shape[1],curl.shape[1]))
        for i in range(2):
            for j in range(2):stiffness+=curl[:,:,i].T@((measure*nu[index,i,j])[:,None]*curl[:,:,j])
        k[np.ix_(cells[index],cells[index])]+=stiffness;f[cells[index]]+=basis.T@(measure*current_density[index])
        h=nu[index]@remanent[index];m[cells[index]]+=sum(curl[:,:,i].T@(measure*h[i]) for i in range(2))
        constant+=.5*float(remanent[index]@h)*float(measure.sum())
    return points,cells,k,f,m,constant



def moment(concave,a,b,region,pattern):
    rectangles=[(-1.,1.,-1.,1.,1)]
    if concave:rectangles.append((0.,1.,0.,1.,-1))
    result=0.
    for x0,x1,y0,y1,sign in rectangles:
        if pattern==1:
            if region==0:y1=min(y1,0.)
            else:y0=max(y0,0.)
        if y1>y0:result+=sign*(x1**(a+1)-x0**(a+1))/(a+1)*(y1**(b+1)-y0**(b+1))/(b+1)/32**(a+b+2)
    return result


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples')
            for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();start=time.monotonic();records=[];pairs={};preserved={}
    maximum_matrix=maximum_current=maximum_remanent=maximum_transform=maximum_polynomial=maximum_equilibrium=maximum_mu=maximum_constant=0.;polynomial_checks=equilibrium_checks=0
    for concave in (False,True):
        for order in (1,2):
            for pattern in (0,1,2):
                for scale in (.5,2.):
                    for motion in (0,1,2):
                        name=f'concave{int(concave)}-p{order}-pattern{pattern}-s{scale}-motion{motion}'
                        p,current,nu,br,cell_current,rotation,shift=make_partition(concave,pattern,scale,motion)
                        space,k,j,m,report=planar_recoil_forms(p,current,order);points,cells,rk,rj,rm,constant=dense_reference(p.mesh,nu,br,cell_current,order)
                        np.testing.assert_array_equal(points,space.dof_points_xy_m);np.testing.assert_array_equal(cells,space.cell_dofs)
                        kd=float(np.linalg.norm(k.toarray()-rk)/np.linalg.norm(rk));jd=float(np.linalg.norm(j-rj)/np.linalg.norm(rj));md=float(np.linalg.norm(m-rm)/np.linalg.norm(rm));cd=abs(report['remanent_reference_constant_j_per_m']/constant-1)
                        assert max(kd,jd,md,cd)<1e-11,(name,kd,jd,md,cd);maximum_matrix=max(maximum_matrix,kd);maximum_current=max(maximum_current,jd);maximum_remanent=max(maximum_remanent,md);maximum_constant=max(maximum_constant,cd)
                        matrix_differences=kd,jd,md
                        kernel=float(np.linalg.norm(k@np.ones(len(points)))/np.linalg.norm(k.data));eigen=eigvalsh(rk)
                        assert kernel<1e-12 and abs(eigen[0]/eigen[-1])<1e-12 and eigen[1]/eigen[-1]>1e-6
                        assert abs(m.sum())/np.linalg.norm(m)<1e-12
                        key=concave,order,pattern;normalized=(k,j/scale**2,m/scale)
                        if key not in pairs:pairs[key]=normalized
                        else:
                            ok,oj,om=pairs[key];difference=max(np.linalg.norm((k-ok).data)/np.linalg.norm(ok.data),np.linalg.norm(j/scale**2-oj)/np.linalg.norm(oj),np.linalg.norm(m/scale-om)/np.linalg.norm(om))
                            assert difference<1e-11,(name,difference);maximum_transform=max(maximum_transform,float(difference))
                        raw=p.to_dict()
                        for material in raw['materials']:material['mu_r_principal']=[7*v for v in material['mu_r_principal']]
                        _,sk,sj,sm,_=planar_recoil_forms(PlanarRecoilPartition.from_dict(raw),current,order)
                        mu_error=max(np.linalg.norm((7*sk-k).data)/np.linalg.norm(k.data),np.linalg.norm(7*sm-m)/np.linalg.norm(m));assert mu_error<1e-11;maximum_mu=max(maximum_mu,float(mu_error));np.testing.assert_array_equal(sj,j)
                        raw=p.to_dict()
                        for material in raw['materials']:material['remanent_b_local_t']=[-v for v in material['remanent_b_local_t']]
                        _,nk,nj,nm,_=planar_recoil_forms(PlanarRecoilPartition.from_dict(raw),{key:-v for key,v in current.items()},order)
                        np.testing.assert_array_equal(nk.toarray(),k.toarray());np.testing.assert_array_equal(nj,-j);np.testing.assert_array_equal(nm,-m)
                        permuted=PlanarRecoilPartition(p.mesh,p.materials[::-1],p.regions[::-1]);_,pk,pj,pm,_=planar_recoil_forms(permuted,current,order)
                        np.testing.assert_array_equal(pk.toarray(),k.toarray());np.testing.assert_array_equal(pj,j);np.testing.assert_array_equal(pm,m)
                        if pattern==0:
                            coefficient=br[0,0]*points[:,1]-br[0,1]*points[:,0];equilibrium=float(np.linalg.norm(k@coefficient-m)/np.linalg.norm(m));assert equilibrium<1e-11
                            maximum_equilibrium=max(maximum_equilibrium,equilibrium);equilibrium_checks+=1
                        if pattern in (0,1):
                            x,y=((points-shift)@rotation/scale).T
                            polynomials=[(0,0),(1,0),(0,1)]+([(2,0),(1,1),(0,2)] if order==2 else [])
                            for a,b in polynomials:
                                coefficient=x**a*y**b;energy=current_work=remanent_work=0.
                                for i,region in enumerate(p.regions):
                                    local_nu,local_br=coefficients(i,(.2,-.4,.7)[i]);h=local_nu@local_br
                                    def integral(u,v):return moment(concave,u,v,i,pattern)
                                    energy+=(local_nu[0,0]*b*b*integral(2*a,2*b-2) if b else 0.)+(local_nu[1,1]*a*a*integral(2*a-2,2*b) if a else 0.)-(2*local_nu[0,1]*a*b*integral(2*a-1,2*b-1) if a and b else 0.)
                                    current_work+=current[region.id]*scale**2*integral(a,b)
                                    remanent_work+=scale*((b*h[0]*integral(a,b-1) if b else 0.)-(a*h[1]*integral(a-1,b) if a else 0.))
                                ed=abs(coefficient@k@coefficient/energy-1) if a or b else kernel
                                # Source-work errors use a Cauchy norm scale, including exact zero odd moments.
                                jd=abs(coefficient@j-current_work)/(np.linalg.norm(coefficient)*np.linalg.norm(j));md=abs(coefficient@m-remanent_work)/(np.linalg.norm(coefficient)*np.linalg.norm(m))
                                assert max(ed,jd,md)<1e-11,(name,a,b,ed,jd,md);maximum_polynomial=max(maximum_polynomial,float(ed),float(jd),float(md));polynomial_checks+=1
                        path=out/(name+'.json');path.write_text(json.dumps(dict(partition=p.to_dict(),current_density_z_a_per_m2=current),indent=2)+'\n')
                        assert PlanarRecoilPartition.from_dict(json.loads(path.read_text())['partition']).to_dict()==p.to_dict();preserved[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
                        records.append(dict(name=name,stiffness_relative_difference=kd,current_load_relative_difference=matrix_differences[1],remanent_load_relative_difference=matrix_differences[2],constant_reference_relative_difference=cd,quadrature=report))
    assert len(records)==72 and polynomial_checks==216 and equilibrium_checks==24 and fingerprints()==before
    for name,digest in preserved.items():assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest
    result=dict(status='PASS',cases=len(records),independent_polynomial_checks=polynomial_checks,uniform_zero_H_equilibria=equilibrium_checks,
        maximum_matrix_relative_difference=maximum_matrix,maximum_current_load_relative_difference=maximum_current,maximum_remanent_load_relative_difference=maximum_remanent,
        maximum_transform_relative_difference=maximum_transform,maximum_polynomial_scaled_difference=maximum_polynomial,maximum_uniform_equilibrium_relative_difference=maximum_equilibrium,
        maximum_mu_scaling_relative_difference=maximum_mu,maximum_constitutive_reference_relative_difference=maximum_constant,
        records=records,source_sha256=before,seconds=time.monotonic()-start,
        interpretation='Synthetic linear recoil material tensors and remanence with explicit orientation. Current and remanent loads separate, constant Az kernel. Constitutive potentials have stated reference states; no absolute magnet internal energy, boundary solve or field-accuracy acceptance.')
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k not in ('records','source_sha256')})


if __name__=='__main__':main()
