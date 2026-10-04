"""`build.py gatling` の出力（PR 3 は STEP / STL / SVG / viewer / bom。図面と音響は後の PR）。"""

from __future__ import annotations

import json
import re
from pathlib import Path

import build
import pytest
from drumcad.dims import unsettled
from drumcad.registry import discover

CAD = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def out_dir(tmp_path_factory):
    out = tmp_path_factory.mktemp("out")
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(build, "OUT", out)
        model = discover(CAD)["gatling"]
        assert build.build(model) == 0
    return out / "gatling-6-6-PROVISIONAL"


def test_the_output_directory_carries_the_provisional_suffix(out_dir):
    assert out_dir.is_dir() and out_dir.name == "gatling-6-6-PROVISIONAL"
    assert not out_dir.with_name("gatling-6-6").exists()


def test_every_part_and_the_assembly_are_exported_as_step_stl_and_svg(out_dir):
    names = [p.name for p in discover(CAD)["gatling"].parts()] + ["assembly"]
    missing = [f"{n}.{ext}" for n in names for ext in ("step", "stl", "svg") if not (out_dir / f"{n}.{ext}").exists()]
    assert missing == []


def test_the_viewer_embeds_every_part_and_says_how_many_values_are_pending(out_dir):
    html = (out_dir / "viewer.html").read_text(encoding="utf-8")
    data = json.loads(re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.DOTALL)
                      .group(1).replace("<\\/", "</"))
    infos = {p.name: p for p in discover(CAD)["gatling"].parts()}
    assert [p["name"] for p in data["parts"]] == list(infos)
    assert all(len(p["indices"]) > 0 for p in data["parts"])
    assert data["note"] == f"未決 {len(unsettled(discover(CAD)['gatling'].spec))} 件（仮値）"
    assert any(p["label"] == "管 ×6" for p in data["parts"])
    assert (data["zmin"], data["zmax"]) == pytest.approx((-450, 125.19), abs=0.01)  # viewer は 0.01 に丸める。管の先端から、フープの上端まで（ロッドの頭の上面もここ）


def test_the_bom_lists_fabricated_and_purchased_rows_with_the_total_mass(out_dir):
    md = (out_dir / "bom.md").read_text(encoding="utf-8")
    assert md.startswith("# 部品表 — gatling-6-6")
    assert md.count("| 製作品 |") == 16 and md.count("| 既製品 |") == 9
    kg = float(re.search(r"\*\*([\d.]+) kg\*\*", md).group(1))
    assert 7.5 < kg < 8.5      # 製作品の合計（既製品の質量は載らない）。D-22 で旧クレードル・胴バンドの分（約 3.6 kg）が減った


def test_a_fatal_configuration_exports_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "OUT", tmp_path)
    broken = discover(CAD)["gatling"].override(tube__gap_ratio=0)
    assert build.build(broken) >= 1      # 致命的な問題の件数。gap_ratio=0 は管の干渉と、先端クランプのボルトの頭が管に当たるのを同時に出す
    assert list(tmp_path.iterdir()) == []


def test_a_zero_tube_count_stops_as_a_fatal_not_as_an_exception(tmp_path, monkeypatch):
    """`_build` は `issues()` より先に `name()` を呼ぶ。`name()` が個数で割ると、構造の検査の前に例外になる。"""
    monkeypatch.setattr(build, "OUT", tmp_path)
    assert build.build(discover(CAD)["gatling"].override(tube__count=0)) >= 1
    assert list(tmp_path.iterdir()) == []


def test_main_builds_gatling_by_name(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "OUT", tmp_path)
    assert build.main(["build.py", "gatling"]) == 0
    assert (tmp_path / "gatling-6-6-PROVISIONAL" / "viewer.html").exists()
