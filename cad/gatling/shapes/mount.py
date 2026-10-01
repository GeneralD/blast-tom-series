"""マウント: 胴バンド（2 分割）・クレードル（フレームと脚とハンドル）・当て板。"""

from __future__ import annotations

import math

import cadquery as cq

from ..fasteners import lookup_screw
from ..params import GatlingSpec
from ..placement import band_bolt_x, band_tab_length, cradle_corner, cradle_y_rear, grip_y, levels, radii
from .common import compound, cylinder, ring

BAND_SPLIT = 2     # 胴バンドは 2 分割


__all__ = ["BAND_SPLIT", "CRADLE_ARMS", "band", "band_bolt_x", "band_tab_length", "cradle", "cradle_y_rear", "pad"]


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
    zc = z.band_centre
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


CRADLE_ARMS = 4    # 4 隅の腕。先端は胴バンドに M6 で留める（溶接しない。部品表の行だけで形は持たない）


def cradle(spec: GatlingSpec) -> cq.Workplane:
    """クレードル。胴を囲む水平の矩形フレーム、4 隅から胴バンドへ降りる脚と腕、後端のハンドル。

    フレームは平角材（幅 × 厚み）を寝かせた形で、厚みの中心が `frame_centre`。脚は垂直、腕は
    バンドの高さで隅から胴バンドの外面まで水平に伸びる。ハンドルは左右の縦桟を後ろへ
    `handle_length` 延ばし、先端をグリップ（丸棒）で結ぶ。

    腕の先端は胴バンドに溶接しない。両方の半環を 1 つの溶接品で結ぶと半環の相対位置が固まり、
    バンドが締まらない。腕は M6 で留め、腕の側の長穴（径方向）で位置を合わせる。組立は胴バンドを
    胴に締めてから腕のボルトを締める。長穴とボルトは形に持たない（図面は PR 5、ボルトは部品表）。
    """
    z, r, c = levels(spec), radii(spec), spec.cradle
    w, t, a = float(c.bar.width), float(c.bar.thickness), r.frame_inner
    outer, zf = a + w, z.frame_centre
    zb = z.band_centre
    gy = grip_y(spec)

    def box(sx: float, sy: float, sz: float, at: tuple[float, float, float]) -> cq.Workplane:
        return cq.Workplane("XY").box(sx, sy, sz).translate(at)

    body = box(2 * outer, w, t, (0, a + w / 2, zf))                                     # 前の横桟
    body = body.union(box(2 * outer, w, t, (0, -(a + w / 2), zf)))                      # 後の横桟
    for sx in (1, -1):
        body = body.union(box(w, outer - gy, t, (sx * (a + w / 2), (outer + gy) / 2, zf)))   # 縦桟（後ろへ延長）
    body = body.union(cylinder((-outer, gy, zf), (1, 0, 0), float(c.grip_dia), 2 * outer))        # グリップ
    corner = cradle_corner(spec)
    leg_top = zf - t / 2
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        body = body.union(box(w, t, leg_top - zb, (sx * (a + w / 2), sy * (a + w / 2), (leg_top + zb) / 2)))   # 脚
        arm = box(corner - r.band_outer, w, t, ((corner + r.band_outer) / 2, 0, zb))                          # 腕
        body = body.union(arm.rotate((0, 0, 0), (0, 0, 1), math.degrees(math.atan2(sy, sx))))
    return body


def pad(spec: GatlingSpec) -> cq.Workplane:
    """当て板。後側の横桟の上面中央に溶接し、ホルダー受けを固定する。"""
    z, p = levels(spec), spec.cradle.pad
    return (cq.Workplane("XY").box(float(p.width), float(p.depth), z.pad_top - z.frame_top)
            .translate((0, cradle_y_rear(spec), (z.frame_top + z.pad_top) / 2)))
