# SPDX-License-Identifier: Apache-2.0
"""Compare a browser mesh/selected history with native geometry, without a solve."""
import argparse
from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
import time
import numpy as np
from superfish_ng import Case, make_mesh
from superfish_ng.curved_space import case_curved_space
from superfish_ng.mesh_input import mesh_from_dict
from superfish_ng.project import Project


def fingerprints():
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('src','tests','scripts','examples')
            for p in sorted(Path(folder).rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo')}


def boundary_moments(space):
    """Independent closed-curve Green integrals, exact for quadratic edge maps.

Area = 1/2 integral(r dz-z dr), volume = pi integral(r^2 dz).
Five-point Gauss integrates the degree-five volume integrand exactly in real
arithmetic. Use the actual polynomial edge, not the analytic ellipse.
"""
    nodes=space.geometry.points_rz_m[space.geometry.boundary_nodes]
    abscissa,weights=np.polynomial.legendre.leggauss(5)
    t=(abscissa+1)/2; weights=weights/2
    basis=np.column_stack(((1-t)*(1-2*t),t*(2*t-1),4*t*(1-t)))
    derivative=np.column_stack((4*t-3,4*t-1,4-8*t))
    points=np.einsum('qi,eik->eqk',basis,nodes)
    tangents=np.einsum('qi,eik->eqk',derivative,nodes)
    r,z=points[:,:,0],points[:,:,1];dr,dz=tangents[:,:,0],tangents[:,:,1]
    area=float(np.sum((r*dz-z*dr)*weights)/2)
    volume=float(math.pi*np.sum(r*r*dz*weights))
    return {'signed_area_m2':area,'signed_volume_m3':volume}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser-directory',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args(); args.out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic(); before=fingerprints(); folder=args.browser_directory
    files={name:(folder/name).read_bytes() for name in ('mesh-document.json','built-project.json','report.json')}
    mesh_document=json.loads(files['mesh-document.json']); browser=json.loads(files['report.json'])
    assert browser['passed'] and not browser['external_requests']
    assert browser['source_sha256']=={p:h for p,h in before.items() if p.startswith('src/superfish_ng/') and Path(p).suffix in ('.py','.js','.html','.css')}
    case=Case.from_dict(mesh_document['case']); built=Project.from_dict(json.loads(files['built-project.json']))
    initial=replace(case,curved_refinement_levels=0,curved_refinement_steps=())
    mesh=make_mesh(initial) if built.mesh_data is None else mesh_from_dict(initial,built.mesh_data)
    base=case_curved_space(initial,mesh)
    parent=case_curved_space(case,mesh)
    assert len(parent.geometry.cell_nodes)>5000
    np.testing.assert_array_equal(mesh_document['points_rz_m'],parent.geometry.points_rz_m)
    np.testing.assert_array_equal(mesh_document['cell_nodes'],parent.geometry.cell_nodes)
    assert mesh_document['cell_index_origin']==0
    assert len(parent.geometry.cell_nodes)==browser['mesh']['cells']
    assert browser['mesh']['dom_cells']==0
    parent_steps=case.to_dict()['mesh'].get('curved_refinement_steps',
        [{'kind':'uniform'} for _ in range(case.curved_refinement_levels)])
    steps=built.case.to_dict()['mesh']['curved_refinement_steps']
    assert steps[:-1]==parent_steps
    ids=steps[-1]['marked_cells']; assert steps[-1]['kind']=='marked'
    expected_ids=sorted([0,1999,2000,len(parent.geometry.cell_nodes)//2,len(parent.geometry.cell_nodes)-1])
    assert ids==expected_ids
    assert replace(built.case,curved_refinement_steps=case.curved_refinement_steps,
        curved_refinement_levels=case.curved_refinement_levels)==case
    child=case_curved_space(built.case,mesh)
    assert len(child.geometry.cell_nodes)>len(parent.geometry.cell_nodes)
    moments={name:boundary_moments(space) for name,space in [('base',base),('displayed',parent),('selected_history',child)]}
    for name in ('displayed','selected_history'):
        for key,expected in moments['base'].items():
            assert expected!=0 and abs(moments[name][key]/expected-1)<1e-12,(name,key,moments)
    assert fingerprints()==before
    assert all((folder/name).read_bytes()==data for name,data in files.items())
    report={'status':'PASS','scope':'native mesh/numbering and selected-history geometry; no large eigensolve or RF accuracy claim',
        'displayed_cells':len(parent.geometry.cell_nodes),'selected_history_cells':len(child.geometry.cell_nodes),
        'selected_native_ids':ids,'boundary_moments':moments,'seconds':time.monotonic()-started,
        'source_files_unchanged':len(before),'browser_files_sha256':{name:hashlib.sha256(data).hexdigest() for name,data in files.items()}}
    (args.out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (args.out/'source-sha256.json').write_text(json.dumps(before,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__': main()
