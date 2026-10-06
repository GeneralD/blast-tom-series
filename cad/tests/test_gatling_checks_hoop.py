"""検査（方位・フープ・ロッド・受金）。ラグの検査は `test_gatling_checks_lug.py`。"""

from __future__ import annotations

import pytest
from gatling.checks import aligned, ear_fits, hoop_seat, key_socket_fits, lug_fits, rod_fits
from gatling.fasteners import lookup_rod
from gatling.params import SPEC, override
from gatling.placement import levels, pipe_inner_radius, radii


def _fatal(issues):
    return [i.what for i in issues if i.fatal]


def test_the_default_hoop_lugs_and_rods_pass():
    assert aligned(6, 6, 6) == [] and rod_fits(SPEC) == [] and lug_fits(SPEC) == [] and hoop_seat(SPEC) == [] and not _fatal(ear_fits(SPEC))


@pytest.mark.parametrize("tubes, lugs", [(6, 6), (6, 3), (6, 2), (6, 1), (3, 6), (12, 6), (12, 4)])
def test_the_tube_count_may_be_a_multiple_or_a_divisor_of_the_lug_count(tubes, lugs):
    assert aligned(tubes, lugs, lugs) == []


@pytest.mark.parametrize("tubes, lugs", [(6, 4), (6, 5), (5, 6), (7, 3)])
def test_a_tube_count_that_is_neither_breaks_the_alignment(tubes, lugs):
    assert any("方位が揃わない" in w for w in _fatal(aligned(tubes, lugs, lugs)))


def test_the_ears_must_be_as_many_as_the_lugs():
    assert any("同数" in w for w in _fatal(aligned(6, 6, 4)))


def test_a_rod_that_does_not_clear_the_inner_ring_is_fatal():
    assert any("内リング" in w for w in _fatal(rod_fits(override(SPEC, lug__standoff=4))))


def test_a_ring_gap_too_narrow_for_the_rod_is_fatal():
    """外側の相手は外リングの管の内側の接線（内リングの外面 80.7 + 間隔）。ロッド中心 87.75 + 2.75 が収まる最小の間隔は 9.8。"""
    assert any("外リング（管）" in w for w in _fatal(rod_fits(override(SPEC, hoop__gap=4))))
    assert any("外リング（管）" in w for w in _fatal(rod_fits(override(SPEC, hoop__gap=9.7))))
    assert _fatal(rod_fits(override(SPEC, hoop__gap=9.9))) == []


def test_the_rod_shaft_must_thread_into_the_lug_by_the_engagement():
    """軸の先 = 受金の上面 120.19 − rod_length。ラグの上端 94.79 からねじ込み代 0.75 × 5.5 = 4.125 まで届く最短は 29.525。"""
    z = levels(SPEC)
    assert z.ear_top - z.lug_top + 0.75 * 5.5 == pytest.approx(29.525)
    assert any("ロッドが短い" in w for w in _fatal(rod_fits(override(SPEC, lug__rod_length=29.5))))
    assert _fatal(rod_fits(override(SPEC, lug__rod_length=29.53))) == []


@pytest.mark.parametrize("path, value", [
    ("hoop.takeup", 27),               # ラグ全体が下がる
    ("hoop.outer.od", 48),             # 管が下へ垂れ、ラグも下がる
    ("head.collar_height", 60),        # フレッシュフープの下端が管より下がり、ラグも下がる
])
def test_the_shortest_rod_follows_every_height_between_the_ear_and_the_lug(path, value):
    assert any("ロッドが短い" in w for w in _fatal(rod_fits(override(SPEC, **{path: value})))), path


def test_a_rod_that_runs_out_of_the_lug_bottom_is_a_warning():
    """必要長（受金の上面からラグの下端まで）= 25.4 − 5 + 5 + 30 = 55.4。軸の先がこれより下に出ると警告。"""
    z = levels(SPEC)
    assert z.ear_top - z.lug_bottom == pytest.approx(55.4)
    found = rod_fits(override(SPEC, lug__rod_length=55.5))
    assert not _fatal(found) and any("ラグの下端" in i.what for i in found)
    assert rod_fits(override(SPEC, lug__rod_length=55.4)) == []


def test_the_rod_head_must_clear_the_inner_ring():
    """頭 φ9 の中心 r 87.75。内縁 87.75 − 径 / 2 が内リングの外面 80.7 を割ると当たる（径 14.1 まで）。"""
    assert any("頭" in w and "内リング" in w for w in _fatal(rod_fits(override(SPEC, lug__rod_head_dia=14.2))))
    assert not any("頭" in w for w in _fatal(rod_fits(override(SPEC, lug__rod_head_dia=14.1))))


def test_the_rod_head_must_clear_the_pipe():
    """standoff 15 でロッド中心 91。頭の高さ（受金の上面 120.19 から上）での管の内面は 97.30 なので、頭の径は 12.60 まで。"""
    out = {"lug.standoff": 15}
    assert any("頭" in w and "外リング（管）" in w for w in _fatal(rod_fits(override(SPEC, lug__rod_head_dia=12.7, **out))))
    assert not any("頭" in w for w in _fatal(rod_fits(override(SPEC, lug__rod_head_dia=12.5, **out))))


