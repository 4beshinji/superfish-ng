# SPDX-License-Identifier: Apache-2.0
"""Validate polygon FEM against independent sine/cosine triangle solutions.

These analytical functions are verification only, never a solver replacement.
"""
import hashlib,json,time
from pathlib import Path
import numpy as np
from superfish_ng.planar import solve_planar,planar_quantities
from superfish_ng.planar_mesh import PlanarMesh
from superfish_ng.planar_polygon import PlanarPolygonCase
from superfish_ng.constants import C0,EPS0,MU0,TAU
from superfish_ng.fem import triangle_quadrature
import argparse
parser=argparse.ArgumentParser(description='Independent right-triangle Cartesian cutoff f, field and wall-loss validation')
parser.add_argument('--out',type=Path,required=True)
parser.add_argument('--p1-levels',nargs='+',type=int,default=[32,96,448])
parser.add_argument('--p2-levels',nargs='+',type=int,default=[16,32,64])
parser.add_argument('--scales',nargs='+',type=float,default=[1.,2.])
args=parser.parse_args()
if any(levels!=sorted(set(levels)) or min(levels)<2 for levels in (args.p1_levels,args.p2_levels)):
 parser.error('mesh levels must be unique increasing integers >=2')
if not np.isfinite(args.scales).all() or min(args.scales)<=0 or len(set(args.scales))!=len(args.scales):
 parser.error('scales must be unique finite positive numbers')
