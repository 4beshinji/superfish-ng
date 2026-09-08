# SPDX-License-Identifier: Apache-2.0
"""Galerkin, Ritz and RF invariants of actual locally refined curved spaces."""
import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
from scipy.linalg import eigh
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng import Case
from superfish_ng.constants import C0,MU0,TAU
from superfish_ng.mesh import make_mesh
from superfish_ng.conics import LineSegment
from superfish_ng.curved_contour import CurvedContour
from superfish_ng.mesh_controls import ContourMeshControls
from superfish_ng.curved_space import curved_space
from superfish_ng.curved_marked_refinement import refine_marked_curved_space
from superfish_ng.curved_fem import assemble_curved
from superfish_ng.curved_solution import CurvedSolution
from superfish_ng.curved_rf import quantities_curved
from superfish_ng.analytic import pillbox_tm010


def dense_solution(case,space,matrices):
    k,m=matrices;free=np.setdiff1d(np.arange(k.shape[0]),space.constrained_dofs)
    values,vectors=eigh(k[free][:,free].toarray(),m[free][:,free].toarray(),subset_by_index=(0,case.modes-1))
    assert np.all(values>0)
    u=np.zeros((k.shape[0],case.modes));u[free]=vectors*np.sqrt(case.normalization_j/(MU0*np.pi))
    residuals=[float(np.linalg.norm((k@u[:,i]-values[i]*(m@u[:,i]))[free])/(np.linalg.norm((k@u[:,i])[free])+values[i]*np.linalg.norm((m@u[:,i])[free]))) for i in range(case.modes)]
    orth=float(np.max(abs(MU0*np.pi/case.normalization_j*(u.T@(m@u))-np.eye(case.modes))))
    assert max(residuals)<1e-7 and orth<1e-7
    return CurvedSolution(case,space,k,m,values,C0*np.sqrt(values)/TAU,u,np.asarray(residuals),orth,12,None)


