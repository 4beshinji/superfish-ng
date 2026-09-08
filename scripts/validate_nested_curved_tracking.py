# SPDX-License-Identifier: Apache-2.0
"""Replay native residual-refinement fields and verify curved mass tracking."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng.saved import read_solution
from superfish_ng.saved_mode_tracking import save_mode_tracking,read_mode_tracking,_snapshot
from superfish_ng.nested_curved_tracking import _nested_transfer
from superfish_ng.curved_fem import assemble_curved
from superfish_ng.curved_rf import quantities_curved
from superfish_ng.analytic import pillbox_tm010
from superfish_ng.mode_tracking import tracked_frequency_hz

CONTROLS=dict(mapping='nested_curved',minimum_overlap=.99,minimum_assignment_margin=.05,
              relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source-root',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();source=args.source_root.resolve();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    before=hashes();sources={};checks={}
    rf_keys=('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm','epk_over_eacc_estimate','bpk_over_eacc_estimate_mt_per_mv_per_m')
    for kind in ('cylinder','ellipse','hyperbola'):
        series=[]
        for scale in (1,2):
            runs=[source/f'{kind}-s{scale}-level{i}' for i in range(3)]
            for run in runs:sources[str(run)]=_snapshot(run)
            with patch('superfish_ng.curved_solution.eigsh',side_effect=AssertionError('tracking must not solve')):
                solutions=[read_solution(run) for run in runs]
            rows=[]
            for level in range(2):
                name=f'{kind}-s{scale}-pair{level}';path=out/(name+'.json')
                request=dict(schema_version=1,previous_run=str(runs[level]),current_run=str(runs[level+1]),previous_ids=['A','B'],controls=CONTROLS)
                if kind=='cylinder' and scale==1 and level==0:
                    request_path=out/'cli-request.json';request_path.write_text(json.dumps(request,indent=2)+'\n')
                    for command in ([sys.executable,'-m','superfish_ng','track-modes',str(request_path),'--out',str(path)],
                                    [sys.executable,'-m','superfish_ng','replay-mode-tracking',str(path)]):
                        result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,env=dict(os.environ,PYTHONPATH=str(ROOT/'src')))
                        (out/(command[3]+'.log')).write_text(result.stdout+result.stderr)
                        if result.returncode:raise RuntimeError('tracking CLI failed; see output logs')
                else:
                    with patch('superfish_ng.curved_solution.eigsh',side_effect=AssertionError('tracking must not solve')):
                        save_mode_tracking(request,path)
                with patch('superfish_ng.curved_solution.eigsh',side_effect=AssertionError('tracking replay must not solve')):
                    document=read_mode_tracking(path)
                a,b=solutions[level:level+2];p,space,_,_,_=_nested_transfer(a,b)
                # Different quadrature orders on different meshes test the Galerkin mass invariant.
                coarse=assemble_curved(a.space,quadrature_order=12)[1];fine=assemble_curved(space,quadrature_order=8)[1]
                mass_error=float(np.linalg.norm((p.T@fine@p-coarse).data)/np.linalg.norm(coarse.data))
                report=document['tracking'];overlaps=[m['minimum_principal_overlap'] for m in report['matches']]
                q=quantities_curved(b);old_q=quantities_curved(a)
                analytical=pillbox_tm010(.1*scale,.08*scale) if kind=='cylinder' else None
                errors={k:abs(q[k]/analytical[k]-1) for k in rf_keys} if analytical else None
                tracked=[tracked_frequency_hz(report,mode_id) for mode_id in ('A','B')]
                passed=(document['status']=='PASS' and report['current_mode_ids']==['A','B'] and report['individual_ids_complete']
                    and mass_error<1e-10 and min(overlaps)>.99 and np.array_equal(tracked,b.frequencies_hz))
                if errors:passed=passed and errors[rf_keys[0]]<1e-4 and max(errors[k] for k in rf_keys[1:3])<.005 and max(errors[k] for k in rf_keys[3:])<.01
                rows.append(dict(passed=bool(passed),level=level,mass_galerkin_relative_error=mass_error,principal_overlaps=overlaps,
                    mass_embedding_relative_difference=report['physical_mapping']['mass_embedding_relative_difference'],tracked_frequencies_hz=tracked,
                    rf=q,rf_relative_changes={k:abs(q[k]/old_q[k]-1) for k in rf_keys},cylinder_analytical_errors=errors))
            series.append(rows)
        similarity=[dict(overlap_max_absolute_difference=max(abs(np.array(a['principal_overlaps'])-b['principal_overlaps'])),
            rf={k:abs(b['rf'][k]*(2 if k=='frequency_hz' else 1)/a['rf'][k]-1) for k in rf_keys}) for a,b in zip(*series)]
        checks[kind]=dict(passed=all(r['passed'] for rows in series for r in rows) and all(s['overlap_max_absolute_difference']<1e-10 and max(s['rf'].values())<2e-8 for s in similarity),series=series,similarity=similarity)
    stable=all(value==_snapshot(Path(path)) for path,value in sources.items());unchanged=before==hashes()
    passed=stable and unchanged and all(c['passed'] for c in checks.values())
    (out/'validation.json').write_text(json.dumps(dict(passed=passed,checks=checks,sources=sources,source_sha256=before,
        source_changed_during_run=not unchanged,native_sources_unchanged=stable,
        scope='18 previously generated native FEM results revalidated; 12 local-refinement tracking pairs, actual CLI/replay, mass Galerkin, cylinder RF and Maxwell similarity; no new eigenvalue solves or adaptive stopping acceptance'),indent=2,allow_nan=False)+'\n')
    print(f'Nested curved tracking {"PASS" if passed else "FAIL"}: {out}');return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
