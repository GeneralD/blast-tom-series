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


def test_six_cylinder_lugs_stand_outside_the_shell_each_with_a_foot_to_the_shell_and_a_bore_for_the_rod():
    part = lug(SPEC)
    box = _box(part)
    zc = (59.7905 + 94.7905) / 2                                                 # ラグの高さの中心（胴の取付穴の高さ）
    assert part.solids().size() == 6 and (box.zmin, box.zmax) == pytest.approx((59.7905, 94.7905))
    assert _inside(part, 86 + 5, 0, 80) and not _inside(part, 86 + 8.5, 0, 80)    # 本体は φ16（r 8）の縦の円筒
    assert not _inside(part, 86 + 2, 0, 80) and _inside(part, 86 + 3, 0, 80)      # ロッドの穴は φ5.5（r 2.75）
    assert _inside(part, 77, 0, zc + 5) and not _inside(part, 77, 0, zc + 7)      # 台座は φ12（r 6）で、ラグの高さの中心に軸がある
    assert _inside(part, 77, 5.5, zc) and not _inside(part, 77, 6.5, zc)
    assert not _inside(part, 75.9, 0, zc) and _inside(part, 76.1, 0, zc)          # 台座の胴側は胴の外面（r 76）で止まる
    assert not _inside(part, 75.8, 5, zc)                                          # 横にずれても胴に食い込まない（円で沿う）
    body = math.pi * (8**2 - 2.75**2) * 35
    assert body < part.solids().vals()[0].Volume() < body + math.pi * 6**2 * 10    # 本体 + 台座。台座は本体の中を数えない


def test_the_lug_is_one_solid_per_lug_even_when_the_body_reaches_the_shell():
    """本体が胴の外面にかかる（standoff が本体の半径より小さい）ときも、胴の外面で切って食い込まない。1 個 1 solid のまま。"""
    part = lug(override(SPEC, lug__standoff=5))
    assert part.solids().size() == 6
    assert not _inside(part, 75.9, 0, 80)                                          # 切らなければ本体（x 73〜89）が胴に入る


def test_the_foot_follows_its_diameter():
    thick = lug(override(SPEC, lug__foot_dia=14))
    zc = (59.7905 + 94.7905) / 2
    assert _inside(thick, 77, 0, zc + 6.5) and not _inside(thick, 77, 0, zc + 7.5)


def test_six_tension_rods_hang_from_the_ear_top_with_the_head_on_the_ear():
    """頭（φ9 × 5）が受金の上面 120.19 に載り（頭の上面 = フープの上端 125.19）、軸（φ5.5 × 50）が下へ伸びてラグに入る。"""
    part = rod(SPEC)
    box = _box(part)
    assert part.solids().size() == 6 and (box.zmin, box.zmax) == pytest.approx((70.1905, 125.1905))
    assert _inside(part, 86, 0, 100) and _inside(part, 86 + 2.7, 0, 100) and not _inside(part, 86 + 2.8, 0, 100)   # 軸
    assert _inside(part, 86 + 4.4, 0, 125) and not _inside(part, 86 + 4.6, 0, 125)                                # 頭
    assert part.solids().vals()[0].Volume() == pytest.approx(math.pi * (2.75**2 * 50 + 4.5**2 * 5), rel=1e-6)
    longer = _box(rod(override(SPEC, lug__rod_length=60)))
    assert (longer.zmin, longer.zmax) == pytest.approx((60.1905, 125.1905))     # 頭の位置は変わらず、先が下がる


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


def test_the_tip_bolts_stand_between_the_tubes_on_the_tube_circle():
    """軸 φ5 の中心は PCD 106.68 の上で、管（0°, 60°, …）から 30° ずれた方位。"""
    b, r = bolt_tip(SPEC), 53.34
    for k in range(6):
        a, t = math.radians(30 + 60 * k), math.radians(60 * k)
        assert _inside(b, r * math.cos(a), r * math.sin(a), -409), k            # 軸
        assert not _inside(b, (r + 2.6) * math.cos(a), (r + 2.6) * math.sin(a), -409), k   # 軸の外（半径 2.5）
        assert not _inside(b, r * math.cos(t), r * math.sin(t), -409), k        # 管の位置には無い


def test_the_band_bolts_run_along_y_through_the_tabs():
    b = bolt_band(SPEC)
    box = _box(b)
    assert b.solids().size() == 2
    assert (box.ymin, box.ymax) == pytest.approx((-5.25, 12.75))              # 軸 12（y = 6.75 → −5.25）と頭 6
    assert (box.zmin, box.zmax) == pytest.approx((31.5 - 5, 31.5 + 5))
    for side in (1, -1):                                                       # 軸 φ6 の中心は耳の中央 x = ±93
        assert _inside(b, side * 93, 0, 31.5)
        assert _inside(b, side * (93 + 2.9), 0, 31.5) and _inside(b, side * (93 - 2.9), 0, 31.5)
        assert not _inside(b, side * (93 + 3.1), 0, 31.5) and not _inside(b, side * (93 - 3.1), 0, 31.5)
