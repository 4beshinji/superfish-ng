# SPDX-License-Identifier: Apache-2.0
"""Validate original-cell Hphi display and probes against accepted analytical natives.

Requires existing outputs from validate_coaxial.py and validate_hphi_mesh.py.
These are full native replays, not new geometry or discretization acceptance.
"""
import argparse,csv,hashlib,json,subprocess,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng.constants import C0,EPS0,MU0
from superfish_ng.hphi_native import read_hphi_run
from superfish_ng.hphi_display import display_hphi_fields
from hphi_mesh_reference import reference


def hashes(directory):return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.iterdir() if p.is_file()}
def sources():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
 parser=argparse.ArgumentParser(description=__doc__)
 for arg in ('out','coaxial-reference','mesh-reference'):parser.add_argument('--'+arg,type=Path,required=True)
 args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False);before=sources();start=time.monotonic();records=[]
 for geometry,base in (('coaxial',args.coaxial_reference),('holes',args.mesh_reference)):
  evidence=json.loads((base/'report.json').read_text());assert evidence['status']=='PASS'
  rows=[r for r in evidence['records'] if r['final'] and (r.get('shape')=='tem' if geometry=='coaxial' else r['holes']==1)]
  assert len(rows)==4
  for row in rows:
   order,scale,n=row['order'],row['scale'],row['n'];name=f'{geometry}-p{order}-s{scale:g}'
   native=base/(f'tem-p{order}-s{scale:g}-n{n}' if geometry=='coaxial' else f'holes1-p{order}-s{scale:g}-n{n}')
   native_before=hashes(native);assert native_before==row['native_sha256'];solution=read_hphi_run(native);case=solution.case
   if geometry=='holes':expected,_,analytic=reference(case.mesh.to_dict(),case.normalization_j,case.conductivity_s_per_m)
   else:
    # Fundamental standing TEM: q=A cos(pi*z/L), Er=-(A*pi/L)/(omega*eps*r) sin(pi*z/L).
    length=case.length_m;k=np.pi/length;amplitude=np.sqrt(2*case.normalization_j/(MU0*np.pi*length*np.log(case.outer_radius_m/case.inner_radius_m)))
    expected=dict(frequency_hz=C0/(2*length))
    def analytic(points):
     r,z=np.asarray(points).T
     return amplitude*np.cos(k*z)/r,-amplitude*np.sin(k*z)/(C0*EPS0*r)
   mode=int(np.argmin(abs(solution.frequencies_hz/expected['frequency_hz']-1)))
   display=display_hphi_fields(solution,mode);triangles=display['points_rz_m'][display['triangles']];points=triangles.mean(axis=1)
   edge1=triangles[:,1]-triangles[:,0];edge2=triangles[:,2]-triangles[:,0];areas=np.abs(edge1[:,0]*edge2[:,1]-edge1[:,1]*edge2[:,0])/2
   assert abs(areas.sum()/(case.mesh.area_m2 if geometry=='holes' else (case.outer_radius_m-case.inner_radius_m)*case.length_m)-1)<1e-12
   # Integral r dA is exact from triangle centroids: this also checks holes are omitted.
   volume=2*np.pi*(areas@points[:,0]);assert abs(volume/(case.mesh.volume_m3 if geometry=='holes' else case.volume_m3)-1)<1e-12
   fields=display['fields'];h,e=analytic(points);measure=areas*points[:,0];ah=fields['Hphi_real_A_per_m'];er=fields['Er_quadrature_V_per_m'];ez=fields['Ez_quadrature_V_per_m'];sign=1 if measure@(ah*h)>=0 else -1
   errors=dict(magnetic=float(np.sqrt(measure@((sign*ah-h)**2)/(measure@(h*h)))),electric=float(np.sqrt(measure@((sign*er-e)**2+ez**2)/(measure@(e*e)))))
   assert errors['magnetic']<(.003 if order==1 else .001) and errors['electric']<(.035 if order==1 else .01),(name,errors)
   direct=solution.fields_at(points[::max(1,len(points)//17)],mode)
   probe_points=points[::max(1,len(points)//17)];point_file=args.out/(name+'-points.json');point_file.write_text(json.dumps(probe_points.tolist()))
   csv_file=args.out/(name+'.csv');png_file=args.out/(name+'.png')
   commands=[['probe-hphi-csv',str(native),'--points',str(point_file),'--mode',str(mode+1),'--out',str(csv_file)],['plot-hphi',str(native),'--mode',str(mode+1),'--length-unit','m' if scale==2 else 'mm','--out',str(png_file)]]
   for index,command in enumerate(commands):
    done=subprocess.run([sys.executable,'-m','superfish_ng',*command],capture_output=True,text=True)
    (args.out/f'{name}-{index}.log').write_text(done.stdout+done.stderr);assert done.returncode==0,done.stderr
   with csv_file.open() as stream:csv_rows=list(csv.DictReader(stream))
   assert len(csv_rows[0])==20
   for key,value in direct.items():np.testing.assert_array_equal([float(r[key]) for r in csv_rows],value)
   meta=json.loads(csv_file.with_suffix('.csv.json').read_text());plot=json.loads(png_file.with_suffix('.png.json').read_text())
   assert meta['native_sha256']==native_before==plot['native_sha256']==hashes(native)
   assert meta['data_sha256']==hashlib.sha256(csv_file.read_bytes()).hexdigest() and plot['data_sha256']==hashlib.sha256(png_file.read_bytes()).hexdigest()
   assert meta['quantities']==plot['quantities'] and meta['quantities']['r_over_q_circuit_ohm'] is None
   records.append(dict(geometry=geometry,order=order,scale=scale,mode=mode+1,samples=len(points),probe_points=len(probe_points),errors=errors,native=str(native.resolve()),native_sha256=native_before))
   print('PASS',name,errors,flush=True)
 assert sources()==before
 (args.out/'report.json').write_text(json.dumps(dict(status='PASS',records=records,source_sha256=before,seconds=time.monotonic()-start,cli_commands=16,scope='original-cell display, full SI probes, independent phase and energy; prior native accuracy gates retained'),indent=2)+'\n')


if __name__=='__main__':main()