def test_a_rod_head_no_larger_than_the_ear_hole_falls_through():
    assert any("頭" in w and "抜ける" in w for w in _fatal(rod_fits(override(SPEC, lug__rod_head_dia=6.5))))
    assert not any("抜ける" in w for w in _fatal(rod_fits(override(SPEC, lug__rod_head_dia=6.6))))


def test_the_inner_ring_must_bear_on_the_collar_and_not_on_the_film():
    assert any("膜" in w for w in _fatal(hoop_seat(override(SPEC, hoop__seat=1.6))))         # 肉厚 1.5 を超えると膜に載る
    assert hoop_seat(override(SPEC, hoop__seat=1.5)) == []


def test_a_rod_that_does_not_clear_the_collar_is_fatal():
    """内リングを薄くして掛かりを増やすと、内リングの外面（76.7）がフレッシュフープの外面（77.7）より内側になる。
    ロッドはフレッシュフープの高さも通るので、内側の下限は 2 つの外面の大きいほう。頭は φ7 にして内リングから逃がす。"""
    thin = {"hoop.inner.thickness": 0.5, "hoop.seat": 1.5, "lug.rod_head_dia": 7}
    assert any("フレッシュフープ" in w for w in _fatal(rod_fits(override(SPEC, lug__standoff=4, **thin))))      # 80 − 2.75 = 77.25
    assert _fatal(rod_fits(override(SPEC, lug__standoff=4.5, **thin))) == []                                # 77.75


def test_an_ear_no_wider_than_the_rod_hole_splits_in_two_and_is_fatal():
    """穴は 5.5 + 逃げ 1 = 6.5。幅が穴径以下だと受金が 2 片に割れる。"""
    for width in (5, 6.5):
        assert any("受金" in w and "割れる" in w for w in _fatal(ear_fits(override(SPEC, hoop__ear__width=width)))), width


def test_a_thin_wall_beside_the_rod_hole_is_only_a_warning():
    """穴の両側に板厚ぶんの肉（6.5 + 2 × 6 = 18.5）は目安なので、下回っても警告にとどめる。板厚 8 で既定の幅 20 も警告。"""
    for values in ({"hoop.ear.width": 6.6}, {"hoop.ear.width": 18.4}, {"hoop.ear.thickness": 8}):
        found = ear_fits(override(SPEC, **values))
        assert found and not _fatal(found) and all("受金" in i.what for i in found), values
    assert not any("幅" in i.what for i in ear_fits(override(SPEC, hoop__ear__width=18.5)))     # 径方向の肉の警告は別（下のテスト）


def test_the_ear_walls_beside_the_rod_hole_are_fatal_when_the_hole_breaks_out_of_the_plate():
    """肉 = 内側は (ロッド − 穴径 / 2) − 内リングの外面（80.7）、外側は受金の z 帯 [114.19, 120.19] での管の内面（94.81）− (ロッド + 穴径 / 2)。
    穴の半径 3.25。ロッドの半径 = 76 + standoff。内側は 84 で 0.05、83.9 で負。外側は 91.5 で 0.06、91.6 で負。"""
    assert any("内側" in w for w in _fatal(ear_fits(override(SPEC, lug__standoff=7.9))))
    assert not any("内側" in w for w in _fatal(ear_fits(override(SPEC, lug__standoff=8.0))))
    assert any("外側" in w for w in _fatal(ear_fits(override(SPEC, lug__standoff=15.6))))
    assert not any("外側" in w for w in _fatal(ear_fits(override(SPEC, lug__standoff=15.5))))
    assert any("外側" in w for w in _fatal(ear_fits(override(SPEC, lug__standoff=15.7))))        # 穴が受金の外端（管の切り欠き）を破る


def test_a_thin_radial_wall_beside_the_rod_hole_is_only_a_warning():
    """径方向の肉は、穴の両側が溶接でリングに支えられるので、板厚（6）の半分の 3 mm を目安にする。既定（standoff 11.75）は両側 3.8 で無警告。
    内側の肉 = standoff − 8.95 は 10.95 で 3.0、外側の肉 = 15.56 − standoff は 12.56 で 3.0（溝を 10 → 14 に広げた理由の 1 つ）。"""
    assert ear_fits(override(SPEC, lug__standoff=10.95)) == [] and ear_fits(override(SPEC, lug__standoff=12.5)) == []
    found = ear_fits(override(SPEC, lug__standoff=10.9))
    assert not _fatal(found) and any("内側" in i.what for i in found) and not any("外側" in i.what for i in found)       # 内側 2.95
    found = ear_fits(override(SPEC, lug__standoff=12.6))
    assert not _fatal(found) and any("外側" in i.what for i in found) and not any("内側" in i.what for i in found)       # 外側 2.96
    narrow = ear_fits(override(SPEC, hoop__gap=10, lug__standoff=10))                                                    # 旧い溝 10: 内側 2.05・外側 1.56
    assert any("内側" in i.what for i in narrow) and any("外側" in i.what for i in narrow)


