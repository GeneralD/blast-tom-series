"""検査（管束）: 干渉・板径・ボルト穴の肉・管クランプ。"""

from __future__ import annotations

import pytest
from gatling.checks import bolt_clearances, plate_size, tube_clamps, tubes_apart, tubes_inside_bore
from gatling.params import SPEC, override


def _fatal(issues):
    return [i.what for i in issues if i.fatal]


def _warn(issues):
    return [i.what for i in issues if not i.fatal]


def test_the_default_bundle_passes_every_check_with_no_warning():
    for found in (tubes_apart(SPEC), plate_size(188, 149.6, 152, 60), bolt_clearances(SPEC), tubes_inside_bore(SPEC), tube_clamps(SPEC)):
        assert found == []


@pytest.mark.parametrize("ratio", [0, -0.1])
def test_tubes_that_touch_or_overlap_are_fatal(ratio):
    assert "干渉" in _fatal(tubes_apart(override(SPEC, tube__gap_ratio=ratio)))[0]


def test_tubes_whose_holes_overlap_through_the_clearance_are_fatal():
    """隙間 0.003 × 38.1 ≈ 0.11 は穴の逃げ 0.2 より狭く、隣の管穴が重なって肉が無くなる。"""
    assert "干渉" in _fatal(tubes_apart(override(SPEC, tube__gap_ratio=0.003)))[0]
    assert _fatal(tubes_apart(override(SPEC, tube__gap_ratio=0.01))) == []


def test_a_plate_smaller_than_the_shell_bore_does_not_close_it():
    found = _fatal(plate_size(140, 149.6, 152, 60))
    assert len(found) == 1 and "蓋にならない" in found[0]
    assert _fatal(plate_size(149.6, 149.6, 152, 60)) == []             # ちょうど内径は通す


def test_a_plate_beyond_the_upper_limit_is_fatal():
    assert "大きすぎる" in _fatal(plate_size(213, 149.6, 152, 60))[0]
    assert _fatal(plate_size(212, 149.6, 152, 60)) == []               # 胴外径 + 60 ちょうど


def test_a_huge_bundle_overshoots_the_plate_limit_through_the_spec():
    from gatling.derived import derive
    spec = override(SPEC, tube__od=50.8, tube__gap_ratio=1.0)
    assert float(derive(spec).plate_od) > 152 + 60


def test_a_bolt_hole_too_close_to_a_tube_is_fatal():
    spec = override(SPEC, flange__bolt_phase=0, flange__bolt_seat=3)      # 管と同じ方位で、胴の近く
    found = _fatal(bolt_clearances(spec))
    assert any("管外面" in w for w in found)


def test_the_bolt_hole_to_plate_edge_distance_is_exactly_the_margin_by_construction_and_passes():
    """縁はボルトの中心から測る（仕様 §5.2 の式「ボルト円径 + 2 × margin」に合わせた読み。計画の「置いた仮定」）。

    板径がこの式の max で決まるので、この検査は恒真で、決して発火しない。浮動小数の誤差で fatal に
    ならないことだけを見る。穴の縁から測った実際の肉は 8 − 3.3 = 4.7（フランジの通し穴 φ6.6）。
    """
    assert not any("板縁" in w for w in _fatal(bolt_clearances(SPEC)))     # 浮動小数の誤差で fatal にならない
    for seat in (10, 12.5, 17.3):
        assert not any("板縁" in w for w in _fatal(bolt_clearances(override(SPEC, flange__bolt_seat=seat))))


def test_a_bolt_whose_head_overlaps_the_shell_wall_is_fatal():
    assert any("胴の外面" in w for w in _fatal(bolt_clearances(override(SPEC, flange__bolt_seat=2))))


@pytest.mark.parametrize("phase", [0, 60, 120, -60])
def test_a_bolt_on_a_tube_bearing_is_fatal(phase):
    assert any("同じ方位" in w for w in _fatal(bolt_clearances(override(SPEC, flange__bolt_phase=phase))))


@pytest.mark.parametrize("change", [dict(flange__bolt_count=4), dict(flange__bolt_count=12), dict(tube__count=8)])
def test_a_bolt_on_a_tube_bearing_is_fatal_when_the_counts_differ(change):
    """ボルト 0 番だけでなく全組を比べる（4 本なら 120°、12 本なら 0°、管 8 本なら 90° で一致する）。"""
    assert any("同じ方位" in w for w in _fatal(bolt_clearances(override(SPEC, **change))))


def test_eight_tubes_put_a_flange_bolt_into_a_tube():
    """管 8 本・ボルト 6 本・位相 30° では、90° のボルトが管に重なる。"""
    assert any("管外面" in w for w in _fatal(bolt_clearances(override(SPEC, tube__count=8))))


@pytest.mark.parametrize("phase", [30, 90, 30.0 + 360])
def test_a_bolt_between_the_tubes_is_fine(phase):
    assert not any("同じ方位" in w for w in _fatal(bolt_clearances(override(SPEC, flange__bolt_phase=phase))))


def test_tubes_poking_out_of_the_shell_bore_are_a_warning_not_fatal():
    spec = override(SPEC, tube__gap_ratio=0.5)                            # 仕様の sweep 値。管の外面が 76.2 > 胴の内半径 74.8
    found = tubes_inside_bore(spec)
    assert found and not any(i.fatal for i in found) and "はみ出" in _warn(found)[0]
    assert tubes_inside_bore(override(SPEC, tube__gap_ratio=0.45)) == []


def test_a_negative_protrusion_is_fatal():
    assert any("突き出し" in w for w in _fatal(tube_clamps(override(SPEC, tube__protrusion_ratio=-0.5))))
    assert _fatal(tube_clamps(override(SPEC, tube__protrusion_ratio=0))) == []


@pytest.mark.parametrize("ratio, fragment", [(-0.1, "0 未満"), (1.2, "1 を超える")])
def test_the_mid_clamp_ratio_must_be_between_0_and_1(ratio, fragment):
    assert any(fragment in w for w in _fatal(tube_clamps(override(SPEC, clamp__mid_position=ratio))))
    for edge in (0, 1):                                                   # 範囲の端は範囲の文言を出さない（重なりは別の検査）
        assert not any("0 未満" in w or "1 を超える" in w for w in _fatal(tube_clamps(override(SPEC, clamp__mid_position=edge))))


def test_a_mid_clamp_that_cuts_into_the_header_plate_is_fatal():
    # 中間クランプの上面 = −比 × 450。ヘッダー下面 −6 より上なら食い込む（比 6 / 450 ≈ 0.0133 まで）
    for ratio in (0, 0.01, 0.013):
        assert any("ヘッダープレート" in w for w in _fatal(tube_clamps(override(SPEC, clamp__mid_position=ratio)))), ratio
    assert not any("ヘッダープレート" in w for w in _fatal(tube_clamps(override(SPEC, clamp__mid_position=0.0134))))


def test_clamps_that_overlap_each_other_are_fatal():
    assert any("重なる" in w for w in _fatal(tube_clamps(override(SPEC, clamp__mid_position=0.99))))


def test_a_centre_hole_that_would_be_zero_or_negative_is_fatal():
    assert any("中央の穴" in w for w in _fatal(tube_clamps(override(SPEC, plate__margin=40))))
