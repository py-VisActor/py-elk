# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright Kiel University and others. Fixed elkjs0.12.1 worker275e6caf,
# NubSpline59470-59677, HOST15/root/spline-math-source-review-01.
"""Actual clamped cubic NUBS knot insertion and Bezier control points.

The list cursor is an original narrow native adapter for this caller's
observed index mutations. No GWT collections or external spline backend.
"""
from .graph import Vec2
from .ports import _divide

_EPSILON=1.0e-6


class _Cursor:
    def __init__(self,values):self.values=values;self.index=0;self.last=-1
    def next(self):
        if self.index>=len(self.values):raise IndexError('No next element')
        self.last=self.index;self.index+=1
        return self.values[self.last]
    def previous(self):
        if self.index<=0:raise IndexError('No previous element')
        self.index-=1;self.last=self.index
        return self.values[self.index]
    def add(self,value):
        if not 0<=self.index<=len(self.values):raise IndexError('Invalid cursor position')
        self.values.insert(self.index,value);self.index+=1;self.last=-1
    def remove(self):
        if self.last==-1:raise RuntimeError('No last element')
        del self.values[self.last];self.index=self.last;self.last=-1


class _PolarControlPoint:
    def __init__(self,point,polar):
        self.cp=Vec2(point.x,point.y);self.polar_coordinate=list(polar)
    @classmethod
    def interpolate(cls,first,second,knot):
        start=first.polar_coordinate[0];end=second.polar_coordinate[-1]
        a=end-knot;b=knot-start
        point=Vec2(first.cp.x*a,first.cp.y*a)
        scaled=Vec2(second.cp.x*b,second.cp.y*b)
        point.x+=scaled.x;point.y+=scaled.y
        scale=_divide(1.0,end-start);point.x*=scale;point.y*=scale
        polar=[];needs=True
        for next_knot in first.polar_coordinate[1:]:
            if needs and next_knot-knot>_EPSILON:polar.append(knot);needs=False
            polar.append(next_knot)
        if needs:polar.append(knot)
        return cls(point,polar)


class NubSpline:
    def __init__(self,points):
        self.knot_vector=[];self.control_points=[]
        # Actual constructor mutates the caller's chain and repeats the same
        # first reference. Polar control points separately clone coordinates.
        for _ in range(len(points)-1,3):points.insert(0,points[0])
        if len(points)<4:raise ValueError('At (least dimension + 1) control points are necessary!')
        self.dimension=3;self.is_clamped=True;self.is_bezier=False
        self._uniform_knots(len(points)+self.dimension-1)
        cursor=iter(self.knot_vector);polar=[next(cursor)for _ in range(self.dimension-1)]
        for point in points:
            polar.append(next(cursor));self.control_points.append(_PolarControlPoint(point,polar))
            del polar[0]
    def _uniform_knots(self,size):
        if size<2*self.dimension:raise ValueError('The knot vector must have at least two time the dimension elements.')
        self.max_knot=1.0
        self.knot_vector.extend(0.0 for _ in range(self.dimension))
        interior=size+1-2*self.dimension
        for index in range(1,interior):self.knot_vector.append(index/interior)
        if self.is_clamped:self.knot_vector.extend(1.0 for _ in range(self.dimension))
    def _multiplicity(self,knot):
        count=0
        for current in self.knot_vector:
            difference=current-knot
            if difference>_EPSILON:return count
            elif difference>-1.0e-6:count+=1
        return count
    def _insert_knot(self,insertions,knot,controls,knots):
        multiplicity=self._multiplicity(knot)
        for insertion in range(insertions):
            knots.add(knot);new=[];second=controls.next()
            for _ in range(multiplicity+insertion,self.dimension):
                first=second;second=controls.next()
                new.append(_PolarControlPoint.interpolate(first,second,knot))
            for index in range(multiplicity+insertion,self.dimension):
                controls.previous()
                if index>multiplicity+insertion:controls.remove()
            for control in new:controls.add(control)
            if insertion<insertions-1:
                for _ in range(multiplicity+insertion,self.dimension):controls.previous()
    def to_bezier(self):
        knots=_Cursor(self.knot_vector);controls=_Cursor(self.control_points)
        if self.is_clamped:
            for _ in range(self.dimension):knots.next()
        else:
            for _ in range(self.dimension-1):knots.next();knots.remove()
        current=knots.next()
        while self.max_knot-current>_EPSILON:
            counted=current;occurrence=0
            while abs(current-counted)<_EPSILON:
                occurrence+=1;current=knots.next();controls.next()
            if occurrence<self.dimension:
                knots.previous();self._insert_knot(self.dimension-occurrence,counted,controls,knots)
                knots.next()
            controls.previous()
        if not self.is_clamped:
            for _ in range(self.dimension-1):knots.next();knots.remove()
        self.is_clamped=True;self.is_bezier=True
    def get_bezier_control_points(self):
        if not self.is_bezier:self.to_bezier()
        values=[control.cp for control in self.control_points[1:]]
        if not values:raise IndexError('No last control point')
        del values[-1]
        return values
