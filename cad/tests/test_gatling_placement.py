"""部品の置き場所（高さ・半径・周上の点）。CadQuery を使わない。"""

from __future__ import annotations

import math

import pytest
from gatling.params import SPEC, override
from drumcad.planar import origin_distance
from gatling.placement import (LUG_HOLE_OFFSETS, LUG_HOLES, PAD_COUNT, PAD_SIDES, arm_bends, arm_path, arm_polys, arm_vertices, block_plan,
                               flange_bolt_points, grip_polys, grip_poses, grip_z, holder_centre, knob_plan, levels, lug_angles,
                               lug_plan, pad_angles, pad_plan, pad_polys, pipe_inner_radius, radii, ring_points, tip_bolt_points,
                               tube_points, ear_hole_dia, knob_rim, tube_hole_dia)


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


def test_the_film_levels_sit_on_the_bearing_edge_and_the_collar_hangs_below_the_edge_top():
    z = levels(SPEC)
    assert z.head_top == pytest.approx(117 + 7.5 * 0.0254)                # 膜の下面 = エッジ頂部、上面 = + 膜厚
    assert z.collar_bottom == pytest.approx(z.head_top - 8)                 # フレッシュフープは膜の上面から 8 垂れる（109.19）
    assert z.collar_bottom < z.edge_top                                     # 胴・エッジ環の外側に下がる


def test_the_rim_is_shallow_and_the_pipe_ring_hangs_from_the_same_top():
    """リムの高さ（膜面から内リングの上端まで）= inner.height。外リングの管は上端を内リングの上端に揃え、下へ垂れる。"""
    z = levels(SPEC)
    assert z.hoop_top == pytest.approx(z.head_top + 8)                        # リムの高さ 8
    assert z.pipe_centre == pytest.approx(z.hoop_top - 25.4 / 2)               # 管の上端 = 内リングの上端
    assert z.hoop_bottom == pytest.approx(z.hoop_top - 25.4)                   # 下端は管の下端（99.79）
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
    assert (z.lug_top, z.lug_bottom) == pytest.approx((94.7905, 64.7905))       # 管の下端 − 締め代 5。下端は上端 − 円盤の径 30
    assert min(z.collar_bottom, z.hoop_bottom) - z.lug_top == pytest.approx(5)   # 引き下ろす余地。ラグが止まりにならない
    assert z.flange_top < z.lug_bottom and z.lug_top < z.shell_top
    low = levels(override(SPEC, hoop__outer__od=38.1))                            # 管が太くなれば、ラグはその下
    assert low.lug_top == pytest.approx(low.hoop_bottom - 5)
    thin = levels(override(SPEC, hoop__outer__od=10))                             # 管が細ければ、フレッシュフープの下端が効く
    assert thin.lug_top == pytest.approx(thin.collar_bottom - 5)


def test_the_rod_path_from_the_ear_top_to_the_lug_bottom_adds_up_ear_pipe_takeup_and_lug():
    z = levels(SPEC)
    assert z.ear_top - z.lug_bottom == pytest.approx(25.4 - 5 + 5 + 30)   # 55.4（管の外径 − 頭の高さ（受金の上面は管の上端より頭の高さだけ下）+ 締め代 + 円盤の径）


def test_the_arm_and_the_pads_sit_at_mid_plenum_height():
    z = levels(SPEC)
    assert z.arm_centre == pytest.approx(57)                                                 # フランジ上面 7 + 胴の高さの半分 50
    assert (z.arm_bottom, z.arm_top) == pytest.approx((57 - 12.7, 57 + 12.7))
    assert (z.pad_bottom, z.pad_top) == pytest.approx((27, 87))                              # 板の高さ 60
    moved = levels(override(SPEC, shell__plenum_height=80, pad__height=30, arm__pipe__od=20))
    assert moved.arm_centre == pytest.approx(47) and (moved.pad_bottom, moved.pad_top) == pytest.approx((32, 62))
    assert (moved.arm_bottom, moved.arm_top) == pytest.approx((37, 57))


def test_the_block_and_the_holder_stack_on_the_arm():
    z = levels(SPEC)
    assert z.block_top == pytest.approx(57 + 30) and z.holder_bottom == z.block_top           # ブロックの上面 = ホルダー受けの下面
    assert (z.holder_bottom, z.holder_top) == pytest.approx((87, 117)) and z.knob_centre == pytest.approx(102)
    assert levels(override(SPEC, block__height=40, mount__body_height=20)).holder_top == pytest.approx(57 + 40 + 20)


