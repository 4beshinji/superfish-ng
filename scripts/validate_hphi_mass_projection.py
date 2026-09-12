# SPDX-License-Identifier: Apache-2.0
"""Independent physical polynomial and orthogonality checks for scalar projection."""
import argparse, hashlib, json, sys, time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from validate_meridional_overlap import mesh, multiply, polynomial_value
from validate_hphi_field_overlap import common_rule
from superfish_ng.hphi_mass_projection import hphi_mass_coupling,project_hphi_coefficients
from superfish_ng.constants import TAU


def monomials(points,order):
    x,y=points[...,0],points[...,1];items=[np.ones_like(x),x,y]
    if order==2:items.extend((x*x,x*y,y*y))
    return np.stack(items,axis=-1)


def reference_field(space,order,values,centers,points):
    """Reconstruct each original polynomial in physical Cartesian monomials.

    The integration grid splits small rectangles along both diagonals, so its
    triangle centers have one parent in each original independently chosen mesh.
    Neither the production intersections nor their barycentric data is used.
    """
    vertices=space.mesh.points[space.mesh.triangles]
    inverse=np.linalg.inv(np.stack((vertices[:,1]-vertices[:,0],vertices[:,2]-vertices[:,0]),axis=2))
    parents=[]
    for start in range(0,len(centers),256):
        local=np.einsum('tij,stj->sti',inverse,centers[start:start+256,None,:]-vertices[None,:,0,:])
        inside=(local.min(axis=2)>-1e-12)&(local.sum(axis=2)<1+1e-12)
        assert np.all(inside.sum(axis=1)==1);parents.extend(np.argmax(inside,axis=1))
    parents=np.array(parents);scale=np.max(abs(space.mesh.points),axis=0)
    vandermonde=monomials(space.dof_points[space.cell_dofs]/scale,order)
    inverse=np.linalg.inv(vandermonde)[parents]
    basis=np.einsum('qti,tij->qtj',monomials(points/scale,order),inverse)
    dofs=space.cell_dofs[parents]
    return np.einsum('qti,tim->qtm',basis,values[dofs]),basis,dofs


def analytic_norm(poly,rectangles,axis,unit):
    squared=multiply(poly,poly);result=0.;shift=0 if axis else 1
    for a,c,b,d,sign in rectangles:
        a+=shift;b+=shift
        for (i,j),coefficient in squared.items():
            power=i+(3 if axis else -1)
            radial=np.log(b/a) if power==-1 else (b**(power+1)-a**(power+1))/(power+1)
            result+=sign*coefficient*radial*(d**(j+1)-c**(j+1))/(j+1)
    return result*unit**(5 if axis else 1)


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();started=time.monotonic();records=[];similarity=[]
    for axis in (False,True):
        for holes in (0,1,2):
            old={}
            for scale in (1.,2.):
                unit=scale/32;transform=({(1,0):unit,(0,0):0 if axis else unit},{(0,1):unit})
                a,rectangles=mesh(1,holes,axis,transform,17);b,_=mesh(2,holes,axis,transform,31)
                centers,points,volume=common_rule(b,order=12)
                radius=points[:,:,0];weights=volume/TAU*(radius**2 if axis else radius**-2)
                for previous_order in (1,2):
                    for current_order in (1,2):
                        coupling=hphi_mass_coupling(a,b,previous_order=previous_order,current_order=current_order)
                        polynomial={(0,0):1.,(1,0):.2,(0,1):-.3}
                        if previous_order==2:polynomial.update({(2,0):.1,(1,1):.07,(0,2):.13})
                        coordinates=coupling.previous_space.dof_points/unit
                        values=np.column_stack((np.ones(len(coordinates)),polynomial_value(polynomial,coordinates),
                            np.random.default_rng(43).normal(size=len(coordinates))))
                        original=values.copy()
                        projection=project_hphi_coefficients(a,b,values,previous_order=previous_order,current_order=current_order)
                        np.testing.assert_array_equal(values,original)
                        source,_,_=reference_field(coupling.previous_space,previous_order,values,centers,points)
                        current,basis,dofs=reference_field(coupling.current_space,current_order,projection.coefficients,centers,points)
                        norm=np.sum(weights[:,:,None]*source**2,axis=(0,1))
                        errors=np.sum(weights[:,:,None]*(source-current)**2,axis=(0,1));relative=np.sqrt(errors/norm)
                        source_difference=float(np.max(abs(np.asarray(projection.diagnostic['source_squared_mass_norm'])/norm-1)))
                        error_difference=float(np.max(abs(np.asarray(projection.diagnostic['relative_mass_error'])-relative)))
                        assert source_difference<1e-10 and error_difference<1e-10
                        residual=np.zeros((coupling.current_mass.shape[0],values.shape[1]))
                        local=np.einsum('qt,qti,qtm->tim',weights,basis,source-current)
                        for i in range(dofs.shape[1]):np.add.at(residual,dofs[:,i],local[:,i])
                        orthogonality=float(np.max(abs(residual)/np.sqrt(coupling.current_mass.diagonal())[:,None]/np.sqrt(norm)[None,:]))
                        assert orthogonality<1e-10
                        exact=np.array([analytic_norm(poly,rectangles,axis,unit) for poly in ({(0,0):1.},polynomial)])
                        analytic_error=float(np.max(abs(norm[:2]/exact-1)));assert analytic_error<1e-11
                        assert relative[0]<1e-11
                        if current_order>=previous_order:assert relative[1]<1e-11
                        else:assert relative[1]>1e-4
                        key=previous_order,current_order
                        if scale==1:old[key]=(projection.coefficients.copy(),relative.copy(),norm.copy())
                        else:
                            coefficients,old_error,old_norm=old[key]
                            similarity.extend((float(np.max(abs(projection.coefficients-coefficients))),float(np.max(abs(relative-old_error))),float(np.max(abs(norm/old_norm/scale**(5 if axis else 1)-1)))))
                        record=dict(axis=axis,holes=holes,scale=scale,previous_order=previous_order,current_order=current_order,
                            reference_mass_difference=source_difference,reference_error_difference=error_difference,orthogonality=orthogonality,
                            analytic_mass_difference=analytic_error,relative_mass_errors=relative.tolist(),diagnostic=projection.diagnostic)
                        records.append(record)
                        np.savez(out/f'axis-{int(axis)}-holes-{holes}-s-{int(scale)}-p-{previous_order}-{current_order}.npz',original=values,projected=projection.coefficients)
                print('DONE',axis,holes,scale,flush=True)
    assert max(similarity)<1e-10 and fingerprints()==before
    report=dict(status='PASS',comparisons=len(records),scalar_columns=3*len(records),records=records,
        max_reference_difference=max(max(r['reference_mass_difference'],r['reference_error_difference'],r['orthogonality'],r['analytic_mass_difference']) for r in records),
        max_similarity_difference=max(similarity),source_sha256=before,seconds=time.monotonic()-started,
        scope='scalar mass and projection only; no new eigenmode or frequency/RF accuracy claim')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:report[k] for k in ('status','comparisons','max_reference_difference','max_similarity_difference','seconds')})


if __name__=='__main__':main()
