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
from .planar import Point, rect
from .tubepath import Path, Vec, fillet, plan_polygons, tangent_length, turn_angle

# 当て板とスペードグリップは左右 1 枚（本）ずつ（D-22）。+X 側と −X 側の符号でループし、員数は `PAD_COUNT` で数える。
PAD_SIDES = (1, -1)
PAD_COUNT = len(PAD_SIDES)        # 当て板の枚数 = スペードグリップの本数（左右対称）

# ラグは胴にねじ 1 本で留める（D-21）。胴の取付穴はラグ 1 個につき、ラグの高さ（= 円盤の径）の中心に 1 つ。
# 値は穴の位置の円盤の中心からの比（円盤の径 × 値だけ上）。形は符号でループし、員数は `LUG_HOLES` で数える。
LUG_HOLE_SIDES = (0,)
LUG_HOLES = len(LUG_HOLE_SIDES)


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

    前半（`hoop_top` 〜 `tube_tip`）は軸の上に積む部品の高さで、上から順（フープ → 受金 → ヘッド → エッジ → 胴 →
    フランジ → ガスケット → ヘッダープレート → 管とクランプ）。後半（`pipe_centre` 以降）は外リングの管・フープの
    下端・テンションロッドと、胴の脇に付く部品（ラグ・当て板・腕・ホルダー受け）の高さで、
    上下の順には並べていない。
    """

    hoop_top: float           # 内リングの上端 = 外リングの管の上端（揃える）。膜面からの高さがリムの高さ（inner.height）
    ear_top: float            # 受金の上面（= フープの上端 − ロッドの頭の高さ。ロッドの頭の上面がリムの上端に揃う）
    ear_bottom: float         # 受金の下面（受金の上面 − 板厚。膜面より下、フレッシュフープの外側に出てよい）
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
    pipe_centre: float        # 外リングの管の中心の高さ（= フープの上端 − 管の外径 / 2）
    hoop_bottom: float        # フープの下端（内リングの下面と管の下端のうち低いほう）
    rod_top: float            # テンションロッドの頭の上面（頭は受金の上面に載る）
    rod_tip: float            # テンションロッドの軸の先（受金の上面から rod_length 下）
    lug_top: float
    lug_bottom: float
    arm_centre: float         # 腕の管の中心の高さ。当て板の高さの中心も同じ（プレナム胴の中ほど）
    arm_bottom: float
    arm_top: float
    pad_bottom: float
    pad_top: float
    block_top: float          # ブロックの上面（= 管の中心 + ブロックの高さ。ホルダー受けの下面）
    holder_bottom: float
    holder_top: float
    knob_centre: float        # つまみの軸の高さ（ホルダー受けの高さの中心）

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
    pipe = float(spec.hoop.outer.od)
    hoop_bottom = min(head_top, hoop_top - pipe)
    # 受金の z はここ 1 か所で決める: ロッドの頭の上面（受金の上面 + 頭の高さ）をリムの上端に揃え、受金はそこから下へ板厚ぶん
    ear_top = hoop_top - float(spec.lug.rod_head_height)
    ear_bottom = ear_top - float(spec.hoop.ear.thickness)
    lug_top = min(collar_bottom, hoop_bottom) - float(spec.hoop.takeup)
    mid_top = -float(c.mid_position) * length
    tip_bottom = -length + float(t.protrusion_ratio) * float(t.od)
    arm_centre = flange_top + float(spec.shell.plenum_height) / 2
    arm_r = float(spec.arm.pipe.od) / 2
    block_top = arm_centre + float(spec.block.height)
    holder_top = block_top + float(spec.mount.body_height)
    return Levels(
        hoop_top=hoop_top, ear_top=ear_top, ear_bottom=ear_bottom, head_top=head_top, edge_top=edge_top, collar_bottom=collar_bottom, shell_top=shell_top, flange_top=flange_top,
        gasket_top=gasket_top, header_bottom=-float(spec.header.thickness),
        mid_top=mid_top, mid_bottom=mid_top - float(c.mid_thickness),
        tip_top=tip_bottom + float(c.tip_thickness), tip_bottom=tip_bottom, tube_tip=-length,
        pipe_centre=hoop_top - pipe / 2, hoop_bottom=hoop_bottom,
        rod_top=ear_top + float(spec.lug.rod_head_height), rod_tip=ear_top - float(spec.lug.rod_length), lug_top=lug_top, lug_bottom=lug_top - float(spec.lug.body_dia),
        arm_centre=arm_centre, arm_bottom=arm_centre - arm_r, arm_top=arm_centre + arm_r,
        pad_bottom=arm_centre - float(spec.pad.height) / 2, pad_top=arm_centre + float(spec.pad.height) / 2,
        block_top=block_top, holder_bottom=block_top, holder_top=holder_top, knob_centre=(block_top + holder_top) / 2,
    )


@dataclass(frozen=True)
class Radii:
    """半径（mm）。"""

    shell: float
    collar: float             # フレッシュフープの外面（ヘッド外径の半分）
    rod: float                # ロッド（ラグのねじ）の中心
    hoop_in_inner: float      # 内リングの内面
    hoop_in_outer: float      # 内リングの外面（= 受金の内端）
    hoop_out_inner: float     # 外リングの管の内側の接線（管の中心の高さで最も軸に近い所）
    hoop_out_centre: float    # 外リングの管の中心（= 受金の外端）
    hoop_out_outer: float     # 外リングの管の外面
    pad_outer: float          # 当て板の外面（= 腕の付け根の高さでの、腕の管の始まり）


def radii(spec: GatlingSpec) -> Radii:
    d = derive(spec)
    shell = float(d.shell_od) / 2
    hoop_in_inner = float(d.head_od) / 2 - float(spec.hoop.seat)          # フレッシュフープの上面に掛かる
    hoop_in_outer = hoop_in_inner + float(spec.hoop.inner.thickness)
    hoop_out_inner = hoop_in_outer + float(spec.hoop.gap)
    pipe = float(spec.hoop.outer.od)
    return Radii(
        shell=shell, collar=float(d.head_od) / 2, rod=shell + float(spec.lug.standoff),
        hoop_in_inner=hoop_in_inner, hoop_in_outer=hoop_in_outer,
        hoop_out_inner=hoop_out_inner, hoop_out_centre=hoop_out_inner + pipe / 2, hoop_out_outer=hoop_out_inner + pipe,
        pad_outer=shell + float(spec.pad.thickness),
    )


def pipe_inner_radius(spec: GatlingSpec, z0: float, z1: float) -> float:
    """外リングの管の外面のうち、胴の軸の側の半径を、z の帯 [z0, z1] の中で最も小さい所で返す。

    管の断面は中心 (`hoop_out_centre`, `pipe_centre`)、半径 = 外径 / 2 の円。帯が管の中心の高さを含めば内側の接線
    （`hoop_out_inner`）、含まなければ中心に近い端の高さでの値。帯が管に掛からなければ無限大（当たる相手が無い）。
    ロッドの軸と頭が管に当たらないかを見るのに使う（`checks.rod_fits`）。
    """
    z, r = levels(spec), radii(spec)
    half = float(spec.hoop.outer.od) / 2
    d = max(z0 - z.pipe_centre, z.pipe_centre - z1, 0.0)
    if d >= half:
        return math.inf
    return r.hoop_out_centre - math.sqrt(half * half - d * d)


def lug_plan(spec: GatlingSpec, z0: float | None = None, z1: float | None = None) -> tuple[float, float, float, float]:
    """ラグの円盤の平面形（ラグの局所座標の矩形 (u0, u1, v0, v1)。干渉の検査用。形と同じ葉から作る）。

    u は胴の中心からラグの方位へ、v はそれに直交（反時計回りが正）。円盤は軸が u の円柱（半径 b = body_dia / 2、中心の高さ
    `zc`）で、胴の外面から `depth` だけ外へ出る。外側の面は平面 u = 胴の半径 + depth。胴側は胴の外面の円柱で切られ、側縁
    （v = ±半幅）では胴に u = √(R² − 半幅²) < R で触れる。矩形の u0 はそこまで広げる（形から出る三日月を取りこぼさない）。

    `z0`, `z1` を渡すと、円盤のうちその z の帯に入る薄片だけの平面形になる。円盤は円柱なので、帯が `zc` から離れるほど細く、
    半幅 = √(b² − 帯と zc の最短距離²)。帯が `zc` を含めば全幅 b。帯と円盤が重なることは呼び出し側が先に確かめる。
    方位 a のラグの平面座標は x = u cos a − v sin a、y = u sin a + v cos a（`lug_angles` の向き）。
    """
    s, z = spec.lug, levels(spec)
    shell = float(derive(spec).shell_od) / 2
    b = float(s.body_dia) / 2
    if z0 is None or z1 is None:
        half = b
    else:
        zc = (z.lug_top + z.lug_bottom) / 2
        lo, hi = max(z0, z.lug_bottom), min(z1, z.lug_top)
        d = 0.0 if lo <= zc <= hi else min(abs(lo - zc), abs(hi - zc))
        half = math.sqrt(max(b * b - d * d, 0.0))
    return math.sqrt(max(shell * shell - half * half, 0.0)), shell + float(s.depth), -half, half


def pad_angles(spec: GatlingSpec) -> list[float]:
    """当て板の方位（度）。+X 側は ±X 軸から後ろ（−Y）へ `pad.angle` 回した向き、−X 側はその左右対称（Y 軸に対する鏡像）。"""
    angle = float(spec.pad.angle)
    return [(-angle) % 360.0, (180.0 + angle) % 360.0]


def pad_plan(spec: GatlingSpec) -> tuple[float, float, float, float]:
    """当て板の平面形（板の局所座標の矩形 (u0, u1, v0, v1)。干渉の検査用。形と同じ葉から作る）。

    u は胴の中心から板の方位へ、v はそれに直交。形は幅 `width`（v）の矩形の柱を、胴の外面から板厚ぶんの円筒殻で切ったもの。
    外側は半径 R + 板厚の円で切られる。胴側は胴の外面の円で切られ、側縁（v = ±半幅）では u = √(R² − 半幅²) < R で胴に触れる。
    矩形の u0 はそこまで広げる（`lug_plan` と同じ。形から出る三日月を取りこぼさない）。
    """
    shell, half = radii(spec).shell, float(spec.pad.width) / 2
    return math.sqrt(max(shell * shell - half * half, 0.0)), radii(spec).pad_outer, -half, half


def pad_polys(spec: GatlingSpec) -> list[list[Point]]:
    """当て板（左右）の平面形。方位ごとに `pad_plan` の矩形を回した凸多角形。"""
    return [rect(*pad_plan(spec), a) for a in pad_angles(spec)]


def arm_vertices(spec: GatlingSpec) -> list[Vec]:
    """腕の中心線の折れ線の頂点（丸める前）。右の当て板の外面 → 右の最初の曲がり → 右の後ろの角 → 左の後ろの角 → 左の最初の曲がり
    → 左の当て板の外面。

    右の当て板は方位 −`pad.angle` の半径方向の線の上にあり、腕はその外面から半径方向に `stub` 進んだ頂点で後ろ（−Y）へ折れ、
    `rear` の高さで横（−X）へ折れて左へ渡る。左は Y 軸に対する鏡像。
    """
    angle = math.radians(float(spec.pad.angle))
    direction = (math.cos(angle), -math.sin(angle))
    start, corner = radii(spec).pad_outer, radii(spec).pad_outer + float(spec.arm.stub)
    first = (corner * direction[0], corner * direction[1])
    right = [(start * direction[0], start * direction[1]), first, (first[0], -float(spec.arm.rear))]
    return right + [(-x, y) for x, y in right[::-1]]


def arm_path(spec: GatlingSpec) -> Path:
    """腕の中心線の経路（直線・円弧・直線…。曲げ半径 `arm.bend_radius` で 4 か所を丸めたもの）。

    添字は固定: 0 直線（右の当て板→最初の曲げ）、1 円弧（右の最初の曲げ）、2 直線（右の脚）、3 円弧（右の後ろの角）、
    4 直線（横渡し）、5 円弧（左の後ろの角）、6 直線（左の脚）、7 円弧（左の最初の曲げ）、8 直線（左の当て板へ）。
    """
    return fillet(arm_vertices(spec), float(spec.arm.bend_radius))


def arm_polys(spec: GatlingSpec) -> list[list[Point]]:
    """腕（管）の平面形を覆う凸多角形。直線は厳密な矩形、曲げは細かく分けた四角形（`tubepath.plan_polygons`）。"""
    return plan_polygons(arm_path(spec), float(spec.arm.pipe.od) / 2)


@dataclass(frozen=True)
class ArmBends:
    """腕の曲げが脚に収まるかを見る長さ（mm）。負なら、その曲げの接点が隣の曲げか当て板の内側に入る。"""

    stub_free: float          # 当て板の外面から最初の曲げの接点までの直線の長さ（= stub − 接線の長さ）
    leg_free: float           # 後ろへの脚の直線の長さ（最初の曲げの接点から後ろの角の接点まで）
    cross_half: float         # 横渡しの直線部の長さの半分（中央から後ろの角の接点まで）


def arm_bends(spec: GatlingSpec) -> ArmBends:
    v, rb = arm_vertices(spec), float(spec.arm.bend_radius)
    first = tangent_length(turn_angle(v[0], v[1], v[2]), rb)
    corner = tangent_length(turn_angle(v[1], v[2], v[3]), rb)
    return ArmBends(stub_free=math.dist(v[0], v[1]) - first, leg_free=math.dist(v[1], v[2]) - first - corner,
                    cross_half=abs(v[2][0]) - corner)


def holder_centre(spec: GatlingSpec) -> Point:
    """ホルダー受け・ブロックの中心（平面）。後ろの横渡しの中央。"""
    return 0.0, -float(spec.arm.rear)


def block_plan(spec: GatlingSpec) -> list[Point]:
    """ブロックの平面形（矩形）。"""
    b, y = spec.block, holder_centre(spec)[1]
    return rect(-float(b.width) / 2, float(b.width) / 2, y - float(b.depth) / 2, y + float(b.depth) / 2)


def knob_plan(spec: GatlingSpec) -> list[Point]:
    """つまみ（ホルダー受けの後ろへ水平に出る円柱）の平面形。本体の外面から 1 mm 食い込ませて（形は 1 つにつなぐ）、`knob_length` 出す。"""
    m, y = spec.mount, holder_centre(spec)[1]
    rim = y - float(m.body_dia) / 2
    half = float(m.knob_dia) / 2
    return rect(-half, half, rim - float(m.knob_length), rim + KNOB_EMBED)


KNOB_EMBED = 1.0                  # つまみが本体の中へ入る長さ（mm）


@dataclass(frozen=True)
class GripPose:
    """スペードグリップ 1 本の置き方。管の中心線は `start` から `direction`（単位ベクトル）へ `length` 伸び、その先に端板が `cap` の厚みで続く。"""

    side: int                              # +1 が +X 側
    start: tuple[float, float, float]
    direction: tuple[float, float, float]
    length: float
    cap: float


def grip_poses(spec: GatlingSpec) -> list[GripPose]:
    """左右のスペードグリップ。付け根は後ろの角の円弧の中央（中心線の上）で、高さは腕の中心。

    向きは後ろ（−Y）を基準に、外（その側の X 方向）へ `grip.out`、下へ `grip.drop` 傾けた単位ベクトル。
    """
    g, z = spec.grip, levels(spec).arm_centre
    out, drop = math.radians(float(g.out)), math.radians(float(g.drop))
    path = arm_path(spec)
    poses = []
    for side, arc in zip(PAD_SIDES, (path[3], path[5])):
        x, y = arc.point(0.5)
        poses.append(GripPose(side, (x, y, z),
                              (side * math.sin(out) * math.cos(drop), -math.cos(out) * math.cos(drop), -math.sin(drop)),
                              float(g.length), float(g.cap)))
    return poses


def grip_polys(spec: GatlingSpec) -> list[list[Point]]:
    """スペードグリップ（端板を含む）の平面形。管の傾きで端の円が楕円に見えるぶん、前後に管の半径ずつ広げた矩形（見落とさない側）。"""
    r = float(spec.arm.pipe.od) / 2
    polys = []
    for pose in grip_poses(spec):
        horizontal = math.hypot(pose.direction[0], pose.direction[1])
        angle = math.degrees(math.atan2(pose.direction[1], pose.direction[0]))
        reach = (pose.length + pose.cap) * horizontal
        polys.append([(pose.start[0] + x, pose.start[1] + y) for x, y in rect(-r, reach + r, -r, r, angle)])
    return polys


def grip_z(spec: GatlingSpec) -> tuple[float, float]:
    """スペードグリップの z の範囲。上は付け根の管の上端、下は端板の中心から管の半径ぶん下（見落とさない側）。"""
    r, pose = float(spec.arm.pipe.od) / 2, grip_poses(spec)[0]
    end = pose.start[2] + (pose.length + pose.cap) * pose.direction[2]
    return min(end, pose.start[2]) - r, pose.start[2] + r
