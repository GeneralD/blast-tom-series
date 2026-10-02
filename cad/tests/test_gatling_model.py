"""契約（仕様 §4.4）を、`build.py` と同じ `discover` 経由で確かめる。"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from types import ModuleType

import pytest
from drumcad.bom import bom_markdown, full_bom
from drumcad.contract import REQUIRED
from drumcad.dims import Choice, Dim, Source, unsettled
from drumcad.registry import discover
from gatling.derived import derive

CAD = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def gatling():
    return discover(CAD)["gatling"]


def _settle(obj):
    """全ての葉を設計判断に置き換えた複製（仮が 1 つも残らない spec）。"""
    if isinstance(obj, Dim):
        return Dim(float(obj), Source.DESIGN, obj.note)
    if isinstance(obj, Choice):
        return Choice(obj.value, Source.DESIGN, obj.note)
    if isinstance(obj, tuple):
        return tuple(_settle(item) for item in obj)
    if dataclasses.is_dataclass(obj):
        return dataclasses.replace(obj, **{f.name: _settle(getattr(obj, f.name)) for f in dataclasses.fields(obj)})
    return obj


def test_discover_finds_gatling_and_reads_the_whole_contract(gatling):
    assert gatling.key == "gatling" and gatling.name() == "gatling-6-6"
    assert len(gatling.parts()) == 21 and set(gatling.assembly()) == {p.name for p in gatling.parts()}
    assert [i for i in gatling.issues() if i.fatal] == []
    assert gatling.bom() and all(r.made == "purchased" for r in gatling.bom())


def test_every_required_name_is_a_function_not_a_shadowing_submodule(gatling):
    """サブモジュール名が契約の関数名と重なると、`hasattr` は通るのに `Model.parts()` が落ちる。"""
    for fn in REQUIRED[1:]:
        attr = getattr(gatling._module, fn)
        assert callable(attr) and not isinstance(attr, ModuleType), fn
    assert gatling.spec is gatling._module.SPEC


def test_drawing_and_acoustic_model_are_not_public_yet(gatling):
    assert gatling.drawing is None and gatling.acoustic_model is None      # PR 4 / 5 で公開する任意属性
    assert not hasattr(gatling._module, "drawing") and not hasattr(gatling._module, "acoustic_model")


def test_override_through_the_model_moves_the_name_the_parts_and_the_derived_values(gatling):
    longer = gatling.override(**{"tube.length": 500})
    dims = {p.name: p.dimensions for p in longer.parts()}
    assert dims["tube"] == "φ38.1 × t1.2 × L530（組立後に L500 へ切り詰め）"
    assert gatling.override(lug__count=3, hoop__ear__count=3).name() == "gatling-6-3"
    assert float(derive(gatling.override(tube__gap_ratio=0.8).spec).plate_od) > 188


def test_the_default_spec_is_provisional_so_the_output_would_be_suffixed(gatling):
    assert len(unsettled(gatling.spec)) == 23       # D-20 でリムの高さ・肉厚とロッドの頭の径・高さ（4 件）が仮で増えた


def test_once_every_leaf_is_settled_nothing_is_provisional_and_every_derived_value_is_derived(gatling):
    settled = _settle(gatling.spec)
    assert unsettled(settled) == []
    d = derive(settled)
    # 面密度だけは、膜の密度（PET の一般値 FILM_DENSITY。SPEC の葉ではない）が仮なので仮のまま残る
    sources = {f.name: getattr(d, f.name).source for f in dataclasses.fields(d)}
    assert sources.pop("areal_density") is Source.PROVISIONAL
    assert all(source is Source.DERIVED for source in sources.values())


def test_the_full_bom_has_a_row_for_every_part_and_a_mass_for_the_fabricated_ones(gatling):
    rows = full_bom(gatling)
    fabricated = [r for r in rows if r.made == "fabricated"]
    assert len(fabricated) == 14 and all(r.mass_g and r.mass_g > 0 for r in fabricated)
    assert len(rows) == 14 + 12
    tube = next(r for r in rows if r.name == "管")
    assert tube.count == 6 and tube.mass_g == pytest.approx(496.4, rel=1e-3)         # solid 1 個分
    assert tube.standard == "手すり用 #400 研磨管" and tube.dimensions.startswith("φ38.1 × t1.2 × L480")
    assert "| 管 | 製作品 | ステンレス SUS304 | 手すり用 #400 研磨管 |" in bom_markdown(gatling.name(), rows)
