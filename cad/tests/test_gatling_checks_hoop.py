"""検査（方位・フープ・ラグ・ロッド）。"""

from __future__ import annotations

import pytest
from gatling.checks import aligned, ear_fits, hoop_seat, lug_fits, rod_fits, spacing
from gatling.params import SPEC, override
from gatling.placement import levels


def _fatal(issues):
    return [i.what for i in issues if i.fatal]


def test_the_default_hoop_lugs_and_rods_pass():
    assert aligned(6, 6, 6) == [] and rod_fits(SPEC) == [] and lug_fits(SPEC) == [] and hoop_seat(SPEC) == [] and ear_fits(SPEC) == []


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
    assert any("外リング" in w for w in _fatal(rod_fits(override(SPEC, hoop__gap=4))))
    assert any("外リング" in w for w in _fatal(rod_fits(override(SPEC, hoop__gap=7.0))))   # ロッド中心 84 ± 2.75 が 79.7 + 隙間に収まる最小は 7.05
    assert _fatal(rod_fits(override(SPEC, hoop__gap=7.1))) == []


def test_the_rod_must_reach_from_the_lug_bottom_to_the_ear_top():
    # 必要長は placement の高さから出す: 受金の上面 148.19 − ラグの下端 69.19 = 79
    z = levels(SPEC)
    assert z.ear_top - z.lug_bottom == pytest.approx(79)
    assert any("ロッドが短い" in w for w in _fatal(rod_fits(override(SPEC, lug__rod_length=78.9))))
    assert _fatal(rod_fits(override(SPEC, lug__rod_length=79))) == []


@pytest.mark.parametrize("path, value", [
    ("lug.height", 40),                # ラグの下端が下がる
    ("hoop.takeup", 9),                # ラグ全体が下がる
    ("head.collar_height", 12),        # フレッシュフープの下端が下がり、ラグも下がる
    ("hoop.inner.height", 30),         # 受金が上がる
    ("hoop.ear.thickness", 12),        # 受金の上面が上がる（ロッドが受金を貫かない）
])
def test_the_required_rod_length_follows_every_height_on_the_rod_path(path, value):
    assert any("ロッドが短い" in w for w in _fatal(rod_fits(override(SPEC, **{path: value})))), path


def test_a_lug_that_hangs_onto_the_band_is_fatal():
    # ラグの上端 104.19。高さ 60.19 で下端がバンド上端 44 にちょうど届く
    assert any("バンド" in w for w in _fatal(lug_fits(override(SPEC, lug__height=60.3))))
    assert not any("バンド" in w for w in _fatal(lug_fits(override(SPEC, lug__height=60.1))))


def test_mounting_holes_that_run_past_the_ends_of_the_shell_are_fatal():
    assert any("上端" in w for w in _fatal(lug_fits(override(SPEC, lug__pitch=60))))        # 86.69 + 32.5 > 107
    assert any("下端" in w for w in _fatal(lug_fits(override(SPEC, lug__height=100, lug__pitch=100))))


def test_mounting_holes_must_fall_inside_the_lug_body():
    # ラグ z 69.19〜104.19（中央 86.69）。穴の外縁 = 中央 ± (pitch / 2 + 穴径 / 2) が収まるのは pitch + 穴径 ≤ 35 まで
    assert any("ラグの高さ" in w for w in _fatal(lug_fits(override(SPEC, lug__pitch=31))))
    assert not any("ラグの高さ" in w for w in _fatal(lug_fits(override(SPEC, lug__pitch=30))))
    assert any("ラグの高さ" in w for w in _fatal(lug_fits(override(SPEC, lug__pitch=40))))      # 高さ 35 を超えるピッチ


def test_the_inner_ring_must_bear_on_the_collar_and_not_on_the_film():
    assert any("膜" in w for w in _fatal(hoop_seat(override(SPEC, hoop__seat=1.6))))         # 肉厚 1.5 を超えると膜に載る
    assert hoop_seat(override(SPEC, hoop__seat=1.5)) == []


def test_a_rod_that_does_not_clear_the_collar_is_fatal():
    """内リングを薄くして掛かりを増やすと、内リングの外面（76.7）がフレッシュフープの外面（77.7）より内側になる。
    ロッドはフレッシュフープの高さも通るので、内側の下限は 2 つの外面の大きいほう。"""
    thin = {"hoop.inner.thickness": 0.5, "hoop.seat": 1.5}
    assert any("フレッシュフープ" in w for w in _fatal(rod_fits(override(SPEC, lug__standoff=4, **thin))))      # 80 − 2.75 = 77.25
    assert _fatal(rod_fits(override(SPEC, lug__standoff=4.5, **thin))) == []                                # 77.75


def test_an_ear_must_leave_a_wall_on_both_sides_of_the_rod_hole():
    """穴（5.5 + 逃げ 1 = 6.5）の両側に板厚 6 の肉: 幅 18.5 以上。幅が穴径以下だと受金が 2 片に割れる。"""
    for width in (5, 6.5, 18.4):
        assert any("受金" in w for w in _fatal(ear_fits(override(SPEC, hoop__ear__width=width)))), width
    assert ear_fits(override(SPEC, hoop__ear__width=18.5)) == []


def test_too_many_ears_and_lugs_run_into_each_other():
    """隣り合う矩形は内側の端で先に当たる。幅 ≤ 2 × 内端の半径 × tan(180° / 個数)。
    受金（幅 20、内端 r 76.7）は 24 個まで、ラグ（幅 16、内端 r 76）は 29 個まで。"""
    found = _fatal(spacing(override(SPEC, lug__count=30, hoop__ear__count=30)))
    assert any("受金" in w for w in found) and any("ラグ" in w for w in found), found
    found = _fatal(spacing(override(SPEC, lug__count=25, hoop__ear__count=25)))
    assert any("受金" in w for w in found) and not any("ラグ" in w for w in found), found
    assert spacing(override(SPEC, lug__count=24, hoop__ear__count=24)) == []
    assert spacing(SPEC) == [] and spacing(override(SPEC, lug__count=2, hoop__ear__count=2)) == []
