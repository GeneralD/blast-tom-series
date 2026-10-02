"""検査（方位・フープ・ラグ・ロッド）。"""

from __future__ import annotations

import pytest
from gatling.checks import aligned, ear_fits, hoop_seat, lug_fits, rod_fits, spacing
from gatling.params import SPEC, override
from gatling.placement import levels


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
    """外側の相手は外リングの管の内側の接線（内リングの外面 80.7 + 間隔）。ロッド中心 86 + 2.75 が収まる最小の間隔は 8.05。"""
    assert any("外リング（管）" in w for w in _fatal(rod_fits(override(SPEC, hoop__gap=4))))
    assert any("外リング（管）" in w for w in _fatal(rod_fits(override(SPEC, hoop__gap=8.0))))
    assert _fatal(rod_fits(override(SPEC, hoop__gap=8.1))) == []


def test_the_rod_shaft_must_thread_into_the_lug_by_the_engagement():
    """軸の先 = 受金の上面 123.19 − rod_length。ラグの上端 98.79 からねじ込み代 0.75 × 5.5 = 4.125 まで届く最短は 28.525。"""
    z = levels(SPEC)
    assert z.ear_top - z.lug_top + 0.75 * 5.5 == pytest.approx(28.525)
    assert any("ロッドが短い" in w for w in _fatal(rod_fits(override(SPEC, lug__rod_length=28.5))))
    assert _fatal(rod_fits(override(SPEC, lug__rod_length=28.53))) == []


@pytest.mark.parametrize("path, value", [
    ("hoop.takeup", 27),               # ラグ全体が下がる
    ("hoop.outer.od", 48),             # 管が下へ垂れ、ラグも下がる
    ("head.collar_height", 35),        # フレッシュフープの下端が管より下がり、ラグも下がる
])
def test_the_shortest_rod_follows_every_height_between_the_ear_and_the_lug(path, value):
    assert any("ロッドが短い" in w for w in _fatal(rod_fits(override(SPEC, **{path: value})))), path


def test_a_rod_that_runs_out_of_the_lug_bottom_is_a_warning():
    """必要長（受金の上面からラグの下端まで）= 6 + 13.4 + 5 + 35 = 59.4。軸の先がこれより下に出ると警告。"""
    z = levels(SPEC)
    assert z.ear_top - z.lug_bottom == pytest.approx(59.4)
    found = rod_fits(override(SPEC, lug__rod_length=59.5))
    assert not _fatal(found) and any("ラグの下端" in i.what for i in found)
    assert rod_fits(override(SPEC, lug__rod_length=59.4)) == []


def test_a_rod_head_above_the_hoop_top_is_a_warning():
    """頭の上面 = 受金の上面 123.19 + 頭の高さ。フープの上端 129.19 を超えるとリムショットの邪魔になる。"""
    found = rod_fits(override(SPEC, lug__rod_head_height=6.1))
    assert not _fatal(found) and any("リムショット" in i.what for i in found)
    assert rod_fits(override(SPEC, lug__rod_head_height=6)) == []


def test_the_rod_head_must_clear_the_inner_ring():
    """頭 φ9 の中心 r 86。内縁 86 − 径 / 2 が内リングの外面 80.7 を割ると当たる（径 10.6 まで）。"""
    assert any("頭" in w and "内リング" in w for w in _fatal(rod_fits(override(SPEC, lug__rod_head_dia=10.7))))
    assert not any("頭" in w for w in _fatal(rod_fits(override(SPEC, lug__rod_head_dia=10.6))))


def test_the_rod_head_must_clear_the_pipe():
    """standoff 11.5 でロッド中心 87.5。頭の高さ（受金の上面から上）での管の内面は 92.61 なので、頭の径は 10.22 まで。"""
    out = {"lug.standoff": 11.5}
    assert any("頭" in w and "外リング（管）" in w for w in _fatal(rod_fits(override(SPEC, lug__rod_head_dia=11, **out))))
    assert not any("頭" in w for w in _fatal(rod_fits(override(SPEC, lug__rod_head_dia=10.2, **out))))


def test_a_rod_head_no_larger_than_the_ear_hole_falls_through():
    assert any("頭" in w and "抜ける" in w for w in _fatal(rod_fits(override(SPEC, lug__rod_head_dia=6.5))))
    assert not any("抜ける" in w for w in _fatal(rod_fits(override(SPEC, lug__rod_head_dia=6.6))))


def test_a_lug_that_hangs_onto_the_band_is_fatal():
    # ラグの上端 98.79。高さ 54.79 で下端がバンド上端 44 にちょうど届く
    assert any("バンド" in w for w in _fatal(lug_fits(override(SPEC, lug__height=54.9))))
    assert not any("バンド" in w for w in _fatal(lug_fits(override(SPEC, lug__height=54.7))))


