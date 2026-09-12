# SPDX-License-Identifier: Apache-2.0
"""Material Hphi workspace, one-sided fields, region measures and independent sweeps."""
import argparse,hashlib,json,os,subprocess,sys,threading,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.validate_material_hphi_forms import make_partition
from superfish_ng.rf_materials import RFMaterialPartition,LinearRFMaterial
from superfish_ng.material_hphi import MaterialHphiCase
from superfish_ng.constants import MU0
from superfish_ng.axis_hphi import AxisAccelerationPath
from superfish_ng.hphi_project import HphiProject
from superfish_ng.hphi_study import HphiStudy
from superfish_ng.hphi_native import read_hphi_run,hphi_result
from superfish_ng.hphi_display import display_hphi_fields
from superfish_ng.hphi_jobs import _native_hashes
from superfish_ng.jobs import JobManager
from superfish_ng.gui_hphi import hphi_response


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples')
            for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def example(axis,holes,order):
    p,_=make_partition(axis,holes,1,1.)
    if axis:p=RFMaterialPartition(p.mesh,[LinearRFMaterial('material-0',1.,1.),p.materials[1]],p.regions)
    mesh=p.mesh;cut=1/16;moments=np.zeros((2,2))
    for region,(low,high) in enumerate(((mesh.points_rz_m[:,1].min(),cut),(cut,mesh.points_rz_m[:,1].max()))):
        for polygon,sign in [(mesh.outer_rz_m,1),*((h,-1) for h in mesh.holes_rz_m)]:
            a,z0=polygon.min(axis=0);b,z1=polygon.max(axis=0);height=max(0.,min(z1,high)-max(z0,low))
            moments[region]+=sign*height*np.array([b-a,(b*b-a*a)/2])
    case=MaterialHphiCase(p,element_order=order,modes=2,
        acceleration=AxisAccelerationPath(.01,.06,.8,.02) if axis else None,name=f'material axis={axis} holes={holes} P{order}')
    return HphiProject(case,'mm'),moments


