"""組立と部品表の元（D-18: 員数ぶんの solid を置き、員数・規格・寸法は SPEC から作る）。"""

from __future__ import annotations

import itertools
import re

import cadquery as cq
import pytest
from drumcad.checks import count_issues
from drumcad.materials import SUS304, mass_g
from gatling.assemble import assembly
from gatling.catalog import SILICONE, parts
from gatling.params import SPEC, override


@pytest.fixture(scope="module")
def built():
    return assembly(SPEC)


def test_assembly_and_parts_have_the_same_names_in_the_same_order(built):
    assert list(built) == [p.name for p in parts(SPEC)]
    assert len(built) == 21


def test_every_part_has_exactly_count_solids_so_the_build_does_not_stop(built):
    assert count_issues(built, parts(SPEC)) == []
    for info in parts(SPEC):
        assert built[info.name].solids().size() == info.count, info.name


def test_the_counts_are_the_spec_counts():
    n = {p.name: p.count for p in parts(SPEC)}
    assert (n["tube"], n["lug"], n["rod"], n["ear"], n["bolt_flange"], n["bolt_tip"]) == (6, 6, 6, 6, 6, 6)
    assert (n["band"], n["bolt_band"]) == (2, 2)
    assert all(n[k] == 1 for k in ("head", "shell", "edge", "flange", "gasket", "header", "clamp_mid", "clamp_tip",
                                   "hoop_inner", "hoop_outer", "cradle", "pad", "holder"))


def test_changing_the_spec_changes_the_counts_and_the_solids_together():
    spec = override(SPEC, lug__count=3, hoop__ear__count=3, tube__count=3, flange__bolt_count=3)
    a, infos = assembly(spec), {p.name: p for p in parts(spec)}
    assert count_issues(a, list(infos.values())) == []
    assert (infos["lug"].count, infos["tube"].count, infos["ear"].count, infos["bolt_flange"].count) == (3, 3, 3, 3)
    assert a["lug"].solids().size() == 3 and a["tube"].solids().size() == 3 and a["bolt_tip"].solids().size() == 3


def test_a_mismatch_between_the_ear_count_and_the_lug_count_is_caught_by_the_contract():
    spec = override(SPEC, lug__count=3)                           # 受金は 6 のまま
    assert any(i.fatal for i in count_issues(assembly(spec), parts(spec)))


def test_fabricated_standards_and_dimensions_are_written_from_the_spec():
    info = {p.name: p for p in parts(SPEC)}
    assert info["tube"].standard == "手すり用 #400 研磨管"
    assert info["tube"].dimensions == "φ38.1 × t1.2 × L480（組立後に L450 へ切り詰め）"
    assert info["shell"].dimensions == "φ152 × t1.2 × H100"
    assert info["header"].dimensions == "φ188 × t6" and info["flange"].dimensions == "φ188 / φ149.6 × t6"
    assert info["hoop_inner"].dimensions == "内径 φ153.4 × 幅8 × t4"
    assert info["hoop_outer"].standard == "手すり用 #400 研磨管を曲げて TIG 突合せ"
    assert info["hoop_outer"].dimensions == "φ25.4 × t1.5、内径 φ181.4（中心径 φ206.8）"
    assert info["ear"].dimensions == "20 × 22.7 × t6"                                  # 内リングの外面から管の中心まで
    assert info["rod"].dimensions == "L50（頭 φ9 × H5）"
    assert info["lug"].dimensions == "φ30 × 厚み20"                                   # 胴の外から見た円盤の径 × 半径方向の厚み
    changed = {p.name: p for p in parts(override(SPEC, tube__length=500, tube__od=42.7, shell__plenum_height=90))}
    assert changed["tube"].dimensions == "φ42.7 × t1.2 × L530（組立後に L500 へ切り詰め）"
    assert changed["shell"].dimensions == "φ152 × t1.2 × H90"


