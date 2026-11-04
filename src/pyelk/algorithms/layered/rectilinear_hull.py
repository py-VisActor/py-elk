# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright Kiel University and others. Fixed elkjs0.12.1 worker275e6caf.
# RH01-RH05 / HOST16/V/recthull-source-review-01.json.
"""Four maximal-point sweeps and the actual rectilinear rectangle split."""
from .cell_layout import Rectangle
from .compaction_graph import _minimum
from .ports import _source_sort, double_compare


class Point:
    def __init__(self, x, y, quadrant=None):
        self.x, self.y = float(x), float(y)
        self.quadrant = quadrant
        self.convex = True


_ORDINAL = {'Q1': 0, 'Q4': 1, 'Q2': 2, 'Q3': 3}


def _left(quadrant):
    return quadrant in ('Q1', 'Q4')


def _upper(quadrant):
    return quadrant in ('Q1', 'Q2')


def _same_half(first, second):
    return (first, second) in (('Q1', 'Q4'), ('Q4', 'Q1'),
                              ('Q3', 'Q2'), ('Q2', 'Q3'))


def _left_then_right(first, second):
    return _left(first) and second in ('Q2', 'Q3')


def _compare(first, second, *, right, high):
    if first.x == second.x:
        return (double_compare(second.y, first.y) if high
                else double_compare(first.y, second.y))
    return (double_compare(first.x, second.x) if right
            else double_compare(second.x, first.x))


def _special(first, second):
    if first.x == second.x:
        if first.quadrant == second.quadrant or _same_half(first.quadrant, second.quadrant):
            value = 1 if _left(first.quadrant) else -1
            if first.convex and not second.convex:
                return value
            if not first.convex and second.convex:
                return -value
        return ((_ORDINAL[first.quadrant] > _ORDINAL[second.quadrant])
                - (_ORDINAL[first.quadrant] < _ORDINAL[second.quadrant]))
    return double_compare(first.x, second.x)


def _maximal(points, quadrant, *, right, high):
    ordered = list(points)
    _source_sort(ordered, lambda a, b: _compare(a, b, right=right, high=high))
    upper = _upper(quadrant)
    maximal_y = float('inf') if upper else -float('inf')
    result = []
    for point in ordered:
        comparison = (double_compare(maximal_y, point.y) if upper
                      else double_compare(point.y, maximal_y))
        if comparison > 0:
            result.append(Point(point.x, point.y, quadrant))
            maximal_y = point.y
    return result


def _concave(points, quadrant):
    # The first next() is unconditional in the actual source. Empty maxima
    # therefore fail here, including for an empty input collection.
    last = points[0]
    corners = [last]
    for following in points[1:]:
        corner = Point(following.x, last.y, quadrant)
        corners.extend((corner, following))
        corner.convex = False
        last = following
    points[:] = corners


class RectilinearConvexHull:
    def __init__(self):
        self.hull = []
        self.x_max1 = self.x_min1 = self.x_min2 = None
        self.y_max1 = self.y_min1 = None

    @classmethod
    def of(cls, points):
        result = cls()
        for point in points:
            if result.x_max1 is None or point.x >= result.x_max1.x:
                result.x_max1 = point
            if result.x_min1 is None or point.x <= result.x_min1.x:
                result.x_min2 = result.x_min1
                result.x_min1 = point
            if result.y_max1 is None or point.y >= result.y_max1.y:
                result.y_max1 = point
            if result.y_min1 is None or point.y <= result.y_min1.y:
                result.y_min1 = point
        q1 = _maximal(points, 'Q1', right=True, high=False)
        q4 = _maximal(points, 'Q4', right=True, high=True)
        q2 = _maximal(points, 'Q2', right=False, high=False)
        q3 = _maximal(points, 'Q3', right=False, high=True)
        _concave(q1, 'Q1')
        _concave(q2, 'Q2')
        _concave(q3, 'Q3')
        _concave(q4, 'Q4')
        result.hull.extend(q1)
        result.hull.extend(reversed(q2))
        result.hull.extend(q3)
        result.hull.extend(reversed(q4))
        return result

    def split_into_rectangles(self):
        last_x = _minimum(self.x_min1.x, self.x_min2.x)
        ordered = list(self.hull)
        _source_sort(ordered, _special)
        rectangles = []
        queued = queued_point = minimum_y = maximum_y = None
        for point in ordered:
            if queued is not None and (point.x != queued_point.x
                    or _left_then_right(queued_point.quadrant, point.quadrant)):
                rectangles.append(queued)
                last_x = queued.x + queued.width
                queued = queued_point = None
            if _upper(point.quadrant):
                minimum_y = point
            else:
                maximum_y = point
            trigger = ((point.quadrant == 'Q1' and not point.convex)
                    or (point.quadrant == 'Q2' and point.convex)
                    or (point.quadrant == 'Q3' and point.convex)
                    or (point.quadrant == 'Q4' and not point.convex))
            if trigger and minimum_y is not None and maximum_y is not None:
                queued = Rectangle(last_x, minimum_y.y,
                                   point.x - last_x, maximum_y.y - minimum_y.y)
                queued_point = point
        if queued is not None:
            rectangles.append(queued)
        return rectangles
