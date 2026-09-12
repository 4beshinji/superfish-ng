# SPDX-License-Identifier: Apache-2.0
"""Independent physical E/H inner products and analytical mode anchors for tracking."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
from scipy.special import jv,jn_zeros
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from validate_meridional_overlap import mesh
from validate_hphi_field_overlap import common_rule,independent_fields,reference_grams,discrepancy
from superfish_ng.axis_hphi import AxisHphiCase,solve_axis_hphi
from superfish_ng.hphi_mesh import HphiMeshCase,solve_hphi_mesh
from superfish_ng.hphi_native import save_hphi_run,read_hphi_run
from superfish_ng.hphi_tracking import HphiTrackingRequest,track_hphi_modes


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def principal(aa,ab,bb,left,right):
    aa=aa[np.ix_(left,left)];bb=bb[np.ix_(right,right)];ab=ab[np.ix_(left,right)]
    def whitening(m):
        value,vector=np.linalg.eigh(m);assert min(value)>0
        return vector/np.sqrt(value)[None,:]
    return np.linalg.svd(whitening(aa).T@ab@whitening(bb),compute_uv=False)


def anchor(fields,points,weights,axis,radius,length):
    r,z=points[:,:,0].ravel(),points[:,:,1].ravel();w=weights.ravel()
    h=jv(1,jn_zeros(0,1)[0]*r/radius) if axis else np.cos(np.pi*z/length)/r
    actual=fields[1][0];overlap=abs(h@(w[:,None]*actual))/np.sqrt(np.dot(w,h*h)*np.sum(w[:,None]*actual**2,axis=0))
    order=np.argsort(overlap);assert overlap[order[-1]]>.9 and overlap[order[-1]]-overlap[order[-2]]>.4
    return int(order[-1]),float(overlap[order[-1]])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();started=time.monotonic();records=[];native_hashes={};similarity=[];anchors=[]
    for axis in (False,True):
        for holes in (0,1,2):
            old={}
            for scale in (1.,2.):
                transform=({(1,0):scale/32,(0,0):0. if axis else scale/32},{(0,1):scale/32});solutions={};fields={};geometry={}
                for n in (2,3,4,6):geometry[n]=mesh(n,holes,axis,transform,17+n)[0]
                centers,points,weights=common_rule(geometry[6],order=10)
                for n in (2,3):
                    for order in (1,2):
                        case=AxisHphiCase(geometry[n],element_order=order,modes=3,normalization_j=scale**3) if axis else HphiMeshCase(geometry[n],element_order=order,modes=3,normalization_j=scale**3,quadrature_order=12)
                        solution=solve_axis_hphi(case) if axis else solve_hphi_mesh(case)
                        native=out/f'axis-{int(axis)}-holes-{holes}-s-{int(scale)}-n-{n}-p-{order}';save_hphi_run(case,solution,native)
                        native_hashes.update({str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in native.iterdir()})
                        solutions[n,order]=read_hphi_run(native);fields[n,order]=independent_fields(solution,centers,points)
                for left_order,right_order in ((1,1),(1,2),(2,2)):
                    a,b=solutions[2,left_order],solutions[3,right_order]
                    request=HphiTrackingRequest(geometry[4],geometry[6]);report=track_hphi_modes(a,b,request)
                    prefix=out/f'axis-{int(axis)}-holes-{holes}-s-{int(scale)}-p-{left_order}-{right_order}'
                    request.save(prefix.with_suffix('.request.json'));assert HphiTrackingRequest.load(prefix.with_suffix('.request.json')).to_dict()==request.to_dict()
                    prefix.with_suffix('.result.json').write_text(json.dumps(report,indent=2)+'\n')
                    expected=reference_grams(fields[2,left_order],fields[3,right_order],weights)
                    errors=[discrepancy(report['physical_mapping'][name],reference) for name,reference in zip(('electric_grams','magnetic_grams'),expected)]
                    assert max(errors)<1e-9
                    principal_errors=[]
                    for match in report['matches']:
                        left=[i-1 for i in match['previous_indices']];right=[i-1 for i in match['current_indices']]
                        for family,recorded in zip(expected,(match['principal_overlaps'],match['magnetic_principal_overlaps'])):
                            if recorded is None:continue
                            reference=principal(*family,left,right)
                            principal_errors.append(float(np.max(abs(reference-recorded))));assert principal_errors[-1]<1e-8
                    if report['status']!='PASS':assert report['current_mode_ids']==[None,None] and report['verification_reasons']
                    if holes==0:
                        first=anchor(fields[2,left_order],points,weights,axis,a.case.outer_radius_m if not axis else float(geometry[2].points_rz_m[:,0].max()),a.case.length_m)
                        second=anchor(fields[3,right_order],points,weights,axis,b.case.outer_radius_m if not axis else float(geometry[3].points_rz_m[:,0].max()),b.case.length_m)
                        if report['status']=='PASS':
                            matching=[m for m in report['matches'] if first[0]+1 in m['previous_indices']];assert len(matching)==1 and second[0]+1 in matching[0]['current_indices']
                        anchors.append(dict(axis=axis,scale=scale,orders=[left_order,right_order],previous_rank=first[0]+1,current_rank=second[0]+1,minimum_analytic_h_overlap=min(first[1],second[1]),tracking_status=report['status']))
                    key=left_order,right_order
                    normalized=[np.asarray(g[1])/np.sqrt(np.diag(g[0]))[:,None]/np.sqrt(np.diag(g[2]))[None,:] for g in expected]
                    identity=[(m['previous_indices'],m['current_indices'],m['previous_ids']) for m in report['matches']]
                    if scale==1:old[key]=(report['status'],identity,normalized)
                    else:
                        status,matches,grams=old[key];assert status==report['status'] and matches==identity
                        similarity.extend(float(np.max(abs(abs(x)-abs(y)))) for x,y in zip(normalized,grams))
                    records.append(dict(axis=axis,holes=holes,scale=scale,previous_order=left_order,current_order=right_order,
                        tracking_status=report['status'],maximum_gram_difference=max(errors),maximum_principal_difference=max(principal_errors,default=0.),individual_ids_complete=report['individual_ids_complete']))
                print('DONE',axis,holes,scale,flush=True)
    for path,digest in native_hashes.items():assert hashlib.sha256((out/path).read_bytes()).hexdigest()==digest
    assert max(similarity)<1e-9 and fingerprints()==before
    report=dict(status='PASS',original_fem_native=48,comparisons=len(records),records=records,analytic_anchors=anchors,native_files_unchanged=len(native_hashes),
        max_physical_gram_difference=max(r['maximum_gram_difference'] for r in records),max_principal_difference=max(r['maximum_principal_difference'] for r in records),
        max_similarity_difference=max(similarity),source_sha256=before,seconds=time.monotonic()-started)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:report[k] for k in ('status','original_fem_native','comparisons','max_physical_gram_difference','max_principal_difference','max_similarity_difference','seconds')})


if __name__=='__main__':main()
