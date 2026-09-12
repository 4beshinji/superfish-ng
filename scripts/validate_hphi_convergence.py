# SPDX-License-Identifier: Apache-2.0
"""Actual Hphi mesh sequences, native replay, similarity and conservative failures."""
import argparse,hashlib,json,subprocess,sys,time
from dataclasses import replace
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from validate_meridional_overlap import mesh
from superfish_ng.axis_hphi import AxisHphiCase,AxisAccelerationPath
from superfish_ng.hphi_mesh import HphiMeshCase
from superfish_ng.hphi_project import HphiProject
from superfish_ng.hphi_convergence import HphiConvergence,compare_hphi_convergence
from superfish_ng.hphi_convergence_saved import execute_hphi_convergence,read_hphi_convergence
from superfish_ng.hphi_native import read_hphi_run


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def request(axis,holes,order,scale):
    projects=[];transform=({(1,0):scale/32,(0,0):0. if axis else scale/32},{(0,1):scale/32})
    for n in (1,2,4):
        geometry,_=mesh(n,holes,axis,transform,17 if n!=2 else 31)
        case=(AxisHphiCase(geometry,element_order=order,modes=3,normalization_j=scale**3,acceleration=AxisAccelerationPath(.01*scale,.08*scale,.8,.003*scale)) if axis else HphiMeshCase(geometry,element_order=order,modes=3,quadrature_order=12,normalization_j=scale**3))
        projects.append(HphiProject(case))
    return HphiConvergence(projects)


def native_hashes(directory):
    return {str(p.relative_to(directory)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(directory.glob('level-*/solution/*')) if p.is_file()}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();started=time.monotonic();records=[];similarity=[];preserved={};cli=[]
    for axis in (False,True):
        for holes in (0,1,2):
            for order in (1,2):
                base=None
                for scale in (1.,2.):
                    q=request(axis,holes,order,scale);directory=out/f'axis-{int(axis)}-holes-{holes}-p-{order}-scale-{int(scale)}'
                    result=execute_hphi_convergence(q,directory);preserved[str(directory)]=native_hashes(directory)
                    assert result==read_hphi_convergence(directory)
                    if order==1:assert result['status']=='UNVERIFIED'
                    if order==2 and holes==0:assert result['status']=='PASS',(axis,order,result['decisions'])
                    numerical=[c[name] for row in result['decisions'] for c in row['checks'].values() for name in ('previous','last')]
                    if base is None:base=(result['status'],np.array(numerical))
                    else:
                        assert result['status']==base[0];similarity.append(float(np.max(abs(np.array(numerical)-base[1]))))
                    if holes==0 and scale==1:
                        command=['replay-hphi-convergence',str(directory)];done=subprocess.run([sys.executable,'-m','superfish_ng',*command],capture_output=True,text=True)
                        assert done.returncode==0,done.stderr;assert json.loads(done.stdout)==result;cli.append(command)
                        solutions=[read_hphi_run(directory/f'level-{i:04d}'/'solution') for i in range(3)]
                        strict=replace(q,thresholds=replace(q.thresholds,frequency_relative=1e-16));assert compare_hphi_convergence(strict,solutions)['status']=='UNVERIFIED'
                        guard=replace(q,mode_ranks=(3,));assert compare_hphi_convergence(guard,solutions)['status']=='UNVERIFIED'
                        solutions[1].coefficients[:,0]*=-1;flipped=compare_hphi_convergence(q,solutions)
                        for first,second in zip(result['comparisons'],flipped['comparisons']):
                            a,b=first['modes'][0],second['modes'][0]
                            for key in ('electric_field_relative','magnetic_field_relative','axis_voltage_relative'):
                                if a[key] is not None:assert abs(a[key]-b[key])<1e-12
                    records.append(dict(axis=axis,holes=holes,order=order,scale=scale,status=result['status'],decisions=result['decisions']))
                    (out/'progress.json').write_text(json.dumps(dict(records=records),indent=2)+'\n');print('DONE',axis,holes,order,scale,result['status'],flush=True)
    assert max(similarity)<1e-9 and all(native_hashes(Path(path))==expected for path,expected in preserved.items()) and fingerprints()==before
    report=dict(status='PASS',scope='explicit mesh sequence and independent finite-difference decisions; general mesh accuracy and mode tracking remain unverified',sequences=len(records),production_fem_solves=3*len(records),cli_commands=cli,records=records,max_similarity_difference=max(similarity),original_native_sha256=preserved,source_sha256=before,seconds=time.monotonic()-started)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
