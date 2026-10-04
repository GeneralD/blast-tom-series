"""部品どうしの干渉の検査。形状を作らずに、形状と同じ placement の値から平面形と z の範囲を作って重なりを見る。

`ear_clear` は受金とフレッシュフープの重なりを見る。
`issues()`（`checks.py`）から呼ぶ。ここでも形状は作らず、例外も投げない。
"""

from __future__ import annotations

import math

from drumcad.checks import Issue

from .derived import derive
from .params import GatlingSpec
from .placement import levels, radii
from .planar import EPS, z_overlap


def hoop_rings(spec: GatlingSpec) -> list[tuple[str, float, float, float]]:
    """フープの回転体の外半径と z の範囲（名前, 外半径, 下端, 上端）。

    外リングは管の環なので、外半径は管の外面、z は管の上端（= 内リングの上端）から下端まで。受金は内リングの外面から
    管の中心まで伸びる板で、外半径は外端の隅（管の中心半径と幅の半分の斜辺）。受金の z は外リングの範囲から外れうる
    （頭の高さ + 板厚が管の外径を超えると、受金の下面 = 上面 − 板厚が管の下端より下になる）ので、別に持つ。
    """
    z, r = levels(spec), radii(spec)
    return [
        ("内リング", r.hoop_in_outer, z.head_top, z.hoop_top),
        ("外リング（管）", r.hoop_out_outer, z.hoop_top - float(spec.hoop.outer.od), z.hoop_top),
        ("受金", math.hypot(r.hoop_out_centre, float(spec.hoop.ear.width) / 2), z.ear_bottom, z.ear_top),
    ]


def _round_parts(spec: GatlingSpec) -> list[tuple[str, float, float, float]]:
    """胴まわりの回転体の外半径と z の範囲（名前, 外半径, 下端, 上端）。平面視ではこの半径の円の内側を占めるとみなす。"""
    z, r = levels(spec), radii(spec)
    return [
        ("胴・エッジ環", r.shell, z.flange_top, z.edge_top),
        ("フレッシュフープ", r.collar, z.collar_bottom, z.head_top),
        *hoop_rings(spec),
        ("フランジ・ヘッダープレート", float(derive(spec).plate_od) / 2, z.header_bottom, z.flange_top),
    ]


def ear_clear(spec: GatlingSpec) -> list[Issue]:
    """受金が、フレッシュフープ（ヘッドのカラー。半径 `collar`、z は下端から膜面）に食い込まない。

    受金の内端は内リングの外面（円柱で切る）なので、平面視ではその半径より内側に入らない。受金の下面は膜面より下に出る
    ので、z はフレッシュフープの帯と重なる。内リングの外面がフレッシュフープの外面より内側（内リングを薄く、掛かりを
    大きくしたとき）だと、受金がカラーを食う。
    """
    z, r = levels(spec), radii(spec)
    name, radius, z0, z1 = next(part for part in _round_parts(spec) if part[0] == "フレッシュフープ")
    if z_overlap(z.ear_bottom, z.ear_top, z0, z1) and r.hoop_in_outer < radius - EPS:
        return [Issue(True, f"受金が{name}に食い込む（平面視で受金の内端 {r.hoop_in_outer:.2f} < 外半径 {radius:.2f}、z も重なる）")]
    return []
