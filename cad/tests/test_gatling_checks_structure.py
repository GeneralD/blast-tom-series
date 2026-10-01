"""検査（構造）: 個数が整数、規格表にある呼び、正の寸法。ここで落ちたら後の計算に進まない。"""

from __future__ import annotations

import pytest
from gatling.checks import structure
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


@pytest.mark.parametrize("path, value", [("edge.angle", 90), ("edge.angle", 0), ("edge.radius", 4), ("edge.height", 2)])
def test_a_bearing_edge_that_cannot_be_cut_is_fatal(path, value):
    assert any("ベアリングエッジ" in w for w in _fatal(override(SPEC, **{path: value}))), (path, value)


def test_every_problem_is_reported_not_just_the_first():
    found = _fatal(override(SPEC, tube__count=2, tube__od=-1, flange__bolt="M99"))
    assert len(found) >= 3
