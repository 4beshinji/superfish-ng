# SPDX-License-Identifier: Apache-2.0
"""Optional A01 comparison using an unmodified, pinned cavsim2d installation.

Run in the isolated reference environment. The Profile adapter specifies the
same closed PEC polygon; no NG mesh, matrices or fields enter the candidate.
"""
import argparse
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import sys
import time

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng import Case,solve
from superfish_ng.io import save_run
from superfish_ng.sampling import FieldSampler
from superfish_ng.analytic import pillbox_tm010

PIN='48741ff46ca44463281a5ab5945328615881b502'
KEYS=('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm')
LIMITS=dict(zip(KEYS,(1e-4,.005,.005)))
MU=1.25663706127e-6
EPS=1/(MU*299792458.**2)


def source_hashes():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def relative_changes(old,new):
    return {k:abs(new[k]/old[k]-1) for k in KEYS}


def check_domain(boundary_lengths,area,volume,radii,length):
    """Independent exact polygon and solid-of-revolution invariants."""
    left,right=radii
    expected=dict(AXI=length,PEC=left+right+math.hypot(length,right-left))
    if set(boundary_lengths)!=set(expected):
        raise ValueError('comparison requires only AXI and PEC boundaries; requested end conditions were not realized')
    for tag,value in expected.items():
        if not math.isclose(boundary_lengths[tag],value,rel_tol=1e-10,abs_tol=1e-14):
            raise ValueError('boundary length differs from the declared closed PEC polygon')
    if not math.isclose(area,length*(left+right)/2,rel_tol=1e-10,abs_tol=1e-16):
        raise ValueError('meridian area differs')
    if not math.isclose(volume,math.pi*length*(left*left+left*right+right*right)/3,rel_tol=1e-10,abs_tol=1e-16):
        raise ValueError('rotational volume differs')


def candidate_quantities(q):
    """Name the matching peak-phasor convention by formula, not terminology."""
    w=2*math.pi*q['freq [MHz]']*1e6
    rq=(q['Vacc [MV]']*1e6)**2/(w*q['U [J]'])
    if not math.isclose(rq,q['R/Q [Ohm]'],rel_tol=1e-12):
        raise ValueError('candidate R/Q does not match |V|^2/(omega U)')
    return dict(frequency_hz=q['freq [MHz]']*1e6,r_over_q_accelerator_ohm=rq,
                r_over_q_circuit_ohm=rq/2,geometry_factor_ohm=q['G [Ohm]'],
                epk_over_eacc_estimate=q['Epk/Eacc []'],
                bpk_over_eacc_estimate_mt_per_mv_per_m=q['Bpk/Eacc [mT/MV/m]'])


def comparison_passes(rows,analytic=None):
    """Require both convergence sequences, agreement and physical invariants."""
    if len(rows)<3:return False
    if not all(row['physical_checks_passed'] for row in rows):return False
    for row in rows:
        for solver in ('ng','candidate'):
            if any(not math.isfinite(row[solver]['quantities'][k]) or row[solver]['quantities'][k]<=0 for k in KEYS):return False
        if any(not math.isfinite(v) or v<0 for v in row['field_relative_l2'].values()):return False
    for solver in ('ng','candidate'):
        if any(v>LIMITS[k] for k,v in relative_changes(rows[-2][solver]['quantities'],rows[-1][solver]['quantities']).items()):return False
    final=rows[-1]
    if any(v>LIMITS[k] for k,v in relative_changes(final['ng']['quantities'],final['candidate']['quantities']).items()):return False
    if max(final['field_relative_l2'].values())>.005:return False
    if analytic:
        for solver in ('ng','candidate'):
            q=final[solver]['quantities']
            if any(abs(q[k]/analytic[k]-1)>LIMITS[k] for k in KEYS):return False
            for key in ('epk_over_eacc_estimate','bpk_over_eacc_estimate_mt_per_mv_per_m'):
                if abs(q[key]/analytic[key]-1)>.01:return False
    return True


