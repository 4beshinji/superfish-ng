# SPDX-License-Identifier: Apache-2.0
"""Independent rectangular-hole fixtures and exact q=cos(3*pi*z/L) mode.

This is validation data generation, not a production general mesh generator.
"""
import numpy as np
from superfish_ng.constants import C0, EPS0, MU0, TAU


def rectangular_holes(n=4, holes=1, scale=1., z_offset=0.):
    if holes not in (0, 1, 2):
        raise ValueError('reference supports zero, one or two holes')
    strips = 5 if holes == 2 else 3
    a, b, length = .025*scale, .1*scale, .18*scale
    # Construct every declared corner from the actual mesh coordinates.
    r = np.linspace(a, b, strips*n+1)
    z = np.linspace(0., length, 3*n+1)+z_offset
    intervals = [] if not holes else ([(n, 2*n)] if holes == 1 else [(n, 2*n), (3*n, 4*n)])
    points = np.array([(x, y) for y in z for x in r])
    cells = []
    for j in range(3*n):
        for i in range(strips*n):
            if n <= j < 2*n and any(left <= i < right for left, right in intervals):
                continue
            p = j*len(r)+i; q = p+len(r)
            cells.extend(((p, p+1, q+1), (p, q+1, q)))
    used = np.unique(cells); indices = np.full(len(points), -1, dtype=int)
    indices[used] = np.arange(len(used))
    outer = [[r[0], z[0]], [r[-1], z[0]], [r[-1], z[-1]], [r[0], z[-1]]]
    inner = [[[r[i], z[n]], [r[i], z[2*n]], [r[j], z[2*n]], [r[j], z[n]]] for i, j in intervals]
    return dict(outer_rz_m=outer, holes_rz_m=inner, points_rz_m=points[used], triangles=indices[np.array(cells)])


def reference(mesh, energy=1., conductivity=5.8e7):
    outer, holes = np.array(mesh['outer_rz_m']), [np.array(h) for h in mesh['holes_rz_m']]
    a, z0 = outer[0]; b, z1 = outer[2]; length = z1-z0; k = 3*np.pi/length
    integral = length/2*np.log(b/a)-sum(length/6*np.log(h[2,0]/h[0,0]) for h in holes)
    amplitude = np.sqrt(energy/(MU0*np.pi*integral)); omega = C0*k
    # Each edge is integrated independently; hole orientation never subtracts loss.
    edge_walls = []
    for polygon in [outer, *holes]:
        for p, q in zip(polygon, np.roll(polygon, -1, axis=0)):
            if p[0] == q[0]:
                low, high = sorted((p[1]-z0, q[1]-z0))
                value = ((high-low)/2+(np.sin(2*k*high)-np.sin(2*k*low))/(4*k))/p[0]
            else:
                value = abs(np.log(q[0]/p[0]))*np.cos(k*(p[1]-z0))**2
            edge_walls.append(TAU*amplitude**2*value)
    walls = np.array(edge_walls); rs = np.sqrt(omega*MU0/(2*conductivity)); loss = rs*walls.sum()/2
    quantities = dict(frequency_hz=omega/TAU, stored_energy_j=energy, wall_loss_w=loss,
                      geometry_factor_ohm=2*omega*energy/walls.sum(), q0=omega*energy/loss)
    def fields(points):
        r, z = np.asarray(points).T
        return (amplitude*np.cos(k*(z-z0))/r,
                -amplitude*k*np.sin(k*(z-z0))/(omega*EPS0*r))
    return quantities, walls, fields
