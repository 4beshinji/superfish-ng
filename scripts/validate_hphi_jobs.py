# SPDX-License-Identifier: Apache-2.0
"""Actual Hphi workers/imports, unchanged native bytes and SI similarity laws.

This validates the workflow with modest meshes. Discretization accuracy is
covered separately by validate_coaxial.py and validate_hphi_mesh.py.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from hphi_mesh_reference import rectangular_holes
from superfish_ng.coaxial import CoaxialCase
from superfish_ng.hphi_mesh import HphiMeshCase
from superfish_ng.meridional_mesh import MeridionalMesh
from superfish_ng.hphi_project import HphiProject
from superfish_ng.hphi_native import read_hphi_run,hphi_result
from superfish_ng.jobs import JobManager


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def native_hashes(path):return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in path.iterdir()}


def wait(manager,identifier):
    deadline=time.monotonic()+120
    while True:
        state=manager.status(identifier)
        if state['status'] not in ('queued','running'):break
        if time.monotonic()>deadline:raise TimeoutError(f'worker {identifier} still live or queued; preserve it for inspection')
        time.sleep(.1)
    assert state['status']=='complete',state
    return manager.status(identifier,verify=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    before=fingerprints();start=time.monotonic();records=[];manager=JobManager(out/'workspace')
    try:
        for geometry in ('coaxial','holes'):
            for order in (1,2):
                for scale in (1.,2.):
                    case=(CoaxialCase(.025*scale,.05*scale,.18*scale,nr=4,nz=12,element_order=order,modes=3,normalization_j=scale**3)
                          if geometry=='coaxial' else HphiMeshCase(MeridionalMesh(**rectangular_holes(3,2,scale)),element_order=order,modes=9,normalization_j=scale**3))
                    project=HphiProject(case,'m');identifier=manager.start_hphi(project);state=wait(manager,identifier)
                    assert state['numerical_validation']=='not_checked' and state['case_format']==case.to_dict()['format']
                    native=manager.directory(identifier)/'solution';hashes=native_hashes(native)
                    solution=read_hphi_run(native);result=hphi_result(solution)
                    assert solution.case.to_dict()==case.to_dict()
                    assert HphiProject.load(manager.directory(identifier)/'project.json')==project
                    for row in result['modes']:
                        assert abs(row['stored_energy_j']/scale**3-1)<1e-8
                        assert row['r_over_q_accelerator_ohm'] is None and row['r_over_q_circuit_ohm'] is None
                        assert abs(row['electric_energy_j']/row['magnetic_energy_j']-1)<1e-8
                    points=solution.space.mesh.points[solution.space.mesh.triangles].mean(axis=1)[::max(1,len(solution.space.mesh.triangles)//15)]
                    fields={k:v.tolist() for k,v in solution.fields_at(points,0).items()}
                    direct=manager.import_hphi_result(native);managed=manager.import_hphi_result(manager.directory(identifier))
                    for imported in (direct,managed):
                        assert manager.status(imported,verify=True)['origin']=='imported'
                        assert native_hashes(manager.directory(imported)/'solution')==hashes
                    manager.close();manager=JobManager(out/'workspace')
                    for job in (identifier,direct,managed):assert manager.status(job,verify=True)['status']=='complete'
                    assert native_hashes(native)==hashes
                    record=dict(geometry=geometry,order=order,scale=scale,job=identifier,imports=[direct,managed],
                                quantities=result['modes'],probe_points_rz_m=points.tolist(),fields=fields,native_sha256=hashes)
                    records.append(record);(out/'progress.json').write_text(json.dumps(dict(records=records),indent=2)+'\n')
                    print('PASS worker/import/restart',geometry,order,scale,flush=True)
    finally:manager.close()
    errors=[]
    for first in [r for r in records if r['scale']==1]:
        second=next(r for r in records if r['geometry']==first['geometry'] and r['order']==first['order'] and r['scale']==2)
        for a,b in zip(first['quantities'],second['quantities']):
            for key,factor in dict(frequency_hz=.5,stored_energy_j=8.,geometry_factor_ohm=1.,q0=np.sqrt(2),wall_loss_w=2**1.5,volume_m3=8.).items():
                errors.append(abs(b[key]/(a[key]*factor)-1))
        np.testing.assert_allclose(second['probe_points_rz_m'],2*np.array(first['probe_points_rz_m']),rtol=1e-13,atol=0)
        h0=np.array(first['fields']['Hphi_real_A_per_m']);h1=np.array(second['fields']['Hphi_real_A_per_m'])
        sign=1 if h0@h1>=0 else -1
        for family in ('E','H'):
            a=np.column_stack([v for k,v in first['fields'].items() if k.startswith(family)])
            b=np.column_stack([v for k,v in second['fields'].items() if k.startswith(family)])
            errors.append(np.linalg.norm(sign*b-a)/np.linalg.norm(a))
    assert max(errors)<1e-8
    after=fingerprints();assert before==after
    report=dict(status='PASS',workers=8,imports=16,restarted_complete_jobs=24,records=records,
                max_similarity_relative_error=float(max(errors)),source_sha256=after,seconds=time.monotonic()-start,
                scope='native/job operation and SI similarity; not a new discretization-accuracy claim')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS Hphi jobs',flush=True)


if __name__=='__main__':main()
