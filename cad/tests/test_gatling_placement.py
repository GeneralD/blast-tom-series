"""部品の置き場所（高さ・半径・周上の点）。CadQuery を使わない。"""

from __future__ import annotations

import math

import pytest
from gatling.params import SPEC, override
from gatling.placement import (flange_bolt_points, levels, lug_angles, radii, ring_points, tip_bolt_points,
                               tube_points)


def _angle(point):
    return math.degrees(math.atan2(point[1], point[0])) % 360


def test_ring_points_are_evenly_spaced_on_the_circle_starting_at_the_phase():
    pts = ring_points(4, 10.0, 45.0)
    assert [round(_angle(p)) for p in pts] == [45, 135, 225, 315]
    assert all(math.hypot(*p) == pytest.approx(10.0) for p in pts)


def test_the_tubes_sit_on_the_pitch_circle_with_the_gap_ratio_between_them():
    pts = tube_points(SPEC)
    assert len(pts) == 6 and pts[0] == pytest.approx((53.34, 0.0))
    assert all(math.hypot(*p) == pytest.approx(53.34) for p in pts)
    gap = math.dist(pts[0], pts[1]) - 38.1
    assert gap == pytest.approx(0.4 * 38.1)                    # D-11: 隙間 = 外径の 0.4 倍（15.24）


def test_the_flange_bolts_are_outside_the_shell_and_offset_30_degrees_from_the_tubes():
    bolts = flange_bolt_points(SPEC)
    assert len(bolts) == 6 and all(math.hypot(*p) == pytest.approx(86.0) for p in bolts)     # ボルト円 172
    tube_angles = [round(_angle(p), 6) for p in tube_points(SPEC)]
    assert all(round(_angle(b) - 30, 6) % 60 == 0 for b in bolts)
    assert not set(round(_angle(b), 6) for b in bolts) & set(tube_angles)


def test_the_tip_bolts_sit_between_the_tubes_on_the_pitch_circle():
    pts = tip_bolt_points(SPEC)
    assert len(pts) == 6 and all(math.hypot(*p) == pytest.approx(53.34) for p in pts)
    assert [round(_angle(p)) for p in pts] == [30, 90, 150, 210, 270, 330]


def test_the_lugs_line_up_with_the_tubes():
    assert lug_angles(SPEC) == [0, 60, 120, 180, 240, 300]
    assert [round(_angle(p)) % 360 for p in tube_points(SPEC)] == [int(a) for a in lug_angles(SPEC)]
    three = override(SPEC, lug__count=3)
    assert set(lug_angles(three)) <= {round(_angle(p), 6) % 360 for p in tube_points(SPEC)}   # ラグが管の部分集合の方位


def test_the_levels_stack_from_the_head_down_to_the_tube_tips():
    z = levels(SPEC)
    assert (z.gasket_top, z.flange_top, z.shell_top, z.edge_top) == (1, 7, 107, 117)
    assert z.header_bottom == -6 and z.tube_tip == -450
    assert z.head_top > z.edge_top > z.shell_top > z.flange_top > z.gasket_top > 0 > z.header_bottom > z.tube_tip


def test_the_film_rests_on_the_bearing_edge_and_the_collar_hangs_outside_the_shell():
    z = levels(SPEC)
    assert z.head_top == pytest.approx(117 + 7.5 * 0.0254)                # 膜の下面 = エッジ頂部、上面 = + 膜厚
    assert z.collar_bottom == pytest.approx(z.head_top - 8)                 # フレッシュフープは膜の上面から 8 垂れる（109.19）
    assert z.collar_bottom < z.edge_top                                     # 胴・エッジ環の外側に下がる


def test_the_hoop_stands_on_the_collar_and_the_ears_sit_on_top_of_both_rings():
    z = levels(SPEC)
    assert z.hoop_bottom == pytest.approx(z.head_top)                       # 内リングの下面 = フレッシュフープの上端
    assert z.hoop_top == pytest.approx(z.head_top + 25) and z.ear_top == pytest.approx(z.hoop_top + 6)
    taller = levels(override(SPEC, hoop__outer__height=30))
    assert taller.hoop_top == pytest.approx(z.hoop_top) and taller.hoop_bottom == pytest.approx(z.head_top - 5)   # 上端を揃え、低いほうが下端


def test_the_plenum_height_runs_from_the_edge_ring_underside_to_the_flange_top():
    assert levels(SPEC).shell_top - levels(SPEC).flange_top == 100


def test_the_clamps_follow_the_tube_length_and_the_ratios():
    z = levels(SPEC)
    assert z.mid_top == pytest.approx(-0.55 * 450) and z.mid_bottom == pytest.approx(z.mid_top - 3)
    assert z.tip_bottom == pytest.approx(-450 + 38.1) and z.tip_top == pytest.approx(z.tip_bottom + 6)     # 突き出し 1 外径
    longer = levels(override(SPEC, tube__length=500, tube__protrusion_ratio=2.0))
    assert longer.mid_top == pytest.approx(-275) and longer.tip_bottom == pytest.approx(-500 + 76.2)


def test_the_lugs_stand_a_takeup_below_the_collar_and_inside_the_shell_height():
    z = levels(SPEC)
    assert (z.lug_top, z.lug_bottom) == pytest.approx((104.1905, 69.1905))      # フレッシュフープの下端 − 締め代 5
    assert min(z.collar_bottom, z.hoop_bottom) - z.lug_top == pytest.approx(5)   # 引き下ろす余地。ラグが止まりにならない
    assert z.flange_top < z.lug_bottom and z.lug_top < z.shell_top
    low = levels(override(SPEC, hoop__outer__height=40))                          # 外リングが下がれば、ラグはその下
    assert low.lug_top == pytest.approx(low.hoop_bottom - 5)


def test_the_rod_path_from_the_lug_bottom_to_the_ear_top_adds_up_lug_takeup_head_hoop_and_ear():
    z = levels(SPEC)
    assert z.ear_top - z.lug_bottom == pytest.approx(35 + 5 + 8 + 25 + 6)       # 79（ヘッドの掛かり = collar_height）


def test_the_band_sits_above_the_flange_and_the_frame_at_mid_plenum_height():
    z = levels(SPEC)
    assert (z.band_bottom, z.band_top) == (19, 44)
    assert z.frame_centre == pytest.approx(57)


def test_the_radii_nest_from_the_shell_out_to_the_frame():
    r = radii(SPEC)
    assert r.shell == pytest.approx(76) and r.rod == pytest.approx(84)
    assert (r.hoop_in_inner, r.hoop_in_outer) == pytest.approx((76.7, 79.7))         # ヘッド外径 155.4 / 2 − 掛かり 1.0
    assert (r.hoop_out_inner, r.hoop_out_outer) == pytest.approx((87.7, 90.7))       # 内外リングの間隔 8
    assert r.hoop_in_outer < r.rod < r.hoop_out_inner                                  # ロッドはリングの間
    assert 152.4 / 2 < r.hoop_in_inner < 155.4 / 2                                     # 内リングはフレッシュフープの環の上に載る
    assert (r.band_inner, r.band_outer, r.frame_inner) == pytest.approx((77, 83, 98))
