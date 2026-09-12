# SPDX-License-Identifier: Apache-2.0
"""Independent Cartesian magnetic reluctivity K/current, gauge and energy forms."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
from scipy.linalg import eigvalsh
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from superfish_ng.planar_mesh import PlanarMesh
from superfish_ng.magnetic_materials import PlanarMagneticPartition,LinearMagneticMaterial,MagneticRegion
from superfish_ng.planar_magnetostatic_fem import planar_magnetostatic_forms
from superfish_ng.constants import MU0


def make_partition(concave,pattern,scale,motion):
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
    permeability=np.array([2.,5.,11.])[:int(labels.max())+1];current_density=np.array([2.,-3.,7.])[:len(permeability)]
    materials=[LinearMagneticMaterial(f'magnetic-{i}',e) for i,e in enumerate(permeability)]
    regions=[MagneticRegion(f'region-{i}',materials[i].id,np.flatnonzero(labels==i).tolist()) for i in range(len(materials))]
    return PlanarMagneticPartition(mesh,materials,regions),{r.id:float(v) for r,v in zip(regions,current_density)},permeability[labels],current_density[labels],rotation,shift


def dense_reference(mesh,permeability,current_density,order):
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
    k=np.zeros((len(points),len(points)));f=np.zeros(len(points))
    for index,triangle in enumerate(mesh.triangles):
        vertices=mesh.points_xy_m[triangle];jac=(vertices[1:]-vertices[0]).T
        gradient=derivative@np.linalg.inv(jac)
        measure=weights*np.linalg.det(jac)
        stiffness=sum(gradient[:,:,i].T@((measure/(MU0*permeability[index]))[:,None]*gradient[:,:,i]) for i in (0,1))
        k[np.ix_(cells[index],cells[index])]+=stiffness;f[cells[index]]+=basis.T@(measure*current_density[index])
    return points,cells,k,f



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
    maximum_k=maximum_f=maximum_transform=maximum_polynomial=maximum_current=maximum_mu=maximum_energy=0.;polynomials_checked=0
    for concave in (False,True):
        for order in (1,2):
            for pattern in (0,1,2):
                for scale in (.5,2.):
                    for motion in (0,1,2):
                        name=f'concave-{int(concave)}-p{order}-pattern{pattern}-s{scale}-motion{motion}'
                        p,current_density,permeability,cell_current_density,rotation,shift=make_partition(concave,pattern,scale,motion)
                        space,k,f,diagnostic=planar_magnetostatic_forms(p,current_density,order)
                        points,cells,rk,rf=dense_reference(p.mesh,permeability,cell_current_density,order)
                        np.testing.assert_array_equal(points,space.dof_points_xy_m);np.testing.assert_array_equal(cells,space.cell_dofs)
                        kd=float(np.linalg.norm(k.toarray()-rk)/np.linalg.norm(rk));fd=float(np.linalg.norm(f-rf)/np.linalg.norm(rf));assert max(kd,fd)<1e-12
                        maximum_k=max(maximum_k,kd);maximum_f=max(maximum_f,fd)
                        kernel=float(np.linalg.norm(k@np.ones(k.shape[0]))/np.linalg.norm(k.data));eigen=eigvalsh(rk)
                        assert kernel<1e-12 and abs(eigen[0])/eigen[-1]<1e-12 and eigen[1]/eigen[-1]>1e-6
                        key=concave,order,pattern
                        if key not in pairs:pairs[key]=k,f/scale**2
                        else:
                            old_k,old_f=pairs[key];difference=max(float(np.linalg.norm((k-old_k).data)/np.linalg.norm(old_k.data)),float(np.linalg.norm(f/scale**2-old_f)/np.linalg.norm(old_f)))
                            assert difference<1e-12;maximum_transform=max(maximum_transform,difference)
                        permuted=PlanarMagneticPartition(p.mesh,p.materials[::-1],p.regions[::-1]);_,pk,pf,_=planar_magnetostatic_forms(permuted,current_density,order)
                        np.testing.assert_array_equal(k.toarray(),pk.toarray());np.testing.assert_array_equal(f,pf)
                        raw=p.to_dict()
                        for material in raw['materials']:material['mu_r']*=7.
                        _,scaled_k,scaled_f,_=planar_magnetostatic_forms(PlanarMagneticPartition.from_dict(raw),current_density,order)
                        mu_error=float(np.linalg.norm((7*scaled_k-k).data)/np.linalg.norm(k.data));assert mu_error<1e-12;maximum_mu=max(maximum_mu,mu_error)
                        np.testing.assert_array_equal(scaled_f,f)
                        _,_,opposite,_=planar_magnetostatic_forms(p,{name:-value for name,value in current_density.items()},order);np.testing.assert_array_equal(opposite,-f)
                        # Az=A0+2*x_local-3*y_local has constant |B|^2=13.
                        # Each original triangle has exact area scale^2/2048.
                        local=(points-shift)@rotation;uniform=.125+2*local[:,0]-3*local[:,1]
                        exact_energy=.5*13*scale**2/2048*np.sum(1/(MU0*permeability))
                        energy_error=float(abs((.5*uniform@k@uniform)/exact_energy-1));assert energy_error<1e-11;maximum_energy=max(maximum_energy,energy_error)
                        if pattern in (0,1):
                            coefficients={m.id:m.mu_r for m in p.materials}
                            current=scale**2*sum(current_density[region.id]*moment(concave,0,0,i,pattern) for i,region in enumerate(p.regions))
                            cd=float(abs(f.sum()/current-1));assert cd<1e-12;maximum_current=max(maximum_current,cd)
                            # Pull nodal values to the original Cartesian fixture. A
                            # rigid motion leaves |grad|^2 unchanged; spatial scale
                            # cancels between 2D gradients and area in the K form.
                            x,y=((points-shift)@rotation/scale).T
                            polynomials=[(np.ones(len(points)),0,0,[]),(x,1,0,[(1.,0,0)]),(y,0,1,[(1.,0,0)])]
                            if order==2:polynomials += [(x*x,2,0,[(4.,2,0)]),(x*y,1,1,[(1.,2,0),(1.,0,2)]),(y*y,0,2,[(4.,0,2)])]
                            absolute_current=scale**2*sum(abs(current_density[region.id])*moment(concave,0,0,i,pattern) for i,region in enumerate(p.regions))
                            for c,a,b,terms in polynomials:
                                expected=(1/MU0)*sum((1/coefficients[region.material])*sum(v*moment(concave,i,j,index,pattern) for v,i,j in terms) for index,region in enumerate(p.regions))
                                work=scale**2*sum(current_density[region.id]*moment(concave,a,b,i,pattern) for i,region in enumerate(p.regions))
                                ed=float(abs(c@k@c/expected-1)) if expected else kernel;wd=float(abs(c@f-work)/(np.max(abs(c))*absolute_current))
                                assert max(ed,wd)<1e-11;maximum_polynomial=max(maximum_polynomial,ed,wd);polynomials_checked+=1
                        path=out/(name+'.json');path.write_text(json.dumps(dict(partition=p.to_dict(),current_density_z_a_per_m2=current_density),indent=2)+'\n')
                        assert PlanarMagneticPartition.from_dict(json.loads(path.read_text())['partition']).to_dict()==p.to_dict()
                        preserved[path.name]=hashlib.sha256(path.read_bytes()).hexdigest();records.append(dict(name=name,stiffness_relative_difference=kd,load_relative_difference=fd,quadrature=diagnostic))
            print('DONE',concave,order,flush=True)
    assert fingerprints()==before
    for path,digest in preserved.items():assert hashlib.sha256((out/path).read_bytes()).hexdigest()==digest
    result=dict(status='PASS',cases=len(records),partition_permutations=len(records),constant_kernel_spectra=len(records),partition_roundtrips=len(preserved),independent_polynomial_checks=polynomials_checked,
        maximum_stiffness_relative_difference=maximum_k,maximum_load_relative_difference=maximum_f,maximum_scale_rigid_motion_relative_difference=maximum_transform,
        maximum_polynomial_relative_difference=maximum_polynomial,maximum_total_current_relative_difference=maximum_current,mu_scaling_cases=len(records),current_sign_cases=len(records),uniform_B_energy_cases=len(records),maximum_mu_scaling_relative_difference=maximum_mu,maximum_uniform_B_energy_relative_difference=maximum_energy,records=records,source_sha256=before,seconds=time.monotonic()-start,
        interpretation='planar magnetic Az reluctivity K[m/H] and Jz load[A]; uniform-B energy[J/m] and constant gauge kernel. No axis, implicit thickness, boundary/gauge constraint, field solve or magnetic accuracy acceptance.')
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k not in ('records','source_sha256')})


if __name__=='__main__':main()
