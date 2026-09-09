# SPDX-License-Identifier: Apache-2.0
"""Compare reconstructed TE symmetry sectors against independently saved halves."""
import argparse,json
from pathlib import Path
from dataclasses import replace
from validate_curved_te import sphere,fingerprint
from superfish_ng import Case,solve
from superfish_ng.model import Model
from superfish_ng.symmetry import reflect_solution
from superfish_ng.io import save_run
from superfish_ng.studies import compare_refinement
from superfish_ng.te import te_quantities
import numpy as np


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    out=parser.parse_args().out;out.mkdir(parents=True,exist_ok=False)
    before=fingerprint();rows=[]
    for shape in ('p1','p2','sphere'):
        for tag in ('magnetic_symmetry','electric_symmetry'):
            paths=[]
            for level in (0,1):
                if shape=='sphere':
                    data=sphere(half=True).to_dict();data['geometry']['edge_tags'][-1]=tag
                    case=replace(Case.from_dict(data),modes=1,curved_refinement_levels=level)
                else:
                    n=16*2**level
                    case=Case(((0.,.1),(.1,.1)),nr=n,nz=3*n//2,modes=1,
                              element_order=1 if shape=='p1' else 2,normalization_j=.5,
                              z_max=tag,model=Model(polarization='te'))
                half=solve(case);full,reflected=reflect_solution(case,half)
                a,b=te_quantities(half),te_quantities(reflected)
                for key,factor in [('frequency_hz',1),('stored_energy_j',2),('wall_loss_w',2),('q0',1),('geometry_factor_ohm',1)]:
                    np.testing.assert_allclose(b[key],factor*a[key],rtol=1e-10)
                hp=out/f'{shape}-{tag}-{level}-half';fp=out/f'{shape}-{tag}-{level}-full'
                save_run(case,half,hp);save_run(full,reflected,fp);paths.append((hp,fp))
            expected=compare_refinement(paths[0][0],paths[1][0])
            actual=compare_refinement(paths[0][1],paths[1][1])
            reflection=actual.pop('reflection_comparison')
            assert actual==expected
            assert reflection['domain']=='reconstructed source half-domain'
            assert all(r['parity']==(1 if tag=='magnetic_symmetry' else -1) for r in reflection['source_reflections'])
            assert all('r_over_q_accelerator_ohm' not in m['relative_changes'] for m in actual['modes'])
            rows.append(dict(shape=shape,tag=tag,comparison=actual,reflection_comparison=reflection))
            (out/'partial.json').write_text(json.dumps(rows,indent=2));print(shape,tag,actual['status'],'exact comparison PASS',flush=True)
    assert before==fingerprint()
    (out/'report.json').write_text(json.dumps(dict(passed=True,new_fem_solves=12,rows=rows,
        scope='reflection/source comparison equivalence; individual numerical statuses retained, no surface or physical error certification',source_sha256=before),indent=2))


if __name__=='__main__':main()
