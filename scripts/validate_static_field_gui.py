# SPDX-License-Identifier: Apache-2.0
"""Verify GUI Project/worker/field transport against accepted original static FEM runs."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.validate_static_field_project import fingerprints
from superfish_ng.static_field_project import StaticFieldProject
from superfish_ng.static_field_jobs import read_static_field_job
from superfish_ng.gui_static_fields import StaticFieldAccess, static_field_response
from superfish_ng.jobs import JobManager


def units(name):
    for suffix,unit in [('_V_per_m','V/m'),('_C_per_m2','C/m²'),('_Wb_per_m','Wb/m'),('_A_per_m','A/m'),('_T','T'),('_Wb','Wb'),('_V','V')]:
        if name.endswith(suffix):return unit
    raise AssertionError(('unknown independent static field unit',name))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();reference=args.reference.resolve();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    reference_report=json.loads((reference/'report.json').read_text());assert reference_report['status']=='PASS' and reference_report['cases']==42
    before=fingerprints();started=time.monotonic();sources=sorted(reference.glob('*/api'));assert len(sources)==42
    original_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for source in sources for p in source.rglob('*') if p.is_file()}
    workspace=out/'workspace';manager=JobManager(workspace);access=StaticFieldAccess(manager);records=[];browser_cases=[];owned={};downloads=0
    def call(action,**data):return static_field_response(manager,access,action,data)[0]
    def ready(identifier):
        end=time.monotonic()+180
        while time.monotonic()<end:
            result=call('static-field-result',id=identifier)
            if result['status']=='ready':return result
            assert result['status'] in ('queued','running','verifying') or result['status']=='failed' and result.get('state',{}).get('outcome_saved'),result
            time.sleep(.025)
        raise AssertionError(('GUI async timeout',identifier))
    try:
        for index,source in enumerate(sources):
            original=read_static_field_job(source);project=StaticFieldProject.from_dict(original['project']);failed=original['status']=='nonlinear_failed'
            raw=(source/'project.json').read_text()
            assert call('static-project-validate',document=raw,display_length_unit=None)==original['project']
            assert call('static-project-download',document=raw,display_length_unit=None)==raw.encode()
            for unit in ('m','mm'):
                changed=call('static-project-validate',document=raw,display_length_unit=unit)
                assert changed['case']==original['project']['case'] and changed['display_length_unit']==unit
            identifier=call('static-project-solve',document=raw,display_length_unit=None)['id']
            result=ready(identifier);manager.processes[identifier].wait(timeout=10);view=result['view'];target=manager.directory(identifier)
            assert view['project']==original['project'] and view['outcome']==original['outcome'] and view['solver_status']==original['status']
            assert read_static_field_job(target)==original
            assert (target/'project.json').read_bytes()==raw.encode()
            native={p.name:p.read_bytes() for p in (source/'solution').iterdir()}
            assert {p.name:p.read_bytes() for p in (target/'solution').iterdir()}==native
            if failed:
                assert view['plot'] is None and len(result['files'])==4
            else:
                name=type(project.case).__module__.rsplit('.',1)[-1];saved=importlib.import_module('superfish_ng.'+name+'_saved')
                solution=getattr(saved,'read_'+name+'_run')(source/'solution');mesh=project.case.partition.mesh
                points=getattr(mesh,'points_xy_m',None);planar=points is not None
                if points is None:points=mesh.points_rz_m
                probe=solution.probe_at(points[mesh.triangles].mean(axis=1));plot=view['plot']
                assert plot['cell_center_probe']==probe
                assert plot['points_m']==points.tolist() and plot['triangles']==mesh.triangles.tolist() and plot['boundary_edges']==mesh.boundary_edges.tolist()
                assert plot['field_units']=={field:units(field) for field in probe['fields']}
                assert plot['coordinate_labels']==(['x','y'] if planar else ['r','z'])
                assert view['measure']==('per_unit_length' if planar else 'full_axisymmetric_domain') and len(result['files'])==6
            assert view['not_applicable']==['RF frequency','R/Q (circuit)','R/Q (accelerator)','RF mode index']
            for name in result['files']:
                assert call('static-field-download',id=identifier,file=name)==(source/name).read_bytes();downloads+=1
            for path in [target/'project.json',target/'manifest.json',target/'job.json',*(target/'solution').iterdir()]:owned[str(path.relative_to(out))]=hashlib.sha256(path.read_bytes()).hexdigest()
            expected=out/(source.parent.name+'-view.json');expected.write_text(json.dumps(view,indent=2)+'\n')
            browser_cases.append(dict(name=source.parent.name,source_job=str(source),project_file=str(source/'project.json'),expected_view_file=str(expected),failed=failed))
            records.append(dict(name=source.parent.name,id=identifier,failed=failed,view=view,files=result['files']))
            print('DONE',index,source.parent.name,'failure' if failed else 'original fields',flush=True)
    finally:access.close();manager.close()
    assert downloads==234
    manager=JobManager(workspace);access=StaticFieldAccess(manager);restart_downloads=0
    try:
        for source,record in zip(sources,records):
            result=ready(record['id']);assert result['view']==record['view'] and result['files']==record['files']
            for name in result['files']:
                assert call('static-field-download',id=record['id'],file=name)==(source/name).read_bytes();restart_downloads+=1
    finally:access.close();manager.close()
    for path,digest in original_hashes.items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
    for path,digest in owned.items():assert hashlib.sha256((out/path).read_bytes()).hexdigest()==digest
    assert fingerprints()==before and restart_downloads==234 and len(original_hashes)==360 and len(owned)==318
    (out/'cases.json').write_text(json.dumps(browser_cases,indent=2)+'\n')
    from superfish_ng.config import Case
    from superfish_ng.project import Project
    Project(Case(profile=((0.,.1),(.12,.1)),nr=8,nz=10,modes=2,element_order=2)).save(out/'rf-project.json')
    from scripts.axis_bh_reference import current_cylinder
    StaticFieldProject(current_cylinder(n=16,quadrature_order=32)[0],'mm').save(out/'cancel-project.json')
    report=dict(status='PASS',cases=42,successful_cases=33,actual_nonlinear_failure_cases=9,case_families=11,
        real_gui_workers=42,initial_async_replays=42,restart_async_replays=42,initial_downloads=downloads,restart_downloads=restart_downloads,
        original_files_unchanged=len(original_hashes),owned_files_unchanged=len(owned),source_sha256=before,
        records=[{k:v for k,v in row.items() if k not in ('view','files')} for row in records],seconds=time.monotonic()-started,
        interpretation='GUI transport preserves the accepted original static Project, all actual FEM quantities and nonlinear failure histories, original cell-center samples and SI units. Local browser rendering, target-version compatibility and static Study require separate evidence.')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('records','source_sha256')})


if __name__=='__main__':main()