def candidate_run(directory,radii,length,maxh_mm,order,probes):
    import ngsolve as ng
    from cavsim2d import Study
    from cavsim2d.models.base import Cavity
    from cavsim2d.geometry import Profile
    from cavsim2d.solvers.NGSolve.eigen_ngsolve import NGSolveMEVP

    class ClosedProfile(Cavity):
        """Geometry-only public Profile adapter for the comparison specification."""
        def __init__(self):
            super().__init__(n_cells=1)
            self.n_cells=1
            self.kind='a01_closed_profile'
            self.bc=11
            self.parameters=dict(length_m=length,left_radius_m=radii[0],right_radius_m=radii[1])

        def create(self,n_cells=None,beampipe=None,mode=None):
            self.self_dir=str(Path(self.projectDir)/self.name)
            geometry=Path(self.self_dir)/'geometry';geometry.mkdir(parents=True,exist_ok=True)
            self.geo_filepath=None
            self._write_geometry_snapshot()
            (geometry/'a01-profile.json').write_text(json.dumps(dict(parameters=self.parameters,
                coordinate_order='zr',length_unit='m',points_zr_m=self.profile().points,
                boundary_tags=['PEC','PEC','PEC','AXI']),indent=2)+'\n')

        def profile(self):
            a,b=radii;half=length/2
            p=Profile('A01 closed PEC polygon')
            p.start(-half,0).line_to(-half,a,'PEC').line_to(half,b,'PEC')
            return p.line_to(half,0,'PEC').close('AXI')

    cfg=dict(processes=1,rerun=True,boundary_conditions='ee',polarisation='monopole',
             n_modes=1,mode_of_interest=1,mesh_config=dict(h=maxh_mm,p=order),pinvit_maxit=100)
    start=time.perf_counter()
    study=Study(str(directory));cav=ClosedProfile()
    study.add_cavity([cav],['CAVITY']);study.run_eigenmode(cfg)
    seconds=time.perf_counter()-start
    folder=Path(cav.self_dir)/'eigenmode/monopole'
    q=json.loads((folder/'qois.json').read_text());meta=json.loads((folder/'field_meta.json').read_text())
    solver=NGSolveMEVP();electric,magnetic=solver.load_fields(str(folder),0)
    field=electric[0];mesh=field.space.mesh;u,uphi=field.components;hin,hphi=magnetic[0]
    boundaries={name:float(ng.Integrate(1,mesh,definedon=mesh.Boundaries(name),order=12)) for name in set(mesh.GetBoundaries())}
    area=float(ng.Integrate(1,mesh,order=12));volume=float(2*math.pi*ng.Integrate(ng.y,mesh,order=12))
    check_domain(boundaries,area,volume,radii,length)
    e2=ng.y*ng.InnerProduct(u,u)+uphi*ng.Conj(uphi)/ng.y
    h2=ng.y*(ng.InnerProduct(hin,hin)+hphi*ng.Conj(hphi))
    ue=float((math.pi*EPS/2*ng.Integrate(e2,mesh,order=12)).real)
    uh=float((math.pi*MU/2*ng.Integrate(h2,mesh,order=12)).real)
    te_energy=float((math.pi*EPS/2*ng.Integrate(uphi*ng.Conj(uphi)/ng.y,mesh,order=12)).real)
    scale=1/math.sqrt(ue+uh)
    values=[]
    for r,z in probes:
        point=mesh(float(z-length/2),float(r));ez,er=u(point)
        h=np.asarray(hphi(point))
        if h.size!=1:raise ValueError('candidate Hphi must have one azimuthal component')
        values.append([float(er)*scale,float(ez)*scale,float(h.item())*scale])
    energy_difference=abs(ue-uh)/(ue+uh)
    q_energy_difference=abs(q['U [J]']/(ue+uh)-1)
    return dict(quantities=candidate_quantities(q),raw_qois=q,seconds=seconds,
        dofs=int(field.space.ndof),free_dofs=sum(bool(d) for d in field.space.FreeDofs()),
        reported_dofs=q['No of DOFs'],computed_modes=meta['n_modes'],mesh_elements=q['No of Mesh Elements'],
        config=cfg,profile=dict(points_zr_m=[[-length/2,0],[-length/2,radii[0]],[length/2,radii[1]],[length/2,0]],tags=['PEC','PEC','PEC','AXI']),
        boundary_lengths_m=boundaries,area_m2=area,volume_m3=volume,
        energy_balance_relative=energy_difference,reported_energy_relative_difference=q_energy_difference,
        te_electric_energy_fraction=te_energy/ue,field_values=values,
        field_scope='loaded saved candidate field, scaled to total peak-phasor energy 1 J; coordinates translated by L/2',
        physical_checks_passed=energy_difference<1e-6 and q_energy_difference<1e-6 and te_energy/ue<1e-8)


