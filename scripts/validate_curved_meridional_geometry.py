# SPDX-License-Identifier: Apache-2.0
"""Independent Vandermonde/quadrature checks for synthetic polynomial geometry."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.curved_meridional_reference import fixture
from superfish_ng.curved_meridional_geometry import CurvedMeridionalGeometry
from superfish_ng.quadratic_geometry import QuadraticTriangle

NODES=np.array(((0.,0.),(1.,0.),(0.,1.),(.5,0.),(.5,.5),(0.,.5)))


def monomials(points):
    x,y=np.asarray(points).T
    return np.column_stack((np.ones_like(x),x,y,x*x,x*y,y*y))


def independent_moments(g,order=8):
    t,w=np.polynomial.legendre.leggauss(order);t=(t+1)/2;w=w/2
    x,y=np.meshgrid(t,t,indexing='ij');weight=(w[:,None]*w[None,:]*(1-x)).ravel()
    x,y=x.ravel(),(y*(1-x)).ravel();reference=np.column_stack((x,y))
    v=monomials(reference);dx=np.column_stack((np.zeros_like(x),np.ones_like(x),np.zeros_like(x),2*x,y,np.zeros_like(x)))
    dy=np.column_stack((np.zeros_like(x),np.zeros_like(x),np.ones_like(x),np.zeros_like(x),x,2*y))
    area=moment=0.;patch=0.;minimum=float('inf')
    for nodes in g.cell_nodes:
        points=g.points_rz_m[nodes];coeff=np.linalg.solve(monomials(NODES),points)
        xy=v@coeff;jx=dx@coeff;jy=dy@coeff;det=jx[:,0]*jy[:,1]-jx[:,1]*jy[:,0]
        area+=weight@det;moment+=weight@(det*xy[:,0]);minimum=min(minimum,float(det.min()))
        actual=QuadraticTriangle(points).evaluate(reference)
        patch=max(patch,float(np.max(abs(actual['points_rz_m']-xy))))
        gradient=np.einsum('ia,qib->qab',points,actual['basis_gradients'])
        patch=max(patch,float(np.max(abs(gradient-np.eye(2)))))
    assert minimum>0
    boundary_area=np.zeros(1+len(g.base_mesh.holes_rz_m));boundary_moment=boundary_area.copy()
    # Independent 1D Lagrange arithmetic, with oriented start/end/midpoint rows.
    basis=np.column_stack(((1-t)*(1-2*t),t*(2*t-1),4*t*(1-t)))
    deriv=np.column_stack((4*t-3,4*t-1,4-8*t))
    for nodes,component in zip(g.boundary_nodes,g.base_mesh.boundary_components):
        xy=basis@g.points_rz_m[nodes];dxy=deriv@g.points_rz_m[nodes]
        boundary_area[component]+=w@(xy[:,0]*dxy[:,1])
        boundary_moment[component]+=w@(xy[:,0]**2*dxy[:,1])/2
    return dict(area_m2=area,volume_m3=2*np.pi*moment,boundary_area_m2=float(boundary_area.sum()),
                boundary_volume_m3=float(2*np.pi*boundary_moment.sum()),
                component_area_m2=boundary_area.tolist(),coordinate_patch_max_error=patch)


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples')
            for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();start=time.monotonic();records=[];snapshots={}
    for axis in (False,True):
        for holes in (0,1,2):
            for n in (1,2):
                for scale in (.5,4.):
                    for shear in (0.,1.,-2.):
                        data,expected=fixture(axis,holes,n,scale,shear,z_offset=-scale/4)
                        g=CurvedMeridionalGeometry(**data);numeric=independent_moments(g)
                        differences=[abs(g.area_m2/expected['area_m2']-1),abs(g.volume_m3/expected['volume_m3']-1),
                            abs(numeric['area_m2']/expected['area_m2']-1),abs(numeric['volume_m3']/expected['volume_m3']-1),
                            abs(numeric['boundary_area_m2']/expected['area_m2']-1),abs(numeric['boundary_volume_m3']/expected['volume_m3']-1)]
                        assert max(differences)<1e-12 and numeric['coordinate_patch_max_error']<1e-11
                        np.testing.assert_allclose(numeric['component_area_m2'],g.validation['boundary_area_by_component_m2'],rtol=1e-12,atol=0)
                        path=out/f'axis-{int(axis)}-holes-{holes}-n-{n}-scale-{scale}-shear-{shear}.json'
                        path.write_text(json.dumps(g.to_dict(),indent=2)+'\n');snapshot=json.loads(path.read_text())
                        rebuilt=CurvedMeridionalGeometry.from_dict(snapshot)
                        assert rebuilt.to_dict()==snapshot and dict(rebuilt.validation)==dict(g.validation)
                        snapshots[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
                        records.append(dict(axis=axis,holes=holes,n=n,scale=scale,shear=shear,cells=len(g.cell_nodes),
                            maximum_relative_moment_difference=max(differences),coordinate_patch_max_error=numeric['coordinate_patch_max_error'],
                            exact_cell_boundary_moments_equal=g.validation['exact_cell_boundary_moments_equal']))
            print('DONE',axis,holes,flush=True)
    for name,digest in snapshots.items():assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest
    assert fingerprints()==before
    report=dict(status='PASS',geometries=len(records),records=records,json_roundtrips=len(snapshots),
        maximum_relative_moment_difference=max(r['maximum_relative_moment_difference'] for r in records),
        maximum_coordinate_patch_error=max(r['coordinate_patch_max_error'] for r in records),
        source_sha256=before,seconds=time.monotonic()-start,
        scope='synthetic polynomial geometry under a known invertible shear; no FEM, legacy or exact-conic result')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print({k:v for k,v in report.items() if k not in ('records','source_sha256')})


if __name__=='__main__':main()
