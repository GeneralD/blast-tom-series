"""検査（クレードル・ホルダー・ボルトの長さ・規格径）。"""

from __future__ import annotations

import pytest
from gatling.checks import MIN_CRADLE_CLEARANCE, bolt_lengths, cradle_fits, holder_fits, stock_warning
from gatling.params import SPEC, override


def _fatal(issues):
    return [i.what for i in issues if i.fatal]


def _warn(issues):
    return [i.what for i in issues if not i.fatal]


def test_the_default_mount_passes_with_no_warning():
    assert cradle_fits(SPEC) == [] and holder_fits(SPEC) == [] and bolt_lengths(SPEC) == [] and stock_warning(SPEC) == []


_LOW = {"shell.plenum_height": 10}      # フレーム（z 9〜15）が外リングの管（z 13.79〜39.19）と同じ高さに来る


def test_a_frame_below_the_hoop_does_not_need_to_clear_it():
    """既定ではフレームの内面 98 < 管の外面 116.1 だが、フレーム（z 54〜60）は管（z 103.79〜129.19）より下にある。"""
    assert cradle_fits(SPEC) == []


def test_a_frame_that_cuts_into_the_outer_ring_is_fatal():
    # z が重なるとき: フレーム内面 = 83 + 逃げ、管の外面 = 116.1。逃げ 33.1 未満は負
    assert any("干渉" in w and "外リング" in w for w in _fatal(cradle_fits(override(SPEC, **_LOW))))
    assert any("干渉" in w for w in _fatal(cradle_fits(override(SPEC, cradle__clearance=33, **_LOW))))
    assert not any("干渉" in w for w in _fatal(cradle_fits(override(SPEC, cradle__clearance=33.1, **_LOW))))


def test_a_frame_that_only_just_clears_the_ring_is_a_warning():
    assert MIN_CRADLE_CLEARANCE == 5.0
    found = cradle_fits(override(SPEC, cradle__clearance=37.9, **_LOW))          # 逃げ 4.8
    assert not any("干渉" in w for w in _fatal(found)) and any("逃げが小さい" in w for w in _warn(found))
    assert not any("逃げ" in w for w in _warn(cradle_fits(override(SPEC, cradle__clearance=38.1, **_LOW))))   # 5.0 ちょうどは通す


def test_the_frame_must_be_above_the_band_so_the_legs_have_a_height():
    assert any("脚" in w for w in _fatal(cradle_fits(override(SPEC, shell__plenum_height=40))))


def test_the_flange_bolts_can_be_pulled_out_under_the_band():
    """頭（r 81〜91）は平面視でバンド（外面 r 83）の下に入るので、頭 6 + ねじ込み 5 = 11 の空きが要る。"""
    assert any("抜けない" in w for w in _fatal(cradle_fits(override(SPEC, band__above_flange=10.9))))
    assert not any("抜けない" in w for w in _fatal(cradle_fits(override(SPEC, band__above_flange=11))))
    assert any("抜けない" in w for w in _fatal(cradle_fits(override(SPEC, flange__bolt_length=14))))      # ねじ込み 7 → 13 要る


def test_bolt_heads_outside_the_band_in_plan_need_no_lift():
    """ボルト座 12: 頭の内縁 = 76 + 12 − 5 = 83 = バンド外面。位相 30° では頭（30°, 90°, …）が耳（0°, 180°）にも
    腕（45°, 135°, …）にも平面視で重ならない（腕の中心線から 88 sin 15° ≈ 22.8 > 腕の半幅 12.5 + 頭の半径 5）。
    頭がどこの下に入るかは方位で決まるので、位相を明示する。"""
    at = {"flange.bolt_phase": 30, "band.above_flange": 1}
    assert not any("抜けない" in w for w in _fatal(cradle_fits(override(SPEC, flange__bolt_seat=12, **at))))
    assert any("抜けない" in w for w in _fatal(cradle_fits(override(SPEC, flange__bolt_seat=11.9, **at))))


def test_a_bolt_head_under_a_band_tab_needs_the_lift_too():
    """位相 5° の頭（r 88）は +X 側の耳（x 77〜103、y −6.75〜12.75。+Y 側にはボルトの頭も出る）の下に入る。"""
    found = _fatal(cradle_fits(override(SPEC, flange__bolt_seat=12, flange__bolt_phase=5, band__above_flange=1)))
    assert any("耳" in w and "抜けない" in w for w in found), found


