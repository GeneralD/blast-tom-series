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
import gatling.interference as interference
from gatling.interference import _round_parts, _tube_bundle, ear_clear, flange_bolts_removable, mount_bodies, mount_clear, Body
from gatling.params import SPEC, override
from gatling.fasteners import lookup_screw
from gatling.placement import arm_polys, block_plan, grip_polys, grip_z, holder_centre, levels, lug_angles, pad_polys, radii
from gatling.planar import origin_distance
from gatling_overlap import overlaps


def test_the_default_has_no_fatal_no_overlap_and_no_warning():
    """既定は警告も無い（溝を 14 に広げて、受金のロッド通し穴の径方向の肉が両側で板厚の半分以上になった。D-20）。"""
    found = issues(SPEC)
    assert fatal_count(found) == 0 and found == []
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


# --- 突き合わせで見つかった穴（変異で落ちなかった項）。境界はどれも、検査と別の式で出す -----------------------------------------------


def _dist_to_rect(p, u0, u1, v0, v1):
    """点から矩形（u0..u1, v0..v1）までの最短距離（矩形の外では角・辺までの距離。検査の `_meet` とは別の式）。"""
    return math.hypot(max(u0 - p[0], 0.0, p[0] - u1), max(v0 - p[1], 0.0, p[1] - v1))


def test_a_pad_swung_onto_a_tension_rod_hits_the_rod_exactly_when_the_rod_circle_reaches_the_pad_edge():
    """当て板（既定の上下 27〜87）はロッドの軸の高さ（先端 70.2〜頭の上面）と重なる。ロッドは半径 rod の円周上の、半径 rod_r の円。
    既定の板厚 2.5 では板の外面（78.5）がロッドの縁（85）に届かないので、板厚を 10 にして外面を 86 に出す。
    当て板の局所座標（u: 板の方位、v: それに直交）でロッドの中心から矩形までの距離が rod_r になる方位がちょうど。"""
    from gatling.fasteners import lookup_rod
    from gatling.placement import pad_plan
    base = override(SPEC, pad__thickness=10)
    rod_r, r = float(lookup_rod(base.lug.thread)) / 2, radii(base)
    u0, u1, v0, v1 = pad_plan(base)

    def distance(angle):
        phi = math.radians(angle)               # 当て板の方位 −angle と、ロッド（方位 0°）の間の角
        return _dist_to_rect((r.rod * math.cos(phi), r.rod * math.sin(phi)), u0, u1, v0, v1)

    hit = lambda a: bool(_hits(mount_clear(override(base, pad__angle=a)), "当て板がロッドに当たる"))
    edge = _edge(hit, 30.0, 0.0)
    assert 0.0 < edge < 30.0
    assert math.isclose(distance(edge), rod_r, abs_tol=0.01), (edge, distance(edge), rod_r)
    assert 0 in lug_angles(SPEC)


def _centroid(poly):
    return (sum(x for x, _ in poly) / len(poly), sum(y for _, y in poly) / len(poly))


@pytest.mark.parametrize("part, point, bottom, extra", [
    ("当て板", lambda s: _centroid(pad_polys(s)[0]), lambda s, z: z.pad_bottom, {}),
    ("スペードグリップ", lambda s: _centroid(grip_polys(s)[0]), lambda s, z: grip_z(s)[0], {"grip__drop": 0}),
    ("ブロック", lambda s: holder_centre(s), lambda s, z: z.arm_centre, {}),
    ("ホルダー受け", lambda s: holder_centre(s), lambda s, z: z.holder_bottom, {}),
])
def test_a_flange_bolt_under_each_mount_part_needs_room_to_be_pulled_exactly_to_that_parts_underside(monkeypatch, part, point, bottom, extra):
    """ボルトの位置を各部品の真下に置き（頭の円がその部品の平面形に入る）、ボルト長を伸ばして、その部品の下端とフランジ上面の
    距離がちょうど頭の高さ + ねじ込み長になるところで、その部品のぶんだけが切り替わる。他の部品（腕など）が同じ点の上にあっても、
    見るのはその部品の名前のメッセージだけ。"""
    base = override(SPEC, **extra)
    z, screw = levels(base), lookup_screw(base.flange.bolt)
    monkeypatch.setattr(interference, "flange_bolt_points", lambda spec: [point(spec)])
    stack = float(base.flange.thickness) + float(base.gasket.thickness)
    edge = (bottom(base, z) - z.flange_top) - float(screw.head_height) + stack
    mine = lambda found: [i for i in found if i.what.startswith(f"{part}の下で")]
    assert mine(flange_bolts_removable(override(base, flange__bolt_length=edge))) == []
    found = mine(flange_bolts_removable(override(base, flange__bolt_length=edge + 0.01)))
    assert len(found) == 1 and found[0].fatal


