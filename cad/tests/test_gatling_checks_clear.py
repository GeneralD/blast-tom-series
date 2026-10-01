"""検査（部品どうしの平面視の重なり）: ラグ・ロッドとホルダー受け・当て板、ホルダー受け・当て板と胴まわりの回転体、
グリップと当て板・ホルダー受け。z が重なり、平面視（グリップは YZ 面）でも重なれば干渉（fatal）。"""

from __future__ import annotations

import pytest
from gatling.checks import mount_clear
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