def test_the_band_bolt_head_on_the_plus_y_side_counts_as_part_of_the_tab():
    """+Y 側の耳の外面は y 6.75（締め代の半分 0.75 + 板厚 6）、ボルトの頭はその外へ 6 出て y 12.75 まで。
    位相 11° の頭（r 88、中心 y 16.79、下縁 11.79）は頭の範囲にだけかかる。12° では下縁 13.30 で外れる
    （12° では 132° の頭が 135° の腕にかかるので、耳だけを見る）。"""
    low = {"flange.bolt_seat": 12, "band.above_flange": 1}
    assert any("耳" in w and "抜けない" in w for w in _fatal(cradle_fits(override(SPEC, flange__bolt_phase=11, **low))))
    assert not any("耳" in w for w in _fatal(cradle_fits(override(SPEC, flange__bolt_phase=12, **low))))


def test_a_bolt_head_under_a_cradle_leg_needs_the_lift_too():
    """脚は 4 隅（中心 (±110.5, ±110.5)）の平角材の断面で、下端はバンドの中心。ボルト座 80（r 156）、位相 45° の頭は
    45° の脚の下に入る。バンドを細く（10）、低く（1）すると脚の下端は 7 + 1 + 5 = 13 で、頭 6 + ねじ込み 5 に 5 足りない。"""
    found = _fatal(cradle_fits(override(SPEC, flange__bolt_seat=80, flange__bolt_phase=45, band__bar__width=10, band__above_flange=1)))
    assert any("脚" in w and "抜けない" in w for w in found), found


def test_a_bolt_head_outside_the_frame_needs_the_lift_under_the_frame():
    """胴を 26 に低くするとフレームの下面は 7 + 13 − 3 = 17 で、フランジ上面から 10（< 11）。ボルト座 20（r 96）、
    位相 0° の頭は x 101 まで出て、フレームの内面 98 の外にかかる。"""
    low = {"shell.plenum_height": 26, "band.bar.width": 6, "band.above_flange": 1, "flange.bolt_phase": 0}
    assert any("フレーム" in w and "抜けない" in w for w in _fatal(cradle_fits(override(SPEC, flange__bolt_seat=20, **low))))
    assert not any("フレーム" in w for w in _fatal(cradle_fits(override(SPEC, flange__bolt_seat=16.9, **low))))   # 頭の外縁 97.9


def test_a_bolt_head_under_the_rubber_sheet_needs_the_lift_too():
    """ゴムシートは胴の外面からバンドの内面までを埋める。ゴム 20 でバンドの内面 r 96 の内側に頭（r 81〜91）が入っても、
    頭はゴムの下にあるので、バンドの下と同じく持ち上げる空きが要る。"""
    assert any("胴バンド" in w and "抜けない" in w
               for w in _fatal(cradle_fits(override(SPEC, band__rubber=20, band__above_flange=10.9))))


def test_a_bolt_head_under_a_cradle_arm_needs_the_lift_too():
    """位相 45° の頭（r 88）は 45° の腕の下に入る。バンドを細く（10）、低く（1）すると腕の下端は 7 + 1 + 5 − 3 = 10。"""
    low = {"flange.bolt_seat": 12, "band.bar.width": 10, "band.above_flange": 1}
    assert any("腕" in w and "抜けない" in w for w in _fatal(cradle_fits(override(SPEC, flange__bolt_phase=45, **low))))
    assert any("腕" in w for w in _fatal(cradle_fits(override(SPEC, flange__bolt_phase=34, **low))))     # 腕の中心線から 11°
    assert not any("抜けない" in w for w in _fatal(cradle_fits(override(SPEC, flange__bolt_phase=33, **low))))   # 12°: 88 sin 12° > 17.5