root=Path(__file__).resolve().parents[1];out=args.out;out.mkdir(parents=True,exist_ok=False)
source={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((root/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
rows=[];started=time.monotonic()
def analytic(points,m,n,pol):
 x,y=points.T;mx=m*np.pi/a;ny=n*np.pi/a
 if pol=='tm':
  q=np.sin(mx*x)*np.sin(ny*y)-np.sin(ny*x)*np.sin(mx*y)
  dx=mx*np.cos(mx*x)*np.sin(ny*y)-ny*np.cos(ny*x)*np.sin(mx*y)
  dy=ny*np.sin(mx*x)*np.cos(ny*y)-mx*np.sin(ny*x)*np.cos(mx*y)
  norm=a*a/4
 else:
  q=np.cos(mx*x)*np.cos(ny*y)+np.cos(ny*x)*np.cos(mx*y)
  dx=-mx*np.sin(mx*x)*np.cos(ny*y)-ny*np.sin(ny*x)*np.cos(mx*y)
  dy=-ny*np.cos(mx*x)*np.sin(ny*y)-mx*np.cos(ny*x)*np.sin(mx*y)
  norm=a*a/2 if n==0 or m==n else a*a/4
 factor=np.sqrt(2/(norm*(EPS0 if pol=='tm' else MU0)))
 return q*factor,np.column_stack((dx,dy))*factor
for scale in args.scales:
 a=.2*scale
 for order,levels in ((1,args.p1_levels),(2,args.p2_levels)):
  for pol in ('te','tm'):
   modes=sorted([(m*m+n*n,m,n) for m in range(1,8) for n in range(0,m+1) if pol=='te' or 0<n<m])[:4]
   for level in levels:
    coordinates=[(i,j) for i in range(level+1) for j in range(i+1)];lookup={v:k for k,v in enumerate(coordinates)}
    points=np.array(coordinates,dtype=float)*(a/level);cells=[]
    for i in range(level):
     for j in range(i+1):
      cells.append([lookup[(i,j)],lookup[(i+1,j)],lookup[(i+1,j+1)]])
      if j<i:cells.append([lookup[(i,j)],lookup[(i+1,j+1)],lookup[(i,j+1)]])
    polygon=points[[lookup[(0,0)],lookup[(level,0)],lookup[(level,level)]]]
    geometry=PlanarMesh.create(polygon,points,cells)
    solution=solve_planar(PlanarPolygonCase(geometry,pol,order,4))
    space=solution.space;mode_rows=[]
    for mode,(number,m,n) in enumerate(modes):
     exact_frequency=C0/(2*a)*np.sqrt(number);omega=TAU*exact_frequency
     # Volume scalar and derivative errors use a single common physical sign.
     overlap=0.;scalar_den=0.;grad_den=0.;scalar_num=0.;grad_num=0.;transverse_num=0.
     batches=[]
     for bary,w in triangle_quadrature(5):
      xy=np.einsum('j,tjk->tk',bary,points[space.triangles]);q,g=analytic(xy,m,n,pol)
      fields=solution.fields_in_cells(np.arange(len(cells)),np.broadcast_to(bary,(len(cells),3)),mode)
      material=EPS0 if pol=='te' else MU0
      scalar=fields['Hz_real_A_per_m'] if pol=='te' else fields['Ez_real_V_per_m']
      actual_omega=TAU*solution.frequencies_hz[mode]
      grad=(np.column_stack((fields['Ey_quadrature_V_per_m'],-fields['Ex_quadrature_V_per_m']))*actual_omega*material if pol=='te' else np.column_stack((-fields['Hy_quadrature_A_per_m'],fields['Hx_quadrature_A_per_m']))*actual_omega*material)
      weight=w*space.determinants;overlap+=np.sum(weight*q*scalar)
      batches.append((weight,q,g,scalar,grad))
     sign=np.sign(overlap)
     for weight,q,g,scalar,grad in batches:
      scalar_den+=np.sum(weight*q*q);grad_den+=np.sum(weight*np.sum(g*g,axis=1))
      scalar_num+=np.sum(weight*(scalar*sign-q)**2);grad_num+=np.sum(weight*np.sum((grad*sign-g)**2,axis=1))
      transverse_num+=np.sum(weight*np.sum((grad*sign*omega/actual_omega-g)**2,axis=1))
     # Independent analytic wall integration on three declared straight walls.
     nodes,weights=np.polynomial.legendre.leggauss(80);t=(nodes+1)/2;weights=weights/2;wall=0.
     for u,v in zip(polygon,np.roll(polygon,-1,axis=0)):
      q,g=analytic(u[None,:]*(1-t[:,None])+v[None,:]*t[:,None],m,n,pol)
      tangent=(v-u)/np.linalg.norm(v-u)
      h=q if pol=='te' else (g[:,1]*tangent[0]-g[:,0]*tangent[1])/(omega*MU0)
      wall+=np.linalg.norm(v-u)*np.sum(weights*h*h)
     if pol=='tm':closed_wall=8*(1+1/np.sqrt(2))/(a*MU0)
     elif n==0:closed_wall=4*(3+2*np.sqrt(2))/(a*MU0)
     elif m==n:closed_wall=4*(4+1.5*np.sqrt(2))/(a*MU0)
     else:closed_wall=8*(2+np.sqrt(2))/(a*MU0)
     assert abs(wall/closed_wall-1)<1e-12
     exact_g=2*omega/closed_wall;rf=planar_quantities(solution,mode)
     assert abs(rf['stored_energy_j_per_m']-1)<1e-10
     row=dict(mode=mode+1,m=m,n=n,frequency_error=abs(solution.frequencies_hz[mode]/exact_frequency-1),scalar_error=float(np.sqrt(scalar_num/scalar_den)),gradient_error=float(np.sqrt(grad_num/grad_den)),transverse_field_error=float(np.sqrt(transverse_num/grad_den)),geometry_factor_error=abs(rf['geometry_factor_ohm']/exact_g-1))
     mode_rows.append(row)
    row=dict(order=order,polarization=pol,scale=scale,a_m=a,n=level,triangles=len(cells),modes=mode_rows);rows.append(row);print(json.dumps(row),flush=True)
    (out/'partial.json').write_text(json.dumps(rows,indent=2)+'\n')
assert source=={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in source}
finest=[row for row in rows if row['n']==(args.p1_levels[-1] if row['order']==1 else args.p2_levels[-1])]
passed=all(r['frequency_error']<1e-4 and max(r['scalar_error'],r['transverse_field_error'])<.01 and r['geometry_factor_error']<.005 for row in finest for r in row['modes'])
report=dict(passed=passed,rows=rows,seconds=time.monotonic()-started,source_sha256=source,source_unchanged=True)
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
if not passed:raise SystemExit('finest independent triangle f/field/G gates not all met; refine without relaxing the limits')
