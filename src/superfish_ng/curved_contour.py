# SPDX-License-Identifier: Apache-2.0
"""Validated axis-connected analytic curve boundary, independent of FEM order."""
from dataclasses import dataclass,replace
import math
import numpy as np
from .conics import LineSegment,EllipseArc,HyperbolaArc,check_curve_join
from .curve_bounds import curve_bounds,certify_curve_separation,certify_adjacent_curves


def split_curve(curve):
    if isinstance(curve,LineSegment):
        midpoint = tuple(map(float,curve.evaluate(.5)['points_zr_m']))
        return LineSegment(curve.start_zr_m,midpoint),LineSegment(midpoint,curve.end_zr_m)
    if isinstance(curve,EllipseArc):
        return (replace(curve,sweep_rad=curve.sweep_rad/2),
                replace(curve,start_rad=curve.start_rad+curve.sweep_rad/2,sweep_rad=curve.sweep_rad/2))
    midpoint = (curve.start_parameter+curve.end_parameter)/2
    return replace(curve,end_parameter=midpoint),replace(curve,start_parameter=midpoint)


@dataclass(frozen=True)
class CurvedContour:
    curves: tuple
    edge_tags: tuple
    join_tolerance_m: float
    minimum_gap_m: float = 0.

    def __post_init__(self):
        if not isinstance(self.curves,(list,tuple)) or len(self.curves)<2 or any(
                not isinstance(c,(LineSegment,EllipseArc,HyperbolaArc)) for c in self.curves):
            raise ValueError('curved contour requires at least two supported primitives')
        if not isinstance(self.edge_tags,(list,tuple)) or len(self.edge_tags)!=len(self.curves) or any(
                tag not in ('axis','pec','electric_symmetry','magnetic_symmetry') for tag in self.edge_tags):
            raise ValueError('curved contour requires one supported tag per primitive')
        for key in ('join_tolerance_m','minimum_gap_m'):
            x = getattr(self,key)
            if type(x) not in (int,float) or not math.isfinite(x) or x<0:
                raise ValueError(f'{key} must be finite and nonnegative')
        object.__setattr__(self,'curves',tuple(self.curves))
        object.__setattr__(self,'edge_tags',tuple(self.edge_tags))
        for a,b in zip(self.curves,self.curves[1:]+self.curves[:1]):
            check_curve_join(a,b,position_tolerance_m=self.join_tolerance_m,require_tangent=False)
        axis = [i for i,t in enumerate(self.edge_tags) if t=='axis']
        if not axis or len(axis)==len(self.curves):
            raise ValueError('curved contour requires an axis chain and physical walls')
        starts = [i for i in axis if (i-1)%len(self.curves) not in axis]
        if len(starts)!=1:
            raise ValueError('curved contour axis must be one contiguous chain')
        axis_segments = []
        for i in axis:
            curve = self.curves[i]
            if not isinstance(curve,LineSegment) or curve.start_zr_m[1]!=0 or curve.end_zr_m[1]!=0:
                raise ValueError('axis tag requires a straight segment at r=0')
            axis_segments.append(sorted((curve.start_zr_m[0],curve.end_zr_m[0])))
        axis_segments.sort()
        length = axis_segments[-1][1]
        if axis_segments[0][0]!=0 or length<=0 or any(a[1]!=b[0] for a,b in zip(axis_segments,axis_segments[1:])):
            raise ValueError('axis chain must cover [0,L] exactly without gaps or overlaps')
        if self.join_tolerance_m>1e-10*length:
            raise ValueError('join tolerance exceeds 1e-10 of axis length; do not hide physical gaps')
        for curve,tag in zip(self.curves,self.edge_tags):
            low,high = curve_bounds(curve)
            if isinstance(curve,LineSegment):
                endpoints = np.array((curve.start_zr_m,curve.end_zr_m))
                low,high = endpoints.min(axis=0),endpoints.max(axis=0)
            if low[0]<-self.join_tolerance_m or high[0]>length+self.join_tolerance_m or low[1]<-self.join_tolerance_m:
                raise ValueError('curved contour leaves z=[0,L] or r>=0 within declared tolerance')
            if tag=='axis':continue
            if isinstance(curve,LineSegment) and curve.start_zr_m[1]==curve.end_zr_m[1]==0:
                raise ValueError('r=0 line requires axis tag')
            if tag.endswith('_symmetry') and not (isinstance(curve,LineSegment)
                    and curve.start_zr_m[0]==curve.end_zr_m[0] and curve.start_zr_m[0] in (0,length)):
                raise ValueError('symmetry tag requires a straight end at z=0 or L')
        # Split each primitive to handle two-edge closed shapes: each tested
        # adjacent pair now has only one permitted shared endpoint.
        pieces = [(piece,i) for i,c in enumerate(self.curves) for piece in split_curve(c)]
        n = len(pieces)
        for i,(a,owner_a) in enumerate(pieces):
            b = pieces[(i+1)%n][0]
            certify_adjacent_curves(a,b,position_tolerance_m=self.join_tolerance_m)
            for j in range(i+1,n):
                if j==i+1 or (i==0 and j==n-1):continue
                b,owner_b = pieces[j]
                original_neighbors = ((owner_a-owner_b)%len(self.curves) in (0,1,len(self.curves)-1))
                gap = 0. if original_neighbors else self.minimum_gap_m
                certify_curve_separation(a,b,gap)
        if not math.isfinite(self.area_m2) or self.area_m2<=0:
            raise ValueError('curved contour must have positive signed area in (z,r)')

    @property
    def area_m2(self):
        return math.fsum(c.signed_line_area_m2 for c in self.curves)
