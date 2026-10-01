"""クレードル（矩形フレーム・脚・ハンドル）と当て板の形状。"""

from __future__ import annotations

import cadquery as cq
import pytest
from gatling.params import SPEC, override
from gatling.shapes.mount import band, cradle, cradle_y_rear, pad


def _inside(part, x, y, z):
    return any(s.isInside(cq.Vector(x, y, z)) for s in part.solids().vals())


def _overlap(a, b):
    return cq.Compound.makeCompound(a.solids().vals()).intersect(cq.Compound.makeCompound(b.solids().vals())).Volume()


def test_the_cradle_is_one_welded_solid_that_surrounds_the_shell():
    c = cradle(SPEC)
    assert c.solids().size() == 1
    box = c.val().BoundingBox()
    assert (box.xmin, box.xmax) == pytest.approx((-123, 123))                  # 内法 196 + 25 × 2 = 246
    assert box.ymax == pytest.approx(123)                                     # 前の横桟の外面
    assert not _inside(c, 0, 0, 57)                                           # 胴の位置は空き
    assert _inside(c, 0, 110.5, 57) and _inside(c, 0, -110.5, 57)             # 前後の横桟
    assert _inside(c, 110.5, 0, 57) and _inside(c, -110.5, 0, 57)             # 左右の縦桟


def test_the_handle_extends_the_side_rails_to_a_round_grip():
    c = cradle(SPEC)
    box = c.val().BoundingBox()
    grip_y = -123 - 120
    assert box.ymin == pytest.approx(grip_y - 14)                             # グリップ φ28 の後端
    assert _inside(c, 110.5, -200, 57)                                         # 縦桟は後ろへ延びる
    assert _inside(c, 0, grip_y, 57) and _inside(c, 0, grip_y, 57 + 13)       # グリップ（丸棒）
    assert not _inside(c, 0, -200, 57)                                         # 縦桟の間は空き
    shorter = cradle(override(SPEC, cradle__handle_length=60)).val().BoundingBox()
    assert shorter.ymin == pytest.approx(-123 - 60 - 14)


def test_four_legs_and_arms_carry_the_frame_down_to_the_band():
    c = cradle(SPEC)
    corner = 110.5
    assert _inside(c, corner, corner, 40) and _inside(c, -corner, -corner, 40)     # 脚（垂直）
    box = c.val().BoundingBox()
    assert box.zmin == pytest.approx(31.5 - 3)                                    # 腕はバンドの高さ中心（31.5）
    assert _inside(c, 85, 85, 31.5) and _inside(c, -85, 85, 31.5)                 # 腕（隅から胴バンドへ）


def test_the_arms_end_on_the_band_surface_without_cutting_into_it():
    assert _overlap(cradle(SPEC), band(SPEC)) == pytest.approx(0, abs=1e-6)


def test_the_cradle_is_heavy_enough_to_matter():
    mass = sum(s.Volume() for s in cradle(SPEC).vals()) * 7.93e-3
    assert 2000 < mass < 4000                                                  # 約 3 kg。うち中実グリップ φ28 が約 1.2 kg（仕様側の直し 4）


def test_the_pad_sits_on_the_top_of_the_rear_crossbar_centre():
    p = pad(SPEC)
    box = p.val().BoundingBox()
    assert p.solids().size() == 1
    assert (box.zmin, box.zmax) == pytest.approx((60, 66))                    # フレーム上面 60 の上
    assert (box.xmin, box.xmax) == pytest.approx((-30, 30))
    assert (box.ymin, box.ymax) == pytest.approx((cradle_y_rear(SPEC) - 30, cradle_y_rear(SPEC) + 30))
    assert cradle_y_rear(SPEC) == pytest.approx(-110.5)


def test_the_pad_touches_the_cradle_without_overlapping_it():
    assert _overlap(pad(SPEC), cradle(SPEC)) == pytest.approx(0, abs=1e-6)
