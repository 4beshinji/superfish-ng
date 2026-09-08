# SPDX-License-Identifier: Apache-2.0
"""Validated axis-connected analytic curve boundary, independent of FEM order."""
from dataclasses import dataclass,replace
import math
import numpy as np
from .conics import LineSegment,EllipseArc,HyperbolaArc,check_curve_join,curve_to_dict,curve_from_dict
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

    @property
    def volume_m3(self):
        from .curve_moments import revolution_volume_contribution
        return math.fsum(revolution_volume_contribution(c) for c in self.curves)

    def reflected(self):
        """Reflect one entire flat symmetry end, retaining analytic primitives."""
        symmetry = [i for i,tag in enumerate(self.edge_tags) if tag.endswith('_symmetry')]
        if not symmetry:
            raise ValueError('curved reflection requires one symmetry end')
        planes = {self.curves[i].start_zr_m[0] for i in symmetry}
        tags = {self.edge_tags[i] for i in symmetry}
        if len(planes)!=1 or len(tags)!=1:
            raise ValueError('curved reflection requires one consistent symmetry end')
        plane = next(iter(planes))
        for i,curve in enumerate(self.curves):
            if isinstance(curve,LineSegment) and curve.start_zr_m[0]==curve.end_zr_m[0]==plane and i not in symmetry:
                raise ValueError('curved reflection plane has mixed wall and symmetry tags')
        n = len(self.curves)
        starts = [i for i in range(n) if i not in symmetry and (i-1)%n in symmetry]
        if len(starts)!=1:
            raise ValueError('curved reflection requires a connected seam')
        remaining = []
        index = starts[0]
        while index not in symmetry:
            remaining.append(index)
            index = (index+1)%n
        if len(remaining)+len(symmetry)!=n:
            raise ValueError('curved reflection has disconnected boundary pieces')
        length = max(max(c.start_zr_m[0],c.end_zr_m[0]) for c,t in zip(self.curves,self.edge_tags) if t=='axis')
        shift = length if plane==0 else 0.
        def transformed(curve,mirror):
            def point(p):return (float(2*plane-p[0]+shift if mirror else p[0]+shift),float(p[1]))
            if isinstance(curve,LineSegment):
                a,b = (curve.end_zr_m,curve.start_zr_m) if mirror else (curve.start_zr_m,curve.end_zr_m)
                return LineSegment(point(a),point(b))
            changes = dict(center_zr_m=point(curve.center_zr_m))
            if mirror:
                changes['rotation_rad'] = -curve.rotation_rad
                if isinstance(curve,EllipseArc):
                    changes['start_rad'] = math.pi-(curve.start_rad+curve.sweep_rad)
                else:
                    changes.update(branch=-curve.branch,start_parameter=curve.end_parameter,end_parameter=curve.start_parameter)
            return replace(curve,**changes)
        curves = tuple(transformed(self.curves[i],False) for i in remaining)+tuple(transformed(self.curves[i],True) for i in reversed(remaining))
        tags = tuple(self.edge_tags[i] for i in remaining)+tuple(self.edge_tags[i] for i in reversed(remaining))
        return CurvedContour(curves,tags,self.join_tolerance_m,self.minimum_gap_m)

    def to_dict(self):
        curves = [curve_to_dict(curve) for curve in self.curves]
        return dict(curves=curves,edge_tags=list(self.edge_tags),join_tolerance_m=self.join_tolerance_m,
                    minimum_gap_m=self.minimum_gap_m)

    @classmethod
    def from_dict(cls,data):
        from .config import keys
        keys(data,('curves','edge_tags','join_tolerance_m','minimum_gap_m'),
             ('curves','edge_tags','join_tolerance_m'),'curved contour')
        if not isinstance(data['curves'],list):raise ValueError('curves must be an array')
        curves = [curve_from_dict(row) for row in data['curves']]
        return cls(tuple(curves),data['edge_tags'],data['join_tolerance_m'],data.get('minimum_gap_m',0.))

    def linearize(self,tolerance_m,*,max_segments=20000):
        """Produce a tagged polygon with explicit, bounded join adjustments.

        Original primitives remain unchanged. Any endpoint displacement is
        charged to the error budget before choosing the curve's chord size.
        max_segments limits the entire polygon, not each individual primitive.
        """
        from .contour import Contour
        if type(tolerance_m) not in (int,float) or not math.isfinite(tolerance_m) or tolerance_m<=0:
            raise ValueError('curve linearization tolerance must be finite and positive')
        if type(max_segments) is not int or max_segments<3:
            raise ValueError('max_segments must be an integer >= 3')
        joins = []
        for i,current in enumerate(self.curves):
            previous = self.curves[i-1]
            start = current.evaluate(0.)['points_zr_m']
            end = previous.evaluate(1.)['points_zr_m']
            # Keep exact axis/end-plane coordinates of straight primitives.
            if isinstance(current,LineSegment):point = start
            elif isinstance(previous,LineSegment):point = end
            else:point = start+(end-start)/2
            joins.append(point)
        shifts = []
        for i,curve in enumerate(self.curves):
            ends = curve.evaluate([0.,1.])['points_zr_m']
            shifts.append(float(np.max(np.linalg.norm(ends-np.asarray((joins[i],joins[(i+1)%len(joins)])),axis=1))))
        maximum_shift = max(shifts)
        if maximum_shift>=tolerance_m:
            raise ValueError('curve join adjustment consumes chord error budget; use a larger tolerance')
        chord_tolerance = tolerance_m-maximum_shift
        vertices,tags,owners,intervals = [],[],[],[]
        for i,(curve,tag) in enumerate(zip(self.curves,self.edge_tags)):
            remaining = max_segments-len(vertices)
            if remaining<1:
                raise ValueError('curve linearization exceeds total max_segments')
            points = curve.linearize(chord_tolerance,max_segments=remaining).copy()
            points[0],points[-1] = joins[i],joins[(i+1)%len(joins)]
            vertices.extend(tuple(map(float,p)) for p in points[:-1])
            tags.extend([tag]*(len(points)-1))
            owners.extend([i]*(len(points)-1))
            parameters = np.linspace(0.,1.,len(points))
            intervals.extend(zip(parameters[:-1].tolist(),parameters[1:].tolist()))
        polygon = Contour(tuple(vertices),tuple(tags))  # Recheck chords, gaps, tags and axis.
        # The validated analytic curve runs CCW. Reject a topology-changing
        # approximation instead of accepting Contour's orientation repair.
        p = np.asarray(vertices)
        q = np.roll(p,-1,axis=0)
        if np.sum(p[:,0]*q[:,1]-p[:,1]*q[:,0])<=0:
            raise ValueError('chord polygon reverses orientation; reduce tolerance')
        offset = vertices.index(polygon.vertices_zr_m[0])
        owners = owners[offset:]+owners[:offset]
        intervals = intervals[offset:]+intervals[:offset]
        return ChordApproximation(polygon,tolerance_m,chord_tolerance,tuple(shifts),tuple(owners),self.area_m2,tuple(intervals))


@dataclass(frozen=True)
class ChordApproximation:
    contour: object
    tolerance_m: float
    primitive_chord_tolerance_m: float
    endpoint_adjustments_m: tuple
    segment_curve_indices: tuple
    analytic_area_m2: float
    segment_parameter_intervals: tuple

    @property
    def area_difference_m2(self):
        return self.contour.area_m2-self.analytic_area_m2
