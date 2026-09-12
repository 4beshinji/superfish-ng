# SPDX-License-Identifier: Apache-2.0
"""Compare shifted inverse diagnostics to full independent finite eigenspectra."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
from scipy.linalg import eigh
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from validate_meridional_overlap import mesh
from superfish_ng.axis_hphi import AxisHphiCase,solve_axis_hphi
from superfish_ng.axis_connected_fem import axis_connected_matrices
from superfish_ng.hphi_mesh import HphiMeshCase,solve_hphi_mesh,hphi_mesh_matrices
from superfish_ng.hphi_mass_projection import project_hphi_coefficients
from superfish_ng.hphi_spectral_resolution import hphi_spectral_resolution
from superfish_ng.hphi_native import save_hphi_run,read_hphi_run
from superfish_ng.constants import C0,TAU


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();started=time.monotonic();records=[];similarity=[];native_hashes={}
    for axis in (False,True):
        for holes in (0,1,2):
            baseline={}
            for scale in (1.,2.):
                transform=({(1,0):scale/32,(0,0):0. if axis else scale/32},{(0,1):scale/32})
                original,_=mesh(1,holes,axis,transform,17)
                for order in (1,2):
                    case=AxisHphiCase(original,element_order=order,modes=3,normalization_j=scale**3) if axis else HphiMeshCase(original,element_order=order,modes=3,quadrature_order=12,normalization_j=scale**3)
                    solution=solve_axis_hphi(case) if axis else solve_hphi_mesh(case)
                    native=out/f'axis-{int(axis)}-holes-{holes}-s-{int(scale)}-p-{order}'
                    save_hphi_run(case,solution,native);read_hphi_run(native)
                    native_hashes.update({str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in native.iterdir()})
                    for n in (2,4):
                        comparison,_=mesh(n,holes,axis,transform,31)
                        report=hphi_spectral_resolution(solution,comparison,comparison_order=order)
                        projection=project_hphi_coefficients(original,comparison,solution.coefficients,previous_order=order,current_order=order)
                        if axis:_,k,m=axis_connected_matrices(comparison,order)
                        else:_,k,m,_=hphi_mesh_matrices(HphiMeshCase(comparison,element_order=order,quadrature_order=12))
                        # Dense full generalized eigenvectors are independent of the
                        # production sparse shifted inverse solve and residual norm.
                        eigenvalues,vectors=eigh(k.toarray(),m.toarray())
                        shift=report['shift_per_m2'];mu=1/((TAU*solution.frequencies_hz/C0)**2+shift)
                        amplitude=vectors.T @ (m @ projection.coefficients)
                        expected=np.sqrt(np.sum(((1/(eigenvalues[:,None]+shift)-mu)*amplitude)**2,axis=0)/np.sum(amplitude**2,axis=0))
                        actual=np.asarray(report['inverse_residual_m2'])
                        residual_difference=float(np.max(abs(actual-expected)/mu));assert residual_difference<1e-10
                        frequency=np.sqrt(np.maximum(eigenvalues,0))*C0/TAU
                        contained=[]
                        for a,b in report['nearby_comparison_frequency_intervals_hz']:
                            count=int(np.sum((frequency>=a)&(True if b is None else frequency<=b)));assert count>=1;contained.append(count)
                        if axis:assert eigenvalues[0]>0
                        else:
                            assert abs(eigenvalues[0])<1e-8*eigenvalues[1]
                            constant=np.ones(m.shape[0]);overlap=abs(constant @ (m @ vectors[:,0]))/np.sqrt(constant @ (m @ constant));assert abs(overlap-1)<1e-10
                        key=order,n
                        summary=np.array([report['relative_inverse_residual'],report['projection']['relative_mass_error']])
                        intervals=np.array([[a,np.nan if b is None else b] for a,b in report['nearby_comparison_frequency_intervals_hz']])
                        if scale==1:baseline[key]=(summary,intervals)
                        else:
                            old,old_intervals=baseline[key];similarity.append(float(np.max(abs(summary-old))))
                            np.testing.assert_array_equal(np.isnan(intervals),np.isnan(old_intervals))
                            finite=np.isfinite(intervals)&(old_intervals>0)
                            similarity.append(float(np.max(abs(intervals[finite]*scale/old_intervals[finite]-1),initial=0.)))
                        records.append(dict(axis=axis,holes=holes,scale=scale,order=order,comparison_subdivision=n,
                            spectral_expansion_residual_difference=residual_difference,contained_eigenvalues=contained,diagnostic=report))
                print('DONE',axis,holes,scale,flush=True)
    for path,digest in native_hashes.items():assert hashlib.sha256((out/path).read_bytes()).hexdigest()==digest
    assert max(similarity)<1e-9 and fingerprints()==before
    report=dict(status='PASS',original_fem_native=24,comparison_full_spectra=len(records),records=records,
        max_spectral_expansion_difference=max(r['spectral_expansion_residual_difference'] for r in records),
        max_similarity_difference=max(similarity),native_files_unchanged=len(native_hashes),source_sha256=before,seconds=time.monotonic()-started,
        scope='finite comparison eigenspectra and numerical residuals only; no continuous-spectrum enclosure or rank identification')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:report[k] for k in ('status','original_fem_native','comparison_full_spectra','max_spectral_expansion_difference','max_similarity_difference','seconds')})


if __name__=='__main__':main()
