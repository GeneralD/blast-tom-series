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
