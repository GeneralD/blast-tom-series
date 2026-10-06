"""導出値（仕様 §5.2「導出値」）と機種名。SPEC には持たず、`derive(spec)` がそのつど計算する。

SPEC に導出値を葉として持たせると、`override()` で入力を振っても導出値が古いまま残り、
`as_provisional` は `init=False` の葉を `TypeError` で止める。計算で出すなら、入力の出典を
辿って「仮の入力があれば仮」を自前で決める必要がある（`dims.derived()` は入力を見ない）。
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from drumcad.dims import Choice, Dim, derived, provisional

from .params import GatlingSpec


def derived_from(value: float, note: str, inputs: Mapping[str, Dim | Choice]) -> Dim:
    """導出値。入力の葉に仮が 1 つでもあれば仮、無ければ導出（仕様 §5.2）。

    `dims.derived()` は入力を見ずに常に `Source.DERIVED` を返す（`Dim` の算術は素の float に落ちて
    出典が消える）。そのまま使うと、仮のヘッドから導いた胴外径が確定に化ける。
    """
    pending = [path for path, leaf in inputs.items() if not leaf.source.is_settled]
    if pending:
        return provisional(value, f"{note}（仮の入力: {', '.join(pending)}）")
    return derived(value, note)


@dataclass(frozen=True)
class Derived:
    """§5.2 の導出値。mm（`areal_density` だけ g/mm²）。"""

    shell_od: Dim
    shell_id: Dim
    head_od: Dim             # フレッシュフープの外径
    areal_density: Dim       # 膜の面密度（膜厚 × `FILM_DENSITY`。コーティングは含めない）
    tube_pitch: Dim          # 管の中心間
    pcd: Dim                 # 管の中心円の直径
    bolt_circle: Dim
    plate_od: Dim            # ヘッダープレート・フランジ・ガスケットの外径
    clamp_od: Dim            # 管クランプの外径
    clamp_hole_d: Dim        # 中間クランプ中央の穴径
    tube_cut_length: Dim     # 製作時の管の切り出し長（切り詰め代を含む）


FILM_DENSITY = provisional(1.39e-3, "PET フィルムの一般値（g/mm³）。コーティングは含めない（PR 4）")
MIL = 0.0254                 # mm
_DENSITY_NOTE = f"膜厚 × {float(FILM_DENSITY) * 1e3:g} g/cm³"     # g/mm³ → g/cm³ は × 1000


def shell_od(spec: GatlingSpec) -> float:
    """胴外径 = フレッシュフープ内径 − 逃げ。個数に依存しないので、`tube.count = 0` でも割らない（`derive`・`name`・`structure` が共有する）。"""
    return float(spec.head.fit_id) - float(spec.head.fit_clearance)


def derive(spec: GatlingSpec) -> Derived:
    """寸法から導出値を計算する。PCD = 中心間 / sin(180° / 本数) なので、`tube.count` が 3 未満だと
    周囲配置にならない（0 は `ZeroDivisionError`、1 は sin(180°) ≈ 0 で割って巨大な値、2 は PCD が中心間と
    等しく 2 本が向かい合うだけ）。`issues()` は `structure()` で 3 未満を fatal にして、ここへ来る前に返す。
    `name()` は `issues()` より先に呼ばれるので、これを使わない。"""
    h, t, f, p = spec.head, spec.tube, spec.flange, spec.plate
    n = float(t.count)
    outer = shell_od(spec)
    shell_id = outer - 2 * float(spec.shell.thickness)
    head_od = float(h.fit_id) + 2 * float(h.collar_wall)
    pitch = float(t.od) * (1 + float(t.gap_ratio))
    pcd = pitch / math.sin(math.pi / n)
    bolt_circle = outer + 2 * float(f.bolt_seat)
    margin = float(p.margin)
    tube_ring = pcd + float(t.od) + 2 * margin
    shell_in = {"head.fit_id": h.fit_id, "head.fit_clearance": h.fit_clearance}
    pitch_in = {"tube.od": t.od, "tube.gap_ratio": t.gap_ratio}
    tube_in = {**pitch_in, "tube.count": t.count}
    return Derived(
        shell_od=derived_from(outer, "フレッシュフープ内径 − 逃げ", shell_in),
        shell_id=derived_from(shell_id, "胴外径 − 2 × 肉厚", {**shell_in, "shell.thickness": spec.shell.thickness}),
        head_od=derived_from(head_od, "フレッシュフープ内径 + 2 × 肉厚",
                             {"head.fit_id": h.fit_id, "head.collar_wall": h.collar_wall}),
        areal_density=derived_from(float(h.film_mil) * MIL * float(FILM_DENSITY), _DENSITY_NOTE,
                                   {"head.film_mil": h.film_mil, "FILM_DENSITY": FILM_DENSITY}),
        tube_pitch=derived_from(pitch, "od × (1 + gap_ratio)", pitch_in),
        pcd=derived_from(pcd, "中心間 / sin(180° / 本数)", tube_in),
        bolt_circle=derived_from(bolt_circle, "胴外径 + 2 × ボルト座", {**shell_in, "flange.bolt_seat": f.bolt_seat}),
        plate_od=derived_from(max(tube_ring, bolt_circle + 2 * margin, outer),
                              "max(PCD + od + 2 × 縁, ボルト円 + 2 × 縁, 胴外径)",
                              {**shell_in, **tube_in, "flange.bolt_seat": f.bolt_seat, "plate.margin": p.margin}),
        clamp_od=derived_from(max(tube_ring, outer), "max(PCD + od + 2 × 縁, 胴外径)",
                              {**shell_in, **tube_in, "plate.margin": p.margin}),
        clamp_hole_d=derived_from(pcd - float(t.od) - 2 * margin, "PCD − od − 2 × 縁",
                                  {**tube_in, "plate.margin": p.margin}),
        tube_cut_length=derived_from(float(t.length) + float(t.trim_allowance), "管長 + 切り詰め代",
                                     {"tube.length": t.length, "tube.trim_allowance": t.trim_allowance}),
    )


def name(spec: GatlingSpec) -> str:
    """出力ディレクトリ名の語幹。`gatling-<径 inch>-<ラグ数>`。

    `derive()` は呼ばない。`build._build` は `issues()` より先に `name()` を呼ぶので、`derive()` の
    `math.pi / n` を通すと `tube.count = 0` が構造の検査（fatal）に届く前に `ZeroDivisionError` になる。
    胴外径だけを `shell_od()` で出す。
    """
    inch = round(shell_od(spec) / 25.4)
    return f"gatling-{inch}-{int(float(spec.lug.count))}"
