"""胴まわり: プレナム胴・ベアリングエッジ環。"""

from __future__ import annotations

import math

import cadquery as cq

from ..derived import derive
from ..params import GatlingSpec
from ..placement import levels, lug_angles
from .common import cylinder, ring


def shell(spec: GatlingSpec) -> cq.Workplane:
    """プレナム胴。ラグの取付穴は、ラグ 1 個につき上下 2 つ（`lug.pitch` 間隔）。"""
    z, d = levels(spec), derive(spec)
    body = ring(float(d.shell_od) / 2, float(d.shell_id) / 2, z.flange_top, z.shell_top)
    zc = (z.lug_top + z.lug_bottom) / 2
    radius = float(spec.lug.hole_dia) / 2
    for angle in lug_angles(spec):
        for dz in (-float(spec.lug.pitch) / 2, float(spec.lug.pitch) / 2):
            bore = cylinder((0, 0, zc + dz), (1, 0, 0), 2 * radius, float(d.shell_od))
            body = body.cut(bore.rotate((0, 0, 0), (0, 0, 1), angle))
    return body


def edge(spec: GatlingSpec) -> cq.Workplane:
    """ベアリングエッジ環。胴の上端に溶接し、溶接後に 45° のエッジを仕上げ旋削する。

    頂部の小 R は同じ大きさの面取りで近似する（形状の確認用。R は図面で指示する）。
    """
    e, z = spec.edge, levels(spec)
    r_out = float(derive(spec).shell_od) / 2
    r_in = r_out - float(e.width)
    chamfer = float(e.radius)
    drop = (r_out - chamfer - r_in) * math.tan(math.radians(float(e.angle)))
    base, top = z.shell_top, z.shell_top + float(e.height)
    profile = [(r_in, base), (r_out, base), (r_out, top - chamfer), (r_out - chamfer, top), (r_in, top - drop)]
    return cq.Workplane("XZ").polyline(profile).close().revolve(360, (0, 0, 0), (0, 1, 0))
