"""既製品の部品表（`bom(spec)`）。製作品の行は `build` が形状から作る（`drumcad.bom.full_bom`）。"""

from __future__ import annotations

from drumcad.contract import BomRow

from .catalog import parts
from .params import GatlingSpec
from .placement import LUG_HOLES

UNDECIDED = "未定"      # 型番は実物を買って測るまで決まらない（仕様 §6 の 3）


def bom(spec: GatlingSpec) -> list[BomRow]:
    """既製品の型番と員数。簡略形状を持つ既製品は `parts()` の員数をそのまま写し、
    形を持たない消耗品・付属品はここで足す。"""
    rows = [BomRow(i.label, "purchased", None, i.standard, i.dimensions, i.count, UNDECIDED)
            for i in parts(spec) if i.made == "purchased"]
    lugs = int(float(spec.lug.count))
    rows += [
        BomRow("ラグボルト", "purchased", None, "ラグ付属のねじ（胴の取付穴に通し、ラグを 1 本で留める）", "", LUG_HOLES * lugs, UNDECIDED),
        BomRow("シール座金", "purchased", None, "ラグ穴のシール用", "", LUG_HOLES * lugs, UNDECIDED),
        BomRow("焼き付き防止剤", "purchased", None, "意匠ボルトのねじ部", "", 1, UNDECIDED),
    ]
    return rows
