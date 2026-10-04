"""マウント（D-22）の形状: 当て板（左右）・コの字の腕・ブロック・スペードグリップと端板。"""

from __future__ import annotations

import math

import cadquery as cq
import pytest
from gatling.params import SPEC, override
from gatling.placement import arm_path
from gatling.shapes.mount import arm, block, grip, grip_cap, pad
from gatling.shapes.body import shell
from gatling.shapes.purchased import holder


def _inside(part, x, y, z):
    return any(s.isInside(cq.Vector(x, y, z)) for s in part.solids().vals())


def _overlap(a, b):
    return cq.Compound.makeCompound(a.solids().vals()).intersect(cq.Compound.makeCompound(b.solids().vals())).Volume()


def _polar(r, deg, z):
    return r * math.cos(math.radians(deg)), r * math.sin(math.radians(deg)), z


def test_there_are_two_pads_that_mirror_each_other_between_the_lugs():
    p = pad(SPEC)
    assert p.solids().size() == 2
    box = p.val().BoundingBox()
    assert (box.zmin, box.zmax) == pytest.approx((27, 87))                         # 高さ 60、中心は胴の中ほど（57）
    assert box.xmin == pytest.approx(-box.xmax, abs=1e-6)                           # 左右対称
    for deg in (330, 210):                                                          # ±X 軸から後ろへ 30°。ラグ（0°, 60°, …）の間
        assert _inside(p, *_polar(77.5, deg, 57))
        assert not _inside(p, *_polar(77.5, deg + 25, 57)) and not _inside(p, *_polar(74, deg, 57))
    for deg in (0, 60, 120, 180, 240, 300):
        assert not _inside(p, *_polar(77.5, deg, 57)), deg                          # ラグの方位には無い


def test_a_pad_is_a_plate_bent_to_the_shell_of_the_given_thickness():
    p = pad(SPEC)
    assert _inside(p, *_polar(78.4, 330, 57)) and not _inside(p, *_polar(78.6, 330, 57))     # 外面 R + 板厚 = 78.5
    assert _inside(p, *_polar(76.1, 330, 57))                                                 # 内面は胴の外面 76
    assert _overlap(p, shell(SPEC)) == pytest.approx(0, abs=1e-6)                             # 胴に食い込まない（全周すみ肉溶接で付く）
    thick = pad(override(SPEC, pad__thickness=4))
    assert _inside(thick, *_polar(79.9, 330, 57)) and not _inside(thick, *_polar(80.1, 330, 57))            # 板厚を振ると外面が動く


def test_a_pad_has_rounded_corners_of_the_given_radius():
    sharp, round_ = pad(override(SPEC, pad__corner=0.5)), pad(SPEC)
    corner = _polar(77.0, 330, 57)
    u, v, z = 75.0, 19.7, 86.7                                                      # 板の局所座標（u 半径方向、v 周方向）の隅の近く
    a = math.radians(-30)
    point = (u * math.cos(a) - v * math.sin(a), u * math.sin(a) + v * math.cos(a), z)
    assert _inside(sharp, *point) and not _inside(round_, *point)
    assert _inside(round_, *corner)


def test_the_arm_is_one_hollow_tube_from_pad_to_pad_through_the_rear():
    a = arm(SPEC)
    assert a.solids().size() == 1
    box = a.val().BoundingBox()
    assert (box.zmin, box.zmax) == pytest.approx((44.3, 69.7))                       # 管の中心 57 ± 12.7
    assert box.xmin == pytest.approx(-box.xmax, abs=1e-6)
    assert box.ymin == pytest.approx(-160 - 12.7)                                    # 後ろの横渡しの中心線 160 + 管の半径
    assert _inside(a, 0, -160, 57 + 11.9) and _inside(a, 0, -160, 57 + 12.6)          # 上の壁（厚み 1.5: 11.2〜12.7）
    assert not _inside(a, 0, -160, 57) and not _inside(a, 0, -160, 57 + 11.1)         # 中空


def test_the_arm_volume_is_the_wall_area_times_the_centre_line_length():
    r, ri = 12.7, 11.2
    length = sum(p.length for p in arm_path(SPEC))
    assert arm(SPEC).val().Volume() == pytest.approx(math.pi * (r * r - ri * ri) * length, rel=1e-6)
    assert 400 < sum(p.length for p in arm_path(SPEC)) < 500


def test_the_arm_leaves_each_pad_along_the_radius_and_does_not_enter_the_pads_or_the_shell():
    a = arm(SPEC)
    for deg in (330, 210):
        assert _inside(a, *_polar(78.6, deg, 57 + 11.9)) and _inside(a, *_polar(100, deg, 57 + 12.0))      # 付け根は半径方向（上の壁）
    assert _overlap(a, pad(SPEC)) == pytest.approx(0, abs=1e-6)
    assert _overlap(a, shell(SPEC)) == pytest.approx(0, abs=1e-6)