def ng_run(directory,radii,length,nr,probes):
    case=Case(((0.,radii[0]),(length,radii[1])),nr=nr,nz=2*nr,element_order=2,modes=1)
    start=time.perf_counter();solution=solve(case);result=save_run(case,solution,directory);q=result['modes'][0]
    seconds=time.perf_counter()-start
    sampled=FieldSampler.from_solution(solution).evaluate(probes)
    fields=np.column_stack((sampled['Er_quadrature_V_per_m'],sampled['Ez_quadrature_V_per_m'],sampled['Hphi_A_per_m']))
    mesh=solution.mesh;corners=mesh.points[mesh.triangles]
    a=corners[:,1]-corners[:,0];b=corners[:,2]-corners[:,0]
    areas=abs(a[:,0]*b[:,1]-a[:,1]*b[:,0])/2
    lengths=np.linalg.norm(mesh.points[mesh.boundary_edges[:,1]]-mesh.points[mesh.boundary_edges[:,0]],axis=1)
    boundaries={str(tag).upper().replace('AXIS','AXI'):float(sum(lengths[mesh.boundary_tags==tag])) for tag in set(mesh.boundary_tags)}
    area=float(sum(areas));volume=float(2*math.pi*sum(areas*np.mean(corners[:,:,0],axis=1)))
    check_domain(boundaries,area,volume,radii,length)
    return dict(quantities=q,seconds=seconds,dofs=len(solution.u),computed_modes=1,
                field_values=fields.tolist(),relative_eigen_residual=float(max(solution.residuals)),
                boundary_lengths_m=boundaries,area_m2=area,volume_m3=volume)


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--source-manifest',type=Path,required=True)
    p.add_argument('--repetitions',type=int,default=3)
    args=p.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    if args.repetitions<1:raise ValueError('repetitions must be positive')
    manifest=json.loads(args.source_manifest.read_text())
    if manifest['commit']!=PIN:raise ValueError('A01 reference commit differs')
    def reference_unchanged():
        return all(hashlib.sha256((Path(manifest['source_root'])/name).read_bytes()).hexdigest()==digest for name,digest in manifest['files'].items())
    if not reference_unchanged():raise ValueError('reference source hash differs before execution')
    before=source_hashes();start=time.perf_counter()
    import ngsolve as ng
    ng.SetNumThreads(1)
    # Also enforces offline execution after imports; all inputs are local.
    def audit(event,args):
        if event in ('socket.connect','socket.getaddrinfo'):raise RuntimeError('comparison solve must remain offline')
    sys.addaudithook(audit)
    cases={}
    for name,radii,length in (('cylinder',(.1,.1),.08),('frustum',(.08,.1),.12)):
        repeats=[];root=out/name;root.mkdir()
        z=np.repeat(np.array([.17,.39,.61,.83])*length,3)
        r=np.interp(z,[0,length],radii)*np.tile([.2,.5,.8],4)
        probes=np.column_stack((r,z))
        analytic=pillbox_tm010(radii[0],length) if name=='cylinder' else None
        for repetition in range(args.repetitions):
            run=root/f'repeat-{repetition}';run.mkdir();rows=[]
            for level,(nr,h) in enumerate(((12,20.),(24,10.),(48,5.))):
                calls=dict(candidate=lambda:candidate_run(run/f'candidate-{level}',radii,length,h,2,probes),
                           ng=lambda:ng_run(run/f'ng-{level}',radii,length,nr,probes))
                order=['candidate','ng'] if repetition%2==0 else ['ng','candidate']
                results={key:calls[key]() for key in order};native=results['ng'];candidate=results['candidate']
                a=np.asarray(native['field_values']);b=np.asarray(candidate['field_values'])
                sign=1. if np.dot(a[:,2],b[:,2])>=0 else -1.
                # Exact cylinder Er is zero: use the full meridian E norm.
                enorm=max(float(np.linalg.norm(a[:,:2])),np.finfo(float).tiny)
                errors=dict(E=float(np.linalg.norm(a[:,:2]-sign*b[:,:2])/enorm),
                            Hphi=float(np.linalg.norm(a[:,2]-sign*b[:,2])/np.linalg.norm(a[:,2])))
                row=dict(level=level,ng=native,candidate=candidate,field_relative_l2=errors,
                    candidate_global_sign=sign,relative_difference=relative_changes(native['quantities'],candidate['quantities']),
                    physical_checks_passed=candidate['physical_checks_passed'] and native['relative_eigen_residual']<1e-7)
                rows.append(row);(run/f'pair-{level}.json').write_text(json.dumps(row,indent=2,allow_nan=False)+'\n')
                print(name,repetition,level,'differences',row['relative_difference'],'fields',errors,flush=True)
            repeats.append(dict(passed=comparison_passes(rows,analytic),rows=rows))
        cases[name]=dict(passed=all(r['passed'] for r in repeats),repetitions=repeats,analytic=analytic,probes_rz_m=probes.tolist())
    unchanged=before==source_hashes() and reference_unchanged()
    result=dict(passed=unchanged and all(c['passed'] for c in cases.values()),cases=cases,limits=LIMITS,
        seconds=time.perf_counter()-start,source_sha256=before,source_unchanged=unchanged,reference=manifest,
        environment=dict(python=platform.python_version(),platform=platform.platform(),packages={d.metadata['Name']:d.version for d in importlib.metadata.distributions()},
                         OPENBLAS_NUM_THREADS=os.environ.get('OPENBLAS_NUM_THREADS'),ngsolve_threads=1),
        scope='A01: two synthetic exact PEC polygons, fundamental TM, both three-level refinements; candidate geometry-only Profile adapter, unmodified numerical solver and QOI evaluator; all candidate modes/actual product-space DOFs retained; no runtime network')
    (out/'comparison.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('Cavsim2d A01 '+('PASS' if result['passed'] else 'FAIL'),flush=True)
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
