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
    """必要長（受金の上面からラグの下端まで）= 25.4 − 5 + 5 + 35 = 60.4。軸の先がこれより下に出ると警告。"""
    z = levels(SPEC)
    assert z.ear_top - z.lug_bottom == pytest.approx(60.4)
    found = rod_fits(override(SPEC, lug__rod_length=60.5))
    assert not _fatal(found) and any("ラグの下端" in i.what for i in found)
    assert rod_fits(override(SPEC, lug__rod_length=60.4)) == []


def test_the_rod_head_top_sits_exactly_at_the_hoop_top_so_it_never_warns_about_the_rim():
    """受金の上面 = フープの上端 − 頭の高さなので、頭の上面は頭の高さによらずフープの上端に揃う（縁ちょうどは通す）。
    リムショットの警告は、受金の位置を別に決める設計に戻したときのために残してある。"""
    for height in (1, 5, 7.9):
        spec = override(SPEC, lug__rod_head_height=height)
        z = levels(spec)
        assert z.rod_top == pytest.approx(z.hoop_top), height
        assert not any("リムショット" in i.what for i in rod_fits(spec)), height


def test_the_rod_head_must_clear_the_inner_ring():
    """頭 φ9 の中心 r 86。内縁 86 − 径 / 2 が内リングの外面 80.7 を割ると当たる（径 10.6 まで）。"""
    assert any("頭" in w and "内リング" in w for w in _fatal(rod_fits(override(SPEC, lug__rod_head_dia=10.7))))
    assert not any("頭" in w for w in _fatal(rod_fits(override(SPEC, lug__rod_head_dia=10.6))))


def test_the_rod_head_must_clear_the_pipe():
    """standoff 11.5 でロッド中心 87.5。頭の高さ（受金の上面 120.19 から上）での管の内面は 93.30 なので、頭の径は 11.60 まで。"""
    out = {"lug.standoff": 11.5}
    assert any("頭" in w and "外リング（管）" in w for w in _fatal(rod_fits(override(SPEC, lug__rod_head_dia=11.7, **out))))
    assert not any("頭" in w for w in _fatal(rod_fits(override(SPEC, lug__rod_head_dia=11.5, **out))))


def test_a_rod_head_no_larger_than_the_ear_hole_falls_through():
    assert any("頭" in w and "抜ける" in w for w in _fatal(rod_fits(override(SPEC, lug__rod_head_dia=6.5))))
    assert not any("抜ける" in w for w in _fatal(rod_fits(override(SPEC, lug__rod_head_dia=6.6))))


def test_a_lug_that_hangs_onto_the_band_is_fatal():
    # ラグの上端 94.79。高さ 50.79 で下端がバンド上端 44 にちょうど届く
    assert any("バンド" in w for w in _fatal(lug_fits(override(SPEC, lug__height=50.9))))
    assert not any("バンド" in w for w in _fatal(lug_fits(override(SPEC, lug__height=50.7))))


def test_the_mounting_hole_that_runs_past_the_ends_of_the_shell_is_fatal():
    # ラグの高さの中心（既定 77.29）に穴が 1 つ。下端はフランジ上面 7、上端は胴の上端 107
    assert not any("フランジ" in w for w in _fatal(lug_fits(override(SPEC, lug__height=150))))         # 中心 19.79、穴の下縁 17.29 > 7
    assert any("フランジ" in w for w in _fatal(lug_fits(override(SPEC, lug__height=180))))             # 中心 4.79、穴の下縁 2.29 < 7
    high = {"hoop.outer.od": 5, "head.collar_height": 1}                                         # ラグの上端が 111.19 に上がる
    assert any("胴の上端" in w for w in _fatal(lug_fits(override(SPEC, lug__height=10, **high))))     # 中心 106.19、穴の上縁 108.69 > 107
    assert not any("胴の上端" in w for w in _fatal(lug_fits(override(SPEC, lug__height=40, **high))))


def test_the_mounting_hole_must_fall_inside_the_foot():
    """穴（φ5）は台座（φ12）の中に収まる。台座が穴より小さい（等しい）と、ねじの座が胴に残らない。"""
    assert any("台座" in w and "穴" in w for w in _fatal(lug_fits(override(SPEC, lug__foot_dia=5))))
    assert any("台座" in w and "穴" in w for w in _fatal(lug_fits(override(SPEC, lug__foot_dia=4))))
    assert not any("台座" in w and "穴" in w for w in _fatal(lug_fits(override(SPEC, lug__foot_dia=5.1))))


def test_the_foot_must_fit_the_lug_height():
    """台座は穴の高さ（ラグの高さの中心）を軸にするので、台座の径がラグの高さを超えるとラグから出る。"""
    assert any("台座" in w and "ラグの高さ" in w for w in _fatal(lug_fits(override(SPEC, lug__foot_dia=35.1, lug__body_dia=40))))
    assert not any("台座" in w and "ラグの高さ" in w for w in _fatal(lug_fits(override(SPEC, lug__foot_dia=35, lug__body_dia=40))))
    assert any("台座" in w and "ラグの高さ" in w for w in _fatal(lug_fits(override(SPEC, lug__height=11))))      # 台座 φ12 > 高さ 11


