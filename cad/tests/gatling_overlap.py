"""Gatling の `assembly()` の部品どうしの重なりを測る（テストの道具）。

ボルトとねじ込む相手（下穴）は既定でも重なる（ねじ山を作らず、軸の円柱が下穴に食い込む）ので除く。
"""

from __future__ import annotations

import itertools

import cadquery as cq
from gatling.assemble import assembly

THREADED = {frozenset(p) for p in [("band", "bolt_band"), ("bolt_flange", "header"), ("clamp_tip", "bolt_tip")]}
MIN_VOLUME = 1e-3   # mm³。これ以下の交差は浮動小数の誤差とみなす


def overlaps(spec) -> list[str]:
    """重なる部品の組と交差体積（"a∩b = v"）。ねじ込みの 3 組は除く。

    包含箱が離れている組は交差を計算しない（交差は必ず 0。重い形状演算を省くだけで、結果は変わらない）。
    """
    shapes = {n: cq.Compound.makeCompound(p.solids().vals()) for n, p in assembly(spec).items()}
    boxes = {n: s.BoundingBox() for n, s in shapes.items()}
    found = []
    for a, b in itertools.combinations(shapes, 2):
        if frozenset((a, b)) in THREADED:
            continue
        p, q = boxes[a], boxes[b]
        if p.xmax < q.xmin or q.xmax < p.xmin or p.ymax < q.ymin or q.ymax < p.ymin or p.zmax < q.zmin or q.zmax < p.zmin:
            continue
        volume = shapes[a].intersect(shapes[b]).Volume()
        if volume > MIN_VOLUME:
            found.append(f"{a}∩{b} = {volume:.2f}")
    return found
