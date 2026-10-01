"""ダブルフープ（オリジナル設計）: 内リング・外リング・受金。"""

from __future__ import annotations

import cadquery as cq

from ..fasteners import lookup_rod
from ..params import GatlingSpec
from ..placement import levels, lug_angles, radii
from .common import around_z, ring


def hoop_inner(spec: GatlingSpec) -> cq.Workplane:
    """内リング（カウンターフープ）。下面がフレッシュフープの上端に載り、内径はヘッド外径より小さい。

    ロッドを締めると受金がこの環を押し下げ、環がフレッシュフープを押し下げて膜をエッジに張る。
    """
    z, r = levels(spec), radii(spec)
    return ring(r.hoop_in_outer, r.hoop_in_inner, z.head_top, z.hoop_top)


def hoop_outer(spec: GatlingSpec) -> cq.Workplane:
    """外リング（質量リング）。上端を内リングに揃え、受金で内リングと結ぶ。"""
    z, r = levels(spec), radii(spec)
    return ring(r.hoop_out_outer, r.hoop_out_inner, z.hoop_top - float(spec.hoop.outer.height), z.hoop_top)


def ear(spec: GatlingSpec) -> cq.Workplane:
    """受金。内外リングの上端に載って両方をつなぎ、ロッドを通す穴がリングの間に開く。"""
    z, r, e = levels(spec), radii(spec), spec.hoop.ear
    span = r.hoop_out_outer - r.hoop_in_inner
    thick = float(e.thickness)
    plate = (cq.Workplane("XY").box(span, float(e.width), thick)
             .translate(((r.hoop_in_inner + r.hoop_out_outer) / 2, 0, z.hoop_top + thick / 2)))
    hole = (cq.Workplane("XY").workplane(offset=z.hoop_top).center(r.rod, 0)
            .circle((float(lookup_rod(spec.lug.thread)) + float(e.hole_clearance)) / 2).extrude(thick))
    return around_z(plate.cut(hole), lug_angles(spec))