def test_the_radii_nest_from_the_shell_out_to_the_pad_face():
    r = radii(SPEC)
    assert r.shell == pytest.approx(76) and r.rod == pytest.approx(87.75)
    assert (r.hoop_in_inner, r.hoop_in_outer) == pytest.approx((76.7, 80.7))         # ヘッド外径 155.4 / 2 − 掛かり 1.0、肉厚 4
    assert r.hoop_out_inner == pytest.approx(94.7)                                     # 管の内側の接線 = 内リングの外面 + 間隔 14
    assert (r.hoop_out_centre, r.hoop_out_outer) == pytest.approx((107.4, 120.1))    # 管の中心・外面（φ25.4）
    assert r.hoop_in_outer < r.rod < r.hoop_out_inner                                  # ロッドはリングの間
    assert 152.4 / 2 < r.hoop_in_inner < 155.4 / 2                                     # 内リングはフレッシュフープの環の上に載る
    assert r.pad_outer == pytest.approx(78.5)                                          # 胴の外面 76 + 板厚 2.5


def test_the_collar_radius_is_half_the_head_diameter():
    assert radii(SPEC).collar == pytest.approx(152.4 / 2 + 1.5)


def test_the_pipe_inner_surface_is_narrowest_at_the_pipe_centre_height():
    """管の内側（胴の軸の側）の面の半径。z の帯の中で最も軸に近い所を返し、帯が管に掛からなければ無限大。"""
    z = levels(SPEC)
    assert pipe_inner_radius(SPEC, z.lug_bottom, z.ear_top) == pytest.approx(94.7)          # 管の中心の高さを含む
    head = 107.4 - math.sqrt(12.7**2 - (z.ear_top - z.pipe_centre) ** 2)                      # 受金の上面（中心から 7.7 上）
    assert pipe_inner_radius(SPEC, z.ear_top, z.rod_top) == pytest.approx(head)              # 97.30
    assert pipe_inner_radius(SPEC, z.hoop_top, z.hoop_top + 10) == math.inf
    assert pipe_inner_radius(SPEC, z.lug_bottom, z.lug_top) == math.inf


def test_a_lug_is_held_by_a_single_screw_at_the_middle_of_its_height():
    assert LUG_HOLE_OFFSETS == (0,) and LUG_HOLES == 1


def test_the_lug_plan_is_a_rectangle_from_the_shell_to_the_outer_face_of_the_disc():
    """平面形（ラグの局所座標 u, v）。円盤は胴の外面から depth だけ半径方向に出た幅 body_dia の矩形。胴側は胴の外面の円で切られ、
    側縁（v = ±b）では u = √(R² − b²) < R で触れるので、矩形の u0 はそこまで広げる。形と同じ葉（depth・body_dia）から作る。"""
    shell = 76.0
    assert lug_plan(SPEC) == pytest.approx((math.sqrt(shell**2 - 15**2), 96, -15, 15)) and lug_plan(SPEC)[0] < shell
    assert lug_plan(override(SPEC, lug__depth=12, lug__body_dia=20)) == pytest.approx((math.sqrt(shell**2 - 10**2), 88, -10, 10))
    assert lug_plan(override(SPEC, lug__standoff=15)) == pytest.approx(lug_plan(SPEC))      # ロッドの位置では動かない


def test_the_lug_plan_narrows_to_the_slice_of_the_disc_inside_the_z_band():
    """円盤は軸が半径方向の円柱なので、z の帯が円盤の中心の高さから離れるほど、その帯での平面形は細い（半幅 = √(b² − 中心からの距離²)）。
    帯が円盤の中心の高さを含めば全幅。帯の中に円盤が無ければ呼ばない（呼び出し側が z の重なりを先に見る）。"""
    z = levels(SPEC)
    zc = (z.lug_top + z.lug_bottom) / 2
    assert lug_plan(SPEC, zc - 1, zc + 1) == pytest.approx(lug_plan(SPEC))
    half = math.sqrt(15**2 - 10**2)
    u0, u1, v0, v1 = lug_plan(SPEC, z.lug_bottom - 5, zc - 10)                  # 帯の上端が中心の 10 下
    assert (v0, v1) == pytest.approx((-half, half)) and u1 == 96 and u0 == pytest.approx(math.sqrt(76**2 - half**2))
    assert lug_plan(SPEC, z.lug_top, z.lug_top + 5) == pytest.approx((76.0, 96, 0.0, 0.0), abs=1e-6)   # 上端の線


