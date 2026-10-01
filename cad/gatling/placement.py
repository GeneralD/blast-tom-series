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
from .fasteners import lookup_screw
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
    """z 座標（mm）。

    前半（`ear_top` 〜 `tube_tip`）は軸の上に積む部品の高さで、上から順（受金 → フープ → ヘッド → エッジ → 胴 →
    フランジ → ガスケット → ヘッダープレート → 管とクランプ）。後半（`hoop_bottom` 以降）はフープの下端と、
    胴の脇に付く部品（ラグ・胴バンド・クレードル・当て板・ホルダー受け）の高さで、上下の順には並べていない。
    """

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
    band_centre: float        # 胴バンドの高さの中心（耳のボルト、クレードルの脚の下端と腕の厚みの中心）
    frame_centre: float       # クレードルの水平フレームの厚みの中心
    frame_top: float          # フレームの上面（= 当て板の下面）
    pad_top: float            # 当て板の上面（= ホルダー受けの下面）
    holder_bottom: float
    holder_top: float


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
    frame_centre = flange_top + float(spec.shell.plenum_height) / 2
    frame_top = frame_centre + float(spec.cradle.bar.thickness) / 2
    pad_top = frame_top + float(spec.cradle.pad.thickness)
    return Levels(
        ear_top=hoop_top + float(spec.hoop.ear.thickness), hoop_top=hoop_top,
        head_top=head_top, edge_top=edge_top, collar_bottom=collar_bottom, shell_top=shell_top, flange_top=flange_top,
        gasket_top=gasket_top, header_bottom=-float(spec.header.thickness),
        mid_top=mid_top, mid_bottom=mid_top - float(c.mid_thickness),
        tip_top=tip_bottom + float(c.tip_thickness), tip_bottom=tip_bottom, tube_tip=-length,
        hoop_bottom=hoop_bottom, lug_top=lug_top, lug_bottom=lug_top - float(spec.lug.height),
        band_bottom=band_bottom, band_top=band_bottom + float(spec.band.bar.width),
        band_centre=band_bottom + float(spec.band.bar.width) / 2,
        frame_centre=frame_centre, frame_top=frame_top, pad_top=pad_top,
        holder_bottom=pad_top, holder_top=pad_top + float(spec.mount.body_height),
    )


@dataclass(frozen=True)
class Radii:
    """半径（mm）。"""

    shell: float
    collar: float             # フレッシュフープの外面（ヘッド外径の半分）
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
        shell=shell, collar=float(d.head_od) / 2, rod=shell + float(spec.lug.standoff),
        hoop_in_inner=hoop_in_inner, hoop_in_outer=hoop_in_outer,
        hoop_out_inner=hoop_out_inner, hoop_out_outer=hoop_out_inner + float(spec.hoop.outer.thickness),
        band_inner=band_inner, band_outer=band_outer, frame_inner=band_outer + float(spec.cradle.clearance),
    )


def lug_box(spec: GatlingSpec) -> tuple[float, float, float, float]:
    """ラグの箱の平面形（ラグの局所座標）。u は胴の中心からラグの方位へ、v はそれに直交（反時計回りが正）。

    (u0, u1, v0, v1) = (胴外面, 胴外面 + 2 × standoff, −standoff, standoff)。ロッドは箱の中心（u = `rod`）を通る。
    方位 a のラグの平面座標は x = u cos a − v sin a、y = u sin a + v cos a（`lug_angles` の向き）。
    """
    shell, stand = float(derive(spec).shell_od) / 2, float(spec.lug.standoff)
    return shell, shell + 2 * stand, -stand, stand


def band_tab_length(spec: GatlingSpec) -> float:
    """胴バンドの耳（締め付け部）の長さ。ボルトの頭が収まるよう、頭径の 2 倍にする。"""
    return 2 * float(lookup_screw(spec.band.bolt).head_dia)


def band_bolt_x(spec: GatlingSpec) -> float:
    """胴バンドのボルトの X 位置（耳の中央、+X 側。−X 側は符号を反転）。"""
    return radii(spec).band_outer + band_tab_length(spec) / 2


def cradle_y_rear(spec: GatlingSpec) -> float:
    """クレードルの後側の横桟の中心の Y 位置（ヘッドの手前を +Y、後ろを −Y とする）。当て板とホルダー受けの中心もここ。"""
    return -(radii(spec).frame_inner + float(spec.cradle.bar.width) / 2)


def grip_y(spec: GatlingSpec) -> float:
    """ハンドルのグリップ（X 方向の丸棒）の中心の Y 位置。フレームの外面から `handle_length` 後ろ。"""
    return -(radii(spec).frame_inner + float(spec.cradle.bar.width)) - float(spec.cradle.handle_length)


def cradle_corner(spec: GatlingSpec) -> float:
    """クレードルの脚（4 隅）の中心までの、胴の中心からの距離。腕はここから対角線に沿って胴バンドの外面まで伸びる。"""
    return (radii(spec).frame_inner + float(spec.cradle.bar.width) / 2) * math.sqrt(2)