def test_an_ear_must_overlap_the_inner_ring_in_z_to_be_welded_to_it():
    """受金の帯 [上面 − 板厚, 上面 = フープの上端 − 頭の高さ 5] と内リングの帯 [膜面, フープの上端] の重なり。
    既定は上面 = 膜面 + 3 で 3 mm（板厚の半分ちょうど。縁は通す）。リム inner.height = 5 で重なり 0 になり、溶接できない。"""
    weld = lambda spec: [i for i in ear_fits(spec) if "内リング" in i.what]
    assert weld(SPEC) == []
    assert any("溶接できない" in w for w in _fatal(ear_fits(override(SPEC, hoop__inner__height=5)))), "重なり 0"
    assert any("溶接できない" in w for w in _fatal(ear_fits(override(SPEC, hoop__inner__height=4))))      # 受金が膜面より下に収まる
    for height in (5.1, 7.9):                                                                           # 正だが板厚の半分（3）に足りない
        found = weld(override(SPEC, hoop__inner__height=height))
        assert len(found) == 1 and not found[0].fatal and "溶接" in found[0].what, height
    assert weld(override(SPEC, hoop__inner__height=8)) == [] and weld(override(SPEC, hoop__inner__height=20)) == []


def test_the_weld_overlap_is_the_whole_thickness_when_the_ear_sits_inside_the_rim_band():
    """受金が内リングの帯に完全に入る（下面が膜面より上）と、重なりは板厚。板厚の半分には足りる。"""
    thin = override(SPEC, hoop__inner__height=20, hoop__ear__thickness=2)
    assert [i for i in ear_fits(thin) if "内リング" in i.what] == []
    assert any("溶接できない" in w for w in _fatal(ear_fits(override(SPEC, hoop__inner__height=5, hoop__ear__thickness=2))))


def test_an_ear_that_does_not_reach_the_pipe_is_fatal():
    """管の下端 = フープの上端 − 外径。受金の上面（フープの上端 − 5）が管の下端以下だと、受金が管に届かず溶接できない。"""
    assert any("受金" in w and "届かない" in w for w in _fatal(ear_fits(override(SPEC, hoop__outer__od=5))))
    assert not any("届かない" in w for w in _fatal(ear_fits(override(SPEC, hoop__outer__od=5.1))))


def test_the_default_key_socket_fits_between_the_rings():
    """ドラムキーの差し口（既定 φ13）を頭に被せた円が、内リングの外面と頭の高さでの管の内面の間に収まる。"""
    assert float(SPEC.lug.key_socket_dia) == 13
    assert key_socket_fits(SPEC) == []


def test_the_key_socket_must_clear_the_inner_ring_exactly_at_the_edge():
    """内縁 = ロッド中心 − 差し口の半径。内リングの外面に縁ちょうどで通り、少し越えると fatal。"""
    r = radii(SPEC)
    exact = 2 * (r.rod - r.hoop_in_outer)
    assert key_socket_fits(override(SPEC, lug__key_socket_dia=exact)) == []
    found = _fatal(key_socket_fits(override(SPEC, lug__key_socket_dia=exact + 0.1)))
    assert any("内リング" in w for w in found) and not any("管" in w for w in found)


def test_the_key_socket_must_clear_the_pipe_exactly_at_the_edge():
    """外縁 = ロッド中心 + 差し口の半径。頭の高さ（受金の上面から頭の上面）での管の内面に縁ちょうどで通り、少し越えると fatal。"""
    z, wide = levels(SPEC), override(SPEC, lug__standoff=15)           # ロッドを外へ寄せ、外側が先に詰まるようにする（中心 91）
    exact = 2 * (pipe_inner_radius(wide, z.ear_top, z.rod_top) - radii(wide).rod)
    assert key_socket_fits(override(wide, lug__key_socket_dia=exact)) == []
    found = _fatal(key_socket_fits(override(wide, lug__key_socket_dia=exact + 0.1)))
    assert any("管" in w for w in found) and not any("内リング" in w for w in found)


def test_the_old_ten_millimetre_gap_cannot_take_the_key_socket():
    """溝 10 では差し口 φ13 が入らない（これが溝を 14 に広げた理由）。"""
    assert any("差し口" in w for w in _fatal(key_socket_fits(override(SPEC, hoop__gap=10, lug__standoff=10))))


def test_the_default_ear_walls_beside_the_rod_hole_are_both_at_least_half_the_plate_thickness():
    """既定の受金の穴の両側の肉（内側・外側）は、板厚の半分（3 mm）以上で、警告が出ない。"""
    r, z = radii(SPEC), levels(SPEC)
    hole = float(lookup_rod(SPEC.lug.thread)) + float(SPEC.hoop.ear.hole_clearance)
    inner = (r.rod - hole / 2) - r.hoop_in_outer
    outer = min(pipe_inner_radius(SPEC, z.ear_bottom, z.ear_top), r.hoop_out_centre) - (r.rod + hole / 2)
    assert inner == pytest.approx(3.8, abs=0.01) and outer == pytest.approx(3.815, abs=0.01)
    assert ear_fits(SPEC) == []