def test_the_pads_are_a_mirror_pair_between_the_lugs():
    assert PAD_SIDES == (1, -1) and PAD_COUNT == 2
    assert pad_angles(SPEC) == pytest.approx([330, 210])                                      # ±X 軸から後ろへ 30°
    assert all(a not in lug_angles(SPEC) for a in pad_angles(SPEC))                           # ラグ（0°, 60°, …）の間
    assert pad_angles(override(SPEC, pad__angle=45)) == pytest.approx([315, 225])
    assert pad_angles(override(SPEC, pad__angle=0)) == pytest.approx([0, 180])


def test_the_pad_plan_is_the_blank_width_between_the_shell_and_the_pad_face():
    """u0 は側縁（v = ±半幅）で胴の外面に触れる所 √(R² − 半幅²)、u1 は板の外面 R + 板厚。lug_plan と同じ作り。"""
    assert pad_plan(SPEC) == pytest.approx((math.sqrt(76**2 - 20**2), 78.5, -20, 20))
    assert pad_plan(override(SPEC, pad__width=30, pad__thickness=4)) == pytest.approx((math.sqrt(76**2 - 15**2), 80, -15, 15))
    polys = pad_polys(SPEC)
    assert len(polys) == 2 and polys[0][1] != polys[1][1]


def test_the_arm_runs_from_the_pad_face_back_to_a_crossing_and_is_mirror_symmetric():
    v = arm_vertices(SPEC)
    face = 78.5
    assert len(v) == 6
    assert v[0] == pytest.approx((face * math.cos(math.radians(30)), -face * math.sin(math.radians(30))))       # 右の当て板の外面
    assert math.hypot(*v[1]) == pytest.approx(78.5 + 45)                                                       # 半径方向に stub
    assert v[2] == pytest.approx((v[1][0], -160)) and v[3] == pytest.approx((-v[2][0], -160))                  # 脚は後ろへ平行、横渡し
    assert [(-x, y) for x, y in v[::-1]] == pytest.approx(v)                                                   # 左右対称
    path = arm_path(SPEC)
    assert len(path) == 9 and [type(p).__name__ for p in path[1::2]] == ["Arc"] * 4
    assert all(p.radius == pytest.approx(50.8) for p in path[1::2])


def test_the_arm_bends_leave_room_on_every_leg_by_default():
    bends = arm_bends(SPEC)
    t1, t2 = 50.8 * math.tan(math.radians(30)), 50.8                                          # 曲がり 60° と 90°
    assert bends.stub_free == pytest.approx(45 - t1) and bends.stub_free > 0
    y1 = (78.5 + 45) * math.sin(math.radians(30))
    assert bends.leg_free == pytest.approx(160 - y1 - t1 - t2) and bends.leg_free > 0
    assert bends.cross_half == pytest.approx((78.5 + 45) * math.cos(math.radians(30)) - 50.8)
    tight = arm_bends(override(SPEC, arm__stub=t1))                                           # 接線の長さちょうど: 当て板に曲げの接点が届く
    assert tight.stub_free == pytest.approx(0, abs=1e-9)


def test_the_arm_plan_is_covered_by_convex_polygons_that_reach_the_pad_face():
    polys = arm_polys(SPEC)
    assert 50 < len(polys) < 120
    assert min(math.hypot(x, y) for poly in polys for x, y in poly) >= 78.5 - 1e-6 - 12.7       # 平らな端の角は管の半径ぶん外れる
    assert min(origin_distance(poly) for poly in polys) == pytest.approx(78.5)                    # 腕の最も胴に近い所は当て板の外面


def test_the_holder_and_the_block_sit_on_the_rear_crossing_centre_line():
    assert holder_centre(SPEC) == (0.0, -160.0) and holder_centre(override(SPEC, arm__rear=200)) == (0.0, -200.0)
    block = block_plan(SPEC)
    assert sorted(block) == pytest.approx(sorted([(-30, -185), (30, -185), (30, -135), (-30, -135)]))
    assert sorted(knob_plan(SPEC)) == pytest.approx(sorted([(-6, -205), (6, -205), (6, -179), (-6, -179)]))   # 本体の外面 −180 から後ろへ 25（1 食い込む）


