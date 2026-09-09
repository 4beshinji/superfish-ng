# SPDX-License-Identifier: Apache-2.0
"""Spherical TE refinement: analytical fields/RF, scale and magnetic symmetry."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import numpy as np
from validate_curved_te import sphere, reference, fingerprint
from superfish_ng.project import Project
from superfish_ng.studies import Study, execute_study
from superfish_ng.te import TEFieldSampler
from superfish_ng.te_saved import read_te_run

parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
out=parser.parse_args().out.resolve();out.mkdir(parents=True,exist_ok=False)
before=fingerprint();rows=[];finals={}
for scale,half in ((1.,False),(2.,False),(1.,True)):
    name=f'scale{scale:g}-'+('half' if half else 'full')
    case=replace(sphere(scale,half=half),modes=1)
    study=Study(Project(case),'fixed_geometry_convergence','/case/mesh/curved_refinement_levels',[1,2,3])
    run=out/name;report=execute_study(study,run)
    assert report['numerical_status']=='PASS',report['comparisons'][-1]
    radius=.08*scale
    offsets=np.linspace(.1,.5,11) if half else np.linspace(-.5,.5,12)
    points=np.array([(a*radius,(b+(0 if half else 1))*radius) for a in np.linspace(0,.7,11) for b in offsets])
    refpoints=points+([0,radius] if half else [0,0])
    frequency,g,fields=reference(refpoints,radius,1)
    levels=[]
    for point in report['points']:
        solution=read_te_run(run/point['directory']/'solution')
        actual=TEFieldSampler(solution).evaluate(points)
        sign=1 if actual['Ephi_V_per_m']@fields['Ephi_V_per_m']>=0 else -1
        errors={key:float(np.max(abs(sign*actual[key]-value))/np.max(abs(value))) for key,value in fields.items()}
        q=point['modes'][0]
        levels.append(dict(level=point['value'],frequency_error=abs(q['frequency_hz']/frequency-1),
                           geometry_factor_error=abs(q['geometry_factor_ohm']/g-1),fields=errors))
    assert all(b['frequency_error']<a['frequency_error'] and b['geometry_factor_error']<a['geometry_factor_error'] for a,b in zip(levels,levels[1:]))
    final=levels[-1]
    assert final['frequency_error']<1e-4 and final['geometry_factor_error']<.005 and max(final['fields'].values())<.01,final
    row=dict(name=name,levels=levels,comparisons=report['comparisons']);rows.append(row)
    finals[name]=report['points'][-1]['modes'][0]
    (out/'partial.json').write_text(json.dumps(rows,indent=2));print(name,'PASS',flush=True)
a=finals['scale1-full'];b=finals['scale2-full'];h=finals['scale1-half']
for key,factor in [('frequency_hz',.5),('geometry_factor_ohm',1.),('q0',np.sqrt(2.))]:
    np.testing.assert_allclose(b[key],factor*a[key],rtol=1e-9)
# Half and full meshes differ; compare each to the same analytic solution above.
assert h['r_over_q_accelerator_ohm'] is None
assert before==fingerprint()
(out/'report.json').write_text(json.dumps(dict(passed=True,new_fem_solves=9,rows=rows,source_sha256=before),indent=2))
