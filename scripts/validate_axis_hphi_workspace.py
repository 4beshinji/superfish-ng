# SPDX-License-Identifier: Apache-2.0
"""Actual axis-Hphi workers, imports, Study similarity and unchanged native ownership."""
import argparse,hashlib,json,subprocess,sys,time
from contextlib import ExitStack
from dataclasses import replace
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from axis_hphi_reference import rectangular_axis_holes
from superfish_ng.axis_connected_mesh import AxisConnectedMesh
from superfish_ng.axis_hphi import AxisHphiCase,AxisAccelerationPath
from superfish_ng.hphi_project import HphiProject
from superfish_ng.hphi_study import HphiStudy
from superfish_ng.hphi_study_jobs import read_hphi_study
from superfish_ng.hphi_native import read_hphi_run,hphi_result
from superfish_ng.jobs import JobManager,read_job


def hashes(directory):return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.iterdir() if p.is_file()}
def fingerprints():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(exist_ok=False,parents=True);before=fingerprints();started=time.monotonic();records=[];errors=[];preserved={};cli=[]
    with ExitStack() as cleanup:
        manager=JobManager(out/'workspace');cleanup.callback(manager.close)
        for holes in (1,2):
            for order in (1,2):
                case=AxisHphiCase(AxisConnectedMesh(**rectangular_axis_holes(2,holes)),element_order=order,modes=2,
                    acceleration=AxisAccelerationPath(.01,.05,.75,.004))
                project=HphiProject(case);job=manager.start_hphi(project)
                assert manager.processes[job].wait(timeout=60)==0;assert manager.status(job,verify=True)['status']=='complete'
                source=manager.directory(job)/'solution';preserved[str(source)]=hashes(source)
                for origin in (source,manager.directory(job)):
                    imported=manager.import_hphi_result(origin)
                    assert hashes(manager.directory(imported)/'solution')==hashes(source)
                path=out/f'project-h{holes}-p{order}.json';project.save(path)
                points=out/f'points-h{holes}-p{order}.json';points.write_text('[[0,0.01],[0.1,0.02]]\n')
                for command in (['plot-hphi',str(source),'--out',str(out/f'h{holes}-p{order}.png')],
                    ['probe-hphi-csv',str(source),'--out',str(out/f'h{holes}-p{order}.csv'),'--points',str(points)]):
                    done=subprocess.run([sys.executable,'-m','superfish_ng',*command],capture_output=True,text=True)
                    assert done.returncode==0,done.stderr;cli.append(command)
                for parameter,values in (('uniform_scale',[1,2]),('/case/rf/stored_energy_j',[1,8]),('/case/rf/conductivity_s_per_m',[5.8e7,2.32e8])):
                    study=HphiStudy(project,parameter,values);identifier=manager.start_hphi_study(study)
                    assert manager.processes[identifier].wait(timeout=90)==0
                    directory=manager.directory(identifier);result=read_hphi_study(directory)
                    assert result['mode_tracking']=='not_performed' and result['numerical_validation']=='not_checked'
                    runs=[directory/point['directory']/'solution' for point in result['points']]
                    solutions=[read_hphi_run(run) for run in runs]
                    for run in runs:
                        preserved[str(run)]=hashes(run);owned=manager.import_hphi_result(run)
                        assert hashes(manager.directory(owned)/'solution')==hashes(run)
                    factors=dict(frequency_hz=1.,stored_energy_j=1.,wall_loss_w=1.,q0=1.,geometry_factor_ohm=1.,r_over_q_accelerator_ohm=1.,r_over_q_circuit_ohm=1.)
                    amplitude=1.;voltage_factor=1.
                    if parameter=='uniform_scale':factors.update(frequency_hz=.5,wall_loss_w=2**-1.5,q0=2**.5);amplitude=2**-1.5;voltage_factor=2**-.5
                    elif parameter.endswith('stored_energy_j'):factors.update(stored_energy_j=8.,wall_loss_w=8.);amplitude=8**.5;voltage_factor=8**.5
                    else:factors.update(wall_loss_w=.5,q0=2.)
                    for mode in range(case.modes):
                        a,b=(hphi_result(solution)['modes'][mode] for solution in solutions)
                        for key,factor in factors.items():errors.append(float(abs(b[key]/(a[key]*factor)-1)))
                        ca,cb=(solution.coefficients[:,mode] for solution in solutions);sign=1 if ca@cb>=0 else -1
                        va,vb=(complex(q['vacc_v']['real'],q['vacc_v']['imag']) for q in (a,b));errors.append(float(abs(sign*vb/(va*voltage_factor)-1)))
                        cells=np.arange(len(solutions[0].space.mesh.triangles));bary=np.full((len(cells),3),1/3)
                        fa,fb=(s.fields_in_cells(cells,bary,mode) for s in solutions)
                        for key in fa:
                            denominator=np.linalg.norm(fa[key])*amplitude
                            if denominator:errors.append(float(np.linalg.norm(sign*fb[key]-fa[key]*amplitude)/denominator))
                            else:assert np.array_equal(fa[key],fb[key])
                    records.append(dict(holes=holes,order=order,parameter=parameter,job=identifier,points=len(runs)))
                    (out/'progress.json').write_text(json.dumps(dict(records=records,max_similarity_error=max(errors)),indent=2)+'\n')
                    print('DONE',holes,order,parameter,max(errors),flush=True)
        manager.close();manager=JobManager(out/'workspace');cleanup.callback(manager.close)
        states=manager.list();assert len(states)==48 and all(state['status']=='complete' for state in states)
        for state in states:assert read_job(manager.directory(state['id']))['status']=='complete'
        assert all(hashes(Path(path))==expected for path,expected in preserved.items());assert max(errors)<1e-8
    after=fingerprints();assert after==before
    (out/'report.json').write_text(json.dumps(dict(status='PASS',scope='wrapper/state/physical similarity; analytical FEM accuracy is verified separately by validate_axis_hphi',
        project_workers=4,study_workers=12,fem_points=28,restarted_jobs=48,cli_commands=cli,records=records,
        original_native_sha256=preserved,max_similarity_error=max(errors),source_sha256=after,seconds=time.monotonic()-started),indent=2)+'\n')


if __name__=='__main__':main()
