"""折れ線を円弧で丸めた管の経路（腕の中心線）と、その平面形。CadQuery を使わない。"""

from __future__ import annotations

import math

import pytest
from drumcad.planar import circle_overlaps, origin_distance
from drumcad.tubepath import Arc, Line, fillet, plan_polygons, tangent_length, turn_angle


def _length(path):
    return sum(p.length for p in path)


def test_a_right_angle_bend_is_rounded_by_a_quarter_circle_of_the_bend_radius():
    path = fillet([(0.0, 0.0), (100.0, 0.0), (100.0, -100.0)], 30.0)
    line_in, arc, line_out = path
    assert isinstance(arc, Arc) and arc.radius == 30.0 and arc.centre == pytest.approx((70.0, -30.0))
    assert line_in.b == pytest.approx((70.0, 0.0)) and line_out.a == pytest.approx((100.0, -30.0))   # 接点は頂点から半径ぶん手前
    assert abs(arc.a1 - arc.a0) == pytest.approx(math.pi / 2) and arc.a1 < arc.a0                      # 右に曲がる（時計回り）
    assert _length(path) == pytest.approx(70 + 30 * math.pi / 2 + 70)


def test_a_left_turn_sweeps_counterclockwise_and_a_shallow_turn_has_a_shorter_tangent():
    left = fillet([(0.0, 0.0), (100.0, 0.0), (100.0, 100.0)], 30.0)
    assert left[1].a1 > left[1].a0
    assert tangent_length(math.radians(60), 30.0) == pytest.approx(30 * math.tan(math.radians(30)))
    assert turn_angle((0.0, 0.0), (10.0, 0.0), (20.0, -10.0)) == pytest.approx(math.radians(45))
    assert turn_angle((0.0, 0.0), (10.0, 0.0), (10.0, -10.0)) == pytest.approx(math.pi / 2)


def test_the_path_is_continuous_and_a_tangent_equal_to_the_leg_leaves_a_zero_length_line():
    path = fillet([(0.0, 0.0), (30.0, 0.0), (30.0, -100.0), (-30.0, -100.0)], 30.0)
    assert [type(p) for p in path] == [Line, Arc, Line, Arc, Line]
    assert path[0].length == pytest.approx(0, abs=1e-9)                       # 最初の脚が接線の長さちょうど
    ends = [p.b if isinstance(p, Line) else p.point(1.0) for p in path[:-1]]
    starts = [p.a if isinstance(p, Line) else p.point(0.0) for p in path[1:]]
    assert all(math.dist(a, b) < 1e-9 for a, b in zip(ends, starts))


def test_the_plan_of_a_straight_leg_is_the_exact_rectangle_of_the_tube():
    (poly,) = plan_polygons([Line((0.0, 0.0), (100.0, 0.0))], 12.7)
    assert sorted(poly) == pytest.approx(sorted([(0.0, -12.7), (100.0, -12.7), (100.0, 12.7), (0.0, 12.7)]))
    assert origin_distance(poly) == 0.0 and origin_distance(plan_polygons([Line((20.0, 0.0), (100.0, 0.0))], 12.7)[0]) == pytest.approx(20)


def test_the_plan_of_a_bend_covers_the_tube_and_every_polygon_is_counterclockwise():
    path = fillet([(0.0, 0.0), (100.0, 0.0), (100.0, -100.0)], 30.0)
    polys = plan_polygons(path, 12.7)
    for poly in polys:
        area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))
        assert area > 0, poly
    arc = path[1]
    for t in (0.0, 0.13, 0.5, 0.77, 1.0):                                       # 管の外側・内側の面の点が、どれかの多角形に入る
        cx, cy = arc.point(t)
        ux, uy = (cx - arc.centre[0]) / 30.0, (cy - arc.centre[1]) / 30.0
        for offset in (-12.7, 12.7):
            p = (cx + offset * ux, cy + offset * uy)
            assert any(circle_overlaps(p, 1e-3, poly) for poly in polys), (t, offset)


def test_a_finer_step_makes_more_polygons_for_the_same_bend():
    path = fillet([(0.0, 0.0), (100.0, 0.0), (100.0, -100.0)], 30.0)
    assert len(plan_polygons(path, 12.7, 5.0)) == 1 + 18 + 1
    assert len(plan_polygons(path, 12.7, 10.0)) == 1 + 9 + 1
