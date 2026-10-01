"""既製品の部品表（`bom(spec)`）。製作品の行は `build` が形状から作る（`drumcad.bom.full_bom`）。"""

from __future__ import annotations

from drumcad.contract import BomRow

from .catalog import fmt, parts
from .params import GatlingSpec
from .shapes.mount import BAND_SPLIT, CRADLE_ARMS

UNDECIDED = "未定"      # 型番は実物を買って測るまで決まらない（仕様 §6 の 3）


def bom(spec: GatlingSpec) -> list[BomRow]:
    """既製品の型番と員数。簡略形状を持つ既製品は `parts()` の員数をそのまま写し、
    形を持たない消耗品・付属品はここで足す。"""
    rows = [BomRow(i.label, "purchased", None, i.standard, i.dimensions, i.count, UNDECIDED)
            for i in parts(spec) if i.made == "purchased"]
    lugs = int(float(spec.lug.count))
    rows += [
        BomRow("ラグボルト", "purchased", None, "ラグ付属のねじ（胴の取付穴に通す）", "", 2 * lugs, UNDECIDED),
        BomRow("シール座金", "purchased", None, "ラグ穴のシール用", "", 2 * lugs, UNDECIDED),
        BomRow("ゴムシート", "purchased", None, "胴バンドと胴の間に挟む", f"t{fmt(spec.band.rubber)}", BAND_SPLIT, UNDECIDED),
        BomRow(f"ボルト {spec.band.bolt.value}（クレードルの腕）", "purchased", None,
               f"六角穴付きボルト {spec.band.bolt.value}（腕の長穴から胴バンドのタップへ）", "", CRADLE_ARMS, UNDECIDED),
        BomRow("焼き付き防止剤", "purchased", None, "意匠ボルトのねじ部", "", 1, UNDECIDED),
    ]
    return rows
