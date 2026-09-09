# SPDX-License-Identifier: Apache-2.0
"""Fixed external-mesh studies: analytical frequency, scaling and CLI identity."""
import argparse,json,math,subprocess,sys
from pathlib import Path
from scipy.special import jn_zeros
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng import Case
from superfish_ng.project import Project
from superfish_ng.mesh import make_mesh
from superfish_ng.mesh_input import mesh_to_dict
from superfish_ng.studies import Study,execute_study
from superfish_ng.jobs import JobManager
from superfish_ng.saved import read_solution
from superfish_ng.constants import C0
from validate_curved_rf_adaptive import fingerprints


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();rows=[];rf={}
    for order in (1,2):
        for scale in (1.,2.):
            case=Case(((0.,.1*scale),(.2*scale,.1*scale)),nr=3,nz=4,modes=1,element_order=order)
            mesh=mesh_to_dict(make_mesh(case));n=len(mesh['points']);mesh['points'].reverse()
            for key in ('triangles','boundary_edges'):mesh[key]=[[n-1-i for i in row] for row in mesh[key]]
            study=Study(Project(case,mesh_data=mesh),'fixed_geometry_convergence','additional_uniform_refinements',[0,1,2])
            directory=out/f'p{order}-scale-{scale:g}';report=execute_study(study,directory)
            exact=C0*float(jn_zeros(0,1)[0])/(2*math.pi*.1*scale);frequencies=[]
            for level in range(3):
                s=read_solution(directory/f'point-{level+1:03d}'/'solution');frequencies.append(float(s.frequencies_hz[0]))
                assert len(s.mesh.triangles)==24*4**level
                rf[(order,scale,level)]=json.loads((directory/f'point-{level+1:03d}/solution/results.json').read_text())['modes'][0]
            assert all(b<a for a,b in zip(frequencies,frequencies[1:]))
            error=abs(frequencies[-1]/exact-1);assert error<(.002 if order==1 else 1e-5)
            rows.append(dict(element_order=order,scale=scale,frequencies_hz=frequencies,final_analytic_relative_error=error))
            if order==2 and scale==1:
                file=out/'study.json';file.write_text(json.dumps(study.to_dict()))
                subprocess.run([sys.executable,'-m','superfish_ng','study',str(file),'--out',str(out/'cli')],check=True,cwd=ROOT)
                for level in range(3):
                    a=json.loads((directory/f'point-{level+1:03d}/solution/results.json').read_text())['modes']
                    b=json.loads((out/f'cli/point-{level+1:03d}/solution/results.json').read_text())['modes'];assert a==b
                manager=JobManager(out)
                try:assert manager.status(directory.name,verify=True)['status']=='complete'
                finally:manager.close()
    errors=[]
    for order in (1,2):
        for level in range(3):
            a,b=rf[(order,1.,level)],rf[(order,2.,level)]
            errors.append(max(abs(b[k]*(2 if k=='frequency_hz' else 1)/a[k]-1)
                for k in ('frequency_hz','r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm')))
    assert max(errors)<1e-10 and fingerprints()==before
    (out/'validation.json').write_text(json.dumps(dict(passed=True,rows=rows,max_maxwell_error=max(errors),cli_modes_exact=True,
        restarted_manager_verified=True,source_sha256=before,source_unchanged=True,
        scope='four P1/P2 fixed imported-mesh studies, analytical cylinder frequency and Maxwell similarity; all levels retain polygonal domain, not absolute RF convergence certification'),indent=2)+'\n')
    print('External mesh Study PASS')


if __name__=='__main__':main()
