"""検査（ボルトの長さ・規格径）。"""

from __future__ import annotations

from gatling.checks import bolt_lengths, stock_warning
from gatling.params import SPEC, override


def _fatal(issues):
    return [i.what for i in issues if i.fatal]


def _warn(issues):
    return [i.what for i in issues if not i.fatal]


def test_the_default_bolts_and_stock_pass_with_no_warning():
    assert bolt_lengths(SPEC) == [] and stock_warning(SPEC) == []


def test_a_flange_bolt_that_pokes_through_the_header_or_stops_short_is_fatal():
    assert any("突き抜け" in w for w in _fatal(bolt_lengths(override(SPEC, flange__bolt_length=14))))     # 7 + 6 = 13 まで
    assert any("届かない" in w for w in _fatal(bolt_lengths(override(SPEC, flange__bolt_length=6))))


def test_a_shallow_thread_engagement_is_a_warning():
    found = bolt_lengths(override(SPEC, flange__bolt_length=10))          # ねじ込み 3 < 0.75 × 6
    assert _fatal(found) == [] and any("ねじ込み" in w for w in _warn(found))
    assert bolt_lengths(override(SPEC, flange__bolt_length=12)) == []      # ねじ込み 5 ≥ 4.5


def test_the_tip_bolts_must_not_poke_through():
    assert any("先端クランプ" in w and "突き抜け" in w for w in _fatal(bolt_lengths(override(SPEC, clamp__bolt_length=7))))


def test_a_hoop_pipe_off_the_standard_sizes_is_only_a_warning():
    found = stock_warning(override(SPEC, hoop__outer__od=29))
    assert len(found) == 1 and not found[0].fatal and "外リング" in found[0].what and "規格径" in found[0].what
    assert stock_warning(override(SPEC, hoop__outer__od=31.8)) == []                  # 規格にある


def test_a_tube_off_the_standard_sizes_is_only_a_warning():
    found = stock_warning(override(SPEC, tube__od=40.0))
    assert len(found) == 1 and not found[0].fatal and "規格径" in found[0].what
    assert stock_warning(override(SPEC, tube__thickness=3.0)) and "肉厚" in stock_warning(override(SPEC, tube__thickness=3.0))[0].what
