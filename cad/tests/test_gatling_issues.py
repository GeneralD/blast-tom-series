"""`issues(spec)`: 仕様 §5.6 の Gatling のテスト（干渉・板径不足・ボルト穴の肉不足・方位不一致・突き出し負）。"""

from __future__ import annotations

import pytest
from drumcad.checks import fatal_count
from gatling.checks import issues
from gatling.params import SPEC, override


def _fatal(spec):
    return [i.what for i in issues(spec) if i.fatal]


def test_the_default_spec_has_no_fatal_issue_and_no_warning():
    assert issues(SPEC) == []


@pytest.mark.parametrize("label, values, fragment", [
    ("管同士の干渉", {"tube.gap_ratio": 0}, "干渉"),
    ("板径が大きすぎる", {"tube.od": 50.8, "tube.gap_ratio": 1.0}, "大きすぎる"),
    ("ボルト穴の肉不足（管外面）", {"flange.bolt_phase": 0, "flange.bolt_seat": 3}, "管外面"),
    ("ボルトが管と同じ方位", {"flange.bolt_phase": 0}, "同じ方位"),
    ("方位不一致", {"lug.count": 4}, "方位が揃わない"),
    ("突き出しが負", {"tube.protrusion_ratio": -0.5}, "突き出し"),
    ("中間クランプの比が範囲外", {"clamp.mid_position": 1.2}, "1 を超える"),
    ("ロッドがリングの間に入らない", {"hoop.gap": 4}, "外リング"),
    ("ロッドが短い", {"lug.rod_length": 20}, "ロッドが短い"),
    ("クレードルがフープに干渉", {"shell.plenum_height": 10}, "クレードルがフープ"),
    ("受金がフープから突き出る", {"hoop.ear.thickness": 13}, "突き出"),
    ("個数が整数でない", {"tube.count": 6.5}, "整数"),
])
def test_each_failure_the_spec_names_is_caught(label, values, fragment):
    found = _fatal(override(SPEC, **values))
    assert any(fragment in w for w in found), (label, found)


def test_a_plate_smaller_than_the_bore_is_caught_through_the_composed_check():
    from gatling import checks
    found = [i.what for i in checks.plate_size(140, 149.6, 152, 60) if i.fatal]       # 板径は導出値なので override では下げられない
    assert found and "蓋にならない" in found[0]


def test_the_sweep_value_that_pushes_the_tubes_out_of_the_bore_warns_but_does_not_block():
    found = issues(override(SPEC, tube__gap_ratio=0.5))
    assert fatal_count(found) == 0 and len(found) == 1 and "はみ出" in found[0].what


def test_a_nonstandard_tube_warns_but_does_not_block():
    found = issues(override(SPEC, tube__od=42.7))
    assert fatal_count(found) == 0 and not any("規格径" in i.what for i in found)       # 42.7 は規格にある
    off = issues(override(SPEC, tube__od=40.0))
    assert fatal_count(off) == 0 and any("規格径" in i.what for i in off)


def test_a_broken_count_stops_at_the_structure_check_before_any_division():
    for bad in (0, 1, 2, -3, 6.5):
        found = issues(override(SPEC, tube__count=bad))
        assert fatal_count(found) >= 1, bad


def test_issues_never_raises_on_a_spec_that_cannot_be_built():
    ugly = override(SPEC, tube__od=-5, tube__gap_ratio=-3, flange__bolt="M99", lug__count=0, hoop__gap=0, head__fit_id=0)
    assert fatal_count(issues(ugly)) >= 4


def test_issues_reports_several_physical_problems_at_once():
    found = _fatal(override(SPEC, tube__gap_ratio=0, lug__count=4, clamp__mid_position=1.2))
    assert len(found) >= 4
