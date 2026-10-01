"""既製品の簡略形状（ヘッド・ラグ・ロッド・ホルダー受け・ボルト）。"""

from __future__ import annotations

import math

import cadquery as cq
import pytest
from gatling.params import SPEC, override
from gatling.shapes.purchased import bolt_band, bolt_flange, bolt_tip, head, holder, lug, rod


def _box(part):
    return part.val().BoundingBox()


def _inside(part, x, y, z):
    return any(s.isInside(cq.Vector(x, y, z)) for s in part.solids().vals())


def test_the_film_rests_on_the_bearing_edge_and_the_collar_hangs_outside_the_shell():
    h = head(SPEC)
    box = _box(h)
    assert h.solids().size() == 1 and (box.zmin, box.zmax) == pytest.approx((109.1905, 117.1905))
    assert box.xlen == pytest.approx(155.4, abs=1e-3)                          # フレッシュフープ外径
    assert _inside(h, 0, 0, 117.1) and not _inside(h, 0, 0, 116.9)             # 膜は z 117（エッジ頂部）から 0.19 mm だけ
    assert _inside(h, 77, 0, 112) and not _inside(h, 70, 0, 112)               # 環は縁だけで、胴の外側に垂れる
    assert not _inside(h, 76.1, 0, 112)                                         # 環の内面（r 76.2）と胴の外面（r 76）の間は空き


def test_six_lugs_stand_outside_the_shell_a_takeup_below_the_collar_with_a_bore_for_the_rod():
    part = lug(SPEC)
    box = _box(part)
    assert part.solids().size() == 6 and (box.zmin, box.zmax) == pytest.approx((69.1905, 104.1905))
    assert _inside(part, 78, 0, 80) and not _inside(part, 84, 0, 80)           # 胴の脇の箱、ロッド穴は空き
    assert not _inside(part, 75, 0, 80)                                          # 胴の中には入らない
    assert part.solids().vals()[0].Volume() == pytest.approx(16 * 16 * 35 - math.pi * 2.75**2 * 35, rel=1e-6)


def test_six_tension_rods_rise_through_the_ring_gap_past_the_ear_top():
    part = rod(SPEC)
    box = _box(part)
    assert part.solids().size() == 6 and (box.zmin, box.zmax) == pytest.approx((69.1905, 151.1905))   # 受金の上面 148.19 から 3 出る
    assert _inside(part, 84, 0, 100) and not _inside(part, 80, 0, 100)
    assert part.solids().vals()[0].Volume() == pytest.approx(math.pi * 2.75**2 * 82, rel=1e-6)
    assert _box(rod(override(SPEC, lug__rod_length=90))).zmax == pytest.approx(159.1905)


def test_the_holder_clamp_stands_on_the_pad_with_a_rod_bore_along_x():
    h = holder(SPEC)
    box = _box(h)
    assert h.solids().size() == 1 and (box.zmin, box.zmax) == pytest.approx((66, 96))
    assert (box.ymin, box.ymax) == pytest.approx((-130.5, -90.5))
    assert not _inside(h, 0, -110.5, 81) and _inside(h, 0, -110.5, 90) and _inside(h, 0, -110.5, 72)      # 穴（φ12.7）は中ほど


def test_the_flange_bolts_seat_on_the_flange_top_and_reach_the_header():
    b = bolt_flange(SPEC)
    box = _box(b)
    assert b.solids().size() == 6 and (box.zmin, box.zmax) == pytest.approx((-5, 13))       # 軸 12 + 頭 6（座面 7）
    assert _inside(b, 86 * math.cos(math.pi / 6), 43, 10) and _inside(b, 86 * math.cos(math.pi / 6), 43, 0)


def test_the_tip_bolts_seat_on_the_underside_with_the_head_below():
    b = bolt_tip(SPEC)
    box = _box(b)
    assert b.solids().size() == 6 and (box.zmin, box.zmax) == pytest.approx((-411.9 - 5, -411.9 + 6))


def test_the_band_bolts_run_along_y_through_the_tabs():
    b = bolt_band(SPEC)
    box = _box(b)
    assert b.solids().size() == 2
    assert (box.ymin, box.ymax) == pytest.approx((-5.25, 12.75))              # 軸 12（y = 6.75 → −5.25）と頭 6
    assert (box.zmin, box.zmax) == pytest.approx((31.5 - 5, 31.5 + 5))
