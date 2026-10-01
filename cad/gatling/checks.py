"""寸法どうしの噛み合わせの検査（仕様 §5.3）。`issues(spec)` が契約の入口。

`_build` は `issues()` を `assembly()` より先に呼び、fatal があれば `assembly()` を呼ばない。
だから **ここでは形状を作らず、例外も投げない**。個数・規格表・正値の検査（`structure`）に
引っかかったら、その場で返す（`derive()` が `sin(180°/個数)` で割るため）。
"""

from __future__ import annotations

import math

from drumcad.checks import Issue
from drumcad.dims import walk
from drumcad.stock import nearest

from .fasteners import HOLDER_RODS, ROD_THREADS, SCREWS, lookup_holder, lookup_rod, lookup_screw
from .derived import derive
from .params import GatlingSpec
from .placement import flange_bolt_points, levels, radii, tube_points

EPS = 1e-6                    # 縁ちょうどの値が浮動小数の誤差で fatal にならないように
MIN_ENGAGEMENT = 0.75         # ねじ込み長 / 呼び径の下限（下回ると警告）
MIN_CRADLE_CLEARANCE = 5.0    # クレードルとフープの逃げがこれ未満なら警告（mm）

# 個数 → 下限。整数であること、かつ下限以上であること。
_COUNTS = {"tube.count": 3, "lug.count": 1, "flange.bolt_count": 1, "hoop.ear.count": 1}
_POSITIVE = (
    "head.fit_id", "head.film_mil", "head.collar_wall", "head.collar_height", "shell.thickness", "shell.plenum_height",
    "edge.angle", "edge.radius", "edge.height", "edge.width",
    "hoop.inner.thickness", "hoop.inner.height", "hoop.outer.thickness", "hoop.outer.height", "hoop.gap",
    "hoop.seat", "hoop.takeup", "hoop.ear.width", "hoop.ear.thickness",
    "lug.pitch", "lug.height", "lug.standoff", "lug.hole_dia", "lug.rod_length",
    "tube.od", "tube.thickness", "tube.length",
    "clamp.tip_thickness", "clamp.mid_thickness", "clamp.bolt_length",
    "header.thickness", "flange.thickness", "flange.bolt_seat", "flange.bolt_length", "plate.margin", "gasket.thickness",
    "band.bar.width", "band.bar.thickness", "band.bolt_length", "band.gap",
    "cradle.bar.width", "cradle.bar.thickness", "cradle.clearance", "cradle.handle_length", "cradle.grip_dia",
    "cradle.pad.width", "cradle.pad.depth", "cradle.pad.thickness", "mount.body_dia", "mount.body_height",
)
_NON_NEGATIVE = (
    "head.fit_clearance", "hoop.ear.hole_clearance", "header.hole_clearance",
    "tube.trim_allowance", "band.rubber", "band.above_flange", "plate.max_over_shell",
)
# Choice → 引く表。表に無い呼びは形が作れない。
_TABLES = {"flange.bolt": SCREWS, "clamp.bolt": SCREWS, "band.bolt": SCREWS, "lug.thread": ROD_THREADS, "mount.type": HOLDER_RODS}


def structure(spec: GatlingSpec) -> list[Issue]:
    """個数が整数・規格表にある呼び・正の寸法。これが通らないと後の計算が割れる。"""
    leaves = {path: leaf for path, leaf in walk(spec)}
    found = []
    for path, floor in _COUNTS.items():
        n = float(leaves[path])
        if not n.is_integer():
            found.append(Issue(True, f"{path} = {n:g} は整数でなければならない"))
        elif n < floor:
            found.append(Issue(True, f"{path} = {n:g} は {floor} 以上でなければならない"))
    for path, table in _TABLES.items():
        if leaves[path].value not in table:
            found.append(Issue(True, f"{path} = {leaves[path].value!r} は規格表（{', '.join(table)}）に無い"))
    found += [Issue(True, f"{p} = {float(leaves[p]):g} は正でなければならない")
              for p in _POSITIVE if not math.isfinite(float(leaves[p])) or float(leaves[p]) <= 0]
    found += [Issue(True, f"{p} = {float(leaves[p]):g} は 0 以上でなければならない")
              for p in _NON_NEGATIVE if not math.isfinite(float(leaves[p])) or float(leaves[p]) < 0]
    t, e, h = spec.tube, spec.edge, spec.head
    if float(t.thickness) * 2 >= float(t.od):
        found.append(Issue(True, f"管の肉厚 {float(t.thickness):g} が外径 {float(t.od):g} の半分以上で、穴が無い"))
    shell_od = float(h.fit_id) - float(h.fit_clearance)   # derive() と同じ式（derive() はここでは呼ばない）
    if 2 * float(spec.shell.thickness) >= shell_od:
        found.append(Issue(True, f"胴の肉厚 {float(spec.shell.thickness):g} が胴外径 {shell_od:g} の半分以上で、穴が無い"))
    if float(e.width) >= shell_od / 2:
        found.append(Issue(True, f"エッジ環の幅 {float(e.width):g} が胴の半径 {shell_od / 2:g} 以上で、内径が残らない"))
    flat = float(e.width) - float(e.radius)          # 頂部の面取りの内側に残るエッジ面の水平幅
    if (not 0 < float(e.angle) < 90 or flat <= 0 or float(e.radius) >= float(e.height)
            or flat * math.tan(math.radians(float(e.angle))) >= float(e.height)):
        found.append(Issue(True, "ベアリングエッジの形が成り立たない（角度は 0〜90°、幅 > R、R < 高さ、面の落ち < 高さ）"))
    return found


