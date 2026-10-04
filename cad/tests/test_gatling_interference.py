"""検査と形の突き合わせ: レビューで見つかった override。

1. 形が干渉する（または `assembly()` が例外を投げる）override は、`issues()` が fatal を返す（軽い）。
2. 境界の内側（干渉しない側）の override は、`issues()` が fatal 0 で、`assembly()` の部品どうしの重なりも 0（重い。代表だけ）。
   ボルトとねじ込む相手（下穴）は既定でも重なるので除く（`gatling_overlap.py`）。
"""

from __future__ import annotations

from drumcad.checks import fatal_count
from gatling.checks import issues
import math

import pytest
from gatling.interference import _round_parts, ear_clear, flange_bolts_removable, mount_bodies, mount_clear
from gatling.params import SPEC, override
from gatling.fasteners import lookup_screw
from gatling.placement import arm_polys, grip_polys, grip_z, levels, pad_polys
from gatling.planar import origin_distance
from gatling_overlap import overlaps


def test_the_default_has_no_fatal_no_overlap_and_only_the_two_known_warnings():
    """既定の警告は受金のロッド通し穴の径方向の肉（内側・外側）の 2 件だけ。リムを浅くしても増えない。"""
    found = issues(SPEC)
    assert fatal_count(found) == 0
    assert sorted(i.what.split("（")[0] for i in found) == ["受金のロッド通し穴の内側の肉", "受金のロッド通し穴の外側の肉"]
    assert overlaps(SPEC) == []


def test_an_ear_must_not_eat_the_fresh_hoop():
    """受金の内端は内リングの外面（既定 80.7）。フレッシュフープの外面（77.7）より内側（内リングを薄くした）で、z も重なれば fatal。
    内リングの内面は 76.7（seat 1）なので、厚み 1 で外面 77.7（縁ちょうどは通す）、0.9 で 77.6。"""
    assert ear_clear(SPEC) == []
    assert ear_clear(override(SPEC, hoop__inner__thickness=1.0)) == []
    found = ear_clear(override(SPEC, hoop__inner__thickness=0.9))
    assert len(found) == 1 and found[0].fatal and "受金" in found[0].what and "フレッシュフープ" in found[0].what


def test_an_ear_above_the_fresh_hoop_in_z_does_not_touch_it_whatever_the_ring_thickness():
    """頭の高さ 1 だと受金（板厚 6）は z 118.19〜124.19 で、フレッシュフープ（〜膜面 117.19）の上。平面視で重なっても z が離れている。"""
    assert ear_clear(override(SPEC, lug__rod_head_height=1, hoop__inner__thickness=0.9)) == []
    assert ear_clear(override(SPEC, lug__rod_head_height=2, hoop__inner__thickness=0.9)) == []          # 下面がちょうど膜面に載る
    assert ear_clear(override(SPEC, lug__rod_head_height=2.1, hoop__inner__thickness=0.9)) != []        # 膜面より下に 0.1 食い込む


# --- 当て板・腕・ブロック・グリップ・ホルダー受け（D-22） -------------------------------------------------------------------


def _hits(found, fragment):
    return [i for i in found if fragment in i.what]


def _edge(hit, clean, bad):
    """`clean` では当たらず `bad` では当たる、単調な境界の値を二分法で出す（境界の両側で検査が切り替わることを確かめるため）。"""
    assert not hit(clean) and hit(bad), (clean, bad)
    for _ in range(60):
        mid = (clean + bad) / 2
        clean, bad = (clean, mid) if hit(mid) else (mid, bad)
    return clean


def test_the_default_mount_has_no_interference_and_no_blocked_bolt():
    assert mount_clear(SPEC) == [] and flange_bolts_removable(SPEC) == []


def test_the_interference_plans_are_the_placement_values_the_shapes_use():
    """干渉の平面形と z の範囲は、形と同じ `placement` の値そのもの（別の式で作り直していない）。"""
    bodies = mount_bodies(SPEC)
    assert [b.polys[0] for b in bodies if b.part == "当て板"] == pad_polys(SPEC)
    assert [b.polys[0] for b in bodies if b.part == "スペードグリップ"] == grip_polys(SPEC)
    assert all(b.z == grip_z(SPEC) for b in bodies if b.part == "スペードグリップ")
    assert [b.part for b in bodies].count("当て板") == 2 and [b.part for b in bodies].count("スペードグリップ") == 2
    arm = next(b for b in bodies if b.part == "腕")
    assert arm.polys == tuple(arm_polys(SPEC)) and arm.z == (levels(SPEC).arm_bottom, levels(SPEC).arm_top)


