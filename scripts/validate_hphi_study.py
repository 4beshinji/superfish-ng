# SPDX-License-Identifier: Apache-2.0
"""Independent Hphi Study workers, native replay, SI laws and cylinder dimension checks."""
import argparse,hashlib,json,subprocess,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng.coaxial import CoaxialCase
from superfish_ng.hphi_mesh import HphiMeshCase
from superfish_ng.meridional_mesh import MeridionalMesh
from superfish_ng.hphi_project import HphiProject
from superfish_ng.hphi_study import HphiStudy
from superfish_ng.hphi_native import read_hphi_run
from superfish_ng.hphi_study_jobs import read_hphi_study
from superfish_ng.jobs import JobManager
from superfish_ng.constants import C0
from hphi_mesh_reference import rectangular_holes
from validate_coaxial import reference


def fingerprints():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
def hashes(directory):return {str(p.relative_to(directory)):hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.glob('point-*/solution/*') if p.is_file()}


def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
 before=fingerprints();start=time.monotonic();records=[];manager=JobManager(out/'workspace');max_similarity=0.;max_dimension=0.
 try:
  for geometry in ('coaxial','holes'):
   for order in (1,2):
    case=(CoaxialCase(.025,.05,.18,nr=4,nz=12,modes=2,element_order=order) if geometry=='coaxial' else HphiMeshCase(MeridionalMesh(**rectangular_holes(2,2)),modes=2,element_order=order))
    specifications=[('scale','uniform_scale',[1.,2.]),('energy','/case/rf/stored_energy_j',[1.,4.]),('conductivity','/case/rf/conductivity_s_per_m',[5.8e7,4*5.8e7])]
    if geometry=='coaxial':specifications += [('inner_radius','/case/geometry/inner_radius_m',[.025,.03]),('outer_radius','/case/geometry/outer_radius_m',[.05,.06]),('length','/case/geometry/length_m',[.18,.216])]
    for label,parameter,values in specifications:
     current=case
     if parameter.startswith('/case/geometry/'):
      current=CoaxialCase(.025,.05,.18,nr=24 if order==1 else 12,nz=64 if order==1 else 32,modes=2,element_order=order)
     study=HphiStudy(HphiProject(current),parameter,values);identifier=manager.start_hphi_study(study)
     code=manager.processes[identifier].wait(timeout=180);assert code==0,(label,(manager.directory(identifier)/'log.txt').read_text())
     state=manager.status(identifier,verify=True);assert state['status']=='complete' and state['mode_tracking']=='not_performed' and state['numerical_validation']=='not_checked'
     folder=manager.directory(identifier);saved=read_hphi_study(folder);native_hashes=hashes(folder);assert len(native_hashes)==10
     solutions=[read_hphi_run(folder/f'point-{i:04d}/solution') for i in range(2)];assert [s.case.to_dict() for s in solutions]==[p.case.to_dict() for p in study.projects()]
     errors=[]
     if label in ('scale','energy','conductivity'):
      factor=2. if label=='scale' else 1.;amplitude=2**-1.5 if label=='scale' else 2. if label=='energy' else 1.
      laws=dict(frequency_hz=.5 if label=='scale' else 1.,stored_energy_j=4. if label=='energy' else 1.,geometry_factor_ohm=1.,q0=np.sqrt(2) if label=='scale' else 2. if label=='conductivity' else 1.,wall_loss_w=2**-1.5 if label=='scale' else 4. if label=='energy' else .5,volume_m3=8. if label=='scale' else 1.)
      for a,b in zip(saved['points'][0]['modes'],saved['points'][1]['modes']):
       for key,value in laws.items():errors.append(abs(b[key]/(a[key]*value)-1))
      first,second=solutions;points=first.space.mesh.points[first.space.mesh.triangles].mean(axis=1)[::7]
      a=first.fields_at(points,0);b=second.fields_at(points*factor,0);sign=1 if a['Hphi_real_A_per_m']@b['Hphi_real_A_per_m']>=0 else -1
      for family in ('E','H'):
       x=np.column_stack([v for k,v in a.items() if k.startswith(family)]);y=np.column_stack([v for k,v in b.items() if k.startswith(family)])
       errors.append(np.linalg.norm(sign*y-amplitude*x)/np.linalg.norm(amplitude*x))
      assert max(errors)<1e-8,(label,errors);max_similarity=max(max_similarity,max(errors))
     else:
      for i,solution in enumerate(solutions):
       expected,walls,field=reference(solution.case,(C0/(2*solution.case.length_m),0,1,0.))
       q=saved['points'][i]['modes'][0]
       rf_errors={key:abs(q[key]/value-1) for key,value in expected.items()}
       for key,error in rf_errors.items():assert error<(1e-8 if key=='stored_energy_j' else (1e-3 if order==1 else 1e-4) if key=='frequency_hz' else .005),(label,order,key,error)
       wall_error=max(abs(np.array(list(q['wall_h2_integral_a2_by_surface'].values()))/walls-1));assert wall_error<.005
       vertices=solution.space.mesh.points[solution.space.mesh.triangles];points=vertices.mean(axis=1);areas=solution.space.determinants*points[:,0]/2
       h,e=field(*points.T);actual=solution.fields_at(points,0);ah=actual['Hphi_real_A_per_m'];ae=np.column_stack([actual['Er_quadrature_V_per_m'],actual['Ez_quadrature_V_per_m']]);sign=1 if areas@(h*ah)>=0 else -1
       he=np.sqrt(areas@((sign*ah-h)**2)/(areas@(h*h)));ee=np.sqrt(areas@np.sum((sign*ae-e)**2,axis=1)/(areas@np.sum(e*e,axis=1)))
       assert he<(.002 if order==1 else .001) and ee<(.035 if order==1 else .01),(label,order,he,ee)
       errors += [*rf_errors.values(),wall_error,he,ee];max_dimension=max(max_dimension,max(errors))
     command=subprocess.run([sys.executable,'-m','superfish_ng','replay-hphi-study',str(folder)],capture_output=True,text=True)
     (out/f'{geometry}-p{order}-{label}-cli.log').write_text(command.stdout+command.stderr);assert command.returncode==0,command.stderr;assert json.loads(command.stdout)==saved
     imported=manager.import_hphi_result(folder/'point-0001');assert manager.status(imported,verify=True)['status']=='complete'
     manager.close();manager=JobManager(out/'workspace');assert manager.status(identifier,verify=True)['status']=='complete';assert manager.status(imported,verify=True)['status']=='complete'
     assert native_hashes==hashes(folder)
     records.append(dict(geometry=geometry,order=order,parameter=parameter,job=identifier,imported_point=imported,native_sha256=native_hashes,max_error=float(max(errors))))
     (out/'progress.json').write_text(json.dumps(dict(records=records),indent=2)+'\n');print('PASS',geometry,order,label,max(errors),flush=True)
 finally:manager.close()
 assert fingerprints()==before
 report=dict(status='PASS',workers=18,fem_points=36,cli_replays=18,imported_points=18,restarted_jobs=36,records=records,max_similarity_relative_error=float(max_similarity),max_dimension_error=float(max_dimension),source_sha256=before,seconds=time.monotonic()-start)
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
