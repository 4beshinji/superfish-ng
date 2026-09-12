# SPDX-License-Identifier: Apache-2.0
"""Independent finite-space spectrum, physical fields and curved-wall RF checks."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
from scipy.linalg import eigh
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.curved_meridional_reference import fixture
from scripts.validate_curved_meridional_geometry import monomials,NODES
from scripts.validate_curved_hphi_forms import independent_matrices
from superfish_ng.curved_meridional_geometry import CurvedMeridionalGeometry
from superfish_ng.curved_hphi import CurvedHphiCase,solve_curved_hphi,restore_curved_hphi
from superfish_ng.curved_hphi_rf import curved_hphi_quantities
from superfish_ng.axis_hphi import AxisAccelerationPath
from superfish_ng.constants import C0,EPS0,MU0,TAU


def independent_fields(solution,cell,reference,mode):
    x,y=np.asarray(reference).T
    value=monomials(reference)
    du=np.column_stack((np.zeros_like(x),np.ones_like(x),np.zeros_like(x),2*x,y,np.zeros_like(x)))
    dv=np.column_stack((np.zeros_like(x),np.zeros_like(x),np.ones_like(x),np.zeros_like(x),x,2*y))
    g=solution.case.geometry;mapping=np.linalg.solve(monomials(NODES),g.points_rz_m[g.cell_nodes[cell]])
    points=value@mapping;a=du@mapping;b=dv@mapping;det=a[:,0]*b[:,1]-a[:,1]*b[:,0]
    size=3 if solution.case.element_order==1 else 6
    coefficients=np.linalg.solve(monomials(NODES)[:size,:size],solution.coefficients[solution.space.cell_dofs[cell],mode])
    scalar=value[:,:size]@coefficients;s=du[:,:size]@coefficients;t=dv[:,:size]@coefficients
    dr=(s*b[:,1]-t*a[:,1])/det;dz=(-s*b[:,0]+t*a[:,0])/det;r=points[:,0];omega=TAU*solution.frequencies_hz[mode]
    if solution.case.axis_connected:
        h=r*scalar;er=r*dz/(omega*EPS0);ez=-(2*scalar+r*dr)/(omega*EPS0)
    else:h=scalar/r;er=dz/(omega*EPS0*r);ez=-dr/(omega*EPS0*r)
    return points,det,np.column_stack((er,ez)),h


def independent_quantities(solution,mode):
    t,w=np.polynomial.legendre.leggauss(24);t=(t+1)/2;w=w/2
    x,y=np.meshgrid(t,t,indexing='ij');weight=(w[:,None]*w[None,:]*(1-x)).ravel()
    reference=np.column_stack((x.ravel(),(y*(1-x)).ravel()));bary=np.column_stack((1-reference.sum(axis=1),reference))
    ue=um=0.;electric_error=electric_norm=magnetic_error=magnetic_norm=0.
    g=solution.case.geometry;base=g.base_mesh
    for cell in range(len(g.cell_nodes)):
        points,det,e,h=independent_fields(solution,cell,reference,mode)
        measure=TAU*weight*det*points[:,0]
        ue+=EPS0/4*(measure@np.sum(e*e,axis=1));um+=MU0/4*(measure@(h*h))
        actual=solution.fields_in_cells(np.full(len(bary),cell,dtype=int),bary,mode)
        ae=np.column_stack((actual['Er_quadrature_V_per_m'],actual['Ez_quadrature_V_per_m']));ah=actual['Hphi_real_A_per_m']
        electric_error+=measure@np.sum((ae-e)**2,axis=1);electric_norm+=measure@np.sum(e*e,axis=1)
        magnetic_error+=measure@((ah-h)**2);magnetic_norm+=measure@(h*h)
        for key,value in actual.items():
            if key not in ('Er_quadrature_V_per_m','Ez_quadrature_V_per_m','Hphi_real_A_per_m'):assert np.all(value==0.)
    walls=np.zeros(len(base.surface_area_m2_by_segment));areas=walls.copy();voltage=0j
    for edge,(cell,(a,b)) in enumerate(zip(base.boundary_cells,base.boundary_local_vertices)):
        bary=np.zeros((len(t),3));bary[:,a]=1-t;bary[:,b]=t
        points,det,e,h=independent_fields(solution,int(cell),bary[:,1:],mode)
        coeff=np.linalg.solve(np.array([[1.,0.,0.],[1.,1.,1.],[1.,.5,.25]]),g.points_rz_m[g.boundary_nodes[edge]])
        tangent=np.column_stack((np.zeros_like(t),np.ones_like(t),2*t))@coeff
        measure=TAU*w*points[:,0]*np.linalg.norm(tangent,axis=1)
        if g.boundary_tags[edge]=='pec':
            segment=base.boundary_segments[edge];walls[segment]+=measure@(h*h);areas[segment]+=measure.sum()
        elif solution.case.acceleration is not None:
            path=solution.case.acceleration;za,zb=g.points_rz_m[g.boundary_nodes[edge,:2],1]
            low=max(min(za,zb),path.z_start_m);high=min(max(za,zb),path.z_end_m)
            if high>low:
                z=low+(high-low)*t;fraction=(z-za)/(zb-za);bary=np.zeros((len(t),3));bary[:,a]=1-fraction;bary[:,b]=fraction
                points,det,e,h=independent_fields(solution,int(cell),bary[:,1:],mode)
                wave=TAU*solution.frequencies_hz[mode]/(path.beta*C0)
                voltage+=1j*(high-low)*np.dot(w,e[:,1]*np.exp(1j*wave*(z-path.phase_origin_m)))
    frequency=solution.frequencies_hz[mode];omega=TAU*frequency;rs=np.sqrt(np.pi*frequency*MU0/solution.case.conductivity_s_per_m);energy=ue+um;loss=rs*walls.sum()/2
    return dict(electric_energy_j=ue,magnetic_energy_j=um,stored_energy_j=energy,wall_loss_w=loss,
        geometry_factor_ohm=2*omega*energy/walls.sum(),q0=omega*energy/loss,
        wall_h2_integral_a2_by_segment=walls,surface_area_m2_by_segment=areas,voltage=voltage,
        r_over_q_accelerator_ohm=abs(voltage)**2/(omega*energy),
        electric_relative_l2=np.sqrt(electric_error/electric_norm),magnetic_relative_l2=np.sqrt(magnetic_error/magnetic_norm))


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples')
            for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();start=time.monotonic();records=[];fields=[];spectra=[];saved={}
    for axis in (False,True):
        for holes in (0,1,2):
            for order in (1,2):
                for shear in (-1.,1.):
                    for scale in (.5,2.):
                        offset=-scale/4;data,_=fixture(axis,holes,1,scale,shear,offset)
                        path=AxisAccelerationPath(offset+.02*scale,offset+.17*scale,.7,offset-.03*scale) if axis else None
                        case=CurvedHphiCase(CurvedMeridionalGeometry(**data),element_order=order,modes=3,normalization_j=scale**3,acceleration=path)
                        solution=solve_curved_hphi(case);reference=independent_matrices(solution.space,axis,order=20)
                        values=eigh(*reference,eigvals_only=True,subset_by_index=(0,2 if axis else 3));values=values if axis else values[1:]
                        frequency=C0/TAU*np.sqrt(values);difference=float(np.max(abs(solution.frequencies_hz/frequency-1)));assert difference<1e-9
                        spectra.append(difference)
                        restored=restore_curved_hphi(case,solution.coefficients,solution.frequencies_hz)
                        np.testing.assert_array_equal(restored.coefficients,solution.coefficients)
                        name=f'axis-{int(axis)}-holes-{holes}-p-{order}-shear-{shear}-scale-{scale}'
                        case_path=out/f'{name}.case.json';case_path.write_text(json.dumps(case.to_dict(),indent=2)+'\n')
                        assert CurvedHphiCase.load(case_path).to_dict()==case.to_dict();saved[case_path.name]=hashlib.sha256(case_path.read_bytes()).hexdigest()
                        results=[]
                        for mode in range(3):
                            actual=curved_hphi_quantities(solution,mode);ref=independent_quantities(solution,mode);errors={}
                            for key in ('electric_energy_j','magnetic_energy_j','stored_energy_j','wall_loss_w','geometry_factor_ohm','q0'):
                                errors[key]=float(abs(actual[key]/ref[key]-1))
                            for key in ('wall_h2_integral_a2_by_segment','surface_area_m2_by_segment'):
                                a,b=np.asarray(actual[key]),ref[key];denominator=np.maximum(abs(a),abs(b))
                                errors[key]=float(np.max(np.divide(abs(a-b),denominator,out=np.zeros_like(a),where=denominator>0)))
                            if axis:
                                value=complex(actual['vacc_v']['real'],actual['vacc_v']['imag']);errors['voltage']=float(abs(value-ref['voltage'])/max(abs(ref['voltage']),1.))
                                errors['r_over_q_accelerator_ohm']=float(abs(actual['r_over_q_accelerator_ohm']/ref['r_over_q_accelerator_ohm']-1))
                                assert actual['r_over_q_circuit_ohm']==actual['r_over_q_accelerator_ohm']/2
                            else:assert all(actual[k] is None for k in ('vacc_v','eacc_v_per_m','r_over_q_accelerator_ohm','r_over_q_circuit_ohm'))
                            assert max(errors.values())<1e-9 and max(ref['electric_relative_l2'],ref['magnetic_relative_l2'])<1e-10
                            fields.append([ref['electric_relative_l2'],ref['magnetic_relative_l2']])
                            records.append(dict(case=name,mode_index=mode+1,maximum_rf_difference=max(errors.values()),differences=errors));results.append(actual)
                        result_path=out/f'{name}.results.json';result_path.write_text(json.dumps(results,indent=2)+'\n');saved[result_path.name]=hashlib.sha256(result_path.read_bytes()).hexdigest()
            print('DONE',axis,holes,flush=True)
    for path,digest in saved.items():assert hashlib.sha256((out/path).read_bytes()).hexdigest()==digest
    assert fingerprints()==before
    result=dict(status='PASS',fem_cases=len(spectra),rf_modes=len(records),case_json_roundtrips=len(spectra),records=records,
        maximum_frequency_difference=max(spectra),maximum_rf_difference=max(r['maximum_rf_difference'] for r in records),
        maximum_electric_relative_l2=max(row[0] for row in fields),maximum_magnetic_relative_l2=max(row[1] for row in fields),
        saved_files_unchanged=len(saved),source_sha256=before,seconds=time.monotonic()-start,
        scope='synthetic quadratic geometry; independently assembled finite FEM and original-field integrals, not a continuum or legacy certification')
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k not in ('records','source_sha256')})


if __name__=='__main__':main()