def test_mounting_holes_that_run_past_the_ends_of_the_shell_are_fatal():
    assert any("上端" in w for w in _fatal(lug_fits(override(SPEC, lug__pitch=60))))        # 81.29 + 32.5 > 107
    assert any("下端" in w for w in _fatal(lug_fits(override(SPEC, lug__height=100, lug__pitch=100))))


def test_mounting_holes_must_fall_inside_the_lug_body():
    # ラグ z 63.79〜98.79（中央 81.29）。穴の外縁 = 中央 ± (pitch / 2 + 穴径 / 2) が収まるのは pitch + 穴径 ≤ 35 まで
    assert any("ラグの高さ" in w for w in _fatal(lug_fits(override(SPEC, lug__pitch=31))))
    assert not any("ラグの高さ" in w for w in _fatal(lug_fits(override(SPEC, lug__pitch=30))))
    assert any("ラグの高さ" in w for w in _fatal(lug_fits(override(SPEC, lug__pitch=40))))      # 高さ 35 を超えるピッチ


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
    """肉 = 内側は (ロッド − 穴径 / 2) − 内リングの外面（80.7）、外側は受金の z 帯での管の内面（90.72）− (ロッド + 穴径 / 2)。
    穴の半径 3.25。ロッドの半径 = 76 + standoff。内側は 84 で 0.05、83.9 で負。外側は 87.4 で 0.07、87.5 で負。"""
    assert any("内側" in w for w in _fatal(ear_fits(override(SPEC, lug__standoff=7.9))))
    assert not any("内側" in w for w in _fatal(ear_fits(override(SPEC, lug__standoff=8.0))))
    assert any("外側" in w for w in _fatal(ear_fits(override(SPEC, lug__standoff=11.5))))
    assert not any("外側" in w for w in _fatal(ear_fits(override(SPEC, lug__standoff=11.4))))
    assert any("外側" in w for w in _fatal(ear_fits(override(SPEC, lug__standoff=11.7))))        # 穴が受金の外端（管の切り欠き）を破る


def test_a_thin_radial_wall_beside_the_rod_hole_is_only_a_warning():
    """径方向の肉は、穴の両側が溶接でリングに支えられるので、板厚（6）の半分の 3 mm を目安にする。既定は内側 2.05・外側 1.47 で警告。
    リングの間（gap）を 4 広げ、ロッドを 1 外へ寄せると、内側 3.05・外側 4.47 で無警告。"""
    found = ear_fits(SPEC)
    assert not _fatal(found) and any("内側" in i.what for i in found) and any("外側" in i.what for i in found)
    wide = float(SPEC.hoop.gap) + 4
    assert ear_fits(override(SPEC, lug__standoff=11, hoop__gap=wide)) == []
    assert any("内側" in i.what for i in ear_fits(override(SPEC, lug__standoff=10.9, hoop__gap=wide)))      # 2.95
    assert ear_fits(override(SPEC, lug__standoff=12.4, hoop__gap=wide)) == []                               # 外側 3.07
    assert any("外側" in i.what for i in ear_fits(override(SPEC, lug__standoff=12.5, hoop__gap=wide)))      # 外側 2.97


def test_too_many_ears_and_lugs_run_into_each_other():
    """隣り合う矩形は内側の端で先に当たる。幅 ≤ 2 × 内端の半径 × tan(180° / 個数)。
    受金（幅 20、内端 = 内リングの外面 r 80.7）は 25 個まで、ラグ（幅 20、内端 r 76）は 24 個まで。"""
    found = _fatal(spacing(override(SPEC, lug__count=26, hoop__ear__count=26)))
    assert any("受金" in w for w in found) and any("ラグ" in w for w in found), found
    found = _fatal(spacing(override(SPEC, lug__count=25, hoop__ear__count=25)))
    assert any("ラグ" in w for w in found) and not any("受金" in w for w in found), found
    assert spacing(override(SPEC, lug__count=24, hoop__ear__count=24)) == []
    assert spacing(SPEC) == [] and spacing(override(SPEC, lug__count=2, hoop__ear__count=2)) == []


def test_an_ear_that_sticks_up_out_of_the_rim_is_fatal():
    """受金の下面 = 膜面、上面 = 膜面 + 板厚。リムの高さ 12 を超えるとフープの上端から突き出る。"""
    assert any("受金" in w and "突き出" in w for w in _fatal(ear_fits(override(SPEC, hoop__ear__thickness=12.1))))
    assert not any("突き出" in w for w in _fatal(ear_fits(override(SPEC, hoop__ear__thickness=12))))
    assert any("突き出" in w for w in _fatal(ear_fits(override(SPEC, hoop__inner__height=5.9))))


def test_an_ear_that_does_not_reach_the_pipe_is_fatal():
    """管の下端 = フープの上端 − 外径。受金の上面（膜面 + 6）が管の下端以下だと、受金が管に届かず溶接できない。"""
    assert any("受金" in w and "届かない" in w for w in _fatal(ear_fits(override(SPEC, hoop__outer__od=6))))
    assert not any("届かない" in w for w in _fatal(ear_fits(override(SPEC, hoop__outer__od=6.1))))
