# SPDX-License-Identifier: Apache-2.0
"""Independent material spectra, original fields/RF and layered TEM refinement."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
from scipy.linalg import eigvalsh
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.validate_material_hphi_forms import make_partition,dense_reference
from scripts.material_hphi_reference import layered_partition,layered_reference
from superfish_ng.material_hphi import MaterialHphiCase,solve_material_hphi,restore_material_hphi
from superfish_ng.material_hphi_rf import material_hphi_quantities
from superfish_ng.constants import C0,EPS0,MU0,TAU


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples')
            for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def independent_polynomials(solution,mode):
    order=solution.case.element_order
    nodes=np.array([[0.,0.],[1.,0.],[0.,1.],[.5,0.],[.5,.5],[0.,.5]])[:3 if order==1 else 6]
    def monomials(x,y):
        return np.column_stack((np.ones(len(x)),x,y)) if order==1 else np.column_stack((np.ones(len(x)),x,y,x*x,x*y,y*y))
    polynomials=np.linalg.solve(monomials(*nodes.T),solution.coefficients[solution.space.cell_dofs,mode].T).T
    vertices=solution.case.partition.mesh.points_rz_m[solution.case.partition.mesh.triangles]
    jacobians=np.transpose(vertices[:,1:]-vertices[:,:1],(0,2,1));inverse=np.linalg.inv(jacobians)
    def evaluate(cell_indices,xy):
        cells=np.asarray(cell_indices);x,y=np.asarray(xy).T;polynomial=polynomials[cells]
        scalar=np.einsum('qi,qi->q',monomials(x,y),polynomial)
        dx=polynomial[:,1].copy();dy=polynomial[:,2].copy()
        if order==2:dx+=2*x*polynomial[:,3]+y*polynomial[:,4];dy+=x*polynomial[:,4]+2*y*polynomial[:,5]
        grad=np.einsum('qa,qab->qb',np.column_stack((dx,dy)),inverse[cells]);points=vertices[cells,0]+np.einsum('qia,qa->qi',jacobians[cells],xy)
        r=points[:,0];omega=TAU*solution.frequencies_hz[mode];eps=solution.case.partition.epsilon_r[cells]
        if solution.case.axis_connected:h=r*scalar;er=r*grad[:,1]/(omega*EPS0*eps);ez=-(2*scalar+r*grad[:,0])/(omega*EPS0*eps)
        else:h=scalar/r;er=grad[:,1]/(omega*EPS0*eps*r);ez=-grad[:,0]/(omega*EPS0*eps*r)
        return points,h,er,ez
    return evaluate,jacobians


def independent_rf(solution,mode,evaluate,jacobians):
    p=solution.case.partition;mesh=p.mesh;electric=np.zeros(len(p.regions));magnetic=np.zeros_like(electric)
    nodes,weights=np.polynomial.legendre.leggauss(18);t=(nodes+1)/2;w=weights/2
    x=np.repeat(t,len(t));y=np.tile(t,len(t))*(1-x);xy=np.column_stack((x,y))
    weights2=np.repeat(w,len(w))*np.tile(w,len(w))*(1-x)
    for cell,jac in enumerate(jacobians):
        points,h,er,ez=evaluate(np.full(len(x),cell),xy);det=jac[0,0]*jac[1,1]-jac[0,1]*jac[1,0]
        measure=TAU*points[:,0]*weights2*det;region=p.cell_region_indices[cell]
        electric[region]+=EPS0*p.epsilon_r[cell]/4*np.dot(measure,er*er+ez*ez)
        magnetic[region]+=MU0*p.mu_r[cell]/4*np.dot(measure,h*h)
    walls=np.zeros(len(mesh.surface_area_m2_by_segment));region_walls=np.zeros(len(p.regions))
    for edge,cell,local,segment in zip(mesh.boundary_edges,mesh.boundary_cells,mesh.boundary_local_vertices,mesh.boundary_segments):
        a,b=mesh.points_rz_m[edge]
        if a[0]==b[0]==0.:continue
        bary=np.zeros((len(t),3));bary[:,local[0]]=1-t;bary[:,local[1]]=t
        points,h,er,ez=evaluate(np.full(len(t),cell),bary[:,1:]);integral=TAU*np.linalg.norm(b-a)*np.dot(w,points[:,0]*h*h)
        walls[segment]+=integral;region_walls[p.cell_region_indices[cell]]+=integral
    energy=float((electric+magnetic).sum());frequency=solution.frequencies_hz[mode]
    rs=np.sqrt(np.pi*frequency*MU0/solution.case.conductivity_s_per_m);loss=rs*walls.sum()/2
    return dict(stored_energy_j=energy,electric_energy_j=float(electric.sum()),magnetic_energy_j=float(magnetic.sum()),
        wall_loss_w=loss,q0=TAU*frequency*energy/loss,geometry_factor_ohm=2*TAU*frequency*energy/walls.sum(),
        electric_regions=electric,magnetic_regions=magnetic,wall_regions=rs*region_walls/2,walls=walls)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();start=time.monotonic()
    records=[];layers=[];preserved={};maximum_spectrum=maximum_field=maximum_rf=0.
    for axis in (False,True):
        for holes in (0,1,2):
            for order in (1,2):
                for pattern in (1,2):
                    p,coefficients=make_partition(axis,holes,pattern,.5);case=MaterialHphiCase(p,element_order=order,modes=3)
                    solution=solve_material_hphi(case);_,_,k,m=dense_reference(p.mesh,coefficients,axis,order)
                    spectrum=eigvalsh(k,m);offset=0 if axis else 1;expected=C0/TAU*np.sqrt(spectrum[offset:offset+case.modes])
                    difference=float(np.max(abs(solution.frequencies_hz/expected-1)));assert difference<1e-10;maximum_spectrum=max(maximum_spectrum,difference)
                    restored=restore_material_hphi(case,solution.coefficients,solution.frequencies_hz);np.testing.assert_array_equal(restored.coefficients,solution.coefficients)
                    for mode in range(case.modes):
                        evaluate,jacobians=independent_polynomials(solution,mode)
                        refs=np.array([[.2,.3],[.5,.25],[.125,.75]]);cells=np.repeat(np.arange(len(p.mesh.triangles)),len(refs));xy=np.tile(refs,(len(p.mesh.triangles),1))
                        points,h,er,ez=evaluate(cells,xy);bary=np.column_stack((1-xy.sum(axis=1),xy));actual=solution.fields_in_cells(cells,bary,mode)
                        for key,expected in (('Hphi_real_A_per_m',h),('Er_quadrature_V_per_m',er),('Ez_quadrature_V_per_m',ez),('Bphi_real_T',MU0*p.mu_r[cells]*h)):
                            error=float(np.linalg.norm(actual[key]-expected)/np.linalg.norm(expected));assert error<1e-10;maximum_field=max(maximum_field,error)
                        expected=independent_rf(solution,mode,evaluate,jacobians);rf=material_hphi_quantities(solution,mode)
                        arrays=[(rf[key],expected[key]) for key in ('stored_energy_j','electric_energy_j','magnetic_energy_j','wall_loss_w','q0','geometry_factor_ohm')]
                        arrays+=[([r[key] for r in rf['regions']],expected[ref]) for key,ref in (('electric_energy_j','electric_regions'),('magnetic_energy_j','magnetic_regions'),('adjacent_wall_loss_w','wall_regions'))]
                        arrays.append((rf['wall_h2_integral_a2_by_segment'],expected['walls']))
                        for a,b in arrays:
                            a,b=np.asarray(a),np.asarray(b);error=float(np.linalg.norm(a-b)/np.linalg.norm(b));assert error<1e-10;maximum_rf=max(maximum_rf,error)
                    path=out/f'axis-{int(axis)}-holes-{holes}-p{order}-pattern-{pattern}.json';path.write_text(json.dumps(case.to_dict(),indent=2)+'\n')
                    assert MaterialHphiCase.load(path).to_dict()==case.to_dict();preserved[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
                    records.append(dict(axis=axis,holes=holes,order=order,pattern=pattern,frequency_relative_difference=difference))
        print('MATERIAL',axis,flush=True)
    for order in (1,2):
        for scale in (.5,2.):
            previous=None
            for nz in (48,96):
                case=MaterialHphiCase(layered_partition(nr=4,nz=nz,scale=scale),element_order=order,modes=3)
                solution=solve_material_hphi(case);per_mode=[]
                # Independent Gauss points in physical rectangles, avoiding an
                # interface average. Weight dV=2*pi*r*dr*dz defines the L2 norm.
                t,w=np.polynomial.legendre.leggauss(16);a,b,length=scale*np.array([.03125,.046875,.1875]);cut=2*length/3
                rr=a+(t+1)*(b-a)/2;points=[];weights=[]
                for low,high in ((0.,cut),(cut,length)):
                    zz=low+(t+1)*(high-low)/2;r,z=np.meshgrid(rr,zz)
                    points.extend(np.column_stack((r.ravel(),z.ravel())));weights.extend((TAU*r*np.outer(w,w)*(b-a)*(high-low)/4).ravel())
                points=np.asarray(points);weights=np.asarray(weights)
                for mode in range(3):
                    expected,fields=layered_reference(mode+1,scale);h,er,ez=fields(points);actual=solution.fields_at(points,mode)
                    sign=np.sign(np.dot(weights*h,actual['Hphi_real_A_per_m']));rf=material_hphi_quantities(solution,mode)
                    errors=dict(frequency=abs(rf['frequency_hz']/expected['frequency_hz']-1),
                        h_l2=np.sqrt(np.dot(weights,(sign*actual['Hphi_real_A_per_m']-h)**2)/np.dot(weights,h*h)),
                        e_l2=np.sqrt(np.dot(weights,(sign*actual['Er_quadrature_V_per_m']-er)**2+actual['Ez_quadrature_V_per_m']**2)/np.dot(weights,er*er)),
                        wall_loss=abs(rf['wall_loss_w']/expected['wall_loss_w']-1),
                        wall_segments=float(np.max(abs(np.array(rf['wall_h2_integral_a2_by_segment'])/expected['wall_h2_integral_a2_by_segment']-1))),
                        electric_regions=float(np.max(abs(np.array([r['electric_energy_j'] for r in rf['regions']])/expected['electric_energy_j_by_region']-1))),
                        magnetic_regions=float(np.max(abs(np.array([r['magnetic_energy_j'] for r in rf['regions']])/expected['magnetic_energy_j_by_region']-1))))
                    limits=(dict(frequency=.01,h_l2=.05,e_l2=.15,wall_loss=.03,wall_segments=.05,electric_regions=.05,magnetic_regions=.05) if order==1 else
                            dict(frequency=1e-4,h_l2=.002,e_l2=.005,wall_loss=.001,wall_segments=.002,electric_regions=.002,magnetic_regions=.002))
                    assert all(errors[k]<v for k,v in limits.items()),(order,scale,nz,mode,errors)
                    if nz==96:
                        fine=(dict(frequency=.003,h_l2=.012,e_l2=.07,wall_loss=.008,wall_segments=.015,electric_regions=.015,magnetic_regions=.015) if order==1 else
                              dict(frequency=1e-5,h_l2=.0003,e_l2=.001,wall_loss=.0001,wall_segments=.0003,electric_regions=.0003,magnetic_regions=.0003))
                        assert all(errors[k]<v for k,v in fine.items()),(order,scale,nz,mode,errors)
                    per_mode.append(errors)
                if previous is not None:
                    for a,b in zip(previous,per_mode):assert all(b[k]<a[k] for k in ('frequency','h_l2','e_l2','wall_loss','wall_segments')),(order,scale,a,b)
                previous=per_mode;layers.append(dict(order=order,scale=scale,nz=nz,modes=per_mode));print('LAYER',order,scale,nz,flush=True)
    for path,digest in preserved.items():assert hashlib.sha256((out/path).read_bytes()).hexdigest()==digest
    assert fingerprints()==before
    report=dict(status='PASS',material_cases=len(records),material_modes=3*len(records),layered_cases=len(layers),layered_modes=3*len(layers),case_roundtrips=len(preserved),
        maximum_frequency_relative_difference=maximum_spectrum,maximum_field_relative_difference=maximum_field,maximum_rf_relative_difference=maximum_rf,
        material_records=records,layered_records=layers,source_sha256=before,seconds=time.monotonic()-start,
        interpretation='independent finite-spectrum/field/RF comparison and two-layer TEM refinement; no arbitrary material geometry error bound')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('material_records','layered_records','source_sha256')})


if __name__=='__main__':main()