def test_a_pad_swung_toward_a_lug_hits_it_and_one_between_the_lugs_does_not():
    """ラグは 60° おき。当て板の既定の方位 30° は 2 つのラグの真ん中。ラグ（0°）へ寄せると、ちょうど当たらない角度から少し越えて当たる。"""
    hit = lambda a: bool(_hits(mount_clear(override(SPEC, pad__angle=a)), "当て板がラグに当たる"))
    edge = _edge(hit, 30.0, 20.0)
    assert 20.0 < edge < 30.0
    assert not hit(edge + 0.01) and hit(edge - 0.01)
    found = _hits(mount_clear(override(SPEC, pad__angle=edge - 0.01)), "当て板がラグに当たる")
    assert [i.what for i in found] == ["当て板がラグに当たる（方位 0°）", "当て板がラグに当たる（方位 180°）"] and all(i.fatal for i in found)   # 左右の板


def test_a_pad_that_is_too_wide_reaches_the_neighbouring_lug():
    hit = lambda w: bool(_hits(mount_clear(override(SPEC, pad__width=w)), "当て板がラグに当たる"))
    edge = _edge(hit, 40.0, 100.0)
    assert not hit(edge - 0.01) and hit(edge + 0.01)


def test_a_holder_pushed_forward_hits_the_outer_ring_exactly_when_its_near_edge_crosses_the_ring():
    """ホルダー受けの手前の縁 = rear − 本体の半径。外リング（管）の外半径に届いたところがちょうど。"""
    ring = next(r for n, r, _, _ in _round_parts(SPEC) if n == "外リング（管）")
    edge = ring + float(SPEC.mount.body_dia) / 2
    assert _hits(mount_clear(override(SPEC, arm__rear=edge)), "ホルダー受けが外リング") == []
    found = _hits(mount_clear(override(SPEC, arm__rear=edge - 0.01)), "ホルダー受けが外リング")
    assert len(found) == 1 and found[0].fatal


def test_a_holder_that_stays_below_the_ring_in_z_does_not_hit_it():
    """外リング（管）の下端より下にホルダー受けの上面が収まれば、平面視で重なっても当たらない（z が離れている）。"""
    ring_bottom = next(z0 for n, _, z0, _ in _round_parts(SPEC) if n == "外リング（管）")
    edge = ring_bottom - levels(SPEC).block_top             # ホルダー受けの高さの上限
    rear = {"arm__rear": 125.0}
    assert _hits(mount_clear(override(SPEC, **rear, mount__body_height=edge)), "ホルダー受けが外リング") == []
    assert _hits(mount_clear(override(SPEC, **rear, mount__body_height=edge + 0.01)), "ホルダー受けが外リング") != []


def test_an_arm_bent_back_into_the_shell_is_caught_at_the_shell_surface():
    """stub を短くすると最初の曲げが胴の側へ入る。腕の平面形の最短距離が胴の外半径に届いたところがちょうど。"""
    shell = next(r for n, r, _, _ in _round_parts(SPEC) if n == "胴・エッジ環")
    near = lambda stub: min(origin_distance(p) for p in arm_polys(override(SPEC, arm__stub=stub)))
    hit = lambda stub: bool(_hits(mount_clear(override(SPEC, arm__stub=stub)), "腕が胴・エッジ環"))
    edge = _edge(hit, 45.0, 20.0)
    assert math.isclose(near(edge), shell, abs_tol=0.01)


def test_a_grip_reaches_a_very_large_outer_ring_but_not_the_default_one():
    """グリップの付け根（腕の後ろの角）は胴の軸から遠く、既定の外リングには届かない。外リングの管を太くして外半径が
    グリップの平面形の最短距離に届いたところがちょうど。"""
    near = min(origin_distance(p) for p in grip_polys(SPEC))
    ring = lambda od: next(r for n, r, _, _ in _round_parts(override(SPEC, hoop__outer__od=od)) if n == "外リング（管）")
    hit = lambda od: bool(_hits(mount_clear(override(SPEC, hoop__outer__od=od)), "スペードグリップが外リング"))
    edge = _edge(hit, 31.8, 140.0)
    assert math.isclose(ring(edge), near, abs_tol=0.05)


def test_the_arm_over_a_flange_bolt_must_leave_room_to_pull_the_bolt():
    """既定の方位 30° の当て板から出る腕は、フランジのボルト（−30°）の上を通る。腕の下端とフランジ上面の距離が頭の高さ + ねじ込み長
    （= 頭の高さ + ボルト長 − フランジ厚 − ガスケット厚）以上なら抜ける。ボルト長を伸ばしてちょうどのところ。"""
    z, screw = levels(SPEC), lookup_screw(SPEC.flange.bolt)
    stack = float(SPEC.flange.thickness) + float(SPEC.gasket.thickness)
    edge = (z.arm_bottom - z.flange_top) - float(screw.head_height) + stack
    assert flange_bolts_removable(override(SPEC, flange__bolt_length=edge)) == []
    found = flange_bolts_removable(override(SPEC, flange__bolt_length=edge + 0.01))
    assert len(found) == 1 and found[0].fatal and found[0].what.startswith("腕の下で")


def test_a_bolt_clear_of_every_mount_part_needs_no_room():
    """ボルトを管の方位からずらしたまま動かし、腕の下に入らなければ、ボルトが長くても止めない。"""
    assert flange_bolts_removable(override(SPEC, flange__bolt_phase=0, flange__bolt_length=40)) == []