def _synthetic(spec, radius, z0, z1, distance, monkeypatch):
    """胴の軸から `distance` の所に半径 1 の円柱を、z の範囲 [z0, z1] に置いた 1 個の部品だけを相手にする。"""
    body = Body("試験片", circles=((( distance + 1.0, 0.0), 1.0),), z=(z0, z1))
    monkeypatch.setattr(interference, "mount_bodies", lambda s: [body])
    return mount_clear(spec)


def test_every_revolved_part_around_the_shell_is_a_counterpart_with_its_own_radius_and_z_band(monkeypatch):
    """胴・エッジ環、フレッシュフープ、内リング、外リング（管）、受金、フランジ・ヘッダープレート、管束・クランプのどれも相手になり、
    外半径の縁ちょうどは通り、少し食い込むと fatal。z の端が接するだけなら通り、少し重なると fatal。"""
    parts = [*_round_parts(SPEC), _tube_bundle(SPEC)]
    assert sorted(p[0] for p in parts) == sorted(["胴・エッジ環", "フレッシュフープ", "内リング", "外リング（管）", "受金",
                                                  "フランジ・ヘッダープレート", "管束・クランプ"])
    for name, radius, z0, z1 in parts:
        mid = (z0 + z1) / 2
        hit = lambda dist, a=mid, b=mid + 0.5: [i for i in _synthetic(SPEC, radius, a, b, dist, monkeypatch) if f"に食い込む" in i.what and name in i.what]
        if name == "外リング（管）":
            continue                      # 環（中が空き）なので、半径は内面〜外面の帯。下の専用のテストで見る
        assert hit(radius) == [] and len(hit(radius - 0.01)) == 1, name
        # z: 上端に接する（ちょうど）か、少し重なる
        touch = [i for i in _synthetic(SPEC, radius, z1, z1 + 5, radius - 3.0, monkeypatch) if name in i.what and "食い込む" in i.what]
        over = [i for i in _synthetic(SPEC, radius, z1 - 0.01, z1 + 5, radius - 3.0, monkeypatch) if name in i.what and "食い込む" in i.what]
        assert touch == [] and len(over) == 1, name


def test_the_outer_ring_is_an_annulus_so_a_part_inside_its_inner_face_does_not_touch_it(monkeypatch):
    """外リング（管）は中が空いた環。半径で見ると内面〜外面の帯。内面より内側に収まる部品は、z が重なっても当たらない。
    外へ伸びる部品は帯を横切るので当たる。"""
    name, outer, z0, z1 = next(p for p in _round_parts(SPEC) if p[0] == "外リング（管）")
    inner = radii(SPEC).hoop_out_inner
    assert inner < outer
    z = ((z0 + z1) / 2, (z0 + z1) / 2 + 0.5)

    def hit(near, far):
        body = Body("試験片", circles=(((( near + far) / 2, 0.0), (far - near) / 2),), z=z)
        monkeypatch.setattr(interference, "mount_bodies", lambda s: [body])
        return [i for i in mount_clear(SPEC) if name in i.what]

    assert hit(inner - 20.0, inner) == []                    # 内面ちょうどまでなら当たらない
    assert len(hit(inner - 20.0, inner + 0.01)) == 1         # 帯に少し入る
    assert len(hit(inner - 20.0, outer + 10.0)) == 1         # 帯を横切る
    assert hit(outer, outer + 10.0) == []                    # 外面ちょうどから外は当たらない
    assert len(hit(outer - 0.01, outer + 10.0)) == 1


def test_a_tall_pad_inside_the_outer_ring_is_not_a_false_positive():
    """当て板の高さをプレナムの高さ（100）まで伸ばすと z は外リング（管）と重なるが、当て板は環の内面（103）より内側。
    3D でも当たらない（`overlaps` は重い。ここでは検査の結果だけ）。"""
    found = mount_clear(override(SPEC, pad__height=100))
    assert [i for i in found if "外リング" in i.what] == []


def test_a_knob_is_a_body_of_its_own_and_hits_the_block_when_it_grows_down(monkeypatch):
    """つまみ（ホルダー受けの後ろへ出る円柱）は軸の高さ = ホルダー受けの高さの中心。つまみの径を太くすると下端が下がり、
    ブロックの上面（= ホルダー受けの下面）に届いたところがちょうど。ホルダー受けの本体の円はブロックの上に載るだけで当たらない。"""
    centre = levels(SPEC).knob_centre
    top = levels(SPEC).block_top
    edge = 2 * (centre - top)
    hit = lambda d: [i for i in mount_clear(override(SPEC, mount__knob_dia=d)) if "ブロック" in i.what and "ホルダー受け" in i.what]
    assert hit(edge) == []
    assert len(hit(edge + 0.02)) == 1
