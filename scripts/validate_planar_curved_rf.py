#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Independent circular f/E/H/G gates on fixed original quadratic domains.

P07 circular evidence only. Geometry series, independent internal meshes and
noncircular/reentrant tests are separately required before accepting P07.
Analytic fields are validator references; production always solves area FEM.
"""
import argparse
import json
from pathlib import Path
import shutil
import time
import numpy as np
from numpy.polynomial.legendre import leggauss
from scipy.special import jv, jvp, jn_zeros, jnp_zeros
from superfish_ng.constants import C0, TAU, EPS0, MU0, Z0
from superfish_ng.jobs import _implementation_hashes
from superfish_ng.planar_curved import PlanarCurvedCase
from superfish_ng.planar_curved_solver import solve_planar_curved, planar_curved_quantities, restore_planar_curved_solution
from superfish_ng.planar_curved_refinement import refine_planar_curved_domain
from validate_planar_curved_fem import circle_domain


def groups(polarization):
    return ([(1,1,2,True),(2,1,2,True),(0,1,1,True),(3,1,2,False)] if polarization=='te'
            else [(0,1,1,True),(1,1,2,True),(2,1,2,False),(0,2,1,False)])


def analytic_fields(points, radius, polarization):
    r=np.linalg.norm(points,axis=1);theta=np.arctan2(points[:,1],points[:,0])
    scalars,gradients,frequencies,g_factors=[],[],[],[]
    for n,s,multiplicity,target in groups(polarization):
        alpha=float((jnp_zeros if polarization=='te' else jn_zeros)(n,s)[-1])
        omega=C0*alpha/radius
        integral=(2*np.pi if n==0 else np.pi)*radius**2/2*(jvp(n,alpha)**2+(1-n*n/alpha**2)*jv(n,alpha)**2)
        material=MU0 if polarization=='te' else EPS0
        amplitude=np.sqrt(2/(material*integral))
        for sine in range(multiplicity):
            angular=np.sin(n*theta) if sine else np.cos(n*theta)
            angular_derivative=n*np.cos(n*theta) if sine else -n*np.sin(n*theta)
            scalar=amplitude*jv(n,alpha*r/radius)*angular
            radial=amplitude*alpha/radius*jvp(n,alpha*r/radius)*angular
            azimuthal=np.divide(amplitude*jv(n,alpha*r/radius)*angular_derivative,r,
                                 out=np.zeros_like(r),where=r!=0)
            derivative=np.column_stack([radial*np.cos(theta)-azimuthal*np.sin(theta),
                                        radial*np.sin(theta)+azimuthal*np.cos(theta)])
            origin=r==0
            if np.any(origin):
                derivative[origin]=[0.,amplitude*alpha/(2*radius)] if n==1 and sine else [amplitude*alpha/(2*radius),0.] if n==1 else [0.,0.]
            scalars.append(scalar);gradients.append(derivative);frequencies.append(omega/TAU)
            g_factors.append(Z0*alpha/2*(1-n*n/alpha**2 if polarization=='te' else 1))
    scalar=np.column_stack(scalars);gradient=np.stack(gradients,axis=1)
    omega=TAU*np.array(frequencies)
    electric=np.zeros((len(points),3,len(frequencies)),dtype=complex)
    magnetic=np.zeros_like(electric)
    if polarization=='te':
        magnetic[:,2,:]=scalar
        electric[:,0,:]=-1j*gradient[...,1]/(omega*EPS0)
        electric[:,1,:]=1j*gradient[...,0]/(omega*EPS0)
    else:
        electric[:,2,:]=scalar
        magnetic[:,0,:]=1j*gradient[...,1]/(omega*MU0)
        magnetic[:,1,:]=-1j*gradient[...,0]/(omega*MU0)
    return scalar,electric,magnetic,np.array(frequencies),np.array(g_factors)


def sample_solution(solution):
    # Independent order-10 Duffy rule, different from the order-8 assembly.
    nodes,weights=leggauss(10);nodes=(nodes+1)/2;weights=weights/2
    refs=np.array([[u,(1-u)*v] for u in nodes for v in nodes])
    reference_weights=np.array([wu*wv*(1-u) for u,wu in zip(nodes,weights) for wv in weights])
    points=[];measure=[];electric=[];magnetic=[]
    for cell,element in enumerate(solution.case.domain.elements):
        mapped=element.evaluate(refs)
        fields=solution.all_fields_at_reference(np.full(len(refs),cell),refs)
        points.append(mapped['points_xy_m']);measure.append(reference_weights*mapped['determinant_m2'])
        for field,unit,destination in [('E','V_per_m',electric),('H','A_per_m',magnetic)]:
            destination.append(np.stack([fields[f'{field}{axis}_real_{unit}']+1j*fields[f'{field}{axis}_quadrature_{unit}'] for axis in 'xyz'],axis=1))
    return np.concatenate(points),np.concatenate(measure),np.concatenate(electric),np.concatenate(magnetic)


def check_solution(solution, radius):
    positions,measure,electric,magnetic=sample_solution(solution)
    scalar,reference_e,reference_h,frequencies,g_factors=analytic_fields(positions,radius,solution.case.polarization)
    numerical_scalar=magnetic[:,2,:].real if solution.case.polarization=='te' else electric[:,2,:].real
    material=MU0 if solution.case.polarization=='te' else EPS0
    rf=[planar_curved_quantities(solution,i) for i in range(solution.case.modes)]
    e_energy=EPS0/4*np.einsum('p,pcm,pcm->m',measure,electric.conj(),electric).real
    h_energy=MU0/4*np.einsum('p,pcm,pcm->m',measure,magnetic.conj(),magnetic).real
    independent_energy_error=max(max(abs(e_energy[i]/row['electric_energy_j_per_m']-1),abs(h_energy[i]/row['magnetic_energy_j_per_m']-1)) for i,row in enumerate(rf))
    assert independent_energy_error<=1e-8
    reports=[];index=0
    for n,s,multiplicity,target in groups(solution.case.polarization):
        selection=slice(index,index+multiplicity)
        cross=(numerical_scalar[:,selection]*measure[:,None]).T@scalar[:,selection]*material/2
        u,singular,vt=np.linalg.svd(cross)
        rotation=u@vt
        errors={}
        for name,numerical,reference in [('electric',electric,reference_e),('magnetic',magnetic,reference_h)]:
            aligned=numerical[:,:,selection]@rotation
            difference=aligned-reference[:,:,selection]
            numerator=np.einsum('p,pcm,pcm->',measure,difference.conj(),difference).real
            denominator=np.einsum('p,pcm,pcm->',measure,reference[:,:,selection].conj(),reference[:,:,selection]).real
            errors[name]=float(np.sqrt(numerator/denominator))
        f_error=float(np.max(abs(solution.frequencies_hz[selection]/frequencies[selection]-1)))
        g_error=float(np.max(abs(np.array([row['geometry_factor_ohm'] for row in rf])[selection]/g_factors[selection]-1)))
        gates=dict(frequency=f_error<=1e-4,electric=errors['electric']<=.01,magnetic=errors['magnetic']<=.01,geometry_factor=g_error<=.005)
        reports.append(dict(analytic_group=dict(angular_order=n,positive_root_index=s,multiplicity=multiplicity),
            numerical_ranks_zero_based=list(range(index,index+multiplicity)),target=target,
            frequency_relative_error=f_error,electric_relative_L2_error=errors['electric'],magnetic_relative_L2_error=errors['magnetic'],
            geometry_factor_relative_error=g_error,scalar_alignment_singular_values=singular.tolist(),
            common_scalar_rotation=rotation.tolist(),gates=gates,passed=all(gates.values())))
        index+=multiplicity
    assert index==solution.case.modes
    target_count=5 if solution.case.polarization=='te' else 3
    assert solution.frequencies_hz[target_count]>solution.frequencies_hz[target_count-1]
    return dict(target_groups_passed=all(row['passed'] for row in reports if row['target']),
        full_analytic_guard_groups_present=True,groups=reports,RF=rf,
        independent_field_energy_relative_error=float(independent_energy_error),
        algebraic_residual_max=float(np.max(solution.residuals)),orthogonality_error=solution.orthogonality_error)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--levels',type=int,default=3)
    parser.add_argument('--angular-segments',type=int,default=16)
    parser.add_argument('--extend-from',type=Path,help='reuse unchanged-product evidence and extend only failing final circular groups by one level')
    args=parser.parse_args()
    if args.levels<3 or args.angular_segments<16:
        parser.error('at least three fixed-domain levels and 16 angular segments are required')
    args.out.mkdir(parents=True,exist_ok=False)
    before=_implementation_hashes();started=time.monotonic()
    (args.out/'implementation-before.json').write_text(json.dumps(before,indent=2)+'\n')
    records=[];new_solves=0
    try:
        pending=[]
        if args.extend_from is not None:
            previous=args.extend_from.resolve()
            if before!=json.loads((previous/'implementation-before.json').read_text()):
                raise ValueError('extension requires the exact same production implementation hashes')
            records=json.loads((previous/'progress.json').read_text())
            for row in records:
                label=row['label']
                if Path(label).name!=label:
                    raise ValueError('invalid previous evidence label')
                shutil.copytree(previous/label,args.out/label)
            for radius in (.01,.02):
                for polarization in ('te','tm'):
                    subset=[row for row in records if row['radius_m']==radius and row['polarization']==polarization]
                    if len(subset)<3:
                        raise ValueError('extension requires at least three original levels per radius/polarization')
                    last=max(subset,key=lambda row:row['level'])
                    if last['checks']['target_groups_passed']:
                        continue
                    folder=args.out/last['label']
                    case=PlanarCurvedCase.from_dict(json.loads((folder/'case.json').read_text()))
                    with np.load(folder/'fem-fields.npz',allow_pickle=False) as data:
                        restore_planar_curved_solution(case,data['coefficients'],data['frequencies_hz'])
                    refined=refine_planar_curved_domain(case.domain)
                    pending.append((radius,polarization,last['level']+1,refined.domain,refined,last['fixed_initial_angular_segments']))
            if not pending:
                raise ValueError('all previous circular analytic targets already pass; do not repeat their FEM solves')
        for radius in (.01,.02):
            for polarization in ('te','tm'):
                if args.extend_from is not None:
                    continue
                domain=circle_domain(radius,args.angular_segments)
                domain=type(domain).from_dict(domain.to_dict(),max_geometry_boxes=10000000)
                for level in range(args.levels):
                    refinement=None
                    if level:
                        refinement=refine_planar_curved_domain(domain)
                        domain=refinement.domain
                    pending.append((radius,polarization,level,domain,refinement,args.angular_segments))
        for radius,polarization,level,domain,refinement,angular_segments in pending:
            modes=7 if polarization=='te' else 6
            case=PlanarCurvedCase(domain,polarization,modes=modes,max_geometry_boxes=10000000)
            label=f'{polarization}-r{radius:g}-L{level}'
            folder=args.out/label;folder.mkdir()
            (folder/'case.json').write_text(json.dumps(case.to_dict(),indent=2)+'\n')
            solution=solve_planar_curved(case)
            new_solves+=1
            np.savez_compressed(folder/'fem-fields.npz',coefficients=solution.coefficients,frequencies_hz=solution.frequencies_hz)
            check=check_solution(solution,radius)
            record=dict(label=label,radius_m=radius,polarization=polarization,level=level,
                fixed_initial_angular_segments=angular_segments,cells=len(domain.cell_nodes),dofs=len(domain.points_xy_m),
                geometry=dict(domain.geometry_diagnostics),checks=check,
                restriction_relative_coordinate_bound=0. if refinement is None else refinement.maximum_relative_coordinate_bound)
            if refinement is not None:
                np.savez_compressed(folder/'parent-restriction.npz',parent_cells=refinement.parent_cells,
                    parent_reference_vertices=refinement.parent_reference_vertices,coordinate_error_bounds_m=refinement.coordinate_error_bounds_m)
            (folder/'checks.json').write_text(json.dumps(record,indent=2)+'\n')
            records.append(record)
            (args.out/'progress.json').write_text(json.dumps(records,indent=2)+'\n')
            maxima={key:max(row[key] for row in check['groups'] if row['target']) for key in ['frequency_relative_error','electric_relative_L2_error','magnetic_relative_L2_error','geometry_factor_relative_error']}
            print(f'{label}: {maxima}, all target gates={check["target_groups_passed"]}',flush=True)
        final=[max((row for row in records if row['radius_m']==radius and row['polarization']==polarization),key=lambda row:row['level']) for radius in (.01,.02) for polarization in ('te','tm')]
        assert all(row['checks']['target_groups_passed'] for row in final), 'final circular f/E/H/G gate failed; refine without relaxing tolerances'
        after=_implementation_hashes();assert before==after
        result=dict(passed=True,scope='P07 circular analytic targets, two scales/polarizations and three fixed-domain levels only',
            remaining_P07_evidence=['geometry approximation series','independent internal mesh comparison','last-level FEM E/H/RF differences','quadrature orders','smooth noncircle and reentrant corner'],
            elapsed_s=time.monotonic()-started,product_files_unchanged=len(after),new_FEM_solves=new_solves,evidence_FEM_solutions=len(records),
            extended_from=None if args.extend_from is None else str(args.extend_from.resolve()),records=records)
        (args.out/'implementation-after.json').write_text(json.dumps(after,indent=2)+'\n')
        (args.out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:v for k,v in result.items() if k!='records'},indent=2))
    except Exception:
        (args.out/'failed-evidence.json').write_text(json.dumps(dict(records=records,elapsed_s=time.monotonic()-started),indent=2)+'\n')
        raise


if __name__=='__main__':main()
