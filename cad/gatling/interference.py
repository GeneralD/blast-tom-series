"""部品どうしの干渉の検査。形状を作らずに、形状と同じ placement の値から平面形と z の範囲を作って重なりを見る。

`mount_clear` は当て板・腕・ブロック・ホルダー受け（つまみ）・スペードグリップ（D-22）が、胴まわりの回転体・ラグ・ロッド・
互いに食い込まないことを見る。`flange_bolts_removable` は、これらを付けたままフランジのボルトを抜けるかを見る。
`ear_clear` は受金とフレッシュフープの重なり。`issues()`（`checks.py`）から呼ぶ。ここでも形状は作らず、例外も投げない。

平面形はどれも実際の形を覆う凸多角形（または円）で、見落とす側にはずれない。腕は曲げを 5° ごとの四角形に分けて覆う
（`drumcad.tubepath.plan_polygons`）。傾いたグリップは前後に管の半径ずつ広げた矩形と、端板までを含む z の範囲で見る。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from drumcad.bounds import at_least
from drumcad.checks import Issue
from drumcad.fasteners import lookup_screw
from drumcad.planar import EPS, Point, circle_overlaps, origin_distance, polygons_overlap, rect, z_overlap

from .derived import derive
from .fasteners import lookup_rod
from .params import GatlingSpec
from .placement import (arm_polys, block_plan, flange_bolt_points, grip_polys, grip_z, holder_centre, knob_plan, levels, lug_angles,
                        lug_plan, pad_polys, radii)


# 部品の名前（表示名）。引くキーと表示を 1 か所に置く: 文字列の書き写しだと、名前を直したときに引けず、`ear_clear` は
# `StopIteration`、`mount_clear` の中空の判定は黙って外れ、`_WELDED` の免除は効かなくなる。
SHELL_RING = "胴・エッジ環"
FRESH_HOOP = "フレッシュフープ"
OUTER_RING = "外リング（管）"
ARM = "腕"
GRIP = "スペードグリップ"
BLOCK = "ブロック"
HOLDER = "ホルダー受け"


def hoop_rings(spec: GatlingSpec) -> list[tuple[str, float, float, float]]:
    """フープの回転体の外半径と z の範囲（名前, 外半径, 下端, 上端）。

    外リングは管の環なので、外半径は管の外面、z は管の上端（= 内リングの上端）から下端まで。受金は内リングの外面から
    管の中心まで伸びる板で、外半径は外端の隅（管の中心半径と幅の半分の斜辺）。受金の z は外リングの範囲から外れうる
    （頭の高さ + 板厚が管の外径を超えると、受金の下面 = 上面 − 板厚が管の下端より下になる）ので、別に持つ。
    """
    z, r = levels(spec), radii(spec)
    return [
        ("内リング", r.hoop_in_outer, z.head_top, z.hoop_top),
        (OUTER_RING, r.hoop_out_outer, z.pipe_bottom, z.hoop_top),
        ("受金", math.hypot(r.hoop_out_centre, float(spec.hoop.ear.width) / 2), z.ear_bottom, z.ear_top),
    ]


def _round_parts(spec: GatlingSpec) -> list[tuple[str, float, float, float]]:
    """胴まわりの回転体の外半径と z の範囲（名前, 外半径, 下端, 上端）。平面視ではこの半径の円の内側を占めるとみなす。"""
    z, r = levels(spec), radii(spec)
    return [
        (SHELL_RING, r.shell, z.flange_top, z.edge_top),
        (FRESH_HOOP, r.collar, z.collar_bottom, z.head_top),
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
    name, radius, z0, z1 = next(part for part in _round_parts(spec) if part[0] == FRESH_HOOP)
    if z_overlap(z.ear_bottom, z.ear_top, z0, z1) and r.hoop_in_outer < radius - EPS:
        return [Issue(True, f"受金が{name}に食い込む（平面視で受金の内端 {r.hoop_in_outer:.2f} < 外半径 {radius:.2f}、z も重なる）")]
    return []


@dataclass(frozen=True)
class Body:
    """干渉を見る部品の 1 かたまり。平面形（凸多角形と円）と z の範囲。`part` は同じ部品の左右・分割を同じ名前でまとめる。"""

    part: str
    polys: tuple[list[Point], ...] = ()
    circles: tuple[tuple[Point, float], ...] = ()
    z: tuple[float, float] = (0.0, 0.0)
    reach: float | None = None      # 胴の軸からの最短距離。多角形が実際より胴の側に広がる部品（当て板）は、ここで厳密な値を持つ

    def nearest(self) -> float:
        """胴の軸から、この部品の平面形までの最短距離。"""
        if self.reach is not None:
            return self.reach
        return min([origin_distance(p) for p in self.polys] + [max(math.hypot(*c) - r, 0.0) for c, r in self.circles])

    def farthest(self) -> float:
        """胴の軸から、この部品の平面形までの最長距離（凸多角形は頂点、円は中心 + 半径）。中が空いた環（外リング）の内面を越えるかを見る。"""
        return max([math.hypot(*v) for p in self.polys for v in p] + [math.hypot(*c) + r for c, r in self.circles])


# 溶接で接する組は、形状が相手の外形で切って体積を共有しない（ブロックとグリップは腕の外形で切る。`shapes/mount.py`）。
# ホルダー受けとつまみは 1 つの部品。当て板と腕は、腕が当て板の外面に平らな端で接するだけなので、免除せず平面の重なりで見る
_WELDED = {frozenset({ARM, GRIP}), frozenset({ARM, BLOCK}), frozenset({HOLDER})}


def mount_bodies(spec: GatlingSpec) -> list[Body]:
    """当て板（左右）・腕・スペードグリップ（左右）・ブロック・ホルダー受け・つまみ。形状（`shapes/mount.py`, `purchased.holder`）と同じ値から作る。"""
    z, r, m = levels(spec), radii(spec), spec.mount
    kr = float(m.knob_dia) / 2
    bodies = [Body("当て板", (poly,), z=(z.pad_bottom, z.pad_top), reach=r.shell) for poly in pad_polys(spec)]
    bodies.append(Body(ARM, tuple(arm_polys(spec)), z=(z.arm_bottom, z.arm_top)))
    bodies += [Body(GRIP, (poly,), z=grip_z(spec)) for poly in grip_polys(spec)]
    bodies += [Body(BLOCK, (block_plan(spec),), z=(z.arm_centre, z.block_top)),
               Body(HOLDER, circles=((holder_centre(spec), float(m.body_dia) / 2),), z=(z.holder_bottom, z.holder_top)),
               Body(HOLDER, (knob_plan(spec),), z=(z.knob_centre - kr, z.knob_centre + kr))]
    return bodies


def _tube_bundle(spec: GatlingSpec) -> tuple[str, float, float, float]:
    d, z = derive(spec), levels(spec)
    return "管束・クランプ", max(float(d.clamp_od) / 2, float(d.pcd) / 2 + float(spec.tube.od) / 2), z.tube_tip, z.header_bottom


def _meet(a: Body, b: Body) -> bool:
    """2 つのかたまりの平面形が EPS を超えて重なる（z の重なりは呼び出し側が先に見る）。"""
    for p in a.polys:
        if any(polygons_overlap(p, q) for q in b.polys) or any(circle_overlaps(c, r, p) for c, r in b.circles):
            return True
    for c, r in a.circles:
        if any(circle_overlaps(c, r, q) for q in b.polys) or any(math.dist(c, c2) < r + r2 - EPS for c2, r2 in b.circles):
            return True
    return False


def mount_clear(spec: GatlingSpec) -> list[Issue]:
    """当て板・腕・スペードグリップ・ブロック・ホルダー受け（つまみ）が、胴まわりの回転体・ラグ・ロッド・互いに食い込まない。

    z の範囲が重なり、かつ平面視でも重なれば干渉（fatal）。相手の平面形は形状と同じ placement の値から作る:
    胴まわりの回転体（胴・エッジ環、フレッシュフープ、フープ、フランジ・ヘッダープレート、管束とクランプ）は外半径の円
    （外から来る部品は外面で当たる。ただし外リングの管は中が空いた環なので、内面〜外面の帯で見て、内面の内側に収まる当て板は
    当たらない）、ラグは `lug_plan`（円盤の矩形。相手の z の帯に入る薄片の幅）を `lug_angles` の
    方位へ回した矩形、ロッドは半径 `rod` の円周上の円（軸の先から頭の上面まで）。
    当て板の内面は胴の外面（半径 R）に沿うので、胴の軸からの距離は R として見る。当て板の角 R（`pad.corner`）は平面形に入れていない
    （矩形で覆う）ので、ラグの円盤が板の丸めた角をかすめるだけの組も fatal にする（保守側）。
    """
    z, r = levels(spec), radii(spec)
    bodies = mount_bodies(spec)
    found: list[Issue] = []
    seen: set[str] = set()

    def report(text: str) -> None:
        if text not in seen:
            seen.add(text)
            found.append(Issue(True, text))

    for body in bodies:
        for name, radius, z0, z1 in [*_round_parts(spec), _tube_bundle(spec)]:
            hollow = r.hoop_out_inner if name == OUTER_RING else 0.0       # 管の環は内面〜外面の帯。内面の内側に収まる部品は当たらない
            if z_overlap(z0, z1, *body.z) and body.nearest() < radius - EPS and body.farthest() > hollow + EPS:
                report(f"{body.part}が{name}に食い込む（平面視で内縁 {body.nearest():.2f} < 外半径 {radius:.2f}、z も重なる）")
    rod_r = float(lookup_rod(spec.lug.thread)) / 2
    rod_z = (z.rod_tip, z.rod_top)
    lug_z = (z.lug_bottom, z.lug_top)
    for body in bodies:
        hits: dict[str, list[float]] = {}
        slice_ = z_overlap(*lug_z, *body.z)
        for a in lug_angles(spec):
            rod = (r.rod * math.cos(math.radians(a)), r.rod * math.sin(math.radians(a)))
            lug = Body(body.part, (rect(*lug_plan(spec, *body.z), a),)) if slice_ else None
            for what, hit in (("ラグに当たる", lug is not None and _meet(body, lug)),
                              ("ロッドに当たる", z_overlap(*rod_z, *body.z) and _meet(body, Body(body.part, circles=((rod, rod_r),))))):
                if hit:
                    hits.setdefault(what, []).append(a)
        for what, angles in hits.items():
            report(f"{body.part}が{what}（方位 {', '.join(f'{a:g}°' for a in angles)}）")
    for i, a in enumerate(bodies):
        for b in bodies[i + 1:]:
            if frozenset({a.part, b.part}) in _WELDED or not z_overlap(*a.z, *b.z):
                continue
            if _meet(a, b):
                report(f"{a.part}が{b.part}に食い込む（平面視でも z でも重なる）" if a.part != b.part else
                       f"{a.part}どうしが重なる（平面視でも z でも重なる）")
    return found


def flange_bolts_removable(spec: GatlingSpec) -> list[Issue]:
    """当て板・腕・スペードグリップ・ブロック・ホルダー受けを付けたまま、フランジのボルトを抜ける。

    平面視で頭が何かの下に入るなら、ボルトを抜くには頭をねじ込み長ぶん持ち上げる空きが要る（その部品の下端 −
    フランジ上面 ≥ 頭の高さ + ねじ込み長）。頭の高さだけを見ると、締めた状態は当たらなくても、腕を外さないと管束を外せない。
    どれの下に入るかは頭の方位（`bolt_phase`）で決まる。
    """
    z = levels(spec)
    screw = lookup_screw(spec.flange.bolt)
    head = float(screw.head_dia) / 2
    need = float(screw.head_height) + float(spec.flange.bolt_length) - z.flange_top       # 頭の高さ + ねじ込み長（軸のうちフランジ・ガスケットを抜けた先）
    over: dict[str, float] = {}
    for centre in flange_bolt_points(spec):
        probe = Body("ボルトの頭", circles=((centre, head),))
        for body in mount_bodies(spec):
            if _meet(probe, body):
                over[body.part] = min(over.get(body.part, math.inf), body.z[0])
    return [issue for name, bottom in over.items()
            for issue in at_least(f"{name}の下でフランジのボルトを抜けない（{name}の下端とフランジ上面の距離 < 頭の高さ + ねじ込み長）",
                                  bottom - z.flange_top, need)]