def scaled_case(kind,scale):
    if kind=='cylinder':
        vertices=((0.,0.),(.08,0.),(.08,.1),(0.,.1))
        base=Case((),curved_contour=CurvedContour(tuple(LineSegment(vertices[i],vertices[(i+1)%4]) for i in range(4)),('axis','pec','pec','pec'),0.),
            curve_chord_tolerance_m=.001,contour_mesh=ContourMeshControls(.025),element_order=2,geometry_order=2,modes=2)
    else:base=replace(Case.load(ROOT/f'examples/curved_{kind}.json'),geometry_order=2,modes=2)
    data=base.to_dict();g=data['geometry']
    for curve in g['curves']:
        for key in ('start_zr_m','end_zr_m','center_zr_m','semiaxes_m'):
            if key in curve:curve[key]=[scale*v for v in curve[key]]
    for key in ('chord_tolerance_m','join_tolerance_m','minimum_gap_m'):
        if key in g:g[key]*=scale
    data['mesh']['contour_mesh']['max_edge_m']*=scale;data['rf']['normalization_j']=scale**2
    return Case.from_dict(data)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    before=hashes();checks={};rf_keys=('frequency_hz','stored_energy_j','eacc_v_per_m','r_over_q_accelerator_ohm','geometry_factor_ohm')
    peak_keys=('epk_discrete_lower_bound_v_per_m','epk_discrete_upper_bound_v_per_m','hpk_discrete_lower_bound_a_per_m','hpk_discrete_upper_bound_a_per_m')
    for kind in ('cylinder','ellipse','hyperbola'):
        rows=[]
        for scale in (1.,2.):
            case=scaled_case(kind,scale);parent=curved_space(case,make_mesh(case));g=parent.geometry
            candidates=[i for i,(tag,owner) in enumerate(zip(parent.boundary_tags,g.boundary_curve_indices)) if tag=='pec' and not isinstance(case.curved_contour.curves[int(owner)],LineSegment)]
            edge=g.boundary_nodes[candidates[0] if candidates else int(np.flatnonzero(parent.boundary_tags=='pec')[0]),:2]
            marked=next(i for i,nodes in enumerate(g.cell_nodes) if all(v in nodes[:3] for v in edge))
            result=refine_marked_curved_space(parent,[marked]);p=result.prolongation
            coarse_matrices=assemble_curved(parent,quadrature_order=12);fine_matrices=assemble_curved(result.space,quadrature_order=12)
            galerkin={name:float(np.linalg.norm((p.T@b@p-a).data)/np.linalg.norm(a.data)) for name,a,b in zip(('stiffness','mass'),coarse_matrices,fine_matrices)}
            coarse=dense_solution(case,parent,coarse_matrices);fine=dense_solution(case,result.space,fine_matrices)
            # This field is a restriction of the coarse solution, not a new eigenpair.
            restricted=replace(coarse,space=result.space,stiffness=fine.stiffness,mass=fine.mass,u=p@coarse.u)
            free=np.setdiff1d(np.arange(fine.stiffness.shape[0]),result.space.constrained_dofs)
            restricted.residuals=np.asarray([np.linalg.norm((fine.stiffness@restricted.u[:,i]-coarse.eigenvalues[i]*(fine.mass@restricted.u[:,i]))[free])/(np.linalg.norm((fine.stiffness@restricted.u[:,i])[free])+coarse.eigenvalues[i]*np.linalg.norm((fine.mass@restricted.u[:,i])[free])) for i in range(case.modes)])
            restricted.orthogonality_error=float(np.max(abs(MU0*np.pi/case.normalization_j*(restricted.u.T@(fine.mass@restricted.u))-np.eye(case.modes))))
            a=quantities_curved(coarse,wall_quadrature_order=16);b=quantities_curved(restricted,wall_quadrature_order=16);q=quantities_curved(fine,wall_quadrature_order=16)
            rf_restriction={key:abs(b[key]/a[key]-1) for key in rf_keys}
            peak_restriction={key:abs(b[key]/a[key]-1) for key in peak_keys}
            ritz=(fine.frequencies_hz/coarse.frequencies_hz-1).tolist()
            errors=None
            if kind=='cylinder':
                reference=pillbox_tm010(.1*scale,.08*scale)
                errors={key:abs(q[key]/reference[key]-1) for key in ('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm','epk_over_eacc_estimate','bpk_over_eacc_estimate_mt_per_mv_per_m')}
            passed=(max(galerkin.values())<1e-10 and max(rf_restriction.values())<1e-9 and max(peak_restriction.values())<2e-6 and max(ritz)<2e-9
                and len(g.cell_nodes)<len(result.space.geometry.cell_nodes)<4*len(g.cell_nodes))
            if errors is not None:passed=passed and errors['frequency_hz']<1e-4 and max(errors[k] for k in ('r_over_q_accelerator_ohm','geometry_factor_ohm'))<.005 and max(errors[k] for k in ('epk_over_eacc_estimate','bpk_over_eacc_estimate_mt_per_mv_per_m'))<.01
            name=f'{kind}-s{scale:g}';np.savez_compressed(out/(name+'.npz'),points_rz_m=result.space.geometry.points_rz_m,cell_nodes=result.space.geometry.cell_nodes,
                boundary_nodes=result.space.geometry.boundary_nodes,parent_cells=result.parent_cells,parent_reference_vertices=result.parent_reference_vertices,restricted_coefficients=restricted.u,new_eigenvectors=fine.u)
            rows.append(dict(passed=passed,scale=scale,case=case.to_dict(),marked_cells=[marked],parent_triangles=len(g.cell_nodes),child_triangles=len(result.space.geometry.cell_nodes),quality=dict(result.quality),
                galerkin_relative_errors=galerkin,restricted_field_rf_relative_errors=rf_restriction,restricted_field_peak_endpoint_relative_errors=peak_restriction,
                ritz_frequency_relative_changes=ritz,coarse_rf=a,new_rf=q,new_rf_relative_changes={k:abs(q[k]/a[k]-1) for k in rf_keys},cylinder_analytical_errors=errors,
                eigenpair_residuals=fine.residuals.tolist(),restricted_field_residuals=restricted.residuals.tolist(),evidence_kind='local space and dense FEM eigenproblem; NPZ is research evidence, not a reconstructible native save_run result'))
        keys=('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm','epk_over_eacc_estimate','bpk_over_eacc_estimate_mt_per_mv_per_m')
        similarity={k:abs(rows[1]['new_rf'][k]*(2 if k=='frequency_hz' else 1)/rows[0]['new_rf'][k]-1) for k in keys}
        checks[kind]=dict(passed=all(r['passed'] for r in rows) and max(similarity.values())<2e-8,series=rows,similarity_relative_errors=similarity)
    unchanged=before==hashes();passed=unchanged and all(c['passed'] for c in checks.values())
    (out/'validation.json').write_text(json.dumps(dict(passed=passed,checks=checks,source_sha256=before,source_changed_during_run=not unchanged,
        scope='local quadratic restriction, Galerkin and Ritz invariants, RF preservation of restricted fields, new dense FEM eigenpairs, cylinder reference and Maxwell scaling; no general physical convergence or adaptive stopping acceptance'),indent=2,allow_nan=False)+'\n')
    print(f'Curved marked refinement {"PASS" if passed else "FAIL"}: {out}');return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