def test_the_standards_of_the_purchased_parts_follow_the_choices():
    info = {p.name: p for p in parts(SPEC)}
    assert info["lug"].standard == "単穴の丸形ラグ（型番未定）" and info["rod"].standard == "テンションロッド #12-24"
    assert info["holder"].standard == "L ロッド 12.7" and info["bolt_tip"].standard == "黒色 SUS 六角穴付きボルト M5"
    other = {p.name: p for p in parts(override(SPEC, mount__type="L ロッド 10.5"))}
    assert other["holder"].standard == "L ロッド 10.5"


def test_every_part_is_marked_fabricated_or_purchased_with_a_valid_colour():
    made = {p.name: p.made for p in parts(SPEC)}
    assert {k for k, v in made.items() if v == "purchased"} == {"head", "lug", "rod", "holder", "bolt_band", "bolt_flange", "bolt_tip"}
    assert all(re.fullmatch(r"#[0-9a-f]{6}", p.color) for p in parts(SPEC))
    assert all(len(p.explode) == 3 for p in parts(SPEC))


def test_fabricated_parts_are_sus304_and_the_gasket_is_silicone():
    mats = {p.name: p.material for p in parts(SPEC) if p.made == "fabricated"}
    assert mats.pop("gasket") is SILICONE
    assert all(m is SUS304 for m in mats.values())


def test_the_spec_section_5_1_mass_check(built):
    """§5.1 の概算（管 3.0 kg、胴 0.45、ヘッダープレートとフランジで 1.5）に収まる。クレードルは概算（1.2 kg）より重い。"""
    mass = {p.name: mass_g(built[p.name], p.material) for p in parts(SPEC) if p.made == "fabricated"}
    assert mass["tube"] == pytest.approx(3000, rel=0.02) and mass["shell"] == pytest.approx(450, rel=0.02)
    assert mass["header"] + mass["flange"] == pytest.approx(1500, rel=0.05)
    assert mass["cradle"] > 2000                                  # 仕様の概算 1.2 kg より重い（置いた仮定を参照）
    assert 9000 < sum(mass.values()) < 12000                      # 概算 9 kg は既製品込み。製作品だけで 10 kg 前後


# 溶接・ねじ込みで接する部品は体積を共有しない。ただしボルトの軸（呼び径）は下穴（ねじの谷径）より太いので、
# ねじ込み先と重なる。この 3 組だけは重なりを許す。
THREADED = {frozenset(("bolt_flange", "header")), frozenset(("bolt_tip", "clamp_tip")), frozenset(("bolt_band", "band"))}


def _compound(part):
    return cq.Compound.makeCompound(part.solids().vals())


def _boxes_touch(a, b):
    p, q = a.BoundingBox(), b.BoundingBox()
    return not (p.xmax < q.xmin or q.xmax < p.xmin or p.ymax < q.ymin or q.ymax < p.ymin or p.zmax < q.zmin or q.zmax < p.zmin)


def test_no_two_parts_overlap_except_a_bolt_in_its_tapped_hole(built):
    shapes = {name: _compound(part) for name, part in built.items()}
    overlaps = []
    for a, b in itertools.combinations(shapes, 2):
        if frozenset((a, b)) in THREADED or not _boxes_touch(shapes[a], shapes[b]):
            continue
        if shapes[a].intersect(shapes[b]).Volume() > 1e-3:
            overlaps.append((a, b))
    assert overlaps == []


def test_the_head_is_drawn_red_and_half_transparent_and_every_other_part_stays_opaque():
    """ヘッドは既製品で、赤の半透明は見た目のイメージ。型番・膜厚などの値は変えない。"""
    info = {p.name: p for p in parts(SPEC)}
    assert info["head"].color == "#d0121b" and info["head"].opacity == 0.5
    assert {k for k, v in info.items() if v.opacity != 1.0} == {"head"}
    assert info["head"].standard == SPEC.head.model.value and info["head"].made == "purchased"
