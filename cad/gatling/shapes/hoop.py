"""ダブルフープ（オリジナル設計）: 内リング・外リング（管の環）・受金。D-20。"""

from __future__ import annotations

import cadquery as cq

from drumcad.solids import around_z, ring

from ..params import GatlingSpec
from ..placement import ear_hole_dia, levels, lug_angles, radii


def hoop_inner(spec: GatlingSpec) -> cq.Workplane:
    """内リング（カウンターフープ）。下面がフレッシュフープの上端に載り、内径はヘッド外径より小さい。

    膜面から上端までの高さ（`inner.height`）がリムの高さで、口径が小さいほどリムが深いとミスショットしやすいので浅くする。
    ロッドを締めると受金がこの環を押し下げ、環がフレッシュフープを押し下げて膜をエッジに張る。
    """
    z, r = levels(spec), radii(spec)
    return ring(r.hoop_in_outer, r.hoop_in_inner, z.head_top, z.hoop_top)


def _pipe_section(spec: GatlingSpec, bore: bool) -> cq.Workplane:
    """外リングの管の環。断面（XZ 面の円）を Z 軸の周りに回す。`bore` が偽なら中実（受金を管の形で切る刃物）。"""
    z, r = levels(spec), radii(spec)
    half = float(spec.hoop.outer.od) / 2
    at = (r.hoop_out_centre, z.pipe_centre)               # XZ 面の局所座標（x = 半径、y = 高さ）
    section = cq.Workplane("XZ").moveTo(*at).circle(half)
    if bore:
        section = section.moveTo(*at).circle(half - float(spec.hoop.outer.thickness))
    return section.revolve(360, (0, 0, 0), (0, 1, 0))     # 局所の y 軸 = Z 軸の周り


def hoop_outer(spec: GatlingSpec) -> cq.Workplane:
    """外リング（質量リング）。管を丸めた中空の環で、上端を内リングの上端に揃え、受金で内リングと結ぶ。"""
    return _pipe_section(spec, bore=True)


def ear(spec: GatlingSpec) -> cq.Workplane:
    """受金。内外リングの間に沈む水平の板で、上面は「フープの上端 − ロッドの頭の高さ」（頭の上面がリムの上端に揃う）。
    下面は上面から板厚ぶん下で、膜面より下（フレッシュフープの外側）に出てよい。

    板は内リングの外面より内側から始め、外端を管の外形で切るのと同じく、内端を内リングの外面の円柱で切って円弧で沿わせる
    （平らな端だと、内リングの外面に y = 0 の線でしか接せず、幅の端で隙間が開く）。内リングと管の両方に溶接する。
    ロッドを通す穴はリングの間（ロッドの半径）に開く。部品表の寸法欄の長さは内リングの外面から管の中心まで。
    """
    z, r, e = levels(spec), radii(spec), spec.hoop.ear
    height = z.ear_top - z.ear_bottom
    start = r.hoop_in_outer - min(float(e.width) / 2, r.hoop_in_outer / 2)   # 幅の端の隅が内リングの外面の内側に入る
    plate = (cq.Workplane("XY").box(r.hoop_out_centre - start, float(e.width), height)
             .translate(((start + r.hoop_out_centre) / 2, 0, (z.ear_bottom + z.ear_top) / 2)))
    inner_ring = cq.Workplane("XY").workplane(offset=z.ear_bottom).circle(r.hoop_in_outer).extrude(height)
    plate = plate.cut(inner_ring)
    hole = (cq.Workplane("XY").workplane(offset=z.ear_bottom).center(r.rod, 0)
            .circle(ear_hole_dia(spec) / 2).extrude(z.ear_top - z.ear_bottom))
    return around_z(plate.cut(hole).cut(_pipe_section(spec, bore=False)), lug_angles(spec))
