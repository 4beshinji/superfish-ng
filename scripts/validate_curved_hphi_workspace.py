# SPDX-License-Identifier: Apache-2.0
"""Curved Hphi workspace, exact display boundaries and independent sweep laws."""
import argparse,hashlib,json,os,subprocess,sys,threading,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.curved_meridional_reference import fixture
from superfish_ng.curved_meridional_geometry import CurvedMeridionalGeometry
from superfish_ng.curved_hphi import CurvedHphiCase
from superfish_ng.axis_hphi import AxisAccelerationPath
from superfish_ng.hphi_project import HphiProject
from superfish_ng.hphi_study import HphiStudy
from superfish_ng.hphi_native import read_hphi_run,hphi_result
from superfish_ng.hphi_display import display_hphi_fields
from superfish_ng.curved_hphi_display import _triangle_path
from superfish_ng.hphi_jobs import _native_hashes
from superfish_ng.jobs import JobManager
from superfish_ng.gui_hphi import hphi_response


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples')
            for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def example(axis,holes,order):
    data,_=fixture(axis,holes,shear=0.);base=data['base_mesh'];raw=base.to_dict()
    def mapped(points):
        r,z=np.asarray(points).T
        return np.column_stack((r+2*r*r,z-r*r))
    # Independent rectangle moments: R=r+2r² and Z=z-r² preserve z thickness.
    area=moment=0.
    for polygon,sign in [(base.outer_rz_m,1),*((p,-1) for p in base.holes_rz_m)]:
        a,z0=polygon.min(axis=0);b,z1=polygon.max(axis=0);a+=2*a*a;b+=2*b*b
        area+=sign*(b-a)*(z1-z0);moment+=sign*(b*b-a*a)*(z1-z0)/2
    for key in ('outer_rz_m','points_rz_m'):raw[key]=mapped(raw[key]).tolist()
    raw['holes_rz_m']=[mapped(h).tolist() for h in raw['holes_rz_m']]
    data['base_mesh']=type(base).from_dict(raw);data['edge_midpoints_rz_m']=mapped(data['edge_midpoints_rz_m'])
    case=CurvedHphiCase(CurvedMeridionalGeometry(**data),element_order=order,modes=2,
        acceleration=AxisAccelerationPath(.01,.16,.8,.02) if axis else None,name=f'curved axis={axis} holes={holes} P{order}')
    return HphiProject(case,'mm'),np.array([area,moment])


def displayed_moments(samples):
    # Integrate the actual Matplotlib Bezier paths: ∮r dz and 1/2 ∮r² dz.
    nodes,weights=np.polynomial.legendre.leggauss(8);t=(nodes+1)/2;weights=weights/2
    vertices=np.array([_triangle_path(p,1.).vertices for p in samples['quadratic_points_rz_m']])
    totals=np.zeros(2)
    for a,c,b in ((0,1,2),(2,3,4),(4,5,6)):
        start,control,end=(vertices[:,i] for i in (a,c,b))
        points=(1-t)[None,:,None]**2*start[:,None]+2*(t*(1-t))[None,:,None]*control[:,None]+t[None,:,None]**2*end[:,None]
        derivative=2*((1-t)[None,:,None]*(control-start)[:,None]+t[None,:,None]*(end-control)[:,None])
        totals[0]+=float(np.sum(points[:,:,1]*derivative[:,:,0]*weights))
        totals[1]+=float(np.sum(.5*points[:,:,1]**2*derivative[:,:,0]*weights))
    return totals


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
                    samples=display_hphi_fields(solution);display_moments=displayed_moments(samples)
                    difference=float(np.max(abs(display_moments/moments-1)));assert difference<1e-12;maximum_moment=max(maximum_moment,difference)
                    fields=solution.fields_in_cells(samples['parent_cells'],samples['barycentric'])
                    for key in fields:np.testing.assert_array_equal(samples['fields'][key],fields[key])
                    cli_run=out/'cli-projects'/name;cli(['execute-hphi-project',project_file,'--out',cli_run]);assert _native_hashes(cli_run/'solution')==_native_hashes(run)
                    png=out/f'{name}.png';cli(['plot-hphi',run,'--out',png,'--mesh','--length-unit','mm'])
                    assert png.read_bytes()==request('hphi-plot',id=identifier,mode=1,mesh=True,length_unit='mm')
                    meta=json.loads(png.with_suffix('.png.json').read_text());assert meta['display_geometry']=='exact quadratic polynomial subtriangle boundaries'
                    cells=np.array([0,len(solution.space.cell_dofs)-1]);points=solution.mapped_points(cells,np.tile([.2,.3,.5],(2,1)))[0].tolist()
                    if axis:points.append([0.,.1])
                    points_file=out/f'{name}.points.json';points_file.write_text(json.dumps(points)+'\n')
                    csv=out/f'{name}.csv';cli(['probe-hphi-csv',run,'--points',points_file,'--out',csv])
                    assert csv.read_bytes()==request('hphi-probe',id=identifier,mode=1,points_rz_m=points)
                    assert json.loads(csv.with_suffix('.csv.json').read_text())==request('hphi-probe-metadata',id=identifier,mode=1,points_rz_m=points)
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
        display_geometry='Bezier path area and radial moment equal independent transformed rectangles minus all holes',
        png_csv='byte-identical GUI/CLI and after source relocation and manager restart',records=records,cli_commands=commands,
        source_sha256=before,seconds=time.monotonic()-start)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('records','cli_commands','source_sha256')})


if __name__=='__main__':main()
