# SPDX-License-Identifier: Apache-2.0
"""Full N05 cylinder/sphere reference grids; never produce native FEM fields.

The curved comparison uses the established full radial-fan sqrt-volume-density
L2 convention. Physical cylindrical components are retained. This is neither
Maxwell push-forward, boundary reprojection nor amplitude fitting.
"""
from copy import deepcopy
import hashlib
import json
import math

import numpy as np
from scipy.special import j0, j1

from .adaptive_efficiency_fields import COMPONENTS
from .adaptive_efficiency_plan import build_adaptive_efficiency_plan
from .analytic import pillbox_tm_mode, pillbox_tm010
from .analytic_sphere import SphereTM
from .config import Case
from .constants import MU0
from .curved_space import case_curved_space
from .mesh import make_mesh
from .mesh_input import mesh_from_dict, mesh_to_dict


def _hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def build_analytic_efficiency_grid(case_id, case, source_mesh, *, order=16):
    """Build a full analytical volume/axis grid bound to the original P2 domain.

    Only the two fixed N05 initial cases and their exact source mesh are
    supported. Curved refinement is subsequently allowed only after the caller
    verifies whole P2 boundary/source/Case and actual individual-mode IDs.
    All reference points and both domains are retained; no 0.95-volume crop.
    """
    if case_id not in ('cylinder','sphere') or type(order) is not int or order not in (16,24):
        raise ValueError('analytic efficiency grid supports fixed N05 cylinder/sphere and orders 16/24; rounded case requires saved independent reference')
    if not isinstance(case,Case):
        raise ValueError('analytic efficiency grid requires the complete original Case')
    plan = build_adaptive_efficiency_plan()
    request = next(row['request'] for row in plan['cases'] if row['id']==case_id)
    if case != Case.from_dict(request['case']):
        raise ValueError('analytic efficiency grid Case differs from the complete fixed N05 initial Case')
    mesh_hash = _hash(source_mesh)
    expected = mesh_to_dict(make_mesh(case)) if request['initial_mesh'] is None else request['initial_mesh']
    if source_mesh != expected:
        raise ValueError('analytic efficiency grid source mesh differs from the fixed N05 full initial mesh')
    mesh = mesh_from_dict(case,source_mesh)
    x,w = np.polynomial.legendre.leggauss(order)
    s = (x+1)/2
    points, native_points, weights, density, axis, axis_weights, partitions = [],[],[],[],[],[],[]
    if case_id=='cylinder':
        radius = case.profile[0][1]
        for z0,z1 in zip(np.linspace(0,case.length,case.nz+1)[:-1],np.linspace(0,case.length,case.nz+1)[1:]):
            z = z0+(z1-z0)*s
            dz = (z1-z0)*w/2
            axis.append(np.column_stack((np.zeros(order),z)))
            axis_weights.append(dz)
            for r0,r1 in zip(np.linspace(0,radius,case.nr+1)[:-1],np.linspace(0,radius,case.nr+1)[1:]):
                r = r0+(r1-r0)*s
                points.append(np.column_stack((np.broadcast_to(r[None,:],(order,order)).ravel(),
                                               np.broadcast_to(z[:,None],(order,order)).ravel())))
                weights.append((2*math.pi*r[None,:]*(r1-r0)*w[None,:]/2*dz[:,None]).ravel())
        analytic_volume = math.pi*radius**2*case.length
        q = pillbox_tm_mode(radius,case.length,beta=case.beta,
                            conductivity_s_per_m=case.conductivity_s_per_m,normalization_j=case.normalization_j)
        peaks = pillbox_tm010(radius,case.length,case.beta,case.conductivity_s_per_m)
        q['epk_over_eacc'] = peaks['epk_over_eacc_estimate']
        q['bpk_over_eacc_mt_per_mv_per_m'] = peaks['bpk_over_eacc_estimate_mt_per_mv_per_m']
        reference_kind = 'independent Bessel TM010; full cylinder and both PEC end plates'
    else:
        space = case_curved_space(case,mesh)
        geometry = space.geometry
        curve = case.curved_contour.to_dict()['curves'][1]
        assert curve['type']=='ellipse_arc' and curve['rotation_rad']==0.
        zc,rc = curve['center_zr_m'];a,b = curve['semiaxes_m']
        low,sweep = curve['start_rad'],curve['sweep_rad']
        entries = []
        for index in np.flatnonzero(geometry.boundary_curve_indices==1):
            first,last = map(float,geometry.boundary_parameters[index])
            entries.append((min(first,last),max(first,last),first,last,int(index)))
        entries.sort()
        if (not entries or abs(entries[0][0])>1e-13 or abs(entries[-1][1]-1)>1e-13 or
                any(abs(previous[1]-current[0])>1e-13 for previous,current in zip(entries,entries[1:]))):
            raise ValueError('full native wall parameter partition has a gap or overlap')
        for lo,hi,first,last,index in entries:
            span = last-first
            if abs(span)<=512*np.finfo(float).eps:
                raise ValueError('native radial-fan parameter interval UNVERIFIED at roundoff scale')
            nodes = geometry.points_rz_m[geometry.boundary_nodes[index]]
            for end in (0.,1.):
                dzdf = (np.array((4*end-3,4*end-1,4-8*end))@nodes/span)[1]
                if dzdf>512*np.finfo(float).eps*case.length:
                    raise ValueError('native full radial wall fan folds in z')
            fraction = lo+(hi-lo)*s
            theta = low+sweep*fraction
            z = zc+a*np.cos(theta)
            radius = rc+b*np.sin(theta)
            analytic_dzdf = abs(a*np.sin(theta)*sweep)
            dz = analytic_dzdf*(hi-lo)*w/2
            t = (fraction-first)/span
            basis = np.column_stack((2*(t-.5)*(t-1),2*t*(t-.5),4*t*(1-t)))
            derivative = np.column_stack((4*t-3,4*t-1,4-8*t))@nodes/span
            wall = basis@nodes
            if (np.any(radius<=0) or np.any(wall[:,0]<=0) or np.any(analytic_dzdf<=0) or
                    np.any(derivative[:,1]>=0) or np.any(dz<=0)):
                raise ValueError('native radial-fan density or z monotonicity UNVERIFIED')
            r = radius[:,None]*s[None,:]
            native_r = wall[:,0,None]*s[None,:]
            points.append(np.column_stack((r.ravel(),np.broadcast_to(z[:,None],r.shape).ravel())))
            native_points.append(np.column_stack((native_r.ravel(),np.broadcast_to(wall[:,1,None],r.shape).ravel())))
            weights.append((2*math.pi*r*radius[:,None]*dz[:,None]*w[None,:]/2).ravel())
            ratio = (wall[:,0]/radius)**2*abs(derivative[:,1])/analytic_dzdf
            density.append(np.broadcast_to(ratio[:,None],r.shape).ravel())
            axis.append(np.column_stack((np.zeros(order),z)));axis_weights.append(dz)
            partitions.append([lo,hi])
        radius = a
        analytic_volume = 4*math.pi*radius**3/3
        reference = SphereTM(radius,beta=case.beta,conductivity_s_per_m=case.conductivity_s_per_m,
                             normalization_j=case.normalization_j)
        q = reference.quantities()
        eacc = abs(complex(q['voltage_real_v'],q['voltage_imag_v']))/case.length
        # l=1 PEC radial E is proportional to cos(theta), Hphi to sin(theta).
        # Their exact boundary maxima are at a pole and the equator respectively.
        pole = reference.fields([[0.,0.]])['Ez_quadrature_V_per_m'][0]
        equator = reference.fields([[radius,radius]])['Hphi_A_per_m'][0]
        q['epk_over_eacc'] = float(abs(pole)/eacc)
        q['bpk_over_eacc_mt_per_mv_per_m'] = float(MU0*abs(equator)/eacc*1e9)
        reference_kind = 'independent SphereTM first regular l=1 m=0 root; full sphere/axis/PEC wall'
    points,weights,axis,axis_weights = (np.concatenate(v) for v in (points,weights,axis,axis_weights))
    if case_id=='cylinder':
        native_points = points.copy();density = np.ones(len(weights))
        fields = np.column_stack((np.zeros(len(points)),q['e0_v_per_m']*j0(q['radial_wave_number_per_m']*points[:,0]),
                                  q['h0_a_per_m']*j1(q['radial_wave_number_per_m']*points[:,0])))
        axis_ez = np.full(len(axis),q['e0_v_per_m'])
    else:
        native_points = np.concatenate(native_points);density = np.concatenate(density)
        fields = np.column_stack([reference.fields(points)[k] for k in COMPONENTS])
        axis_ez = reference.fields(axis)['Ez_quadrature_V_per_m']
    if (any(not np.isfinite(v).all() for v in (points,native_points,weights,density,axis,axis_weights,fields,axis_ez)) or
            np.any(weights<=0) or np.any(density<=0) or np.any(axis_weights<=0) or
            abs(float(weights.sum())/analytic_volume-1)>1e-12 or abs(float(axis_weights.sum())/case.length-1)>1e-12):
        raise ValueError('complete analytic/native grid, volume or axis coverage UNVERIFIED')
    if _hash(source_mesh)!=mesh_hash:
        raise ValueError('initial source mesh changed during analytic reference construction')
    return dict(case_id=case_id,case=case.to_dict(),source_mesh=deepcopy(source_mesh),source_mesh_canonical_sha256=mesh_hash,
                fixed_input_sources=deepcopy(plan['input_sources']),order=order,reference_kind=reference_kind,
                analytic_volume_points_rz_m=points,native_volume_points_rz_m=native_points,volume_weights_m3=weights,
                native_volume_density_ratio=density,axis_points_rz_m=axis,axis_weights_m=axis_weights,
                reference_fields=fields,reference_axis_ez=axis_ez,reference_quantities=q,
                native_wall_parameter_partitions=partitions,component_order=list(COMPONENTS),analytic_volume_m3=analytic_volume,
                physical_error_bound=None,physical_acceptance_status='NATIVE_SOURCE_DOMAIN_ID_CHECKS_REQUIRED',
                scope='full analytic and actual initial native volume/physical axis; finite Gauss16/24; unitary sqrt volume density with fixed cylindrical components; no fit/crop/discarded nodes, native solve, reprojection or physical-error bound')