def test_the_corners_of_the_arm_are_rounded_by_the_bend_radius_not_welded_square():
    a = arm(SPEC)
    x1 = 123.5 * math.cos(math.radians(30))
    # 頂点（x1, −160）の外側の角（管の中心の高さ）は、曲げで丸く切れているので空き。直角に突き合わせた溶接なら埋まる点
    assert not _inside(a, x1 + 3, -160 - 12, 57) and not _inside(a, x1 + 12, -160 - 3, 57)      # 突き合わせの管の壁（厚み 1.5）の延長上
    wide = arm(override(SPEC, arm__bend_radius=55)).val().BoundingBox()
    assert wide.ymin == pytest.approx(-172.7)                                         # 曲げ半径を振っても横渡しの位置は変わらない


def test_the_block_hugs_the_top_of_the_rear_crossing_like_a_saddle():
    b, a = block(SPEC), arm(SPEC)
    assert b.solids().size() == 1
    box = b.val().BoundingBox()
    assert (box.xmin, box.xmax) == pytest.approx((-30, 30)) and (box.ymin, box.ymax) == pytest.approx((-185, -135))
    assert (box.zmin, box.zmax) == pytest.approx((57, 87))                              # 管の中心の高さから 30
    assert _inside(b, 0, -160, 57 + 13) and not _inside(b, 0, -160, 57 + 12)             # 管の外形（半径 12.7）で切った鞍
    assert _inside(b, 0, -160 - 20, 57 + 1) and _inside(b, 0, -160 + 20, 57 + 1)         # 管の脇に肩が残る
    assert _overlap(b, a) == pytest.approx(0, abs=1e-6)


def test_the_holder_stands_on_the_block_without_overlapping_it_or_the_arm():
    assert _overlap(holder(SPEC), block(SPEC)) == pytest.approx(0, abs=1e-6)
    assert _overlap(holder(SPEC), arm(SPEC)) == pytest.approx(0, abs=1e-6)


def test_two_spade_grips_leave_the_rear_corners_down_back_and_outward():
    g = grip(SPEC)
    assert g.solids().size() == 2
    box = g.val().BoundingBox()
    d = (math.sin(math.radians(15)) * math.cos(math.radians(30)), -math.cos(math.radians(15)) * math.cos(math.radians(30)), -0.5)
    start = (92.0751618516548, -145.12102448427663, 57.0)
    end = tuple(s + 110 * c for s, c in zip(start, d))
    mid = tuple(s + 60 * c for s, c in zip(start, d))
    assert not _inside(g, *mid)                                                              # 中心線は中空
    wall = tuple(m + 11.9 * n for m, n in zip(mid, (0, 0.5, -0.8660254037844386)))              # 軸に直交する方向（真上から見て管の壁）
    assert _inside(g, *tuple(m - 11.9 * n for m, n in zip(mid, (0, 0.5, -0.8660254037844386)))) or _inside(g, *wall)
    assert box.xmax > end[0] and box.ymin < end[1] and box.zmin < end[2]                    # 外・後ろ・下へ張り出す
    assert box.zmax <= 57 + 12.7 + 1e-6                                                      # リムより上に出ない（付け根の管の上端まで）
    assert g.val().BoundingBox().xmin == pytest.approx(-box.xmax, abs=1e-6)                  # 左右対称


def test_a_grip_is_cut_by_the_arm_so_that_it_touches_without_overlapping():
    assert _overlap(grip(SPEC), arm(SPEC)) == pytest.approx(0, abs=1e-6)
    straight = grip(override(SPEC, grip__out=0)).val().BoundingBox()
    assert straight.xmax < grip(SPEC).val().BoundingBox().xmax                                 # 外へ開く角度で広がる


def test_the_grip_cap_closes_the_end_of_each_grip_with_a_round_plate():
    c, g = grip_cap(SPEC), grip(SPEC)
    assert c.solids().size() == 2
    assert _overlap(c, g) == pytest.approx(0, abs=1e-6)
    volume = c.solids().vals()[0].Volume()
    assert volume == pytest.approx(math.pi * 12.7**2 * 3, rel=1e-6)                           # 管の外径と同じ径、厚み 3
    # 端板は管の端面に接する（管の端から cap の厚みだけ先まで）
    gb, cb = g.val().BoundingBox(), c.val().BoundingBox()
    assert cb.zmin < gb.zmin + 1 and cb.ymin < gb.ymin


def test_the_mount_parts_do_not_overlap_one_another_or_the_shell():
    parts = {"pad": pad(SPEC), "arm": arm(SPEC), "block": block(SPEC), "grip": grip(SPEC), "cap": grip_cap(SPEC), "holder": holder(SPEC)}
    names = list(parts)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            assert _overlap(parts[a], parts[b]) == pytest.approx(0, abs=1e-6), (a, b)