def displayed_moments(samples,partition):
    vertices=samples['points_rz_m'][samples['triangles']];a=vertices[:,1]-vertices[:,0];b=vertices[:,2]-vertices[:,0]
    areas=(a[:,0]*b[:,1]-a[:,1]*b[:,0])/2;owners=partition.cell_region_indices[samples['parent_cells']]
    return np.column_stack((np.bincount(owners,weights=areas,minlength=len(partition.regions)),
        np.bincount(owners,weights=areas*vertices[:,:,0].mean(axis=1),minlength=len(partition.regions))))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();start=time.monotonic()
    env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),OPENBLAS_NUM_THREADS='1')
    commands=[];records=[];native={};sources={};maximum_moment=maximum_scale=0.;restarts=0;study_workers=0
    def cli(command):
        result=subprocess.run([sys.executable,'-m','superfish_ng',*map(str,command)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=120)
        (out/f'cli-{len(commands):03d}.log').write_text(result.stdout+result.stderr)
        commands.append(dict(arguments=list(map(str,command)),returncode=result.returncode));assert result.returncode==0,result.stderr
        return result.stdout
    lock=threading.Lock();manager=JobManager(out/'jobs')
    def request(action,**data):return hphi_response(manager,action,data,lock,out/'cache')[0]
    try:
        cancelled=manager.start_hphi(example(True,1,2)[0]);assert manager.cancel(cancelled)['status']=='cancelled'
        for axis in (False,True):
            for holes in (0,1,2):
                for order in (1,2):
                    name=f'axis-{int(axis)}-holes-{holes}-p-{order}';project,moments=example(axis,holes,order)
                    project_file=out/f'{name}.project.json';project.save(project_file);sources[project_file.name]=hashlib.sha256(project_file.read_bytes()).hexdigest()
                    assert request('hphi-normalize',document=project.dumps())==project.to_dict()
                    identifier=request('hphi-start',document=project.to_dict())['id'];assert manager.processes[identifier].wait(timeout=120)==0
                    result=request('hphi-result',id=identifier);run=manager.directory(identifier)/'solution'
                    solution=read_hphi_run(run);assert hphi_result(solution)==result['result'];assert result['project']==project.to_dict()
                    samples=display_hphi_fields(solution);display_moments=displayed_moments(samples,solution.case.partition)
                    difference=float(np.max(abs(display_moments/moments-1)));assert difference<1e-12;maximum_moment=max(maximum_moment,difference)
                    fields=solution.fields_in_cells(samples['parent_cells'],samples['barycentric'])
                    for key in fields:np.testing.assert_array_equal(samples['fields'][key],fields[key])
                    np.testing.assert_array_equal(samples['fields']['Bphi_real_T'],MU0*solution.case.partition.mu_r[samples['parent_cells']]*fields['Hphi_real_A_per_m'])
                    cli_run=out/'cli-projects'/name;cli(['execute-hphi-project',project_file,'--out',cli_run]);assert _native_hashes(cli_run/'solution')==_native_hashes(run)
                    png=out/f'{name}.png';cli(['plot-hphi',run,'--out',png,'--mesh','--length-unit','mm'])
                    assert png.read_bytes()==request('hphi-plot',id=identifier,mode=1,mesh=True,length_unit='mm')
                    meta=json.loads(png.with_suffix('.png.json').read_text());assert meta['material_field_policy']=='epsilon_r/mu_r from each original cell; no interface averaging'
                    cells=np.array([0,len(solution.space.cell_dofs)-1]);points=np.einsum('ci,cij->cj',np.tile([.2,.3,.5],(2,1)),solution.case.partition.mesh.points_rz_m[solution.case.partition.mesh.triangles[cells]]).tolist()
                    points.append(solution.case.partition.mesh.points_rz_m[solution.case.partition.interface_edges[0]].mean(axis=0).tolist())
                    if axis:points.append([0.,.1])
                    points_file=out/f'{name}.points.json';points_file.write_text(json.dumps(points)+'\n')
                    csv=out/f'{name}.csv';cli(['probe-hphi-csv',run,'--points',points_file,'--out',csv])
                    assert csv.read_bytes()==request('hphi-probe',id=identifier,mode=1,points_rz_m=points)
                    assert json.loads(csv.with_suffix('.csv.json').read_text())==request('hphi-probe-metadata',id=identifier,mode=1,points_rz_m=points)
                    probe=solution.probe_at(points);metadata=json.loads(csv.with_suffix('.csv.json').read_text())
                    for key in ('cell_indices','region_ids','material_ids','epsilon_r','mu_r','barycentric','interface_policy'):assert metadata['material_samples'][key]==probe[key]
                    assert len(csv.read_text().splitlines()[0].split(','))==25
                    imports=[manager.import_hphi_result(run),manager.import_hphi_result(manager.directory(identifier))]
                    for imported in imports:assert _native_hashes(manager.directory(imported)/'solution')==_native_hashes(run)
                    study=HphiStudy(project,'uniform_scale',[1.,2.]);study_id=request('hphi-start-study',document=study.to_dict())['id'];study_workers+=1
                    assert manager.processes[study_id].wait(timeout=120)==0
                    study_result=request('hphi-study-result',id=study_id)['result'];assert study_result['mode_tracking']=='not_performed'
                    for a,b in zip(*(p['modes'] for p in study_result['points'])):
                        for key,ratio in dict(frequency_hz=.5,stored_energy_j=1.,wall_loss_w=2**-1.5,q0=2**.5,geometry_factor_ohm=1.).items():
                            difference=abs(b[key]/a[key]/ratio-1);assert difference<1e-9;maximum_scale=max(maximum_scale,difference)
                        if axis:
                            for key in ('r_over_q_accelerator_ohm','r_over_q_circuit_ohm'):assert abs(b[key]/a[key]-1)<1e-9
                    point=request('hphi-study-point',id=study_id,index=1)['id'];assert request('hphi-result',id=point)['project']==study.projects()[1].to_dict()
                    manager.close();moved=out/'moved-originals'/identifier;moved.parent.mkdir(exist_ok=True);(out/'jobs'/identifier).rename(moved)
                    manager=JobManager(out/'jobs');restarts+=1
                    for imported in imports:assert manager.status(imported,verify=True)['status']=='complete'
                    assert png.read_bytes()==request('hphi-plot',id=imports[1],mode=1,mesh=True,length_unit='mm')
                    assert csv.read_bytes()==request('hphi-probe',id=imports[1],mode=1,points_rz_m=points)
                    for directory in (moved/'solution',cli_run/'solution',*(manager.directory(i)/'solution' for i in imports),manager.directory(point)/'solution'):
                        native.update({str((directory/key).relative_to(out)):value for key,value in _native_hashes(directory).items()})
                    records.append(dict(name=name,project_worker=identifier,imports=imports,study_worker=study_id,study_point=point,display_samples=len(samples['triangles']),display_moment_difference=maximum_moment))
                print('DONE',axis,holes,flush=True)
        assert manager.status(cancelled)['status']=='cancelled'
    finally:manager.close()
    for path,digest in native.items():assert hashlib.sha256((out/path).read_bytes()).hexdigest()==digest
    for path,digest in sources.items():assert hashlib.sha256((out/path).read_bytes()).hexdigest()==digest
    assert fingerprints()==before
    report=dict(status='PASS',cases=len(records),project_workers=len(records),study_workers=study_workers,study_fem_points=2*study_workers,
        owned_imports=2*len(records),restarts=restarts,cancelled=1,native_files_unchanged=len(native),project_files_unchanged=len(sources),
        maximum_display_moment_relative_difference=maximum_moment,maximum_scale_relative_difference=maximum_scale,
        display_geometry='original display triangles retain material partition; per-region area/radial moment match independently clipped rectangles minus all holes',
        png_csv='byte-identical GUI/CLI and after source relocation and manager restart',records=records,cli_commands=commands,
        source_sha256=before,seconds=time.monotonic()-start)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('records','cli_commands','source_sha256')})


if __name__=='__main__':main()
