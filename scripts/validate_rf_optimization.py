# SPDX-License-Identifier: Apache-2.0
"""Two-variable native FEM search, CLI resumption and independent sphere scaling."""
import argparse,json,subprocess,sys
from dataclasses import replace
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng.project import Project
from superfish_ng.curved_project_transform import transform_curved_project
from superfish_ng.rf_optimization import read_rf_optimization
from superfish_ng.analytic_sphere import SphereTM
from validate_curved_rf_adaptive import fingerprints


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();reports=[];errors=[]
    for scale in (1,2):
        request=json.loads((ROOT/'examples/optimization/curved_rf.json').read_text())
        project=transform_curved_project(Project.from_dict(request['project']),
            dict(radial_scale=float(scale),axial_scale=float(scale),axial_shear=0.),rf_coordinates='axial')
        project=replace(project,case=replace(project.case,normalization_j=float(scale**2)))
        request['project']=project.to_dict();request['objective_improvement']/=scale
        document=out/f'request-{scale}.json';document.write_text(json.dumps(request,indent=2)+'\n')
        first=out/f'first-{scale}';resumed=out/f'resumed-{scale}'
        subprocess.run([sys.executable,'-m','superfish_ng','optimize-rf',str(document),'--out',str(first),'--max-new-trials','1'],check=True,cwd=ROOT)
        subprocess.run([sys.executable,'-m','superfish_ng','replay-rf-optimization',str(first/'checkpoint-001.json')],check=True,cwd=ROOT)
        subprocess.run([sys.executable,'-m','superfish_ng','resume-rf-optimization',str(first/'checkpoint-001.json'),'--out',str(resumed)],check=True,cwd=ROOT)
        report=read_rf_optimization(resumed/'checkpoint-004.json');reports.append(report)
        assert report['status']=='SEARCH_COMPLETE' and report['completed_fem_solves']==12
        assert [t['values'] for t in report['trials']]==[[1.,1.],[1.01,1.],[1.01,1.01],[1.01,1.01]]
        assert report['decision']['search_stop']=='TRIAL_LIMIT'
        initial=report['trials'][0]['assessment'];final=report['trials'][-1]['assessment']
        assert initial['status']==final['status']=='CRITERIA_MET'
        assert final['objective']['eligible_value']<initial['objective']['eligible_value']
        exact=SphereTM(.08*scale*1.01,normalization_j=float(scale**2)).quantities()['frequency_hz']
        frequency=final['assessment']['rows'][-1]['intervals']['frequency_hz'][0]
        error=abs(frequency/exact-1);assert error<1e-4;errors.append(error)
    similarity=[]
    for a,b in zip(reports[0]['trials'],reports[1]['trials']):
        for k,interval in a['assessment']['observed_envelopes'].items():
            other=b['assessment']['observed_envelopes'][k]
            similarity.extend(abs(y*(2 if k=='frequency_hz' else 1)/x-1) for x,y in zip(interval,other))
    assert max(similarity)<2e-9 and fingerprints()==before
    (out/'validation.json').write_text(json.dumps(dict(passed=True,analytic_final_frequency_relative_errors=errors,
        max_maxwell_relative_error=max(similarity),cli_pause_resume_replay=True,source_sha256=before,source_unchanged=True,
        scope='two scales, two-variable native searches with independently solved finer final sphere and all trial replay; not general optimality or physical error certification'),indent=2)+'\n')
    print('RF optimization PASS')


if __name__=='__main__':main()
