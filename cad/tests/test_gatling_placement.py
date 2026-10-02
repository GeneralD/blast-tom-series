"""部品の置き場所（高さ・半径・周上の点）。CadQuery を使わない。"""

from __future__ import annotations

import math

import pytest
from gatling.params import SPEC, override
from gatling.placement import (flange_bolt_points, levels, lug_angles, pipe_inner_radius, radii, ring_points,
                               tip_bolt_points, tube_points)


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


def test_the_rim_is_shallow_and_the_pipe_ring_hangs_from_the_same_top():
    """リムの高さ（膜面から内リングの上端まで）= inner.height。外リングの管は上端を内リングの上端に揃え、下へ垂れる。"""
    z = levels(SPEC)
    assert z.hoop_top == pytest.approx(z.head_top + 8)                        # リムの高さ 8
    assert z.pipe_centre == pytest.approx(z.hoop_top - 25.4 / 2)               # 管の上端 = 内リングの上端
    assert z.hoop_bottom == pytest.approx(z.hoop_top - 25.4)                   # 下端は管の下端（103.79）
    assert z.hoop_bottom < z.head_top
    thin = levels(override(SPEC, hoop__outer__od=6))
    assert thin.hoop_bottom == pytest.approx(thin.head_top)                    # 管がリムより細ければ、内リングの下面が下端


def test_the_ear_top_is_the_hoop_top_minus_the_rod_head_height_and_the_ear_hangs_a_thickness_below():
    """ロッドの頭の上面をリムの上端に揃える。受金の z はこの式 1 か所で決まり、下面は膜面より下（フレッシュフープの外側）に出る。"""
    z = levels(SPEC)
    assert z.ear_top == pytest.approx(z.hoop_top - 5) and z.ear_top == pytest.approx(z.head_top + 3)
    assert z.ear_bottom == pytest.approx(z.ear_top - 6) and z.ear_bottom < z.head_top
    for path, value in (("hoop.inner.height", 10), ("lug.rod_head_height", 2), ("hoop.ear.thickness", 9), ("head.film_mil", 10)):
        spec = override(SPEC, **{path.replace(".", "__"): value})
        moved = levels(spec)
        assert moved.ear_top == pytest.approx(moved.hoop_top - float(spec.lug.rod_head_height)), path
        assert moved.ear_bottom == pytest.approx(moved.ear_top - float(spec.hoop.ear.thickness)), path


def test_the_rod_head_rests_on_the_ear_and_the_shaft_runs_down_by_the_rod_length():
    z = levels(SPEC)
    assert z.rod_top == pytest.approx(z.ear_top + 5)                           # 頭の高さ 5
    assert z.rod_tip == pytest.approx(z.ear_top - 50)                          # 軸の長さ 50
    assert z.lug_bottom < z.rod_tip < z.lug_top
    assert z.rod_top == pytest.approx(z.hoop_top)                              # 頭の上面 = リムの上端（頭の高さを変えても揃う）
    assert levels(override(SPEC, lug__rod_head_height=3)).rod_top == pytest.approx(z.hoop_top)


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
    assert (z.lug_top, z.lug_bottom) == pytest.approx((94.7905, 59.7905))       # 管の下端 − 締め代 5
    assert min(z.collar_bottom, z.hoop_bottom) - z.lug_top == pytest.approx(5)   # 引き下ろす余地。ラグが止まりにならない
    assert z.flange_top < z.lug_bottom and z.lug_top < z.shell_top
    low = levels(override(SPEC, hoop__outer__od=38.1))                            # 管が太くなれば、ラグはその下
    assert low.lug_top == pytest.approx(low.hoop_bottom - 5)
    thin = levels(override(SPEC, hoop__outer__od=10))                             # 管が細ければ、フレッシュフープの下端が効く
    assert thin.lug_top == pytest.approx(thin.collar_bottom - 5)


def test_the_rod_path_from_the_ear_top_to_the_lug_bottom_adds_up_ear_pipe_takeup_and_lug():
    z = levels(SPEC)
    assert z.ear_top - z.lug_bottom == pytest.approx(25.4 - 5 + 5 + 35)   # 60.4（管の外径 − 頭の高さ（受金の上面は管の上端より頭の高さだけ下）+ 締め代 + ラグ）


def test_the_band_sits_above_the_flange_and_the_frame_at_mid_plenum_height():
    z = levels(SPEC)
    assert (z.band_bottom, z.band_top) == (19, 44)
    assert z.frame_centre == pytest.approx(57)


def test_the_radii_nest_from_the_shell_out_to_the_frame():
    r = radii(SPEC)
    assert r.shell == pytest.approx(76) and r.rod == pytest.approx(86)
    assert (r.hoop_in_inner, r.hoop_in_outer) == pytest.approx((76.7, 80.7))         # ヘッド外径 155.4 / 2 − 掛かり 1.0、肉厚 4
    assert r.hoop_out_inner == pytest.approx(90.7)                                     # 管の内側の接線 = 内リングの外面 + 間隔 10
    assert (r.hoop_out_centre, r.hoop_out_outer) == pytest.approx((103.4, 116.1))    # 管の中心・外面（φ25.4）
    assert r.hoop_in_outer < r.rod < r.hoop_out_inner                                  # ロッドはリングの間
    assert 152.4 / 2 < r.hoop_in_inner < 155.4 / 2                                     # 内リングはフレッシュフープの環の上に載る
    assert (r.band_inner, r.band_outer, r.frame_inner) == pytest.approx((77, 83, 98))


def test_the_pad_and_the_holder_stack_on_the_frame():
    """当て板とホルダー受けの高さは placement に置き、形状と検査が同じ値を読む。"""
    z = levels(SPEC)
    assert z.frame_top == pytest.approx(57 + 3) and z.pad_top == pytest.approx(66)
    assert (z.holder_bottom, z.holder_top) == pytest.approx((66, 96))


def test_the_collar_radius_is_half_the_head_diameter():
    assert radii(SPEC).collar == pytest.approx(152.4 / 2 + 1.5)


def test_the_pipe_inner_surface_is_narrowest_at_the_pipe_centre_height():
    """管の内側（胴の軸の側）の面の半径。z の帯の中で最も軸に近い所を返し、帯が管に掛からなければ無限大。"""
    z = levels(SPEC)
    assert pipe_inner_radius(SPEC, z.lug_bottom, z.ear_top) == pytest.approx(90.7)          # 管の中心の高さを含む
    head = 103.4 - math.sqrt(12.7**2 - (z.ear_top - z.pipe_centre) ** 2)                      # 受金の上面（中心から 7.7 上）
    assert pipe_inner_radius(SPEC, z.ear_top, z.rod_top) == pytest.approx(head)              # 93.30
    assert pipe_inner_radius(SPEC, z.hoop_top, z.hoop_top + 10) == math.inf
    assert pipe_inner_radius(SPEC, z.lug_bottom, z.lug_top) == math.inf
