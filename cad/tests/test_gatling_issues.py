"""`issues(spec)`: 仕様 §5.6 の Gatling のテスト（干渉・板径不足・ボルト穴の肉不足・方位不一致・突き出し負）。"""

from __future__ import annotations

import pytest
from drumcad.checks import fatal_count
from gatling.checks import issues
from gatling.params import SPEC, override


def _fatal(spec):
    return [i.what for i in issues(spec) if i.fatal]


def test_the_default_spec_has_no_fatal_issue_and_no_warning():
    """既定の受金のロッド通し穴は、径方向の肉が両側 3.8 で、目安（板厚の半分 = 3）を満たす（溝 14、仕様 §5.3）。警告は無い。"""
    found = issues(SPEC)
    assert fatal_count(found) == 0 and found == []


def test_the_key_socket_check_is_part_of_issues():
    """差し口の検査は issues() に合成されて build で効く。溝 10 の旧値と、差し口を大きくした例の両方で fatal になる（既定は空）。"""
    assert issues(SPEC) == []
    assert any("差し口" in w for w in _fatal(override(SPEC, hoop__gap=10, lug__standoff=10)))
    assert any("差し口" in w for w in _fatal(override(SPEC, lug__key_socket_dia=30)))


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
    ("受金が内リングに溶接できない", {"hoop.inner.height": 5}, "溶接できない"),
    ("個数が整数でない", {"tube.count": 6.5}, "整数"),
    ("当て板がラグに当たる", {"pad.angle": 20}, "当て板がラグ"),
    ("腕の曲げが折れる（脚が短い）", {"arm.rear": 130}, "後ろへの脚"),
    ("腕の曲げ半径が管の半径以下", {"arm.bend_radius": 5}, "掃引が折れる"),
    ("ホルダー受けが外リングに当たる", {"arm.rear": 120, "arm.bend_radius": 30}, "ホルダー受けが外リング"),
    ("ブロックが横渡しに収まらない", {"block.width": 120}, "横渡し"),
    ("グリップの角度が範囲外", {"grip.drop": 95}, "落ち角"),
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
    assert fatal_count(found) == 0 and sum("はみ出" in i.what for i in found) == 1 and len(found) == 1


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


def test_a_folded_arm_path_stops_before_any_plan_is_built():
    """曲げ半径が大きく経路が折れる値は、平面形の検査（例外を投げうる）に進まず、寸法の検査で止まる。"""
    found = issues(override(SPEC, arm__bend_radius=70, pad__angle=89))
    assert fatal_count(found) >= 1
