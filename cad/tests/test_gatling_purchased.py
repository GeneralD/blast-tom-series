"""既製品の簡略形状（ヘッド・ラグ・ロッド・ホルダー受け・ボルト）。"""

from __future__ import annotations

import math

import cadquery as cq
import pytest
from gatling.params import SPEC, override
from gatling.shapes.purchased import bolt_flange, bolt_tip, head, holder, lug, rod


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


def test_six_turret_lugs_are_discs_on_the_shell_each_with_a_vertical_bore_for_the_rod():
    """円盤の軸は半径方向（胴の外から見て丸い）。胴側は胴の外面（r 76）で止まり、外側の面は胴の外面から depth 20（x = 96）。
    ロッドの穴（φ5.5）は円盤の上端から縦に開く止まり穴で、底はロッドの軸の先（z 70.19。円盤の下端 64.79 より上）。"""
    part = lug(SPEC)
    box = _box(part)
    zc = (64.7905 + 94.7905) / 2                                                 # 円盤の中心の高さ（胴の取付穴の高さ）
    assert part.solids().size() == 6 and (box.zmin, box.zmax) == pytest.approx((64.7905, 94.7905))
    assert _inside(part, 90, 14, zc) and not _inside(part, 90, 15.5, zc)          # 円盤は φ30（r 15）
    assert _inside(part, 90, 0, zc + 14) and not _inside(part, 90, 0, zc + 15.5)
    assert _inside(part, 95.9, 0, zc) and not _inside(part, 96.1, 0, zc)          # 外側の面は胴の外面から 20（平面）
    assert _inside(part, 95.9, 14, zc) and not _inside(part, 96.1, 14, zc)        # 平面なので、縁でも同じ x
    assert not _inside(part, 75.9, 0, zc) and _inside(part, 76.1, 0, zc)          # 胴側は胴の外面で止まる
    assert not _inside(part, 75.8, 5, zc) and _inside(part, 76.3, 5, zc)          # 横にずれても胴に食い込まない（円で沿う）
    assert not _inside(part, 86 + 2, 0, zc) and _inside(part, 86 + 3, 0, zc)      # ロッドの穴は φ5.5（r 2.75）
    assert not _inside(part, 86, 0, zc + 14.9) and not _inside(part, 86, 0, 70.3)   # 穴は円盤の上端から軸の先まで開く
    assert _inside(part, 86, 0, 70.0) and _inside(part, 86, 0, 65)                  # 軸の先より下は肉が残る（止まり穴）
    assert _inside(part, 90, 0, zc + 10) and _inside(part, 90, 0, zc - 10)
    disc = math.pi * 15**2 * 20
    assert disc - math.pi * 2.75**2 * (94.7905 - 70.1905) < part.solids().vals()[0].Volume() < disc + 1000   # 円盤 + 胴の外面の円弧から出る三日月


def test_the_bore_is_through_only_when_the_rod_tip_sticks_out_below_the_disc():
    """軸の先が円盤の下端より下（警告になる設定）なら、穴は下端まで通る（穴の底を円盤の外に出さない）。"""
    long = lug(override(SPEC, lug__rod_length=70))
    assert not _inside(long, 86, 0, 65) and not _inside(long, 86, 0, 94)


def test_the_lugs_stand_round_about_the_shell_at_the_lug_angles():
    part = lug(SPEC)
    zc = (64.7905 + 94.7905) / 2
    for k in range(6):
        a = math.radians(60 * k)
        assert _inside(part, 90 * math.cos(a), 90 * math.sin(a), zc), k
        assert not _inside(part, 90 * math.cos(a + math.radians(30)), 90 * math.sin(a + math.radians(30)), zc), k


def test_the_lug_is_one_solid_per_lug_even_when_the_rod_sits_near_the_disc_edge():
    part = lug(override(SPEC, lug__standoff=15))
    assert part.solids().size() == 6 and _inside(part, 91 + 3, 0, 80) and not _inside(part, 91 + 2, 0, 80)


def test_the_disc_follows_its_diameter_and_depth():
    thick = lug(override(SPEC, lug__depth=30, lug__body_dia=24))
    zc = 94.7905 - 12
    assert _box(thick).zmin == pytest.approx(94.7905 - 24)                       # 上端は変わらず、下端は径ぶん
    assert _inside(thick, 105.9, 0, zc) and not _inside(thick, 106.1, 0, zc)
    assert _inside(thick, 90, 0, zc + 11.5) and not _inside(thick, 90, 0, zc + 12.5)


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


def test_the_holder_clamp_stands_on_the_block_with_a_rod_bore_along_x_and_a_knob_to_the_rear():
    h = holder(SPEC)
    box = _box(h)
    assert h.solids().size() == 1 and (box.zmin, box.zmax) == pytest.approx((87, 117))               # ブロックの上面（管の中心 57 + 30）から 30
    assert (box.xmin, box.xmax) == pytest.approx((-20, 20))
    assert (box.ymin, box.ymax) == pytest.approx((-205, -140))                                    # 本体 φ40（中心 y −160）と、後ろへ 25 出るつまみ
    assert not _inside(h, 0, -160, 102) and _inside(h, 0, -160, 111) and _inside(h, 0, -160, 93)    # 穴（φ12.7）は中ほど
    assert _inside(h, 0, -190, 102) and _inside(h, 0, -204, 102) and not _inside(h, 0, -206, 102)    # つまみ（φ12）は後ろへ水平
    assert not _inside(h, 0, -190, 109) and not _inside(h, 7, -190, 102)                          # つまみの太さ（半径 6）


def test_the_holder_knob_follows_the_leaves():
    box = _box(holder(override(SPEC, mount__knob_length=40, mount__knob_dia=8, arm__rear=200)))
    assert box.ymin == pytest.approx(-200 - 20 - 40) and box.xmax == pytest.approx(20)


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
