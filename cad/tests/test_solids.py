"""形状関数が共有する小さな部品（円盤・環・円柱・まとめ・回転複製）。"""

from __future__ import annotations

import math

import cadquery as cq
import pytest
from drumcad.solids import around_z, compound, cylinder, cylinders, disc, ring


def _volume(part):
    return sum(s.Volume() for s in part.vals())


def test_a_disc_and_a_ring_span_the_given_heights():
    d, r = disc(10, -2, 3), ring(10, 6, -2, 3)
    assert _volume(d) == pytest.approx(math.pi * 100 * 5) and _volume(r) == pytest.approx(math.pi * (100 - 36) * 5)
    box = r.val().BoundingBox()
    assert (box.zmin, box.zmax) == pytest.approx((-2, 3)) and box.xlen == pytest.approx(20)
    box = d.val().BoundingBox()
    assert (box.zmin, box.zmax) == pytest.approx((-2, 3)) and box.xlen == pytest.approx(20)


def test_cylinders_stand_one_solid_on_each_point():
    c = cylinders([(0, 0), (20, 0), (0, 20)], 6, 1, 4)
    assert c.solids().size() == 3 and _volume(c) == pytest.approx(3 * math.pi * 9 * 3)
    box = c.val().BoundingBox()
    assert box.xmax == pytest.approx(23) and (box.zmin, box.zmax) == pytest.approx((1, 4))


def test_a_cylinder_runs_along_any_direction_from_its_origin():
    c = cylinder((5, 0, 0), (0, 1, 0), 4, 10)
    box = c.val().BoundingBox()
    assert (box.ymin, box.ymax) == pytest.approx((0, 10)) and (box.xmin, box.xmax) == pytest.approx((3, 7))
    down = cylinder((0, 0, 2), (0, 0, -1), 4, 5).val().BoundingBox()           # 軸が −Z: 原点から下へ伸びる
    assert (down.zmin, down.zmax) == pytest.approx((-3, 2))


def test_compound_keeps_the_number_of_solids_even_when_they_touch():
    a = cq.Workplane("XY").box(10, 10, 10)
    b = cq.Workplane("XY").box(10, 10, 10).translate((10, 0, 0))        # a と面で接する
    assert a.union(b).solids().size() == 1                                # union は融合する
    assert compound([a, b]).solids().size() == 2                          # compound は数を保つ
    assert compound([cylinders([(0, 0), (30, 0)], 4, 0, 1), a]).solids().size() == 3


def test_around_z_places_a_rotated_copy_at_each_angle():
    peg = cylinders([(10, 0)], 2, 0, 5)
    ring_of_pegs = around_z(peg, [0, 90, 180, 270])
    assert ring_of_pegs.solids().size() == 4
    centres = sorted((round(s.Center().x), round(s.Center().y)) for s in ring_of_pegs.solids().vals())
    assert centres == [(-10, 0), (0, -10), (0, 10), (10, 0)]
