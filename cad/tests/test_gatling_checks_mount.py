"""検査（クレードル・ホルダー・ボルトの長さ・規格径）。"""

from __future__ import annotations

from gatling.checks import MIN_CRADLE_CLEARANCE, bolt_lengths, cradle_fits, holder_fits, stock_warning
from gatling.params import SPEC, override


def _fatal(issues):
    return [i.what for i in issues if i.fatal]


def _warn(issues):
    return [i.what for i in issues if not i.fatal]


def test_the_default_mount_passes_with_no_warning():
    assert cradle_fits(SPEC) == [] and holder_fits(SPEC) == [] and bolt_lengths(SPEC) == [] and stock_warning(SPEC) == []


def test_a_frame_that_cuts_into_the_outer_ring_is_fatal():
    # フレーム内面 = 83 + 逃げ、外リング外面 = 90.7。逃げ 7.7 未満は負
    assert any("干渉" in w for w in _fatal(cradle_fits(override(SPEC, cradle__clearance=7.5))))
    assert not any("干渉" in w for w in _fatal(cradle_fits(override(SPEC, cradle__clearance=7.7))))


def test_a_frame_that_only_just_clears_the_ring_is_a_warning():
    assert MIN_CRADLE_CLEARANCE == 5.0
    found = cradle_fits(override(SPEC, cradle__clearance=12.5))          # 逃げ 4.8
    assert _fatal(found) == [] and "逃げが小さい" in _warn(found)[0]
    assert cradle_fits(override(SPEC, cradle__clearance=12.7)) == []      # 5.0 ちょうどは通す


def test_the_frame_must_be_above_the_band_so_the_legs_have_a_height():
    assert any("脚" in w for w in _fatal(cradle_fits(override(SPEC, shell__plenum_height=40))))


def test_the_flange_bolts_can_be_pulled_out_under_the_band():
    """頭（r 81〜91）は平面視でバンド（外面 r 83）の下に入るので、頭 6 + ねじ込み 5 = 11 の空きが要る。"""
    assert any("抜けない" in w for w in _fatal(cradle_fits(override(SPEC, band__above_flange=10.9))))
    assert not any("抜けない" in w for w in _fatal(cradle_fits(override(SPEC, band__above_flange=11))))
    assert any("抜けない" in w for w in _fatal(cradle_fits(override(SPEC, flange__bolt_length=14))))      # ねじ込み 7 → 13 要る


def test_bolt_heads_outside_the_band_in_plan_need_no_lift():
    # ボルト座 12: 頭の内縁 = 76 + 12 − 5 = 83 = バンド外面
    assert not any("抜けない" in w for w in _fatal(cradle_fits(override(SPEC, flange__bolt_seat=12, band__above_flange=1))))
    assert any("抜けない" in w for w in _fatal(cradle_fits(override(SPEC, flange__bolt_seat=11.9, band__above_flange=1))))


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


def test_the_band_bolt_engagement_counts_the_gap_between_the_tabs():
    found = bolt_lengths(override(SPEC, band__gap=3))                     # ねじ込み 12 − 6 − 3 = 3 < 4.5
    assert _fatal(found) == [] and any("胴バンド" in w and "ねじ込み" in w for w in _warn(found))


def test_a_tube_off_the_standard_sizes_is_only_a_warning():
    found = stock_warning(override(SPEC, tube__od=40.0))
    assert len(found) == 1 and not found[0].fatal and "規格径" in found[0].what
    assert stock_warning(override(SPEC, tube__thickness=3.0)) and "肉厚" in stock_warning(override(SPEC, tube__thickness=3.0))[0].what
