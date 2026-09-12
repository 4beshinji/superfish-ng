# SPDX-License-Identifier: Apache-2.0
"""Independent material Hphi dense forms, scalar kernels and dimensional laws."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
from scipy.linalg import eigvalsh
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.curved_meridional_reference import fixture
from superfish_ng.rf_materials import LinearRFMaterial,RFMaterialRegion,RFMaterialPartition
from superfish_ng.material_hphi_fem import material_hphi_matrices
from superfish_ng.axis_connected_fem import axis_connected_matrices
from superfish_ng.hphi_mesh import HphiMeshCase,hphi_mesh_matrices


def make_partition(axis,holes,pattern,scale):
    mesh=fixture(axis,holes,scale=scale,shear=0.)[0]['base_mesh'];count=len(mesh.triangles)
    labels=(np.zeros(count,dtype=int) if pattern==0 else
            (mesh.points_rz_m[mesh.triangles][:,:,1].mean(axis=1)>=scale/16).astype(int) if pattern==1 else
            np.arange(count)%3)
    material_values=((2.,3.),(7.,.5),(11.,5.))[:int(labels.max())+1]
    materials=[LinearRFMaterial(f'material-{i}',e,m) for i,(e,m) in enumerate(material_values)]
    regions=[RFMaterialRegion(f'region-{i}',materials[i].id,np.flatnonzero(labels==i).tolist()) for i in range(len(materials))]
    return RFMaterialPartition(mesh,materials,regions),np.asarray(material_values)[labels]


def dense_reference(mesh,coefficients,axis,order):
    # Polynomial interpolation is independent of the production P2 basis.
    nodes=np.array([[0.,0.],[1.,0.],[0.,1.],[.5,0.],[.5,.5],[0.,.5]])[:3 if order==1 else 6]
    def monomials(x,y):
        values=np.column_stack((np.ones(len(x)),x,y))
        return values if order==1 else np.column_stack((values,x*x,x*y,y*y))
    inverse=np.linalg.inv(monomials(*nodes.T));gauss,weights=np.polynomial.legendre.leggauss(18);gauss=(gauss+1)/2;weights=weights/2
    x=np.repeat(gauss,len(gauss));y=np.tile(gauss,len(gauss))*(1-x);w=np.repeat(weights,len(weights))*np.tile(weights,len(weights))*(1-x)
    basis=monomials(x,y)@inverse
    dx=np.column_stack((0*x,0*x+1,0*x));dy=np.column_stack((0*x,0*x,0*x+1))
    if order==2:dx=np.column_stack((dx,2*x,y,0*x));dy=np.column_stack((dy,0*x,x,2*y))
    derivative=np.stack((dx@inverse,dy@inverse),axis=-1)
    cells=mesh.triangles.copy();points=mesh.points_rz_m
    if order==2:
        edges=sorted({tuple(sorted((int(t[a]),int(t[b])))) for t in cells for a,b in ((0,1),(1,2),(2,0))})
        indices={edge:len(points)+i for i,edge in enumerate(edges)}
        cells=np.array([[*t,*(indices[tuple(sorted((int(t[a]),int(t[b]))))] for a,b in ((0,1),(1,2),(2,0)))] for t in cells])
        points=np.vstack((points,np.array([(mesh.points_rz_m[a]+mesh.points_rz_m[b])/2 for a,b in edges])))
    k=np.zeros((len(points),len(points)));m=np.zeros_like(k)
    for index,triangle in enumerate(mesh.triangles):
        vertices=mesh.points_rz_m[triangle];jac=(vertices[1:]-vertices[0]).T
        determinant=jac[0,0]*jac[1,1]-jac[0,1]*jac[1,0]
        gradient=derivative@np.linalg.inv(jac);radius=vertices[0,0]+x*jac[0,0]+y*jac[0,1]
        eps,mu=coefficients[index];measure=w*determinant
        if axis:
            a=radius[:,None]*gradient[:,:,1];b=2*basis+radius[:,None]*gradient[:,:,0]
            stiffness=a.T@((measure*radius/eps)[:,None]*a)+b.T@((measure*radius/eps)[:,None]*b)
            mass=basis.T@((measure*mu*radius**3)[:,None]*basis)
        else:
            stiffness=sum(gradient[:,:,i].T@((measure/(eps*radius))[:,None]*gradient[:,:,i]) for i in (0,1))
            mass=basis.T@((measure*mu/radius)[:,None]*basis)
        locations=np.ix_(cells[index],cells[index]);k[locations]+=stiffness;m[locations]+=mass
    return points,cells,k,m


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples')
            for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();start=time.monotonic();records=[];paired={};preserved={}
    max_matrix=max_scale=max_uniform=0.;spectra=0
    for axis in (False,True):
        for holes in (0,1,2):
            for order in (1,2):
                for pattern in (0,1,2):
                    for scale in (.5,2.):
                        name=f'axis-{int(axis)}-holes-{holes}-p-{order}-pattern-{pattern}-scale-{scale}'
                        p,coefficients=make_partition(axis,holes,pattern,scale);space,k,m,report=material_hphi_matrices(p,order)
                        np.testing.assert_array_equal(np.column_stack((p.epsilon_r,p.mu_r)),coefficients)
                        points,cells,rk,rm=dense_reference(p.mesh,coefficients,axis,order)
                        np.testing.assert_array_equal(points,space.dof_points);np.testing.assert_array_equal(cells,space.cell_dofs)
                        differences=[float(np.linalg.norm(a.toarray()-b)/np.linalg.norm(b)) for a,b in ((k,rk),(m,rm))]
                        assert max(differences)<1e-12;max_matrix=max(max_matrix,*differences)
                        if not axis:assert np.linalg.norm(k@np.ones(k.shape[0]))/np.linalg.norm(k.data)<1e-12
                        key=axis,holes,order,pattern
                        if key not in paired:paired[key]=(k,m)
                        else:
                            exponents=(3,5) if axis else (-1,1)
                            for old,new,power in zip(paired[key],(k,m),exponents):
                                difference=float(np.linalg.norm((new/4**power-old).data)/np.linalg.norm(old.data));assert difference<1e-12;max_scale=max(max_scale,difference)
                        raw=p.to_dict();raw['materials'].reverse();raw['regions'].reverse();permuted=material_hphi_matrices(RFMaterialPartition.from_dict(raw),order)
                        for a,b in zip((k,m),permuted[1:3]):np.testing.assert_array_equal(a.toarray(),b.toarray())
                        if pattern==0 and scale==.5:
                            old=axis_connected_matrices(p.mesh,order) if axis else hphi_mesh_matrices(HphiMeshCase(p.mesh,element_order=order,quadrature_order=12))
                            eigenvalues=eigvalsh(k.toarray(),m.toarray());original=eigvalsh(old[1].toarray(),old[2].toarray());offset=0 if axis else 1
                            difference=float(np.max(abs(eigenvalues[offset:]*6/original[offset:]-1)));assert difference<1e-10;max_uniform=max(max_uniform,difference);spectra+=1
                            if axis:assert eigenvalues[0]>0
                            else:assert abs(eigenvalues[0])<1e-10*eigenvalues[-1] and eigenvalues[1]>0
                        path=out/(name+'.json');path.write_text(json.dumps(p.to_dict(),indent=2)+'\n');assert RFMaterialPartition.from_dict(json.loads(path.read_text())).to_dict()==p.to_dict();preserved[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
                        records.append(dict(name=name,regions=len(p.regions),interfaces=len(p.interface_edges),matrix_relative_differences=differences,quadrature=report))
            print('DONE',axis,holes,flush=True)
    for path,digest in preserved.items():assert hashlib.sha256((out/path).read_bytes()).hexdigest()==digest
    assert fingerprints()==before
    result=dict(status='PASS',cases=len(records),material_region_permutations=len(records),partition_roundtrips=len(preserved),uniform_full_spectra=spectra,
        maximum_matrix_relative_difference=max_matrix,maximum_spatial_scale_relative_difference=max_scale,maximum_uniform_eigenvalue_relative_difference=max_uniform,
        interpretation='finite K/M and explicit material partition; no material eigensolver or RF accuracy acceptance',records=records,source_sha256=before,seconds=time.monotonic()-start)
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k not in ('records','source_sha256')})


if __name__=='__main__':main()
