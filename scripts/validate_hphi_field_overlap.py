# SPDX-License-Identifier: Apache-2.0
"""Independent physical-polynomial reconstruction of Hphi cross integrals."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from validate_meridional_overlap import mesh
from superfish_ng.axis_hphi import AxisHphiCase,solve_axis_hphi
from superfish_ng.hphi_mesh import HphiMeshCase,solve_hphi_mesh
from superfish_ng.hphi_field_overlap import hphi_field_grams
from superfish_ng.hphi_native import save_hphi_run
from superfish_ng.constants import EPS0,TAU


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def common_rule(declared,order=16):
    """Split each fine rectangular pixel into four triangles without mesh intersections."""
    r,z=(np.unique(declared.points_rz_m[:,i]) for i in (0,1));triangles=[]
    for a,b in zip(r,r[1:]):
        for c,d in zip(z,z[1:]):
            center=np.array([(a+b)/2,(c+d)/2])
            if any(h[0,0]<center[0]<h[2,0] and h[0,1]<center[1]<h[2,1] for h in declared.holes_rz_m):continue
            square=np.array([[a,c],[b,c],[b,d],[a,d]])
            triangles.extend([p,q,center] for p,q in zip(square,np.roll(square,-1,axis=0)))
    vertices=np.array(triangles);u=vertices[:,1]-vertices[:,0];v=vertices[:,2]-vertices[:,0];det=u[:,0]*v[:,1]-u[:,1]*v[:,0]
    nodes,weights=np.polynomial.legendre.leggauss(order);nodes=(nodes+1)/2;weights=weights/2
    bary=np.array([[1-x,x*(1-y),x*y] for x in nodes for y in nodes]);w=np.array([a*b*x for x,a in zip(nodes,weights) for b in weights])
    points=np.einsum('qi,tij->qtj',bary,vertices)
    volume_weights=TAU*points[:,:,0]*w[:,None]*det[None,:]
    return vertices.mean(axis=1),points,volume_weights


def independent_fields(solution,centers,points):
    """Fit each original nodal polynomial in physical coordinates, then differentiate.

    No production field evaluator, overlay barycentric data or production
    quadrature is used by this reference. Coordinates are scaled to condition
    the small Vandermonde systems; the derivative chain rule is explicit.
    """
    space=solution.space;vertices=space.mesh.points[space.mesh.triangles]
    matrix=np.stack((vertices[:,1]-vertices[:,0],vertices[:,2]-vertices[:,0]),axis=2)
    coordinates=np.einsum('tij,stj->sti',np.linalg.inv(matrix),centers[:,None,:]-vertices[None,:,0,:])
    inside=(coordinates.min(axis=2)>-1e-12)&(coordinates.sum(axis=2)<1+1e-12)
    assert np.all(inside.sum(axis=1)==1);parents=np.argmax(inside,axis=1)
    scale=np.max(abs(space.mesh.points),axis=0);dof=space.dof_points[space.cell_dofs]/scale
    def monomials(p):
        x,y=p[...,0],p[...,1];items=[np.ones_like(x),x,y]
        if solution.case.element_order==2:items.extend((x*x,x*y,y*y))
        return np.stack(items,axis=-1)
    coefficients=np.linalg.solve(monomials(dof),solution.coefficients[space.cell_dofs])
    local=coefficients[parents];coordinates=points/scale;x,y=coordinates[...,0],coordinates[...,1]
    value=np.einsum('qti,tim->qtm',monomials(coordinates),local)
    dr=np.broadcast_to(local[:,1]/scale[0],value.shape).copy();dz=np.broadcast_to(local[:,2]/scale[1],value.shape).copy()
    if solution.case.element_order==2:
        dr+=(2*x[:,:,None]*local[None,:,3]+y[:,:,None]*local[None,:,4])/scale[0]
        dz+=(x[:,:,None]*local[None,:,4]+2*y[:,:,None]*local[None,:,5])/scale[1]
    radius=points[:,:,0,None];omega=TAU*solution.frequencies_hz
    if isinstance(solution.case,AxisHphiCase):h=radius*value;er=radius*dz/(omega*EPS0);ez=-(2*value+radius*dr)/(omega*EPS0)
    else:h=value/radius;er=dz/(omega*EPS0*radius);ez=-dr/(omega*EPS0*radius)
    return [[er.reshape(-1,solution.case.modes),ez.reshape(-1,solution.case.modes)],[h.reshape(-1,solution.case.modes)]]


def reference_grams(a,b,weights):
    result=[];w=weights.reshape(-1,1)
    for left,right in zip(a,b):
        result.append([sum(x.T@(w*x) for x in left),sum(x.T@(w*y) for x,y in zip(left,right)),sum(y.T@(w*y) for y in right)])
    return result


def discrepancy(actual,expected):
    left,right=np.sqrt(np.diag(expected[0])),np.sqrt(np.diag(expected[2]))
    return max(float(np.max(abs(a-b)/x[:,None]/y[None,:])) for a,b,x,y in zip(actual,expected,(left,left,right),(left,right,right)))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();started=time.monotonic();records=[];solutions={};similarity=[]
    for axis in (False,True):
        for holes in (0,1,2):
            base_grams={}
            for scale in (1.,2.):
                transform=({(1,0):scale/32,(0,0):0. if axis else scale/32},{(0,1):scale/32})
                fields={}
                for n in (1,2):
                    geometry,_=mesh(n,holes,axis,transform,17 if n==1 else 31)
                    for order in (1,2):
                        case=(AxisHphiCase(geometry,element_order=order,modes=3,normalization_j=scale**3) if axis else HphiMeshCase(geometry,element_order=order,modes=3,normalization_j=scale**3,quadrature_order=12))
                        sol=solve_axis_hphi(case) if axis else solve_hphi_mesh(case)
                        solutions[n,order]=sol;save_hphi_run(case,sol,out/f'axis-{int(axis)}-holes-{holes}-scale-{int(scale)}-n-{n}-p-{order}')
                centers,points,weights=common_rule(solutions[2,1].case.mesh)
                for key,sol in solutions.items():fields[key]=independent_fields(sol,centers,points)
                for left_order in (1,2):
                    for right_order in (1,2):
                        a,b=solutions[1,left_order],solutions[2,right_order]
                        computed=hphi_field_grams(a,b);expected=reference_grams(fields[1,left_order],fields[2,right_order],weights)
                        errors=[discrepancy(actual,reference) for actual,reference in zip((computed.electric,computed.magnetic),expected)]
                        assert max(errors)<1e-9,(axis,holes,scale,left_order,right_order,errors)
                        key=left_order,right_order
                        if scale==1.:base_grams[key]=(computed,[a.coefficients.copy(),b.coefficients.copy()])
                        else:
                            old,coefficients=base_grams[key];signs=[np.sign(np.sum(c*sol.coefficients,axis=0)) for c,sol in zip(coefficients,(a,b))]
                            for current,previous in zip((computed.electric,computed.magnetic),(old.electric,old.magnetic)):
                                adjusted=[q*x[:,None]*y[None,:]/scale**3 for q,x,y in zip(current,(signs[0],signs[0],signs[1]),(signs[0],signs[1],signs[1]))]
                                similarity.append(discrepancy(adjusted,previous))
                        records.append(dict(axis=axis,holes=holes,scale=scale,previous_order=left_order,current_order=right_order,electric_error=errors[0],magnetic_error=errors[1],diagnostic=computed.diagnostic))
                        (out/'progress.json').write_text(json.dumps(dict(comparisons=len(records),last=records[-1]),indent=2)+'\n')
                print('DONE',axis,holes,scale,flush=True)
    assert max(similarity)<1e-9 and fingerprints()==before
    report=dict(status='PASS',scope='original-field integrals and physical similarity; coarse fixture spectra are not discretization accuracy evidence',fem_native=48,comparisons=len(records),records=records,max_reference_difference=max(max(r['electric_error'],r['magnetic_error']) for r in records),max_similarity_difference=max(similarity),source_sha256=before,seconds=time.monotonic()-started)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({key:report[key] for key in ('status','max_reference_difference','max_similarity_difference','seconds')})


if __name__=='__main__':main()
