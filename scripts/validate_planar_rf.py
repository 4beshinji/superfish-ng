# SPDX-License-Identifier: Apache-2.0
"""Independent planar cutoff spectrum, fields, side-wall loss and CLI/native checks."""
import argparse,json,subprocess,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng.constants import C0,TAU,EPS0,MU0
from superfish_ng.fem import triangle_quadrature
from superfish_ng.high_order import basis_p2
from superfish_ng.planar import PlanarCase,solve_planar,planar_quantities
from superfish_ng.planar_saved import save_planar_run,read_planar_run
from validate_curved_rf_adaptive import fingerprints


def check_rectangle(a,b,n,order,polarization):
    case=PlanarCase(a,b,polarization=polarization,nx=n,ny=n,element_order=order,modes=8)
    solution=solve_planar(case);space=solution.space
    points=space.dof_points_xy_m;cells=space.triangles;dofs=space.cell_dofs
    p=space.points_xy_m[cells];det=space.determinants;grad=space.gradients
    k,m=solution.stiffness,solution.mass;free=solution.free_dofs
    values=solution.eigenvalues
    material=EPS0 if polarization=='tm' else MU0
    normalization=np.sqrt(2*case.normalization_j_per_m/material)
    vectors=solution.coefficients[free]/normalization
    constant=np.ones(len(points));null_error=np.linalg.norm(k@constant)/np.linalg.norm(k.data)
    assert null_error<1e-12
    null_overlap=None
    if polarization=='te':
        null_overlap=float(np.max(abs(constant@(m@vectors)))/np.sqrt(constant@(m@constant)))
        assert null_overlap<1e-9
    assert np.max(abs(vectors.T@(m[free][:,free]@vectors)-np.eye(8)))<1e-9
    lo=1 if polarization=='tm' else 0
    exact=sorted((C0/2*np.hypot(i/a,j/b),i,j) for i in range(lo,8) for j in range(lo,8) if i+j)[:8]
    freq=C0/TAU*np.sqrt(values);error=max(abs(freq/np.array([r[0] for r in exact])-1))
    # Positive Ritz values, correct TE zero exclusion and rectangular scale law.
    assert min(freq)>0
    rf_errors=[];field_errors=[]
    if True:
        # Boundary adjacency comes solely from the triangulation.
        boundary_edges={}
        for cell,tri in enumerate(cells):
            for ia,ib in ((0,1),(1,2),(2,0)):
                edge=tuple(sorted((int(tri[ia]),int(tri[ib]))))
                if edge in boundary_edges:boundary_edges[edge]=None
                else:boundary_edges[edge]=(cell,ia,ib)
        actual_edges=[(edge,v) for edge,v in boundary_edges.items() if v is not None]
        c=np.zeros((len(points),8));c[free]=vectors
        wnodes,wweights=np.polynomial.legendre.leggauss(5)
        wall=np.zeros(8);wall_matrix=np.zeros((8,8))
        for edge,(cell,ia,ib) in actual_edges:
            tangent=points[edge[1]]-points[edge[0]];edge_length=np.linalg.norm(tangent)
            normal=np.array([tangent[1],-tangent[0]])/edge_length
            for node,weight in zip((wnodes+1)/2,wweights/2):
                bary=np.zeros(3);bary[ia]=1-node;bary[ib]=node
                v,g=(bary,grad[cell]) if order==1 else basis_p2(bary,grad[cell])
                if polarization=='te':h=v@c[dofs[cell]]
                else:h=(g@normal)@c[dofs[cell]]/(TAU*freq*MU0)
                wall+=weight*edge_length*h**2
                wall_matrix+=weight*edge_length*np.outer(h,h)
        material=MU0 if polarization=='te' else EPS0
        actual_g=TAU*freq*material/wall
        for idx,(f,ix,iy) in enumerate(exact):
            if polarization=='te':
                cx=1 if ix==0 else .5;cy=1 if iy==0 else .5
                exact_g=TAU*f*MU0*a*b*cx*cy/(2*b*cy+2*a*cx)
            else:
                kx=ix*np.pi/a;ky=iy*np.pi/b
                exact_g=TAU*f*MU0*(kx*kx+ky*ky)*a*b/(4*(b*kx*kx+a*ky*ky))
            rf_errors.append(float(abs(actual_g[idx]/exact_g-1)))
    if True:
        scalar_norm=np.zeros((3,8));grad_norm=np.zeros((3,8));cross=np.zeros((8,8));dcross=np.zeros((8,8))
        for bary,w in triangle_quadrature(5):
            v,g=(bary,grad) if order==1 else basis_p2(bary,grad)
            xy=np.einsum('tij,i->tj',p,bary);x,y=xy.T
            actual=np.einsum('i,tim->tm',v,c[dofs]);dg=np.einsum('tij,tim->tmj',g,c[dofs])
            e=[];de=[]
            for f,ix,iy in exact:
                kx=ix*np.pi/a;ky=iy*np.pi/b
                if polarization=='tm':
                    amplitude=2/np.sqrt(a*b)
                    e.append(amplitude*np.sin(kx*x)*np.sin(ky*y))
                    de.append(np.column_stack((amplitude*kx*np.cos(kx*x)*np.sin(ky*y),amplitude*ky*np.sin(kx*x)*np.cos(ky*y))))
                else:
                    amplitude=1/np.sqrt(a*b*(1 if ix==0 else .5)*(1 if iy==0 else .5))
                    e.append(amplitude*np.cos(kx*x)*np.cos(ky*y))
                    de.append(np.column_stack((-amplitude*kx*np.sin(kx*x)*np.cos(ky*y),-amplitude*ky*np.cos(kx*x)*np.sin(ky*y))))
            e=np.array(e).T;de=np.stack(de,axis=1)
            cross+=np.einsum('t,ta,tb->ab',w*det,e,actual)
            dcross+=np.einsum('t,taj,tbj->ab',w*det,de,dg)
            for index,array in enumerate((actual**2,e**2,actual*e)):
                scalar_norm[index]+=np.einsum('t,tm->m',w*det,array)
            for index,array in enumerate((dg**2,de**2,dg*de)):
                grad_norm[index]+=np.einsum('t,tmj->m',w*det,array)
        signs=np.sign(scalar_norm[2])
        scalar_error=np.sqrt(np.maximum(0,(scalar_norm[0]+scalar_norm[1]-2*signs*scalar_norm[2])/scalar_norm[1]))
        gradient_error=np.sqrt(np.maximum(0,(grad_norm[0]+grad_norm[1]-2*signs*grad_norm[2])/grad_norm[1]))
        # The magnetic/electric derivative phasor uses the numerical frequency.
        ratio=np.array([r[0] for r in exact])/freq
        derived_error=np.sqrt(np.maximum(0,(ratio**2*grad_norm[0]+grad_norm[1]-2*signs*ratio*grad_norm[2])/grad_norm[1]))
        field_errors=[];wall_subspace_geometry_factors=[];first=0
        exact_values=(TAU*np.array([r[0] for r in exact])/C0)**2
        dcross/=np.sqrt(exact_values[:,None]*values[None,:])
        while first<8:
            last=first+1
            while last<8 and abs(exact[last][0]/exact[first][0]-1)<1e-10:last+=1
            cc=cross[first:last,first:last];left,singular,right=np.linalg.svd(cc)
            rotation=right.T@left.T
            # One electric/scalar alignment also aligns the derivative field.
            field_errors.extend([float(np.sqrt(max(0,2-2*singular.mean()))),
                float(np.sqrt(max(0,2-2*np.trace(dcross[first:last,first:last]@rotation)/(last-first))))])
            # Individual G values depend on the chosen degenerate basis.
            # Eigenvalues of the full wall quadratic form do not.
            inverse_g=wall_matrix[first:last,first:last]/(material*TAU*np.sqrt(freq[first:last,None]*freq[None,first:last]))
            wall_subspace_geometry_factors.append(sorted((1/np.linalg.eigvalsh(inverse_g)).tolist()))
            first=last
        assert np.max(abs(grad_norm[0]/values/scalar_norm[0]-1))<1e-9
    record=dict(a=a,b=b,n=n,order=order,polarization=polarization,frequency_hz=freq.tolist(),
        max_frequency_relative_error=float(error),null_overlap=None if null_overlap is None else float(null_overlap),
        null_residual=float(null_error),dofs=len(points),geometry_factor_relative_errors=rf_errors,field_relative_l2_errors=field_errors,wall_subspace_geometry_factors=wall_subspace_geometry_factors)
    api_g=np.array([planar_quantities(solution,i)['geometry_factor_ohm'] for i in range(8)])
    np.testing.assert_allclose(api_g,actual_g,rtol=1e-10,atol=0)
    indices=np.arange(len(cells));bary=np.full((len(cells),3),1/3)
    v,g=(bary[0],grad) if order==1 else basis_p2(bary[0],grad)
    for mode in range(8):
        fields=solution.fields_in_cells(indices,bary,mode)
        scalar=np.einsum('i,ti->t',v,c[dofs,mode])
        gradient=np.einsum('tij,ti->tj',g,c[dofs,mode]);omega=TAU*freq[mode]
        if polarization=='tm':
            other=fields['Ez_real_V_per_m']/normalization
            dg=np.column_stack((-fields['Hy_quadrature_A_per_m'],fields['Hx_quadrature_A_per_m']))*(omega*MU0/normalization)
        else:
            other=fields['Hz_real_A_per_m']/normalization
            dg=np.column_stack((fields['Ey_quadrature_V_per_m'],-fields['Ex_quadrature_V_per_m']))*(omega*EPS0/normalization)
        assert np.max(abs(other-scalar))<1e-11*max(abs(scalar))
        assert np.max(abs(dg-gradient))<1e-11*np.max(abs(gradient))
    return record,solution


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();rows=[];cli_rows=[]
    for shape in ((.31,.2),(.2,.2)):
        for polarization in ('tm','te'):
            for order,levels in ((1,(32,96,512)),(2,(8,32,96))):
                for n in levels:
                    for scale in (1,2):
                        row,solution=check_rectangle(*(v*scale for v in shape),n,order,polarization);rows.append(row)
                        print(polarization,shape,order,n,scale,row['max_frequency_relative_error'],max(row['field_relative_l2_errors']),max(row['geometry_factor_relative_errors']),flush=True)
                        if n==(32 if order==1 else 96):
                            name=f'{shape[0]:g}-{polarization}-p{order}-s{scale}'
                            native=out/name;save_planar_run(solution.case,solution,native)
                            saved=read_planar_run(native);np.testing.assert_array_equal(saved.coefficients,solution.coefficients)
                            request=out/f'{name}.json';request.write_text(json.dumps(solution.case.to_dict())+'\n')
                            cli=out/f'{name}-cli';command=[sys.executable,'-m','superfish_ng','solve-planar',str(request),'--out',str(cli)]
                            run=subprocess.run(command,capture_output=True,text=True);(out/f'{name}-cli.log').write_text(run.stdout+run.stderr);assert run.returncode==0
                            other=read_planar_run(cli);np.testing.assert_array_equal(other.coefficients,solution.coefficients)
                            assert json.loads((native/'results.json').read_text())==json.loads((cli/'results.json').read_text())
                            cli_rows.append(dict(name=name,passed=True))
                        (out/'partial.json').write_text(json.dumps(rows,indent=2)+'\n')
                    np.testing.assert_allclose(np.array(rows[-1]['frequency_hz'])*2,rows[-2]['frequency_hz'],rtol=1e-10)
                    for left,right in zip(rows[-1]['wall_subspace_geometry_factors'],rows[-2]['wall_subspace_geometry_factors']):
                        np.testing.assert_allclose(left,right,rtol=1e-9,atol=0)
                assert rows[-1]['max_frequency_relative_error']<1e-4
                assert max(rows[-1]['geometry_factor_relative_errors'])<.005,rows[-1]
                assert max(rows[-1]['field_relative_l2_errors'])<.01,rows[-1]
    assert fingerprints()==before
    (out/'report.json').write_text(json.dumps(dict(passed=True,scope='48 API FEM plus 16 CLI solves; additional native eigenspectrum/field/RF replay; eight complete rectangular/square TE/TM modes, P1/P2, two scales, three refinements; no general geometry/GUI acceptance',rows=rows,cli_rows=cli_rows,source_sha256=before,source_unchanged=True),indent=2)+'\n')


if __name__=='__main__':main()
