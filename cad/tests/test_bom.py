from pathlib import Path

import pytest
from drumcad.bom import bom_markdown, full_bom
from drumcad.registry import discover

TESTS = Path(__file__).parent


def test_full_bom_adds_a_row_per_fabricated_part_with_its_mass():
    m = discover(TESTS)["demo"]
    rows = full_bom(m)
    names = [r.name for r in rows]
    assert names == ["胴", "底板", "ラグ"]
    shell = rows[0]
    assert shell.made == "fabricated" and shell.material.name.startswith("ステンレス")
    assert shell.mass_g == pytest.approx(3.14159 * (76.2**2 - 75.0**2) * 100 * 7.93e-3, rel=1e-3)
    assert rows[2].part_number == "DWSM2200"


def test_bom_markdown_is_a_table_with_a_total_mass():
    m = discover(TESTS)["demo"]
    md = bom_markdown(m.name(), full_bom(m))
    assert md.startswith("# 部品表 — demo-6-6")
    assert "| 胴 | 製作品 | ステンレス SUS304 |" in md
    assert "| ラグ | 既製品 |" in md and "DWSM2200" in md
    assert "合計質量" in md