def test_the_spade_grips_start_in_the_middle_of_the_rear_bends_and_point_down_back_and_out():
    right, left = grip_poses(SPEC)
    d = right.direction
    assert math.hypot(*d) == pytest.approx(1) and d[2] == pytest.approx(-0.5)                  # 下へ 30°
    assert d[0] == pytest.approx(math.sin(math.radians(10)) * math.cos(math.radians(30))) and d[1] < 0
    assert left.direction == pytest.approx((-d[0], d[1], d[2])) and left.start == pytest.approx((-right.start[0], right.start[1], right.start[2]))
    cx, cy = -50.8 + 123.5 * math.cos(math.radians(30)), -160 + 50.8
    assert right.start[:2] == pytest.approx((cx + 50.8 * math.cos(math.pi / 4), cy - 50.8 * math.sin(math.pi / 4)))   # 円弧の中央
    assert right.start[2] == pytest.approx(57) and (right.length, right.cap) == (110, 3)


def test_the_grip_plan_and_z_range_cover_the_sloped_tube_and_its_cap():
    polys = grip_polys(SPEC)
    low, high = grip_z(SPEC)
    right = grip_poses(SPEC)[0]
    end = right.start[2] + 113 * right.direction[2]
    assert low == pytest.approx(end - 12.7) and high == pytest.approx(57 + 12.7)
    xs = [x for x, _ in polys[0]]
    assert max(xs) > right.start[0] + 113 * right.direction[0]                                 # 端の円は斜めに見えて、前後に広がる
    assert grip_z(override(SPEC, grip__drop=0))[0] == pytest.approx(57 - 12.7)


def test_the_shared_levels_are_derived_once_from_the_leaves():
    """形と検査が各自で書いていた式を、`Levels` の葉に 1 か所で持つ（式のずれで形と検査が別の値を見る穴を塞ぐ）。"""
    for spec in (SPEC, override(SPEC, lug__body_dia=24, hoop__outer__od=30, hoop__takeup=4, shell__plenum_height=90)):
        z = levels(spec)
        assert z.lug_centre == pytest.approx((z.lug_top + z.lug_bottom) / 2)
        assert z.lug_centre - z.lug_bottom == pytest.approx(float(spec.lug.body_dia) / 2)
        assert z.pipe_bottom == pytest.approx(z.hoop_top - float(spec.hoop.outer.od))
        assert z.hoop_bottom == pytest.approx(min(z.head_top, z.pipe_bottom))


def test_the_rod_head_top_sits_at_the_hoop_top_for_any_input():
    """受金の上面 = フープの上端 − 頭の高さ、頭の上面 = 受金の上面 + 頭の高さ。なので頭の上面はフープの上端に揃い、受金は
    フープの上端から突き出ない。この 2 つは入力によらず成り立つので、`checks` では見ない（恒真）。振って確かめる。"""
    for height in (1, 5, 7.9):
        for rim in (5, 8, 20):
            for film in (3, 7.5, 10):
                z = levels(override(SPEC, lug__rod_head_height=height, hoop__inner__height=rim, head__film_mil=film))
                assert z.rod_top == pytest.approx(z.hoop_top, abs=1e-9) and z.ear_top < z.hoop_top, (height, rim, film)


def test_the_hole_diameters_that_the_shapes_and_the_checks_share():
    assert ear_hole_dia(SPEC) == pytest.approx(5.5 + 1.0)                      # ロッドの呼び径 + 逃げ
    assert ear_hole_dia(override(SPEC, hoop__ear__hole_clearance=2, lug__thread="M5")) == pytest.approx(5.0 + 2.0)
    assert tube_hole_dia(SPEC) == pytest.approx(38.1 + 0.2)                    # 管の外径 + 穴の逃げ
    assert tube_hole_dia(override(SPEC, tube__od=42.7, header__hole_clearance=0.5)) == pytest.approx(43.2)


def test_the_knob_rim_is_the_outside_of_the_holder_body_toward_the_back():
    assert knob_rim(SPEC) == pytest.approx(-160 - 20)                                   # 中心 −160、本体の径 40 の半分
    assert knob_rim(override(SPEC, arm__rear=200, mount__body_dia=30)) == pytest.approx(-215)
    assert sorted(knob_plan(SPEC)) == pytest.approx(sorted([(-6, -205), (6, -205), (6, -179), (-6, -179)]))


def test_a_grip_has_the_tube_tip_and_the_cap_end_on_its_axis():
    right = grip_poses(SPEC)[0]
    d = right.direction
    assert right.tip == pytest.approx(tuple(s + 110 * c for s, c in zip(right.start, d)))
    assert right.end == pytest.approx(tuple(s + 113 * c for s, c in zip(right.start, d)))
    assert grip_z(SPEC)[0] == pytest.approx(min(right.end[2], right.start[2]) - 12.7)
