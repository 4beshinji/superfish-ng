# SPDX-License-Identifier: Apache-2.0
"""Independent TE crossing checks through the product API and saved CLI."""
import sys,json,argparse,subprocess
from pathlib import Path
import numpy as np
from scipy.special import jn_zeros
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from validate_curved_te import fingerprint
from superfish_ng import Case,solve
from superfish_ng.model import Model
from superfish_ng.te import TEFieldSampler
from superfish_ng.mode_tracking import track_cylindrical_modes
from superfish_ng.io import save_run
from superfish_ng.saved_mode_tracking import read_mode_tracking,build_saved_mode_tracking
parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprint();roots=jn_zeros(1,3)
aspect=np.pi*np.sqrt(8/(roots[1]**2-roots[0]**2));rows=[];base={}
for order in (1,2):
 for scale in (1.,2.):
  solutions=[];labels=[];paths=[]
  for factor in (.97,1.03):
   ratio=factor*aspect;r=.1*scale
   case=Case(((0.,r),(r*ratio,r)),nr=64,nz=96,element_order=order,modes=6,model=Model(polarization='te'))
   solution=solve(case);solutions.append(solution);path=out/f'p{order}-s{scale:g}-x{factor:g}';save_run(case,solution,path);paths.append(str(path));spectrum=sorted((np.hypot(chi,n*np.pi/ratio),p,n) for p,chi in enumerate(roots,1) for n in range(1,7))[:6]
   labels.append([f'r{p}-z{n}' for _,p,n in spectrum])
  reports=[]
  for sample_order in (12,24,48):
   controls=dict(mapping='normalized_cylinder',sample_order=sample_order,minimum_overlap=.98,minimum_assignment_margin=.05,relative_cluster_gap=.001,minimum_relative_singular_value=1e-8)
   result=track_cylindrical_modes(*solutions,labels[0],**controls);assert result['status']=='PASS',result
   for match in result['matches']:assert match['previous_ids']==[labels[1][i-1] for i in match['current_indices']]
   from dataclasses import replace
   altered=track_cylindrical_modes(replace(solutions[0],coefficients_v_per_m2=solutions[0].coefficients_v_per_m2*[1,-2,3,-4,5,-6]),replace(solutions[1],coefficients_v_per_m2=solutions[1].coefficients_v_per_m2*[-.5,1,2,3,-4,5]),labels[0],**controls)
   assert altered['status']=='PASS'
   assert [(m['previous_ids'],m['current_indices']) for m in altered['matches']]==[(m['previous_ids'],m['current_indices']) for m in result['matches']]
   reports.append(dict(sample_order=sample_order,minimum_overlap=min(m['minimum_principal_overlap'] for m in result['matches']),all_ids_match=True,sign_amplitude_invariant=True))
   if sample_order==24:
    request=dict(schema_version=1,previous_run=paths[0],current_run=paths[1],previous_ids=labels[0],controls=controls)
    request_path=out/f'p{order}-s{scale:g}-request.json';request_path.write_text(json.dumps(request));destination=out/f'p{order}-s{scale:g}-tracking.json'
    for command in ([sys.executable,'-m','superfish_ng','track-modes',str(request_path),'--out',str(destination)],[sys.executable,'-m','superfish_ng','replay-mode-tracking',str(destination)]):
     run=subprocess.run(command,capture_output=True,text=True);assert run.returncode==0,run.stdout+run.stderr
    replayed=read_mode_tracking(destination);assert replayed==build_saved_mode_tracking(request);assert replayed['tracking']==result
  frequencies=np.array([s.frequencies_hz for s in solutions])
  if scale==1:base[order]=frequencies
  else:np.testing.assert_allclose(frequencies*scale,base[order],rtol=1e-10,atol=0)
  rows.append(dict(order=order,scale=scale,sampling=reports));print(order,scale,'PASS',flush=True)
assert fingerprint()==before
(out/'report.json').write_text(json.dumps(dict(passed=True,product_adapter=True,cli_and_replay_cases=4,new_fem_solves=8,rows=rows,source_sha256=before),indent=2))
