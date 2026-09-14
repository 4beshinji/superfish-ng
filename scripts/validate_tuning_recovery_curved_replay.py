# SPDX-License-Identifier: Apache-2.0
"""Reidentify existing curved tuning samples with actual anchor-derived maps."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from superfish_ng.tuning import read_tune,_assemble
from superfish_ng.saved import read_solution
from superfish_ng.analytic import tm0np_frequency
from validate_large_curved_mesh_selection import fingerprints


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--affine-reference',required=True,type=Path)
    parser.add_argument('--harmonic-reference',required=True,type=Path,help='saved four-trial TM011 checkpoint')
    parser.add_argument('--out',required=True,type=Path);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);source=fingerprints();started=time.monotonic()
    documents=[(f'affine-{scale}-{unit}',args.affine_reference/f'scale-{scale}-unit-{unit}/resumed/checkpoint-004.json',scale)
        for scale in [1,2] for unit in ['m','1']]+[('harmonic',args.harmonic_reference,1)]
    retained={};rows=[];rf=[]
    for name,path,scale in documents:
        original=read_tune(path);assert len(original['trial_runs'])==4
        files={path.resolve()}|{p for run in original['trial_runs'] for p in Path(run).rglob('*') if p.is_file()}
        retained.update({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
        solutions=[read_solution(Path(run)/'solution') for run in original['trial_runs']]
        controls=deepcopy(original['request']['controls']);base=deepcopy(original['request'])
        base['controls'].update(relative_cluster_gap=.2,cluster_transition_policy='retain_subspace',minimum_cluster_link=.2)
        for selection in ['fixed_trial','latest_resolved_trial']:
            policy=dict(anchor_selection=selection,controls=controls)
            if selection=='fixed_trial':policy['anchor_trial_index']=0
            request=dict(schema_version=6,tune_request=base,identity_recovery=policy)
            recovered=_assemble(request,original['trial_runs']);output=out/f'{name}-{selection}.json'
            output.write_text(json.dumps(recovered,indent=2,allow_nan=False)+'\n')
            assert read_tune(output)==recovered and recovered['status']=='TUNED'
            assert [t['frequency_hz'] for t in recovered['trials']]==[t['frequency_hz'] for t in original['trials']]
            errors=[];bindings=[]
            for i,trial in enumerate(recovered['trials']):
                exact=tm0np_frequency(.1*scale,solutions[i].case.length,1,1)
                errors.append(abs(trial['frequency_hz']/exact-1))
                event=trial['identity_recovery']
                if i==0:assert event is None;continue
                assert event['status']=='PASS';anchor=event['anchor_trial_index'];assert anchor==(0 if selection=='fixed_trial' else i-1)
                comparison=event['comparison'];mapping=comparison['request']['controls']
                assert comparison['request']['previous_run']==str(Path(original['trial_runs'][anchor])/'solution')
                if base['schema_version']==4:
                    physical_ratio=solutions[i].case.length/solutions[anchor].case.length
                    assert abs(mapping['affine_map']['axial_scale']/physical_ratio-1)<1e-12
                    assert mapping['affine_map']['radial_scale']==1. and mapping['affine_map']['axial_shear']==0.
                else:
                    for mesh,index in zip(mapping['comparison_meshes'],[anchor,i]):
                        assert mesh['source_mesh']==solutions[index].source_mesh_data
                        assert mesh['curved_refinement_steps']==base['project']['case']['mesh']['curved_refinement_steps']
                bindings.append(dict(trial=i,parent=trial['parent_index'],anchor=anchor))
            assert max(errors)<1e-4 and errors[-1]<1e-5
            rows.append(dict(variant=name,geometry_request_version=base['schema_version'],selection=selection,
                status=recovered['status'],bindings=bindings,frequency_errors=errors))
        mode=original['trials'][-1]['current_mode_ids'].index('TM011')
        if base['schema_version']==4:rf.append((scale,solutions[-1].results['modes'][mode]))
    reference=rf[0][1];maxwell=[]
    for scale,quantities in rf:
        maxwell.append(max(abs(quantities[k]*(scale if k=='frequency_hz' else 1)/reference[k]-1)
            for k in ['frequency_hz','r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm']))
    assert max(maxwell)<1e-9
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==v for p,v in retained.items()) and fingerprints()==source
    report=dict(status='PASS',new_fem_solves=0,reused_native_solutions=20,rows=rows,maxwell_errors=maxwell,
        seconds=time.monotonic()-started,native_sha256=retained,source_sha256=source,source_unchanged=True,
        scope='recovery on saved curved P2 cylinder samples, two scales/units, affine and fixed-history harmonic comparison maps; genuine non-affine three-mode recovery is covered separately by the unit fixture')
    (out/'validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:report[k] for k in ['status','new_fem_solves','reused_native_solutions','seconds']}))


if __name__=='__main__':main()
