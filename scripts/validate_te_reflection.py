# SPDX-License-Identifier: Apache-2.0
"""Independent full-domain FEM, Bessel and native checks for TE parity subsets."""
import argparse,json
from dataclasses import replace
from pathlib import Path
import numpy as np
from validate_te import analytic
from validate_curved_te import fingerprint
from superfish_ng import Case,solve
from superfish_ng.model import Model
from superfish_ng.symmetry import reflect_solution
from superfish_ng.te import TEFieldSampler,te_quantities
from superfish_ng.mesh_input import mesh_to_dict
from superfish_ng.io import save_run
from superfish_ng.te_saved import read_te_run
parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
out=parser.parse_args().out.resolve();out.mkdir(parents=True,exist_ok=False)
before=fingerprint();records=[]
for order in (1,2):
 for side in ('z_min','z_max'):
  for tag in ('magnetic_symmetry','electric_symmetry'):
   name=f'p{order}-{side}-{tag}';n=16 if order==1 else 32
   case=Case(((0.,.1),(.1,.1)),nr=n,nz=3*n//2,modes=2,element_order=order,normalization_j=.5,model=Model(polarization='te'),**{side:tag})
   half=solve(case);full,reflected=reflect_solution(case,half)
   destination=out/name;save_run(full,reflected,destination);saved=read_te_run(destination)
   np.testing.assert_array_equal(saved.coefficients_v_per_m2,reflected.coefficients_v_per_m2)
   independent=solve(replace(full,modes=8),mesh_data=mesh_to_dict(reflected.mesh))
   exact,evaluate=analytic(.1,.2,1.,8)
   points=np.array([[r,z] for r in np.linspace(.002,.098,17) for z in np.linspace(.003,.197,23)])
   modes=[]
   for mode in range(2):
    index=int(np.argmin(abs(independent.frequencies_hz/reflected.frequencies_hz[mode]-1)))
    np.testing.assert_allclose(independent.frequencies_hz[index],reflected.frequencies_hz[mode],rtol=1e-9)
    a=TEFieldSampler(reflected).evaluate(points,mode);b=TEFieldSampler(independent).evaluate(points,index)
    sign=1 if a['Ephi_V_per_m']@b['Ephi_V_per_m']>=0 else -1
    for key in ('Ephi_V_per_m','Hr_quadrature_A_per_m','Hz_quadrature_A_per_m'):
     assert max(abs(a[key]-sign*b[key]))/max(abs(a[key]))<1e-8
    qa,qh,qi=te_quantities(reflected,mode),te_quantities(half,mode),te_quantities(independent,index)
    for key,factor in [('stored_energy_j',2),('wall_loss_w',2),('q0',1),('geometry_factor_ohm',1)]:
     np.testing.assert_allclose(qa[key],factor*qh[key],rtol=1e-10)
     np.testing.assert_allclose(qa[key],qi[key],rtol=1e-8)
    fields,g=evaluate(exact[index],points)
    sign=1 if a['Ephi_V_per_m']@fields['Ephi_V_per_m']>=0 else -1
    errors={key:float(max(abs(sign*a[key]-value))/max(abs(value))) for key,value in fields.items()}
    row=dict(source_mode=mode+1,independent_full_rank=index+1,analytic_radial_index=exact[index][1],analytic_axial_index=exact[index][2],frequency_error=abs(qa['frequency_hz']/exact[index][0]-1),geometry_factor_error=abs(qa['geometry_factor_ohm']/g-1),field_errors=errors)
    assert exact[index][2]%2==(1 if tag=='magnetic_symmetry' else 0)
    if order==2:assert row['frequency_error']<1e-4 and row['geometry_factor_error']<.005 and max(errors.values())<.01,row
    modes.append(row)
   assert [m['independent_full_rank'] for m in modes]!=[1,2]
   records.append(dict(name=name,modes=modes,p1_scope='discrete reflection invariants; coarse P1 is not certified by its residual' if order==1 else None))
   (out/'partial.json').write_text(json.dumps(records,indent=2));print(name,'PASS',flush=True)
assert before==fingerprint()
(out/'report.json').write_text(json.dumps(dict(passed=True,new_fem_solves=16,rows=records,source_sha256=before),indent=2))
