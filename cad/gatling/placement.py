"""部品の置き場所（高さ・半径・周上の点）。CadQuery を使わない素の数値計算。

形状（`shapes/`）と検査（`checks.py`）が同じ値を読むための唯一の置き場。形状と検査で別々に
計算すると、検査は通るのに形がずれる、が起きる。

座標系: 胴の軸が Z、ヘッドが上。**z = 0 はヘッダープレートの上面**（管の上端と同じ高さ）。
管は下（−z）へ伸びる。管 0 番は +X 方向、角度は反時計回り（度）。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .derived import MIL, derive
from .params import GatlingSpec


def ring_points(count: int, radius: float, phase_deg: float = 0.0) -> list[tuple[float, float]]:
    """半径 `radius` の円周を `count` 等分した点。0 番は `phase_deg` の方向。"""
    return [(radius * math.cos(math.radians(phase_deg + 360.0 * k / count)),
             radius * math.sin(math.radians(phase_deg + 360.0 * k / count))) for k in range(count)]


def tube_points(spec: GatlingSpec) -> list[tuple[float, float]]:
    return ring_points(int(float(spec.tube.count)), float(derive(spec).pcd) / 2)


def flange_bolt_points(spec: GatlingSpec) -> list[tuple[float, float]]:
    """フランジとヘッダープレートの M6 の穴。管に対して `bolt_phase` ずれる。"""
    return ring_points(int(float(spec.flange.bolt_count)), float(derive(spec).bolt_circle) / 2,
                       float(spec.flange.bolt_phase))


def tip_bolt_points(spec: GatlingSpec) -> list[tuple[float, float]]:
    """先端クランプの意匠ボルト。管の間（中心円の上、隣り合う管の真ん中）。"""
    n = int(float(spec.tube.count))
    return ring_points(n, float(derive(spec).pcd) / 2, 180.0 / n)


def lug_angles(spec: GatlingSpec) -> list[float]:
    """ラグ・テンションロッド・受金の方位（度）。0 番は管 0 番と同じ方向。"""
    n = int(float(spec.lug.count))
    return [360.0 * k / n for k in range(n)]


@dataclass(frozen=True)
class Levels:
    """z 座標（mm）。上から並べると受金 → フープ → ヘッド → 胴 → フランジ → ヘッダープレート → 管。"""

    ear_top: float            # 受金の上面
    hoop_top: float           # 内外リングの上端（揃える）
    head_top: float           # 膜の上面（= フレッシュフープの上端、内リングの下面）
    edge_top: float           # ベアリングエッジの頂部（= 膜の下面。§5.4 の「ヘッド面」）
    collar_bottom: float      # フレッシュフープの下端（胴とエッジ環の外側に垂れる）
    shell_top: float
    flange_top: float
    gasket_top: float
    header_bottom: float
    mid_top: float            # 中間クランプのヘッダー側の面
    mid_bottom: float
    tip_top: float            # 先端クランプのヘッダー側の面
    tip_bottom: float
    tube_tip: float
    hoop_bottom: float        # 内外リングの下端のうち低いほう
    lug_top: float
    lug_bottom: float
    band_bottom: float
    band_top: float
    frame_centre: float       # クレードルの水平フレームの厚みの中心


def levels(spec: GatlingSpec) -> Levels:
    t, c = spec.tube, spec.clamp
    length = float(t.length)
    gasket_top = float(spec.gasket.thickness)
    flange_top = gasket_top + float(spec.flange.thickness)
    shell_top = flange_top + float(spec.shell.plenum_height)
    edge_top = shell_top + float(spec.edge.height)
    head_top = edge_top + float(spec.head.film_mil) * MIL
    collar_bottom = head_top - float(spec.head.collar_height)
    hoop_top = head_top + float(spec.hoop.inner.height)
    hoop_bottom = hoop_top - max(float(spec.hoop.inner.height), float(spec.hoop.outer.height))
    lug_top = min(collar_bottom, hoop_bottom) - float(spec.hoop.takeup)
    mid_top = -float(c.mid_position) * length
    tip_bottom = -length + float(t.protrusion_ratio) * float(t.od)
    band_bottom = flange_top + float(spec.band.above_flange)
    return Levels(
        ear_top=hoop_top + float(spec.hoop.ear.thickness), hoop_top=hoop_top,
        head_top=head_top, edge_top=edge_top, collar_bottom=collar_bottom, shell_top=shell_top, flange_top=flange_top,
        gasket_top=gasket_top, header_bottom=-float(spec.header.thickness),
        mid_top=mid_top, mid_bottom=mid_top - float(c.mid_thickness),
        tip_top=tip_bottom + float(c.tip_thickness), tip_bottom=tip_bottom, tube_tip=-length,
        hoop_bottom=hoop_bottom, lug_top=lug_top, lug_bottom=lug_top - float(spec.lug.height),
        band_bottom=band_bottom, band_top=band_bottom + float(spec.band.bar.width),
        frame_centre=flange_top + float(spec.shell.plenum_height) / 2,
    )


@dataclass(frozen=True)
class Radii:
    """半径（mm）。"""

    shell: float
    rod: float                # ロッド（ラグのねじ）の中心
    hoop_in_inner: float
    hoop_in_outer: float
    hoop_out_inner: float
    hoop_out_outer: float
    band_inner: float
    band_outer: float
    frame_inner: float        # クレードルのフレーム内面（正方形の半幅）


def radii(spec: GatlingSpec) -> Radii:
    d = derive(spec)
    shell = float(d.shell_od) / 2
    hoop_in_inner = float(d.head_od) / 2 - float(spec.hoop.seat)          # フレッシュフープの上面に掛かる
    hoop_in_outer = hoop_in_inner + float(spec.hoop.inner.thickness)
    hoop_out_inner = hoop_in_outer + float(spec.hoop.gap)
    band_inner = shell + float(spec.band.rubber)
    band_outer = band_inner + float(spec.band.bar.thickness)
    return Radii(
        shell=shell, rod=shell + float(spec.lug.standoff),
        hoop_in_inner=hoop_in_inner, hoop_in_outer=hoop_in_outer,
        hoop_out_inner=hoop_out_inner, hoop_out_outer=hoop_out_inner + float(spec.hoop.outer.thickness),
        band_inner=band_inner, band_outer=band_outer, frame_inner=band_outer + float(spec.cradle.clearance),
    )