def test_the_body_must_leave_a_wall_around_the_rod_bore():
    """ラグの本体（φ16）にロッドの穴（#12-24 = φ5.5）を通す。本体の径が穴径以下だと肉が残らない。"""
    assert lug_fits(SPEC) == []
    assert any("本体" in w for w in _fatal(lug_fits(override(SPEC, lug__body_dia=5.5))))
    assert any("本体" in w for w in _fatal(lug_fits(override(SPEC, lug__body_dia=5))))
    assert not any("本体" in w for w in _fatal(lug_fits(override(SPEC, lug__body_dia=5.6))))
    assert any("本体" in w for w in _fatal(lug_fits(override(SPEC, lug__thread="M5", lug__body_dia=4.9))))
    assert not any("本体" in w for w in _fatal(lug_fits(override(SPEC, lug__thread="M5", lug__body_dia=5.1))))


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
    """肉 = 内側は (ロッド − 穴径 / 2) − 内リングの外面（80.7）、外側は受金の z 帯 [114.19, 120.19] での管の内面（90.81）− (ロッド + 穴径 / 2)。
    穴の半径 3.25。ロッドの半径 = 76 + standoff。内側は 84 で 0.05、83.9 で負。外側は 87.5 で 0.06、87.6 で負。"""
    assert any("内側" in w for w in _fatal(ear_fits(override(SPEC, lug__standoff=7.9))))
    assert not any("内側" in w for w in _fatal(ear_fits(override(SPEC, lug__standoff=8.0))))
    assert any("外側" in w for w in _fatal(ear_fits(override(SPEC, lug__standoff=11.6))))
    assert not any("外側" in w for w in _fatal(ear_fits(override(SPEC, lug__standoff=11.5))))
    assert any("外側" in w for w in _fatal(ear_fits(override(SPEC, lug__standoff=11.7))))        # 穴が受金の外端（管の切り欠き）を破る


def test_a_thin_radial_wall_beside_the_rod_hole_is_only_a_warning():
    """径方向の肉は、穴の両側が溶接でリングに支えられるので、板厚（6）の半分の 3 mm を目安にする。既定は内側 2.05・外側 1.56 で警告。
    リングの間（gap）を 4 広げ、ロッドを 1 外へ寄せると、内側 3.05・外側 4.47 で無警告。"""
    found = ear_fits(SPEC)
    assert not _fatal(found) and any("内側" in i.what for i in found) and any("外側" in i.what for i in found)
    wide = float(SPEC.hoop.gap) + 4
    assert ear_fits(override(SPEC, lug__standoff=11, hoop__gap=wide)) == []
    assert any("内側" in i.what for i in ear_fits(override(SPEC, lug__standoff=10.9, hoop__gap=wide)))      # 2.95
    assert ear_fits(override(SPEC, lug__standoff=12.5, hoop__gap=wide)) == []                               # 外側 3.06
    assert any("外側" in i.what for i in ear_fits(override(SPEC, lug__standoff=12.6, hoop__gap=wide)))      # 外側 2.96


def test_too_many_ears_and_lugs_run_into_each_other():
    """隣り合う矩形は内側の端で先に当たる。幅 ≤ 2 × 内端の半径 × tan(180° / 個数)。
    受金（幅 20、内端 = 内リングの外面 r 80.7）は 25 個まで、ラグ（幅 20、内端 r 76）は 24 個まで。"""
    found = _fatal(spacing(override(SPEC, lug__count=26, hoop__ear__count=26)))
    assert any("受金" in w for w in found) and any("ラグ" in w for w in found), found
    found = _fatal(spacing(override(SPEC, lug__count=25, hoop__ear__count=25)))
    assert any("ラグ" in w for w in found) and not any("受金" in w for w in found), found
    assert spacing(override(SPEC, lug__count=24, hoop__ear__count=24)) == []
    assert spacing(SPEC) == [] and spacing(override(SPEC, lug__count=2, hoop__ear__count=2)) == []


def test_an_ear_cannot_stick_up_out_of_the_rim_because_its_top_is_the_hoop_top_minus_the_head():
    """受金の上面 = フープの上端 − ロッドの頭の高さ。頭の高さが正（構造の検査が保証する）なら、突き出ない。負なら fatal。"""
    assert not any("突き出" in w for w in _fatal(ear_fits(SPEC)))
    assert not any("突き出" in w for w in _fatal(ear_fits(override(SPEC, hoop__ear__thickness=40))))      # 板厚は下へ伸びるだけ
    assert any("受金" in w and "突き出" in w for w in _fatal(ear_fits(override(SPEC, lug__rod_head_height=-1))))


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


def test_a_lug_body_whose_radius_exceeds_the_standoff_is_a_warning_not_silently_clipped():
    """本体の半径が standoff（胴の外面からロッドの中心）を超えると、本体が胴の外面で切られ、BOM の本体径と形が合わなくなる。"""
    ok = lug_fits(override(SPEC, lug__body_dia=20))              # 半径 10 = standoff 10（縁ちょうど）
    assert not any("本体" in i.what and "胴の外面" in i.what for i in ok)
    for dia in (20.5, 24):
        found = lug_fits(override(SPEC, lug__body_dia=dia))
        hit = [i for i in found if "本体" in i.what and "胴の外面" in i.what]
        assert len(hit) == 1 and not hit[0].fatal, found
