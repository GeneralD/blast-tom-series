import math
import re
from pathlib import Path

import pytest
from drumcad.bom import bom_markdown, full_bom
from drumcad.registry import discover

TESTS = Path(__file__).parent


def test_full_bom_adds_a_row_per_fabricated_part_with_its_mass():
    m = discover(TESTS)["demo"]
    rows = full_bom(m)
    names = [r.name for r in rows]
    assert names == ["胴", "底板", "スタッド", "ラグ"]
    shell = rows[0]
    assert shell.made == "fabricated" and shell.material.name.startswith("ステンレス")
    assert shell.mass_g == pytest.approx(3.14159 * (76.2**2 - 75.0**2) * 100 * 7.93e-3, rel=1e-3)
    assert rows[3].part_number == "DWSM2200"


def test_a_fabricated_row_carries_the_standard_and_dimensions_the_model_wrote():
    rows = {r.name: r for r in full_bom(discover(TESTS)["demo"])}
    assert rows["胴"].standard == "手すり用 #400 研磨管"
    assert rows["胴"].dimensions == "φ152.4 × t1.2 × L100"
    assert rows["底板"].standard == "" and rows["底板"].dimensions == ""   # 書かなければ空


def test_a_fabricated_row_is_the_mass_of_one_solid_and_the_total_multiplies_by_count():
    m = discover(TESTS)["demo"]
    stud = next(r for r in full_bom(m) if r.name == "スタッド")
    one = math.pi * 4**2 * 100 * 7.93e-3          # φ8 × 100 を 1 個分（3 個全部ではない）
    assert stud.count == 3 and stud.mass_g == pytest.approx(one, rel=1e-3)
    total = float(re.search(r"\*\*([\d.]+) kg\*\*", bom_markdown(m.name(), full_bom(m))).group(1))
    expected = sum(r.mass_g * r.count for r in full_bom(m) if r.mass_g is not None) / 1000
    assert total == pytest.approx(expected, abs=0.01)


def test_bom_markdown_is_a_table_with_a_total_mass():
    m = discover(TESTS)["demo"]
    md = bom_markdown(m.name(), full_bom(m))
    assert md.startswith("# 部品表 — demo-6-6")
    assert "| 胴 | 製作品 | ステンレス SUS304 |" in md
    assert "| ラグ | 既製品 |" in md and "DWSM2200" in md
    assert "合計質量" in md


@pytest.mark.parametrize("override, expected", [
    ({"shell__height": 120}, "φ152.4 × t1.2 × L120"),
    ({"shell__od": 127}, "φ127 × t1.2 × L100"),
    ({"shell__thickness": 1.5}, "φ152.4 × t1.5 × L100"),
])
def test_the_shell_row_follows_an_overridden_dimension(override, expected):
    rows = {r.name: r for r in full_bom(discover(TESTS)["demo"].override(**override))}
    assert rows["胴"].dimensions == expected
