# SPDX-License-Identifier: Apache-2.0
"""Synthetic Bessel cylinder with zero-tangential-E rectangular conductor holes.

This independent analytical fixture is not a measured LANL/KEK cavity. The
production FEM does not import its field, roots, mesh generator or mode labels.
"""
import numpy as np
from scipy.special import jv, jn_zeros
from superfish_ng.constants import C0, EPS0, MU0, TAU


def rectangular_axis_holes(n,holes=1,scale=1.):
    R,L=.1*scale,.06*scale;roots=jn_zeros(0,2*holes+1);kr=roots[-1]/R
    cuts=np.r_[0.,roots/kr]
    r=np.r_[np.concatenate([np.linspace(a,b,n,endpoint=False) for a,b in zip(cuts,cuts[1:])]),R]
    z=np.linspace(0,L,3*n+1);points=np.array([(a,b) for b in z for a in r]);tri=[]
    for j in range(3*n):
        for i in range(len(r)-1):
            if n<=j<2*n and any((2*h+1)*n<=i<(2*h+2)*n for h in range(holes)):continue
            p=j*len(r)+i;q=p+len(r);tri.extend(((p,p+1,q+1),(p,q+1,q)))
    used=np.unique(tri);mapping=np.full(len(points),-1,dtype=int);mapping[used]=np.arange(len(used))
    outer=[[r[0],z[0]],[r[-1],z[0]],[r[-1],z[-1]],[r[0],z[-1]]]
    inner=[[[r[(2*h+1)*n],z[n]],[r[(2*h+1)*n],z[2*n]],[r[(2*h+2)*n],z[2*n]],[r[(2*h+2)*n],z[n]]] for h in range(holes)]
    return dict(outer_rz_m=outer,holes_rz_m=inner,points_rz_m=points[used],triangles=mapping[np.array(tri)])


def reference(data,energy_j=1.,conductivity_s_per_m=5.8e7):
    outer=np.asarray(data['outer_rz_m']);holes=[np.asarray(h) for h in data['holes_rz_m']]
    R,L=outer[2];kr=jn_zeros(0,2*len(holes)+1)[-1]/R;kz=3*np.pi/L;omega=C0*np.hypot(kr,kz)
    def radial(a,b):
        def p(r):return r*r/2*(jv(1,kr*r)**2-jv(0,kr*r)*jv(2,kr*r))
        return p(b)-p(a)
    def axial(a,b):return (b-a)/2+(np.sin(2*kz*b)-np.sin(2*kz*a))/(4*kz)
    mass=radial(0.,R)*axial(0.,L)-sum(radial(h[0,0],h[2,0])*axial(h[0,1],h[2,1]) for h in holes)
    A=np.sqrt(energy_j/(MU0*np.pi*mass))
    def fields(rz):
        r,z=np.asarray(rz).T
        return (A*jv(1,kr*r)*np.cos(kz*z),
            -A*kz/(omega*EPS0)*jv(1,kr*r)*np.sin(kz*z),
            -A*kr/(omega*EPS0)*jv(0,kr*r)*np.cos(kz*z))
    walls=[]
    for contour in (outer,*holes):
        for a,b in zip(contour,np.roll(contour,-1,axis=0)):
            if a[0]==b[0]:wall=TAU*A*A*a[0]*jv(1,kr*a[0])**2*axial(min(a[1],b[1]),max(a[1],b[1]))
            else:
                assert a[1]==b[1]
                wall=TAU*A*A*np.cos(kz*a[1])**2*radial(min(a[0],b[0]),max(a[0],b[0]))
            walls.append(float(wall))
    f=omega/TAU;rs=np.sqrt(np.pi*f*MU0/conductivity_s_per_m);loss=rs*sum(walls)/2
    wave=omega/C0;line=L/2*sum(np.exp(1j*v*L/2)*np.sinc(v*L/(2*np.pi)) for v in (wave+kz,wave-kz))
    voltage=-1j*A*kr/(omega*EPS0)*line;rq=abs(voltage)**2/(omega*energy_j)
    return dict(frequency_hz=f,stored_energy_j=energy_j,electric_energy_j=energy_j/2,magnetic_energy_j=energy_j/2,
        geometry_factor_ohm=2*omega*energy_j/sum(walls),q0=omega*energy_j/loss,wall_loss_w=loss,
        r_over_q_accelerator_ohm=rq,r_over_q_circuit_ohm=rq/2),np.array(walls),complex(voltage),fields
