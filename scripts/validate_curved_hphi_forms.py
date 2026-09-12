# SPDX-License-Identifier: Apache-2.0
"""Independent dense quadrature and analytic energies for curved Hphi forms."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
from scipy.linalg import eigh
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.curved_meridional_reference import fixture,form_invariants
from scripts.validate_curved_meridional_geometry import monomials,NODES
from superfish_ng.curved_meridional_geometry import CurvedMeridionalGeometry
from superfish_ng.curved_hphi_fem import curved_hphi_matrices


def independent_matrices(space,axis,order=18):
    g=space.geometry;t,w=np.polynomial.legendre.leggauss(order);t=(t+1)/2;w=w/2
    x,y=np.meshgrid(t,t,indexing='ij');weights=(w[:,None]*w[None,:]*(1-x)).ravel()
    x,y=x.ravel(),(y*(1-x)).ravel()
    v=monomials(np.column_stack((x,y)))
    dx=np.column_stack((np.zeros_like(x),np.ones_like(x),np.zeros_like(x),2*x,y,np.zeros_like(x)))
    dy=np.column_stack((np.zeros_like(x),np.zeros_like(x),np.ones_like(x),np.zeros_like(x),x,2*y))
    size=3 if space.element_order==1 else 6
    inverse=np.linalg.inv(monomials(NODES)[:size,:size])
    phi=v[:,:size]@inverse;du=dx[:,:size]@inverse;dv=dy[:,:size]@inverse
    k=np.zeros((len(space.dof_points),)*2);m=np.zeros_like(k)
    for nodes,dofs in zip(g.cell_nodes,space.cell_dofs):
        coefficients=np.linalg.solve(monomials(NODES),g.points_rz_m[nodes])
        r=(v@coefficients)[:,0];first=dx@coefficients;second=dy@coefficients
        determinant=first[:,0]*second[:,1]-first[:,1]*second[:,0]
        gr=(du*second[:,1,None]-dv*first[:,1,None])/determinant[:,None]
        gz=(-du*second[:,0,None]+dv*first[:,0,None])/determinant[:,None]
        if axis:
            gr=2*phi+r[:,None]*gr;gz=r[:,None]*gz
            kw=weights*determinant*r;mw=weights*determinant*r**3
        else:kw=mw=weights*determinant/r
        k[np.ix_(dofs,dofs)]+=gr.T@(kw[:,None]*gr)+gz.T@(kw[:,None]*gz)
        m[np.ix_(dofs,dofs)]+=phi.T@(mw[:,None]*phi)
    return k,m


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples')
            for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();start=time.monotonic();records=[];spectra=[];scaled={};similarity=[]
    for axis in (False,True):
        for holes in (0,1,2):
            for order in (1,2):
                for shear in (0.,1.,-2.):
                    for scale in (.5,4.):
                        data,_=fixture(axis,holes,2,scale,shear,-scale/4);g=CurvedMeridionalGeometry(**data)
                        space,k,m,report=curved_hphi_matrices(g,order)
                        matrices=[k.toarray(),m.toarray()];reference=independent_matrices(space,axis)
                        differences=[float(np.linalg.norm(a-b)/np.linalg.norm(b)) for a,b in zip(matrices,reference)]
                        assert max(differences)<1e-11
                        expected=form_invariants(axis,holes,2,scale,shear,-scale/4);radial=expected['radial_integrals']
                        one=np.ones(len(space.dof_points));energy=[]
                        if axis:
                            energy=[abs((one@k@one)/(4*radial[1])-1),abs((one@m@one)/radial[3]-1)]
                            assert len(space.axis_dofs)>0
                        else:
                            assert np.linalg.norm(k@one)/(np.linalg.norm(k.data)*np.linalg.norm(one))<1e-14
                            r,z=space.dof_points.T
                            energy=[abs((one@m@one)/radial[-1]-1),abs((r@k@r)/radial[-1]-1),abs((r@m@r)/radial[1]-1)]
                            if order==2:energy.extend((abs((z@k@z)/radial[-1]-1),abs(r@k@z)/radial[-1],abs((z@m@z)/expected['z_mass']-1)))
                        assert max(energy)<1e-11
                        if shear==-2. and scale==.5:
                            values=eigh(*matrices,eigvals_only=True)
                            if axis:assert values[0]>0
                            else:assert abs(values[0])/values[-1]<1e-14 and values[1]>0
                            spectra.append(dict(axis=axis,holes=holes,element_order=order,dimension=len(values),
                                lowest_eigenvalues_per_m2=values[:3].tolist(),highest_eigenvalue_per_m2=float(values[-1])))
                        key=(axis,holes,order,shear)
                        if scale==.5:scaled[key]=matrices
                        else:
                            for first,second,power in zip(scaled.pop(key),matrices,(3,5) if axis else (-1,1)):
                                similarity.append(float(np.linalg.norm(second-first*8**power)/np.linalg.norm(second)))
                        records.append(dict(axis=axis,holes=holes,element_order=order,shear=shear,scale=scale,
                            dimension=len(space.dof_points),maximum_matrix_difference=max(differences),
                            maximum_analytic_energy_difference=float(max(energy)),quadrature=report))
            print('DONE',axis,holes,flush=True)
    assert not scaled and max(similarity)<1e-11 and fingerprints()==before
    result=dict(status='PASS',forms=len(records),records=records,dense_kernel_spectra=spectra,
        maximum_matrix_difference=max(r['maximum_matrix_difference'] for r in records),
        maximum_analytic_energy_difference=max(r['maximum_analytic_energy_difference'] for r in records),
        maximum_similarity_difference=max(similarity),source_sha256=before,seconds=time.monotonic()-start,
        scope='finite curved K/M and analytical field energies; no physical eigenmode/RF accuracy claim')
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print({k:v for k,v in result.items() if k not in ('records','source_sha256','dense_kernel_spectra')})


if __name__=='__main__':main()
