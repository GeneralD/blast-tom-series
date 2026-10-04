"""検査（ボルトの長さ・規格径・当て板と腕とブロックとグリップとホルダー受けの寸法の噛み合わせ）。

境界の値は、検査と別の式（`arm_bends` の直線部が線形に動くことなど）から出す。縁ちょうどは通り、少し越えると fatal になる。
"""

from __future__ import annotations

import pytest
from gatling.checks import bolt_lengths, mount_fits, stock_warning
from gatling.params import SPEC, override
from gatling.placement import arm_bends, grip_z, levels


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


def _hits(found, fragment):
    return [i for i in found if fragment in i.what]


def _root(f, x0, x1):
    """線形な f(x) = 0 の x。2 点の値から出す（直線部の長さは曲げ半径・rear・stub・床の高さに線形）。"""
    y0, y1 = f(x0), f(x1)
    return x0 - y0 * (x1 - x0) / (y1 - y0)


def test_the_default_mount_fits_without_any_warning():
    assert mount_fits(SPEC) == []


@pytest.mark.parametrize("key, inside, outside, fragment", [
    ("pad__angle", 0, -0.1, "当て板の方位"), ("pad__angle", 89.9, 90, "当て板の方位"),
    ("grip__drop", 0, -0.1, "落ち角"), ("grip__drop", 89.9, 90, "落ち角"),
    ("grip__out", 0, -0.1, "開き角"), ("grip__out", 89.9, 90, "開き角"),
])
def test_the_angles_stay_in_zero_to_ninety_degrees(key, inside, outside, fragment):
    assert _hits(mount_fits(override(SPEC, **{key: inside})), fragment) == []
    found = _hits(mount_fits(override(SPEC, **{key: outside})), fragment)
    assert len(found) == 1 and found[0].fatal


@pytest.mark.parametrize("key, inside, outside, fragment", [
    ("pad__height", 100.0, 100.01, "プレナムの高さ"),      # 胴（プレナム）の高さ 100
    ("pad__width", 25.4, 25.39, "板幅"),                   # 管の外径 25.4
    ("pad__height", 25.4, 25.39, "板の高さ < 管の外径"),
    ("pad__corner", 12.7, 12.71, "角の R"),                # 板幅 25.4 の半分
])
def test_a_pad_holds_the_pipe_and_fits_the_plenum(key, inside, outside, fragment):
    base = {"pad__width": 25.4} if key == "pad__corner" else {}
    assert _hits(mount_fits(override(SPEC, **{**base, key: inside})), fragment) == []
    found = _hits(mount_fits(override(SPEC, **{**base, key: outside})), fragment)
    assert len(found) == 1 and found[0].fatal


def test_a_bend_radius_at_the_pipe_radius_folds_the_sweep_and_one_just_above_does_not():
    fold = _hits(mount_fits(override(SPEC, arm__bend_radius=12.7)), "掃引が折れる")
    assert len(fold) == 1 and fold[0].fatal
    assert _hits(mount_fits(override(SPEC, arm__bend_radius=12.71)), "掃引が折れる") == []
    assert _hits(mount_fits(override(SPEC, arm__bend_radius=0)), "掃引が折れる") != []     # 0 でも例外を投げない


def test_a_bend_radius_under_one_and_a_half_diameters_is_only_a_warning():
    """管の外径 25.4 の 1.5 倍 = 38.1。ちょうどは警告なし、少し下で警告（fatal ではない）。"""
    assert _hits(mount_fits(override(SPEC, arm__bend_radius=38.1)), "潰れやすい") == []
    found = _hits(mount_fits(override(SPEC, arm__bend_radius=38.09)), "潰れやすい")
    assert len(found) == 1 and not found[0].fatal


