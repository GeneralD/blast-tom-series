"""マウント: 胴バンド（2 分割）・クレードル（フレームと脚とハンドル）・当て板。"""

from __future__ import annotations

import math

import cadquery as cq

from ..fasteners import lookup_screw
from ..params import GatlingSpec
from ..placement import levels, radii
from .common import compound, cylinder, ring

BAND_SPLIT = 2     # 胴バンドは 2 分割


def band_tab_length(spec: GatlingSpec) -> float:
    """バンドの耳（締め付け部）の長さ。ボルトの頭が収まるよう、頭径の 2 倍にする。"""
    return 2 * float(lookup_screw(spec.band.bolt).head_dia)


def band_bolt_x(spec: GatlingSpec) -> float:
    """バンドのボルトの X 位置（耳の中央、+X 側。−X 側は符号を反転）。"""
    return radii(spec).band_outer + band_tab_length(spec) / 2


def band(spec: GatlingSpec) -> cq.Workplane:
    """胴バンド。+Y 側と −Y 側の 2 つの半環。分割面（XZ 面）の両端に耳があり、M6 で Y 方向に締める。

    分割面ごとに `band.gap` の隙間を空ける（半環は y = ±gap/2 から外側）。隙間が無いと、締めても
    先に耳どうしが当たり、ゴムシートと胴に締め付け力がかからない。
    +Y 側の耳に通し穴、−Y 側の耳に下穴（タップ）を開ける。
    """
    z, r = levels(spec), radii(spec)
    height = z.band_top - z.band_bottom
    tab, thick = band_tab_length(spec), float(spec.band.bar.thickness)
    half_gap = float(spec.band.gap) / 2
    screw = lookup_screw(spec.band.bolt)
    zc = (z.band_bottom + z.band_top) / 2
    halves = []
    for sign in (1, -1):
        half_box = cq.Workplane("XY").box(2 * r.band_outer, r.band_outer - half_gap, height, centered=(True, False, False))
        body = ring(r.band_outer, r.band_inner, z.band_bottom, z.band_top).intersect(
            half_box.translate((0, half_gap if sign > 0 else -r.band_outer, z.band_bottom)))
        hole = float(screw.clearance if sign > 0 else screw.tap_drill)
        for side in (1, -1):
            # 耳は半環の肉に食い込ませる（接するだけだと union が別 solid のまま残す）
            reach = r.band_outer + tab - r.band_inner
            x0 = r.band_inner if side > 0 else -r.band_outer - tab
            lug = cq.Workplane("XY").box(reach, thick, height, centered=False).translate(
                (x0, half_gap if sign > 0 else -half_gap - thick, z.band_bottom))
            bore = cylinder((side * band_bolt_x(spec), sign * half_gap, zc), (0, sign, 0), hole, thick)
            body = body.union(lug).cut(bore)
        halves.append(body)
    return compound(halves)
