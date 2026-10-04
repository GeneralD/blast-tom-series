"""既製品の簡略形状（ヘッド・ラグ・テンションロッド・ホルダー受け・ボルト）。

寸法は実物を測るまで置き値（`provisional`）で、形は位置と大きさの確認用。ねじ山や内部の構造は作らない。
"""

from __future__ import annotations

import cadquery as cq

from ..fasteners import lookup_holder, lookup_rod, lookup_screw
from ..params import GatlingSpec
from ..placement import KNOB_EMBED, flange_bolt_points, holder_centre, levels, lug_angles, radii, tip_bolt_points
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
    """ラグ（タレット形）。胴の外から見て丸い円盤で、軸は胴の半径方向。円盤の中心を胴の内側から 1 本のねじで留める。
    円盤は径 `body_dia`、胴の外面から外側の面まで `depth`、中心の高さはラグの高さ帯の中心（胴の取付穴の高さ）。
    胴側は胴の外面の円柱で切って、食い込まず離れず沿わせる。ロッドの穴（呼び径）は円盤の上端から縦に開く止まり穴で、
    底はロッドの軸の先（円盤の下端より下に出る設定では下端まで通る。先がラグの上端からねじ込み代まで届くかは `checks.rod_fits` が見る）。"""
    z, r, s = levels(spec), radii(spec), spec.lug
    zc = (z.lug_top + z.lug_bottom) / 2
    # 軸の上の胴の中心から始めて外側の面まで伸ばし、胴の外面の円柱で切る（円弧に沿わせる。外側の面は胴の外面から depth の平面）
    disc = cylinder((0, 0, zc), (1, 0, 0), float(s.body_dia), r.shell + float(s.depth))
    bore = cylinders([(r.rod, 0)], float(lookup_rod(s.thread)), max(z.rod_tip, z.lug_bottom), z.lug_top)   # 底 = 軸の先（軸が穴を埋める）
    solid = disc.cut(bore).cut(cylinders([(0, 0)], 2 * r.shell, z.lug_bottom - 1, z.lug_top + 1))   # 円盤の上下の接線を避けて 1 mm 広く
    return around_z(solid, lug_angles(spec))


def rod(spec: GatlingSpec) -> cq.Workplane:
    """テンションロッド。頭が受金の上面に載り、軸が受金の穴から内外リングの間を下りてラグにねじ込む
    （軸の先がラグに届くか・ラグの下に出ないか、頭がリングに当たらないかの検査は `checks.rod_fits`）。"""
    z, r, s = levels(spec), radii(spec), spec.lug
    shaft = cylinders([(r.rod, 0)], float(lookup_rod(s.thread)), z.rod_tip, z.ear_top)
    head = cylinders([(r.rod, 0)], float(s.rod_head_dia), z.ear_top, z.rod_top)
    return around_z(shaft.union(head), lug_angles(spec))


def holder(spec: GatlingSpec) -> cq.Workplane:
    """ホルダー受け（簡略）。ブロックの上の円柱で、L ロッドが X 方向に通る穴がある。締めるつまみは後ろ（−Y）へ水平に出す
    （本体の中ほどの高さの円柱。形は簡単にして、本体の外面から `KNOB_EMBED` 食い込ませて 1 つにつなぐ）。"""
    z, m = levels(spec), spec.mount
    x, y = holder_centre(spec)
    body = cylinders([(x, y)], float(m.body_dia), z.holder_bottom, z.holder_top)
    bore = cylinder((-float(m.body_dia), y, z.knob_centre), (1, 0, 0), float(lookup_holder(m.type)), 2 * float(m.body_dia))
    rim = y - float(m.body_dia) / 2
    knob = cylinder((x, rim + KNOB_EMBED, z.knob_centre), (0, -1, 0), float(m.knob_dia), float(m.knob_length) + KNOB_EMBED)
    return body.cut(bore).union(knob)


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
