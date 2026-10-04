"""付け根の曲げの概算（D-22）。検査ではなく、仕様と決定ログの根拠。形は作らず、`placement` と `params` の値から計算する。

ドラム全体を後ろのホルダーだけで支えるとき、荷重（質量 × g）が胴の中心から `arm.rear` の腕の元に掛かる。左右の付け根
（当て板 1 枚と腕の始まり）が 1 か所あたり受ける曲げモーメントは、総モーメントの半分とする（左右対称）。
衝撃係数を掛けた値も出す。腕の管の曲げ応力と、当て板の上下の縁が受ける偶力（モーメント / 板の高さ）は、
当て板の大きさと板厚の目安に使う。

`derived.py` は `placement` から import されるので、`placement` を読むこの計算は `derived.py` に置けない（循環する）。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from drumcad.dims import Dim

from .derived import derived_from
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
    pad_edge_force: Dim      # 当て板の上下の縁の偶力（N）= モーメント / 板の高さ
    pad_edge_force_impact: Dim


def root_load(spec: GatlingSpec) -> RootLoad:
    lever = abs(holder_centre(spec)[1])
    moment = float(spec.load.mass) * G * lever / 2
    impact = float(spec.load.impact)
    od, wall = float(spec.arm.pipe.od), float(spec.arm.pipe.thickness)
    modulus = math.pi * (od ** 4 - (od - 2 * wall) ** 4) / (32 * od)
    height = float(spec.pad.height)
    inputs = {"load.mass": spec.load.mass, "load.impact": spec.load.impact, "arm.rear": spec.arm.rear,
              "arm.pipe.od": spec.arm.pipe.od, "arm.pipe.thickness": spec.arm.pipe.thickness, "pad.height": spec.pad.height}

    def make(value: float, note: str) -> Dim:
        return derived_from(value, note, inputs)

    return RootLoad(
        lever=make(lever, "ホルダーから胴の中心まで = arm.rear"),
        moment=make(moment, "質量 × g × 距離 / 2"),
        moment_impact=make(moment * impact, "質量 × g × 距離 / 2 × 衝撃係数"),
        section_modulus=make(modulus, "π(D⁴ − d⁴) / (32 D)"),
        pipe_stress=make(moment / modulus, "モーメント / 断面係数"),
        pipe_stress_impact=make(moment * impact / modulus, "衝撃込みのモーメント / 断面係数"),
        pad_edge_force=make(moment / height, "モーメント / 板の高さ"),
        pad_edge_force_impact=make(moment * impact / height, "衝撃込みのモーメント / 板の高さ"),
    )
