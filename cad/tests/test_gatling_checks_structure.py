"""検査（構造）: 個数が整数、規格表にある呼び、正の寸法。ここで落ちたら後の計算に進まない。"""

from __future__ import annotations

import pytest
from drumcad.dims import Dim, walk
from gatling.checks import _COUNTS, _NON_NEGATIVE, _POSITIVE, structure
from gatling.params import SPEC, override


def _fatal(spec):
    return [i.what for i in structure(spec) if i.fatal]


def test_the_default_spec_has_a_sound_structure():
    assert structure(SPEC) == []


@pytest.mark.parametrize("path, value, fragment", [
    ("tube.count", 6.5, "整数"),
    ("lug.count", 2.5, "整数"),
    ("tube.count", 2, "3 以上"),
    ("lug.count", 0, "1 以上"),
    ("flange.bolt_count", 0, "1 以上"),
    ("hoop.ear.count", 0.5, "整数"),
])
def test_a_count_must_be_an_integer_and_large_enough(path, value, fragment):
    found = _fatal(override(SPEC, **{path: value}))
    assert any(path in w and fragment in w for w in found), found


@pytest.mark.parametrize("path, value", [
    ("flange.bolt", "M99"), ("clamp.bolt", "M3"), ("band.bolt", "M8"), ("lug.thread", "1/4-20"), ("mount.type", "L ロッド 9"),
])
def test_a_choice_that_is_not_in_the_standard_table_is_fatal(path, value):
    found = _fatal(override(SPEC, **{path: value}))
    assert any(path in w and "規格表" in w for w in found), found


@pytest.mark.parametrize("path", ["tube.od", "tube.length", "shell.plenum_height", "header.thickness", "cradle.bar.width", "head.fit_id"])
def test_a_dimension_that_is_zero_or_negative_is_fatal(path):
    for bad in (0, -1):
        assert any(path in w and "正" in w for w in _fatal(override(SPEC, **{path: bad}))), (path, bad)


def test_a_clearance_may_be_zero_but_not_negative():
    assert _fatal(override(SPEC, header__hole_clearance=0, band__rubber=0, band__above_flange=0)) == []
    assert any("header.hole_clearance" in w for w in _fatal(override(SPEC, header__hole_clearance=-0.1)))


def test_a_tube_wall_that_leaves_no_bore_is_fatal():
    assert any("肉厚" in w for w in _fatal(override(SPEC, tube__thickness=19.05)))


@pytest.mark.parametrize("changes", [
    {"edge.angle": 90}, {"edge.angle": 0}, {"edge.radius": 4}, {"edge.height": 2},
    {"edge.radius": 10, "edge.width": 12},   # 面の幅は残るが、R が高さ以上で面取りが収まらない
])
def test_a_bearing_edge_that_cannot_be_cut_is_fatal(changes):
    assert any("ベアリングエッジ" in w for w in _fatal(override(SPEC, **changes))), changes


def test_a_shell_wall_that_leaves_no_bore_is_fatal():
    assert any("胴" in w and "穴" in w for w in _fatal(override(SPEC, shell__thickness=80)))


def test_a_bearing_edge_wider_than_the_shell_radius_is_fatal():
    assert any("エッジ環" in w for w in _fatal(override(SPEC, edge__width=80, edge__angle=5)))


def test_a_nan_dimension_is_fatal():
    nan = float("nan")
    found = _fatal(override(SPEC, tube__length=nan, header__hole_clearance=nan))
    assert any("tube.length" in w for w in found), found
    assert any("header.hole_clearance" in w for w in found), found


# 正・0 以上・個数のどれでもない数値の葉。新しい葉が分類されずに入るのを防ぐため、ここに理由つきで列挙する。
_UNCHECKED = {
    "head.f01_range[0]", "head.f01_range[1]",   # 周波数の目標範囲。形状に入らず、音の検査（PR 4）が見る
    "head.loss_factor",                         # 膜の損失係数。形状に入らない
    "tube.gap_ratio", "tube.protrusion_ratio",  # od に掛ける比。寸法ではなく、符号の決まりは配置の側にある
    "clamp.mid_position",                       # 管長に対する比（0〜1）。寸法ではない
    "flange.bolt_phase",                        # 位相（度）。負でも 360 超でも形は作れる
}


def test_every_numeric_leaf_is_classified():
    numeric = {path for path, leaf in walk(SPEC) if isinstance(leaf, Dim)}
    classified = set(_COUNTS) | set(_POSITIVE) | set(_NON_NEGATIVE) | _UNCHECKED
    assert numeric - classified == set()
    assert classified - numeric == set()   # 一覧に古い名前が残っていない


def test_every_problem_is_reported_not_just_the_first():
    found = _fatal(override(SPEC, tube__count=2, tube__od=-1, flange__bolt="M99"))
    assert len(found) >= 3