@pytest.mark.parametrize("key, fragment, free", [
    ("arm__stub", "最初の曲げまで", lambda s: arm_bends(s).stub_free),
    ("arm__rear", "後ろへの脚", lambda s: arm_bends(s).leg_free),
])
def test_the_bends_must_fit_in_the_stub_and_the_leg(key, fragment, free):
    """直線部の長さが 0 になる値（stub・rear に線形）で縁ちょうど。少し短いと曲げの接点が隣の曲げや当て板の内側に入って fatal。"""
    edge = _root(lambda x: free(override(SPEC, **{key: x})), 100.0, 160.0)     # 腕の向きが変わらない範囲の 2 点（stub = 100 でも線形）
    assert _hits(mount_fits(override(SPEC, **{key: edge})), fragment) == []
    found = _hits(mount_fits(override(SPEC, **{key: edge - 0.01})), fragment)
    assert len(found) == 1 and found[0].fatal


def test_the_crossing_must_keep_a_straight_run_between_the_two_rear_bends():
    """横渡しの直線部は曲げ半径に線形（接線の長さが半径に比例）。0 になる半径がちょうど、少し大きいと左右の曲げが中央で重なる。"""
    edge = _root(lambda r: arm_bends(override(SPEC, arm__bend_radius=r)).cross_half, 10.0, 40.0)
    assert edge > 38.1                                      # 警告の線より外（この値の周りは警告も出る）
    assert _hits(mount_fits(override(SPEC, arm__bend_radius=edge, block__width=1e-6)), "横渡しの直線が負") == []
    found = _hits(mount_fits(override(SPEC, arm__bend_radius=edge + 0.01)), "横渡しの直線が負")
    assert len(found) == 1 and found[0].fatal


def test_the_block_must_sit_on_the_straight_crossing():
    full = 2 * arm_bends(SPEC).cross_half
    assert _hits(mount_fits(override(SPEC, block__width=full)), "ブロックが後ろの横渡し") == []
    found = _hits(mount_fits(override(SPEC, block__width=full + 0.01)), "ブロックが後ろの横渡し")
    assert len(found) == 1 and found[0].fatal


def test_the_block_top_must_clear_the_pipe_centreline():
    assert _hits(mount_fits(override(SPEC, block__height=12.7)), "ブロックの上面") == []
    found = _hits(mount_fits(override(SPEC, block__height=12.69)), "ブロックの上面")
    assert len(found) == 1 and found[0].fatal


def test_the_holder_body_sits_on_the_block_and_is_thicker_than_its_rod():
    """既定のホルダーの型は L ロッド 12.7。ブロックの幅 60・奥行き 50 の小さいほう（50）に収まり、ロッド径より太い。"""
    assert _hits(mount_fits(override(SPEC, mount__body_dia=50.0)), "ブロックからはみ出す") == []
    found = _hits(mount_fits(override(SPEC, mount__body_dia=50.01)), "ブロックからはみ出す")
    assert len(found) == 1 and found[0].fatal
    assert _hits(mount_fits(override(SPEC, mount__body_dia=12.7)), "ロッド径") == []
    found = _hits(mount_fits(override(SPEC, mount__body_dia=12.69)), "ロッド径")
    assert len(found) == 1 and found[0].fatal


def test_a_grip_must_not_stand_above_the_rim():
    """グリップの上端（付け根の管の上端 = 腕の中心 + 管の半径）がフープの上端以下。腕の中心はプレナムの中ほどなので、
    プレナムの高さに線形に動く。"""
    def margin(plenum):
        s = override(SPEC, shell__plenum_height=plenum)
        return levels(s).hoop_top - grip_z(s)[1]
    edge = _root(margin, 20.0, 60.0)
    assert _hits(mount_fits(override(SPEC, shell__plenum_height=edge)), "グリップの上端") == []
    found = _hits(mount_fits(override(SPEC, shell__plenum_height=edge - 0.01)), "グリップの上端")
    assert len(found) == 1 and found[0].fatal


def test_an_arm_pipe_off_the_standard_sizes_is_only_a_warning():
    found = stock_warning(override(SPEC, arm__pipe__od=30.0))
    assert len(found) == 1 and not found[0].fatal and "腕の管" in found[0].what and "規格径" in found[0].what
    assert stock_warning(override(SPEC, arm__pipe__od=31.8)) == []                  # 規格にある


def test_a_pipe_with_no_bore_is_fatal_not_a_crash():
    found = _hits(mount_fits(override(SPEC, arm__pipe__thickness=12.7)), "穴が無い")
    assert len(found) == 1 and found[0].fatal