def _at_least(what: str, value: float, floor: float, fatal: bool = True) -> list[Issue]:
    """`value` が `floor` 以上であること（縁ちょうどは通す）。"""
    return [] if value >= floor - EPS else [Issue(fatal, f"{what}（{value:.2f} < {floor:.2f}）")]


def _at_most(what: str, value: float, ceiling: float, fatal: bool = True) -> list[Issue]:
    return [] if value <= ceiling + EPS else [Issue(fatal, f"{what}（{value:.2f} > {ceiling:.2f}）")]


def tubes_apart(gap_ratio: float) -> list[Issue]:
    """管同士が干渉しない（隙間比 > 0）。"""
    return [] if gap_ratio > 0 else [Issue(True, f"管同士が干渉する（tube.gap_ratio = {gap_ratio:g} は正でなければならない）")]


def plate_size(plate_od: float, shell_id: float, shell_od: float, max_over_shell: float) -> list[Issue]:
    """ヘッダープレートの外径が胴内径以上（蓋になる）で、胴外径 + 上限以下。"""
    return (_at_least("ヘッダープレートが胴の内径より小さく、蓋にならない", plate_od, shell_id)
            + _at_most("ヘッダープレートが大きすぎる（胴外径 + 上限を超える）", plate_od, shell_od + max_over_shell))


def bolt_clearances(spec: GatlingSpec) -> list[Issue]:
    """フランジのボルト穴: 管外面・板縁・胴への距離が縁以上、管の方位からずれている。"""
    d, margin = derive(spec), float(spec.plate.margin)
    od, screw = float(spec.tube.od), lookup_screw(spec.flange.bolt)
    bolts, tubes = flange_bolt_points(spec), tube_points(spec)
    to_tube = min(math.hypot(bx - tx, by - ty) for bx, by in bolts for tx, ty in tubes) - od / 2
    to_edge = float(d.plate_od) / 2 - float(d.bolt_circle) / 2
    to_shell = float(spec.flange.bolt_seat) - float(screw.head_dia) / 2
    pitch = 360.0 / float(spec.tube.count)
    shifted = abs(((float(spec.flange.bolt_phase) + pitch / 2) % pitch) - pitch / 2) > EPS
    found = (_at_least("ボルト穴と管外面の距離が縁に足りない", to_tube, margin)
             + _at_least("ボルト穴と板縁の距離が縁に足りない", to_edge, margin)
             + _at_least("ボルトの頭が胴の外面にかかる（ボルト座が頭の半径に足りない）", to_shell, 0.0))
    if not shifted:
        found.append(Issue(True, f"フランジのボルトが管と同じ方位にある（bolt_phase = {float(spec.flange.bolt_phase):g}° は管の間隔 {pitch:g}° の倍数）"))
    return found


def tubes_inside_bore(spec: GatlingSpec) -> list[Issue]:
    """管の外面が胴の内径に収まる。はみ出すとフランジが管の開口を塞ぐ（警告）。"""
    d = derive(spec)
    reach = float(d.pcd) / 2 + float(spec.tube.od) / 2
    return _at_most("管の外面が胴の内径からはみ出し、開口の一部をフランジが塞ぐ", reach, float(d.shell_id) / 2, fatal=False)


def tube_clamps(spec: GatlingSpec) -> list[Issue]:
    """先端の突き出しが 0 以上、中間クランプの比が 0〜1、中間クランプがヘッダープレートにも先端クランプにも重ならない。"""
    z, c = levels(spec), spec.clamp
    found = _at_least("先端クランプの突き出しが負", float(spec.tube.protrusion_ratio), 0.0)
    found += _at_least("中間クランプの位置の比が 0 未満", float(c.mid_position), 0.0)
    found += _at_most("中間クランプの位置の比が 1 を超える", float(c.mid_position), 1.0)
    found += _at_least("中間クランプがヘッダープレートに重なる（ヘッダー下面と中間クランプの距離）", z.header_bottom - z.mid_top, 0.0)
    found += _at_least("中間クランプが先端クランプに重なる（クランプ間の距離）", z.mid_bottom - z.tip_top, 0.0)
    d = derive(spec)
    found += _at_least("中間クランプ中央の穴径が 0 以下（管が詰まりすぎ）", float(d.clamp_hole_d), EPS)
    return found
