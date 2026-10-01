"""検査（部品どうしの平面視の重なり）: ラグ・ロッドとホルダー受け・当て板、ホルダー受け・当て板と胴まわりの回転体、
グリップと当て板・ホルダー受け。z が重なり、平面視（グリップは YZ 面）でも重なれば干渉（fatal）。"""

from __future__ import annotations

import pytest
from gatling.interference import mount_clear
from gatling.params import SPEC, override


def _fatal(spec):
    return [i.what for i in mount_clear(spec) if i.fatal]


def test_the_default_spec_has_nothing_in_the_way():
    assert mount_clear(SPEC) == []


@pytest.mark.parametrize("count", [4, 8, 12])
def test_a_lug_under_the_holder_is_fatal(count):
    """ラグ数 4・8・12 では −Y（270°）にラグが来て、ホルダー受け（中心 y −110.5、半径 20）にラグの箱（u 76〜92）が 1.5 食い込む。"""
    found = _fatal(override(SPEC, lug__count=count, hoop__ear__count=count))
    assert any("ラグ" in w and "ホルダー受け" in w for w in found), found


def test_a_lug_that_just_clears_the_holder_passes():
    # 逃げ 17: ホルダー中心 y −112.5、内縁 −92.5 > ラグの外端 −92
    assert not any("ホルダー受け" in w for w in _fatal(override(SPEC, lug__count=12, hoop__ear__count=12, cradle__clearance=17)))


def test_a_lug_that_reaches_down_to_the_pad_is_fatal():
    # ラグ 12 個、高さ 60（下端 44.19）で当て板（z 60〜66）と z が重なる。ホルダーは逃げ 17 で避けておく
    found = _fatal(override(SPEC, lug__count=12, hoop__ear__count=12, lug__height=60, lug__rod_length=110, cradle__clearance=17))
    assert any("ラグ" in w and "当て板" in w for w in found), found


def test_a_holder_that_rises_into_the_outer_ring_is_fatal():
    """ホルダー受けの内縁 r 90.5 は外リングの外面 r 90.7 の内側。上端 66 + 高さが外リングの下端 117.19 を超えると当たる。"""
    assert any("ホルダー受け" in w and "外リング" in w for w in _fatal(override(SPEC, mount__body_height=60)))
    assert _fatal(override(SPEC, mount__body_height=51)) == []          # 上端 117 < 117.19


def test_a_pad_that_reaches_over_the_shell_is_fatal():
    """当て板の内縁 y = −(83 + 逃げ + 12.5) + 30。胴の外面 r 76 より内側に入ると胴に食い込む（逃げ 10.5 未満）。"""
    assert any("当て板" in w and "胴" in w for w in _fatal(override(SPEC, cradle__clearance=8)))
    assert not any("当て板" in w for w in _fatal(override(SPEC, cradle__clearance=10.5)))


def test_a_grip_too_close_to_the_frame_runs_into_the_pad_and_the_holder():
    """グリップ（φ28、中心 z 57）は当て板の下の角（y −140.5、z 60）から 14 離す。handle_length の下限は約 31.17。"""
    found = _fatal(override(SPEC, cradle__handle_length=5))
    assert any("グリップ" in w and "当て板" in w for w in found) and any("グリップ" in w and "ホルダー受け" in w for w in found), found
    assert any("グリップ" in w for w in _fatal(override(SPEC, cradle__handle_length=31.1)))
    assert _fatal(override(SPEC, cradle__handle_length=31.2)) == []


def test_a_lug_that_reaches_down_to_the_frame_and_sticks_out_of_it_is_fatal():
    """ラグ高さ 60（下端 44.19）でフレーム（z 54〜60）と z が重なる。0° のラグの外の隅 (92, ±8) がフレーム内面 83 + 逃げ の外に出ると当たる。"""
    tall = {"lug.height": 60, "lug.rod_length": 120}
    assert any("ラグ" in w and "フレーム" in w for w in _fatal(override(SPEC, cradle__clearance=8, **tall)))
    assert any("ラグ" in w and "フレーム" in w for w in _fatal(override(SPEC, cradle__clearance=8.9, **tall)))
    assert not any("フレーム" in w for w in _fatal(override(SPEC, cradle__clearance=9, **tall)))     # 隅がちょうど内面に接する


def test_a_lug_on_the_diagonal_that_reaches_down_to_an_arm_is_fatal():
    """腕はフレームの内側（対角線上、胴バンドの外面から隅まで）にある。フレームの平角材を厚くすると腕が胴バンドの上端より上に出て、
    45° のラグ（ラグ 8 個）の下端に届く。脚はフレームの内面より外にあるので、脚に届くラグはフレームの検査で先に止まる。"""
    values = {"lug.count": 8, "hoop.ear.count": 8, "cradle.bar.thickness": 40, "lug.height": 60, "lug.rod_length": 120}
    assert any("ラグ" in w and "腕" in w for w in _fatal(override(SPEC, **values)))
    assert not any("腕" in w for w in _fatal(override(SPEC, **{**values, "lug.height": 52})))     # 下端 52.19 > 腕の上端 51.5


@pytest.mark.parametrize("values", [{"band.bar.width": 36}, {"band.above_flange": 23}, {"shell.plenum_height": 76}])
def test_a_band_tab_that_rises_into_the_frame_is_fatal(values):
    """耳の外端（バンド外面 83 + 耳の長さ 20 = 103）はフレームの内面 98 より外にある。既定では z が離れている
    （バンド 19〜44、フレーム 54〜60）だけで、バンドを広げる・上げる、胴を低くしてフレームを下げると当たる。"""
    assert any("耳" in w and "フレーム" in w for w in _fatal(override(SPEC, **values))), values


def test_a_band_tab_inside_the_frame_passes():
    """逃げ 21 でフレームの内面 104 > 耳の外端 103。"""
    assert not any("耳" in w for w in _fatal(override(SPEC, cradle__clearance=21, band__bar__width=36)))
