"""既製品の簡略形状（ヘッド・ラグ・テンションロッド・ホルダー受け・ボルト）。

寸法は実物を測るまで置き値（`provisional`）で、形は位置と大きさの確認用。ねじ山や内部の構造は作らない。
"""

from __future__ import annotations

import cadquery as cq

from ..fasteners import lookup_holder, lookup_rod, lookup_screw
from ..params import GatlingSpec
from ..placement import (BAND_SIDES, band_bolt_x, cradle_y_rear, flange_bolt_points, levels, lug_angles, radii,
                         tip_bolt_points)
from .common import around_z, compound, cylinder, cylinders, disc, ring


def head(spec: GatlingSpec) -> cq.Workplane:
    """ヘッド。膜（円盤）の下面がベアリングエッジの頂部に載り、フレッシュフープ（環）は膜の上面から
    胴とエッジ環の外側に垂れる（環の内径 = 胴外径 + 逃げ）。内リングは環の上端に載る。"""
    z, h = levels(spec), spec.head
    collar = ring(radii(spec).collar, float(h.fit_id) / 2, z.collar_bottom, z.head_top)
    # 膜の縁は環の肉厚の中ほどまで広げる。環の内面（fit_id / 2）で止めると膜と環が面で接するだけになり、
    # union が 1 つの solid に融合しない（形は位置と大きさの確認用で、実物の膜の巻き込みは表さない）
    film = disc(float(h.fit_id) / 2 + float(h.collar_wall) / 2, z.edge_top, z.head_top)
    return collar.union(film)


def lug(spec: GatlingSpec) -> cq.Workplane:
    """ラグ。ロッドと同軸の縦の円筒の本体（ロッドの穴が縦に通る）と、胴の外面から本体までの台座（胴にねじ 1 本で留める）を
    1 つの solid にする。台座はラグの高さの中心を軸に胴の外面へ向かって伸び、胴の外面の円柱で切って、食い込まず離れず沿わせる。"""
    z, r, s = levels(spec), radii(spec), spec.lug
    zc = (z.lug_top + z.lug_bottom) / 2
    body = cylinders([(r.rod, 0)], float(s.body_dia), z.lug_bottom, z.lug_top)
    start = r.shell - float(s.foot_dia)                 # 胴の壁の中から始めて、下で胴の外面の円柱で切る（円弧に沿わせる）
    foot = cylinder((start, 0, zc), (1, 0, 0), float(s.foot_dia), r.rod - start)
    solid = body.union(foot).cut(cylinders([(r.rod, 0)], float(lookup_rod(s.thread)), z.lug_bottom, z.lug_top))
    # 胴の外面より内側（台座の根元、胴にかかる本体）は胴の壁なので、胴の外面の円柱で切る
    solid = solid.cut(cylinders([(0, 0)], 2 * r.shell, z.lug_bottom, z.lug_top))
    return around_z(solid, lug_angles(spec))


def rod(spec: GatlingSpec) -> cq.Workplane:
    """テンションロッド。頭が受金の上面に載り、軸が受金の穴から内外リングの間を下りてラグにねじ込む
    （軸の先がラグに届くか・ラグの下に出ないか、頭がリングに当たらないかの検査は `checks.rod_fits`）。"""
    z, r, s = levels(spec), radii(spec), spec.lug
    shaft = cylinders([(r.rod, 0)], float(lookup_rod(s.thread)), z.rod_tip, z.ear_top)
    head = cylinders([(r.rod, 0)], float(s.rod_head_dia), z.ear_top, z.rod_top)
    return around_z(shaft.union(head), lug_angles(spec))


def holder(spec: GatlingSpec) -> cq.Workplane:
    """ホルダー受け（簡略）。当て板の上の円柱で、L ロッドが X 方向に通る穴がある。"""
    z, m = levels(spec), spec.mount
    y = cradle_y_rear(spec)
    body = cylinders([(0, y)], float(m.body_dia), z.holder_bottom, z.holder_top)
    bore = cylinder((-float(m.body_dia), y, (z.holder_bottom + z.holder_top) / 2), (1, 0, 0), float(lookup_holder(m.type)), 2 * float(m.body_dia))
    return body.cut(bore)


def _screw(head_dia: float, head_h: float, shank: float, length: float,
           origin: tuple[float, float, float], direction: tuple[float, float, float]) -> cq.Workplane:
    """六角穴付きボルトの簡略形（頭の円柱と軸の円柱）。`origin` は頭の座面で、軸は `direction` へ `length` 伸び、頭は逆向き。"""
    opposite = (-direction[0], -direction[1], -direction[2])
    return cylinder(origin, direction, shank, length).union(cylinder(origin, opposite, head_dia, head_h))


def bolt_flange(spec: GatlingSpec) -> cq.Workplane:
    """フランジの M6。頭がフランジ上面に座り、軸がフランジ・ガスケットを通ってヘッダープレートに入る。"""
    s, z = lookup_screw(spec.flange.bolt), levels(spec)
    return compound([_screw(float(s.head_dia), float(s.head_height), float(s.major), float(spec.flange.bolt_length),
                            (x, y, z.flange_top), (0, 0, -1)) for x, y in flange_bolt_points(spec)])


def bolt_tip(spec: GatlingSpec) -> cq.Workplane:
    """先端クランプの意匠ボルト（M5）。頭が下面に座り、軸が上へ入る。"""
    s, z = lookup_screw(spec.clamp.bolt), levels(spec)
    return compound([_screw(float(s.head_dia), float(s.head_height), float(s.major), float(spec.clamp.bolt_length),
                            (x, y, z.tip_bottom), (0, 0, 1)) for x, y in tip_bolt_points(spec)])


def bolt_band(spec: GatlingSpec) -> cq.Workplane:
    """胴バンドの M6。+Y 側の耳の外面（y = gap/2 + 耳の厚み）に頭が座り、−Y 向きに締め代を渡って −Y 側の耳にねじ込む。"""
    s, z = lookup_screw(spec.band.bolt), levels(spec)
    zc, top = z.band_centre, float(spec.band.gap) / 2 + float(spec.band.bar.thickness)
    return compound([_screw(float(s.head_dia), float(s.head_height), float(s.major), float(spec.band.bolt_length),
                            (side * band_bolt_x(spec), top, zc), (0, -1, 0)) for side in BAND_SIDES])
