"""付け根の曲げの概算（D-22）。検査ではなく、仕様と決定ログの根拠。形は作らず、`placement` と `params` の値から計算する。

ドラム全体を後ろのホルダーだけで支えるとき、荷重（質量 × g）が胴の中心から `arm.rear` の腕の元に掛かる。左右の付け根
（当て板 1 枚と腕の始まり）が 1 か所あたり受ける曲げモーメントは、総モーメントの半分とする（左右対称）。
衝撃係数を掛けた値も出す。腕の管の曲げ応力と、当て板が受ける力は、当て板の大きさと板厚の目安に使う。
ホルダーは当て板の中心からほぼ半径方向に揃う（接線方向にずれるのは小さい）ので、当て板のモーメントの大半は、板の面内
（板の面に垂直な軸まわり）のねじりになる。溶接線にはその偶力が、左右（周方向）の縁の間隔 = 板幅で掛かる。上下の縁を引き剥がす
向きのモーメントではない。ほかに鉛直せん断（質量 × g / 2）が付け根 1 か所に掛かる。

`derived.py` は `placement` から import されるので、`placement` を読むこの計算は `derived.py` に置けない（循環する）。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from drumcad.dims import Dim, derived_from

from .params import GatlingSpec
from .placement import holder_centre

G = 9.80665                  # m/s²


@dataclass(frozen=True)
class RootLoad:
    """付け根 1 か所あたりの値。モーメントは N·mm、応力は MPa、力は N。入力の葉に仮があれば仮（`derived_from`）。"""

    lever: Dim               # ホルダー（後ろの横渡し）から胴の中心までの距離（mm）
    moment: Dim              # 1 か所あたりの曲げモーメント = 質量 × g × 距離 / 2
    moment_impact: Dim       # 衝撃係数を掛けた値
    section_modulus: Dim     # 腕の管の断面係数 π(D⁴ − d⁴) / (32 D)（mm³）
    pipe_stress: Dim         # 管の曲げ応力（MPa）= モーメント / 断面係数
    pipe_stress_impact: Dim
    pad_edge_force: Dim      # 当て板の面内のねじりの偶力（N）= モーメント / 板幅。左右（周方向）の縁で受ける
    pad_edge_force_impact: Dim
    shear: Dim               # 付け根 1 か所の鉛直せん断（N）= 質量 × g / 2
    shear_impact: Dim


def root_load(spec: GatlingSpec) -> RootLoad:
    lever = abs(holder_centre(spec)[1])
    moment = float(spec.load.mass) * G * lever / 2
    impact = float(spec.load.impact)
    od, wall = float(spec.arm.pipe.od), float(spec.arm.pipe.thickness)
    modulus = math.pi * (od ** 4 - (od - 2 * wall) ** 4) / (32 * od)
    width = float(spec.pad.width)
    weight = float(spec.load.mass) * G
    inputs = {"load.mass": spec.load.mass, "load.impact": spec.load.impact, "arm.rear": spec.arm.rear,
              "arm.pipe.od": spec.arm.pipe.od, "arm.pipe.thickness": spec.arm.pipe.thickness, "pad.width": spec.pad.width}

    def make(value: float, note: str) -> Dim:
        return derived_from(value, note, inputs)

    return RootLoad(
        lever=make(lever, "ホルダーから胴の中心まで = arm.rear"),
        moment=make(moment, "質量 × g × 距離 / 2"),
        moment_impact=make(moment * impact, "質量 × g × 距離 / 2 × 衝撃係数"),
        section_modulus=make(modulus, "π(D⁴ − d⁴) / (32 D)"),
        pipe_stress=make(moment / modulus, "モーメント / 断面係数"),
        pipe_stress_impact=make(moment * impact / modulus, "衝撃込みのモーメント / 断面係数"),
        pad_edge_force=make(moment / width, "モーメント / 板幅（面内のねじりを左右の縁で受ける）"),
        pad_edge_force_impact=make(moment * impact / width, "衝撃込みのモーメント / 板幅"),
        shear=make(weight / 2, "質量 × g / 2"),
        shear_impact=make(weight / 2 * impact, "質量 × g / 2 × 衝撃係数"),
    )
