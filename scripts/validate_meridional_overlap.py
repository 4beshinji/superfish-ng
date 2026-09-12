# SPDX-License-Identifier: Apache-2.0
"""Independent polynomial integrals on remeshed vacuum with zero to two holes."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng.axis_connected_mesh import AxisConnectedMesh
from superfish_ng.meridional_mesh import MeridionalMesh
from superfish_ng.meridional_overlap import meridional_overlay
from superfish_ng.fem import triangle_quadrature


def multiply(a,b):
    result={}
    for (i,j),x in a.items():
        for (k,l),y in b.items():result[i+k,j+l]=result.get((i+k,j+l),0.)+x*y
    return result


def power(poly,n):
    result={(0,0):1.}
    for _ in range(n):result=multiply(result,poly)
    return result


def mapped_polynomial(poly,transform):
    result={};r,z=transform
    for (i,j),value in poly.items():
        for key,coefficient in multiply(power(r,i),power(z,j)).items():result[key]=result.get(key,0.)+value*coefficient
    return result


def polynomial_value(poly,points):
    return sum(value*points[...,0]**i*points[...,1]**j for (i,j),value in poly.items())


def mesh(n,holes,axis,transform,seed):
    width=5 if holes==2 else 3;voids=[(1,1,2,2),(3,1,4,2)][:holes]
    rectangles=[(0,0,width,3,1)]+[(*box,-1) for box in voids]
    points=np.array([(i/n,j/n) for j in range(3*n+1) for i in range(width*n+1)])
    triangles=[];rng=np.random.default_rng(seed)
    for j in range(3*n):
        for i in range(width*n):
            if any(a*n<=i<b*n and c*n<=j<d*n for a,c,b,d in voids):continue
            a=j*(width*n+1)+i;b=a+1;d=a+width*n+1;c=d+1
            triangles.extend(((a,b,c),(a,c,d)) if rng.integers(2) else ((a,b,d),(b,c,d)))
    used=np.unique(triangles);index=np.full(len(points),-1,dtype=int);index[used]=np.arange(len(used));triangles=index[np.array(triangles)];points=points[used]
    def mapped(p):return np.column_stack([polynomial_value(poly,np.asarray(p)) for poly in transform])
    outer=mapped([[0,0],[width,0],[width,3],[0,3]])
    holes_rz=[mapped([[a,c],[a,d],[b,d],[b,c]]) for a,c,b,d in voids]
    permutation=rng.permutation(len(points));inverse=np.argsort(permutation)
    result=(AxisConnectedMesh if axis else MeridionalMesh)(outer,holes_rz,mapped(points[permutation]),inverse[triangles][rng.permutation(len(triangles))])
    return result,rectangles


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();started=time.monotonic();records=[]
    polynomials=[{(0,0):1.,(1,0):2.,(0,1):-3.},{(0,0):2.,(2,0):4.,(1,1):-2.,(0,2):3.}]
    for axis in (False,True):
        for holes in (0,1,2):
            for variant in range(4):
                ar=(1,2,1,2)[variant]/32;az=(1,1,2,2)[variant]/32
                shear=1/64 if not axis and variant>=2 else 0.
                transform=({(1,0):ar,(0,1):shear,(0,0):0. if axis else 1/32},{(0,1):az,(0,0):-.125 if variant%2 else 0.})
                for n in (1,2):
                    a,rectangles=mesh(n,holes,axis,transform,17);b,_=mesh(n*2,holes,axis,transform,31)
                    overlay=meridional_overlay(a,b);errors=[]
                    for order,poly in enumerate(polynomials,1):
                        values=[]
                        for original,cells in ((a,overlay.previous_cells),(b,overlay.current_cells)):
                            vertices=original.points_rz_m[original.triangles[cells]]
                            local=vertices if order==1 else np.concatenate((vertices,(vertices+vertices[:,[1,2,0]])/2),axis=1)
                            values.append(polynomial_value(poly,local))
                        for radial_power in (0,1,3):
                            integral=0.
                            for bary,weight in triangle_quadrature(5):
                                fields=[]
                                for coefficients,vertex_bary in zip(values,(overlay.previous_vertex_barycentric,overlay.current_vertex_barycentric)):
                                    q=np.einsum('i,tij->tj',bary,vertex_bary)
                                    basis=q if order==1 else np.column_stack((q*(2*q-1),4*q[:,0]*q[:,1],4*q[:,1]*q[:,2],4*q[:,2]*q[:,0]))
                                    fields.append(np.einsum('ti,ti->t',basis,coefficients))
                                rz=np.einsum('i,tij->tj',bary,overlay.vertices_rz_m)
                                integral+=np.dot(weight*overlay.determinants*rz[:,0]**radial_power,fields[0]*fields[1])
                            composed=mapped_polynomial(multiply(multiply(poly,poly),{(radial_power,0):1.}),transform)
                            exact=ar*az*sum(sign*coefficient*(xr**(i+1)-xl**(i+1))*(zt**(j+1)-zb**(j+1))/((i+1)*(j+1)) for xl,zb,xr,zt,sign in rectangles for (i,j),coefficient in composed.items())
                            error=abs(integral/exact-1);assert error<1e-11,(axis,holes,variant,n,order,radial_power,error);errors.append(error)
                    records.append(dict(axis=axis,holes=holes,transform=variant,coarse_subdivision=n,previous_cells=len(a.triangles),current_cells=len(b.triangles),common_triangles=len(overlay.determinants),max_polynomial_error=max(errors)))
    assert fingerprints()==before
    report=dict(status='PASS',scope='geometry and original P1/P2 polynomial products; no FEM solve or mode tracking',records=records,integrals=len(records)*6,max_relative_error=max(row['max_polynomial_error'] for row in records),source_sha256=before,seconds=time.monotonic()-started)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({key:report[key] for key in ('status','integrals','max_relative_error','seconds')})


if __name__=='__main__':main()
