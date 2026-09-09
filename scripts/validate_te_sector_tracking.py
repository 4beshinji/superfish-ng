# SPDX-License-Identifier: Apache-2.0
"""Independent crossings, similarity and native CLI replay for TE cylinder sectors."""
import sys,json,argparse,subprocess
from pathlib import Path
from dataclasses import replace
import numpy as np
from scipy.special import jn_zeros
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import hashlib
def fingerprint():
 root=ROOT
 return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((root/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
from superfish_ng import Case,solve
from superfish_ng.constants import C0,TAU
from superfish_ng.model import Model
from superfish_ng.symmetry import reflect_solution
from superfish_ng.mode_tracking import track_cylindrical_modes
from superfish_ng import te_mode_tracking
assert Path(te_mode_tracking.__file__).resolve()==ROOT/'src/superfish_ng/te_mode_tracking.py'
from superfish_ng.io import save_run
from superfish_ng.saved_mode_tracking import read_mode_tracking,build_saved_mode_tracking
parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);out=parser.parse_args().out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprint();roots=jn_zeros(1,4);rows=[];base={}
for element_order,scale in [(1,1.),(1,2.),(2,1.),(2,2.)]:
 for side in ('z_min','z_max'):
  for tag,offset in [('magnetic_symmetry',1),('electric_symmetry',2)]:
   aspect=np.pi*np.sqrt((8 if offset==1 else 12)/(roots[1]**2-roots[0]**2))/2
   halves=[];fulls=[];labels=[];frequency_errors=[];paths=[]
   for factor in (.97,1.03):
    ratio=float(factor*aspect);r=.1*scale
    case=Case(((0.,r),(r*ratio,r)),nr=96 if element_order==1 else 24,nz=144 if element_order==1 else 36,modes=4,element_order=element_order,normalization_j=.5,model=Model(polarization='te'),**{side:tag})
    solution=solve(case);halves.append(solution);full,reflected=reflect_solution(case,solution);fulls.append(reflected)
    spectrum=sorted((np.hypot(root,p*np.pi/(2*ratio)),n,p) for n,root in enumerate(roots,1) for p in range(offset,14,2))[:4]
    labels.append([f'r{n}-full-z{p}' for _,n,p in spectrum])
    error=float(max(abs(solution.frequencies_hz/(np.array([item[0] for item in spectrum])*C0/(TAU*r))-1)));frequency_errors.append(error)
    assert error < (.001 if element_order==1 else 1e-4)
    if scale==1. and side=='z_max':
     destinations={}
     for domain,item in [('half',solution),('reflected',reflected)]:
      path=out/f'p{element_order}-{tag}-{factor:g}-{domain}';save_run(item.case,item,path);destinations[domain]=path
     paths.append(destinations)
   assert labels[0]!=labels[1]
   samples=[]
   for order in (12,24,48):
    assignments=[]
    for name,solutions in [('half',halves),('reflected',fulls)]:
     controls=dict(mapping='normalized_cylinder',sample_order=order,minimum_overlap=.98,minimum_assignment_margin=.05,relative_cluster_gap=.001,minimum_relative_singular_value=1e-8)
     result=track_cylindrical_modes(*solutions,labels[0],**controls);assert result['status']=='PASS',result
     for match in result['matches']:assert match['previous_ids']==[labels[1][i-1] for i in match['current_indices']]
     altered=track_cylindrical_modes(replace(solutions[0],coefficients_v_per_m2=solutions[0].coefficients_v_per_m2*[1,-2,3,-4]),replace(solutions[1],coefficients_v_per_m2=solutions[1].coefficients_v_per_m2*[-.5,1,2,3]),labels[0],**controls)
     assignment=[(m['previous_ids'],m['current_indices']) for m in result['matches']]
     assert assignment==[(m['previous_ids'],m['current_indices']) for m in altered['matches']]
     assignments.append(assignment);samples.append(dict(domain=name,order=order,min_overlap=min(m['minimum_principal_overlap'] for m in result['matches'])))
     if paths and order==24:
      request=dict(schema_version=1,previous_run=str(paths[0][name]),current_run=str(paths[1][name]),previous_ids=labels[0],controls=controls)
      request_path=out/f'p{element_order}-{tag}-{name}-request.json';request_path.write_text(json.dumps(request));destination=out/f'p{element_order}-{tag}-{name}-tracking.json'
      for command in ([sys.executable,'-m','superfish_ng','track-modes',str(request_path),'--out',str(destination)],[sys.executable,'-m','superfish_ng','replay-mode-tracking',str(destination)]):
       run=subprocess.run(command,cwd=ROOT,capture_output=True,text=True);assert run.returncode==0,run.stdout+run.stderr
      replayed=read_mode_tracking(destination);assert replayed==build_saved_mode_tracking(request) and replayed['tracking']==result
    assert assignments[0]==assignments[1]
   frequencies=np.array([x.frequencies_hz for x in halves])
   if scale==1.:base[element_order,side,tag]=frequencies
   else:np.testing.assert_allclose(frequencies*scale,base[element_order,side,tag],rtol=1e-10)
   rows.append(dict(element_order=element_order,scale=scale,side=side,tag=tag,labels=labels,samples=samples,frequency_errors=frequency_errors));print(element_order,scale,side,tag,'product crossing PASS',flush=True)
assert before==fingerprint()
(out/'report.json').write_text(json.dumps(dict(passed=True,main_tree_implementation=True,cli_and_replay_cases=8,new_fem_solves=32,rows=rows,source_sha256=before),indent=2))