def test_the_holder_body_must_leave_a_wall_around_the_l_rod_bore_and_sit_on_the_pad():
    assert any("L ロッド" in w for w in _fatal(holder_fits(override(SPEC, mount__body_dia=12))))
    assert any("L ロッド" in w for w in _fatal(holder_fits(override(SPEC, mount__body_dia=12.7))))       # 穴と同じ径は肉が無い
    assert any("当て板" in w for w in _fatal(holder_fits(override(SPEC, mount__body_dia=70))))
    assert not any("L ロッド" in w for w in _fatal(holder_fits(override(SPEC, mount__body_dia=28.7))))     # 12.7 + 縁 8 × 2


def test_a_flange_bolt_that_pokes_through_the_header_or_stops_short_is_fatal():
    assert any("突き抜け" in w for w in _fatal(bolt_lengths(override(SPEC, flange__bolt_length=14))))     # 7 + 6 = 13 まで
    assert any("届かない" in w for w in _fatal(bolt_lengths(override(SPEC, flange__bolt_length=6))))


def test_a_shallow_thread_engagement_is_a_warning():
    found = bolt_lengths(override(SPEC, flange__bolt_length=10))          # ねじ込み 3 < 0.75 × 6
    assert _fatal(found) == [] and any("ねじ込み" in w for w in _warn(found))
    assert bolt_lengths(override(SPEC, flange__bolt_length=12)) == []      # ねじ込み 5 ≥ 4.5


def test_the_tip_and_band_bolts_must_not_poke_through():
    assert any("先端クランプ" in w and "突き抜け" in w for w in _fatal(bolt_lengths(override(SPEC, clamp__bolt_length=7))))
    assert any("胴バンド" in w and "突き抜け" in w for w in _fatal(bolt_lengths(override(SPEC, band__bolt_length=14))))   # 耳 6 + 締め代 1.5 + 耳 6 = 13.5 まで


@pytest.mark.parametrize("values", [{"band.gap": 200}, {"band.gap": 7}, {"band.bolt_length": 5}])
def test_a_band_bolt_that_does_not_reach_the_far_tab_is_fatal(values):
    """+Y 側の耳 6 と締め代を渡りきらないと、−Y 側の耳のタップに入らない（フランジのボルトと同じ扱い）。"""
    assert any("胴バンド" in w and "届かない" in w for w in _fatal(bolt_lengths(override(SPEC, **values)))), values


def test_a_band_bolt_that_just_reaches_the_far_tab_is_only_a_warning():
    found = bolt_lengths(override(SPEC, band__gap=6))                     # 12 = 耳 6 + 締め代 6: 届くがねじ込み 0
    assert _fatal(found) == [] and any("胴バンド" in w and "ねじ込み" in w for w in _warn(found))


def test_a_band_gap_so_wide_that_the_tabs_leave_the_half_rings_is_fatal():
    """耳（x ≥ バンド内面）が半環の肉に重なるのは、分割面からの距離 gap/2 が √(外半径² − 内半径²) 未満のとき（√(83² − 77²) ≈ 31.0）。"""
    assert any("耳" in w and "離れる" in w for w in _fatal(bolt_lengths(override(SPEC, band__gap=62.5, band__bolt_length=70))))
    assert not any("離れる" in w for w in _fatal(bolt_lengths(override(SPEC, band__gap=61, band__bolt_length=70))))


def test_the_band_bolt_engagement_counts_the_gap_between_the_tabs():
    found = bolt_lengths(override(SPEC, band__gap=3))                     # ねじ込み 12 − 6 − 3 = 3 < 4.5
    assert _fatal(found) == [] and any("胴バンド" in w and "ねじ込み" in w for w in _warn(found))


def test_a_hoop_pipe_off_the_standard_sizes_is_only_a_warning():
    found = stock_warning(override(SPEC, hoop__outer__od=29))
    assert len(found) == 1 and not found[0].fatal and "外リング" in found[0].what and "規格径" in found[0].what
    assert stock_warning(override(SPEC, hoop__outer__od=31.8)) == []                  # 規格にある


def test_a_tube_off_the_standard_sizes_is_only_a_warning():
    found = stock_warning(override(SPEC, tube__od=40.0))
    assert len(found) == 1 and not found[0].fatal and "規格径" in found[0].what
    assert stock_warning(override(SPEC, tube__thickness=3.0)) and "肉厚" in stock_warning(override(SPEC, tube__thickness=3.0))[0].what
