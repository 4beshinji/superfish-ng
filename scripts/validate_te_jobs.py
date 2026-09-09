# SPDX-License-Identifier: Apache-2.0
"""Real TE Project jobs, imports and independent cylinder/sphere RF checks."""
import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from superfish_ng import Case,solve
from superfish_ng.jobs import JobManager,read_job
from superfish_ng.model import Model
from superfish_ng.project import Project
from superfish_ng.mesh import make_mesh
from superfish_ng.mesh_input import mesh_to_dict
from superfish_ng.te import TEFieldSampler,te_quantities
from superfish_ng.te_saved import read_te_run
from validate_te import analytic
from validate_curved_te import sphere,reference,fingerprint


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True,type=Path);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprint();rows=[];ids=[]
    manager=JobManager(out/'imports')
    try:
        for family in ('cylinder','sphere'):
            for scale in (1.,2.):
                label=f'{family}-{scale:g}'
                case=(Case(((0.,.1*scale),(.2*scale,.1*scale)),nr=64,nz=96,element_order=2,modes=6,model=Model(polarization='te'))
                      if family=='cylinder' else replace(sphere(scale),curved_refinement_levels=4))
                source_mesh=mesh_to_dict(make_mesh(case));project=Project(case,mesh_data=source_mesh)
                path=out/f'{label}-project.json';project.save(path)
                command=[sys.executable,'-m','superfish_ng','run-project',str(path),'--out',str(out/label)]
                run=subprocess.run(command,cwd=ROOT,env=dict(os.environ,PYTHONPATH=str(ROOT/'src')),capture_output=True,text=True)
                (out/f'{label}-cli.log').write_text(run.stdout+run.stderr)
                assert run.returncode==0,run.stdout+run.stderr
                assert read_job(out/label)['status']=='complete'
                actual=read_te_run(out/label/'solution');expected=solve(case,mesh_data=source_mesh)
                np.testing.assert_array_equal(actual.coefficients_v_per_m2,expected.coefficients_v_per_m2)
                np.testing.assert_array_equal(actual.frequencies_hz,expected.frequencies_hz)
                if family=='cylinder':
                    probes=np.array([[r,z] for r in np.linspace(0,.1*scale,19) for z in np.linspace(0,.2*scale,23)])
                    exact,evaluate=analytic(.1*scale,.2*scale,1.,6)
                else:
                    radius=.08*scale
                    probes=np.array([(a,b+radius) for a in np.linspace(0,.75*radius,11) for b in np.linspace(-.5*radius,.5*radius,12) if a*a+b*b<(.94*radius)**2])
                sampler=TEFieldSampler(actual);modes=[]
                for mode in range(case.modes):
                    q=te_quantities(actual,mode);assert q==te_quantities(expected,mode)
                    if family=='cylinder':
                        fields,g=evaluate(exact[mode],probes);frequency=exact[mode][0]
                    else:frequency,g,fields=reference(probes,.08*scale,mode+1)
                    numerical=sampler.evaluate(probes,mode);sign=np.sign(numerical['Ephi_V_per_m']@fields['Ephi_V_per_m'])
                    errors={name:float(max(abs(sign*numerical[name]-values))/max(abs(values))) for name,values in fields.items()}
                    modes.append(dict(frequency_error=abs(q['frequency_hz']/frequency-1),geometry_factor_error=abs(q['geometry_factor_ohm']/g-1),field_errors=errors,energy_balance=abs(q['electric_energy_j']/q['magnetic_energy_j']-1),quantities=q))
                rows.append(dict(family=family,scale=scale,modes=modes));(out/'partial.json').write_text(json.dumps(rows,indent=2))
                for row in modes:
                    assert row['frequency_error']<1e-4 and row['geometry_factor_error']<.005 and max(row['field_errors'].values())<.01 and row['energy_balance']<1e-9,row
                for source in (out/label,out/label/'solution'):
                    identifier=manager.import_result(source);ids.append(identifier);folder=manager.directory(identifier)
                    assert Project.load(folder/'project.json').to_dict()==project.to_dict()
                    imported=read_te_run(folder/'solution')
                    np.testing.assert_array_equal(imported.coefficients_v_per_m2,actual.coefficients_v_per_m2)
                    assert manager.status(identifier)['origin']=='imported'
                print(label,'PASS',flush=True)
    finally:manager.close()
    restarted=JobManager(out/'imports')
    try:
        for identifier in ids:assert restarted.status(identifier)['status']=='complete'
    finally:restarted.close()
    similarity=[]
    for family in ('cylinder','sphere'):
        a,b=[row for row in rows if row['family']==family]
        for x,y in zip(a['modes'],b['modes']):
            for key,factor in (('frequency_hz',.5),('geometry_factor_ohm',1.),('q0',np.sqrt(2.))):
                similarity.append(abs(y['quantities'][key]/x['quantities'][key]/factor-1))
    assert max(similarity)<1e-8
    assert fingerprint()==before
    (out/'validation.json').write_text(json.dumps(dict(passed=True,rows=rows,imports=len(ids),max_similarity=max(similarity),new_fem_solves=8,source_sha256=before),indent=2))
    print('PASS',flush=True)


if __name__=='__main__':main()
