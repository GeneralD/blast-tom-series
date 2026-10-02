"""部品どうしの干渉の検査。形状を作らずに、形状と同じ placement の値から平面形と z の範囲を作って重なりを見る。

`mount_clear` はホルダー受け・当て板・グリップ・ラグ・ロッド・胴バンドの耳とクレードルの重なり（ラグと耳の重なりも）、
`flange_bolts_removable` は胴バンドとクレードルを付けたままフランジのボルトを抜けるかを見る。
`issues()`（`checks.py`）から呼ぶ。ここでも形状は作らず、例外も投げない。
"""

from __future__ import annotations

import math

from drumcad.checks import Issue

from .bounds import at_least
from .derived import derive
from .fasteners import lookup_rod, lookup_screw
from .params import GatlingSpec
from .placement import (band_tab_length, cradle_corner, cradle_y_rear, flange_bolt_points, grip_y, levels, lug_angles, lug_plan,
                        radii)
from .planar import EPS, Point, circle_overlaps, origin_distance, polygons_overlap, rect, square_reach, z_overlap

ARM_ANGLES = (45, 135, 225, 315)      # クレードルの腕の方位（対角線）
# ラグより下にある胴まわりの回転体。軸の先がラグの下端より下に出る（警告）と当たりうる。フープとフレッシュフープは
# `rod_fits` が、胴・エッジ環はロッドが胴の外にあること（`rod_fits` の内側の下限 ≥ フレッシュフープの外面 > 胴の外面）が見る
_OUTSIDE_THE_LUG = ("胴バンド", "フランジ・ヘッダープレート")


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
        ("胴バンド", r.band_outer, z.band_bottom, z.band_top),
        ("フランジ・ヘッダープレート", float(derive(spec).plate_od) / 2, z.header_bottom, z.flange_top),
    ]


def _band_tabs(spec: GatlingSpec) -> tuple[list[list[Point]], tuple[float, float]]:
    """胴バンドの耳の平面形（±X の 2 つ）と z の範囲。ボルトの頭を含む。

    x はバンドの内面から外面 + 耳の長さ、y は −Y 側の耳の外面から +Y 側の耳の外面 + ボルトの頭
    （締め代の隙間も含めて 1 つの矩形で見る）。z はバンドの高さと、バンドの中心に置いた頭の径の広いほう。
    ボルトの頭は両側とも +Y 側に出る（180° 回すと y も裏返るので、回さずに x の範囲を反転する）。
    """
    z, r, b = levels(spec), radii(spec), spec.band
    screw = lookup_screw(b.bolt)
    head = float(screw.head_dia) / 2
    near, far = float(b.gap) / 2 + float(b.bar.thickness), float(b.gap) / 2 + float(b.bar.thickness) + float(screw.head_height)
    reach = r.band_outer + band_tab_length(spec)
    return ([rect(r.band_inner, reach, -near, far), rect(-reach, -r.band_inner, -near, far)],
            (min(z.band_bottom, z.band_centre - head), max(z.band_top, z.band_centre + head)))


def _arms(spec: GatlingSpec) -> list[list[Point]]:
    """クレードルの 4 本の腕の平面形。対角線上、胴バンドの外面から脚の中心まで、幅は平角材の幅。

    z の範囲はバンドの中心 ± 平角材の厚みの半分（形状 `shapes/mount.py` の `cradle` と同じ）。
    """
    w = float(spec.cradle.bar.width)
    return [rect(radii(spec).band_outer, cradle_corner(spec), -w / 2, w / 2, a) for a in ARM_ANGLES]


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


def mount_clear(spec: GatlingSpec) -> list[Issue]:
    """ホルダー受け・当て板・グリップ・胴バンドの耳が、胴まわりの部品・ラグ・ロッド・クレードルに食い込まない。
    ラグは胴バンドの耳（`_band_tabs`。ボルトの頭を含む）にも当たらない。

    z の範囲が重なり、かつ平面視でも重なれば干渉（fatal）。平面視の形は形状と同じ placement の値から作る:
    ホルダー受けは中心 (0, `cradle_y_rear`)・半径 body_dia/2 の円、当て板は同じ中心の軸平行な矩形、ラグは
    `lug_plan`（台座の矩形と本体の正方形）を `lug_angles` の方位へ回した矩形の組、ロッドは半径 `rod` の円周上の円。胴まわりの回転体は
    外半径の円で見る（中は空いていても、外から来る部品は外面で当たる）。グリップは X 方向の丸棒なので、
    YZ 面の円（中心 (`grip_y`, frame_centre)、半径 grip_dia/2）と、当て板・ホルダー受けの YZ 面の矩形で見る。
    """
    z, r, m, p = levels(spec), radii(spec), spec.mount, spec.cradle.pad
    y0, rb = cradle_y_rear(spec), float(m.body_dia) / 2
    pw, pd = float(p.width), float(p.depth)
    pad = rect(-pw / 2, pw / 2, y0 - pd / 2, y0 + pd / 2)
    holder_z, pad_z = (z.holder_bottom, z.holder_top), (z.frame_top, z.pad_top)
    found = []
    for name, radius, z0, z1 in _round_parts(spec):
        if z_overlap(z0, z1, *holder_z) and abs(y0) - rb < radius - EPS:
            found.append(Issue(True, f"ホルダー受けが{name}に食い込む（平面視で内縁 {abs(y0) - rb:.2f} < 外半径 {radius:.2f}、z も重なる）"))
        if z_overlap(z0, z1, *pad_z) and origin_distance(pad) < radius - EPS:
            found.append(Issue(True, f"当て板が{name}に食い込む（平面視で内縁 {origin_distance(pad):.2f} < 外半径 {radius:.2f}、z も重なる）"))
    plan, rod_r = lug_plan(spec), float(lookup_rod(spec.lug.thread)) / 2
    # ロッドは軸の先から頭の上面まで（平面視は軸の径で見る。頭は内外リングの間にあり、`rod_fits` が見る）。
    # 軸の先はラグの下端より下に出うる（警告）ので、ラグの外の部品（胴バンド・フランジ・腕・耳・フレーム・当て板・ホルダー受け）とも見る
    lug_z, rod_z = (z.lug_bottom, z.lug_top), (z.rod_tip, z.rod_top)
    # クレードル: フレームの内面（正方形の半幅 frame_inner）、腕（`_arms`、厚みの中心はバンドの中心）。
    # 脚はフレームの内面より外、フレームの下にあり、ラグの上端はフレームより上なので、脚に届くラグはフレームの z にも
    # かかって内面の外に出る（フレームの検査で止まる）。
    t = float(spec.cradle.bar.thickness)
    frame_z, arm_z = (z.frame_centre - t / 2, z.frame_top), (z.band_centre - t / 2, z.band_centre + t / 2)
    arms = _arms(spec)
    # 胴バンドの耳（ボルトの頭を含む）。バンドの幅が頭径より狭いと、頭がバンドの上端より上に出るので、
    # `lug_fits` のラグ下端とバンド上端の比較だけでは止まらない
    tabs, tab_z = _band_tabs(spec)
    hits: dict[str, list[float]] = {}
    for a in lug_angles(spec):
        lug = [rect(*box, a) for box in plan]
        rod = (r.rod * math.cos(math.radians(a)), r.rod * math.sin(math.radians(a)))
        for what, hit in (
            ("ラグがホルダー受けに当たる", z_overlap(*lug_z, *holder_z) and any(circle_overlaps((0.0, y0), rb, part) for part in lug)),
            ("ラグが当て板に当たる", z_overlap(*lug_z, *pad_z) and any(polygons_overlap(part, pad) for part in lug)),
            ("ロッドが当て板に当たる", z_overlap(*rod_z, *pad_z) and circle_overlaps(rod, rod_r, pad)),
            ("ロッドがホルダー受けに当たる", z_overlap(*rod_z, *holder_z) and math.dist(rod, (0.0, y0)) < rod_r + rb - EPS),
            ("ラグがクレードルのフレームの内面から外に出て当たる", z_overlap(*lug_z, *frame_z) and square_reach(lug) > r.frame_inner + EPS),
            ("ラグがクレードルの腕に当たる", z_overlap(*lug_z, *arm_z) and any(polygons_overlap(part, arm) for part in lug for arm in arms)),
            ("ラグが胴バンドの耳（ボルトの頭を含む）に当たる", z_overlap(*lug_z, *tab_z) and any(polygons_overlap(part, tab) for part in lug for tab in tabs)),
            ("ロッドがクレードルのフレームの内面から外に出て当たる",
             z_overlap(*rod_z, *frame_z) and max(abs(rod[0]), abs(rod[1])) + rod_r > r.frame_inner + EPS),
            ("ロッドがクレードルの腕に当たる", z_overlap(*rod_z, *arm_z) and any(circle_overlaps(rod, rod_r, arm) for arm in arms)),
            ("ロッドが胴バンドの耳（ボルトの頭を含む）に当たる",
             z_overlap(*rod_z, *tab_z) and any(circle_overlaps(rod, rod_r, tab) for tab in tabs)),
            *((f"ロッドが{name}に当たる", z_overlap(*rod_z, z0, z1) and r.rod - rod_r < radius - EPS)
              for name, radius, z0, z1 in _round_parts(spec) if name in _OUTSIDE_THE_LUG),
        ):
            if hit:
                hits.setdefault(what, []).append(a)
    found += [Issue(True, f"{what}（方位 {', '.join(f'{a:g}°' for a in angles)}）") for what, angles in hits.items()]
    # 胴バンドの耳（ボルトの頭を含む）とフレーム。耳の外端は既定でもフレームの内面より外にあり、z が離れているだけ
    if z_overlap(*tab_z, *frame_z) and square_reach(tabs) > r.frame_inner + EPS:
        found.append(Issue(True, f"胴バンドの耳がクレードルのフレームに当たる（耳の外端 {square_reach(tabs):.2f} > "
                                 f"フレームの内面 {r.frame_inner:.2f}、z も重なる）"))
    # グリップ（YZ 面の円）と、当て板・ホルダー受け（YZ 面の矩形）。グリップは X 方向にフレームの幅いっぱい通る
    grip = (grip_y(spec), z.frame_centre)
    grip_r = float(spec.cradle.grip_dia) / 2
    for what, (y_lo, y_hi), (z_lo, z_hi) in (("当て板", (y0 - pd / 2, y0 + pd / 2), pad_z),
                                             ("ホルダー受け", (y0 - rb, y0 + rb), holder_z)):
        if circle_overlaps(grip, grip_r, rect(y_lo, y_hi, z_lo, z_hi)):
            found.append(Issue(True, f"ハンドルのグリップが{what}に食い込む（cradle.handle_length = {float(spec.cradle.handle_length):g} が短い）"))
    return found


def _above_the_flange(spec: GatlingSpec) -> list[tuple[str, list[Point], float]]:
    """フランジの上にある、胴バンドの環より外の部品の平面形（凸多角形）と下端の z（名前, 多角形, 下端）。

    耳: `_band_tabs`。腕: `_arms`。脚: 4 隅の平角材の断面（下端はバンドの中心）。
    値は形状（`shapes/mount.py`）と同じ placement から読む。
    """
    z, r, c = levels(spec), radii(spec), spec.cradle
    w, t = float(c.bar.width), float(c.bar.thickness)
    tabs, (tab_bottom, _) = _band_tabs(spec)
    k = r.frame_inner + w / 2
    return ([("胴バンドの耳", tab, tab_bottom) for tab in tabs]
            + [("クレードルの腕", arm, z.band_centre - t / 2) for arm in _arms(spec)]
            + [("クレードルの脚", rect(sx * k - w / 2, sx * k + w / 2, sy * k - t / 2, sy * k + t / 2), z.band_centre)
               for sx in (1, -1) for sy in (1, -1)])


def flange_bolts_removable(spec: GatlingSpec) -> list[Issue]:
    """胴バンド・耳・クレードルを付けたまま、フランジのボルトを抜ける。

    平面視で頭が何かの下に入るなら、ボルトを抜くには頭をねじ込み長ぶん持ち上げる空きが要る（その部品の下端 −
    フランジ上面 ≥ 頭の高さ + ねじ込み長）。頭の高さだけを見ると、締めた状態は当たらなくても、バンド（とクレードル）を
    外さないと管束を外せない。見る相手は胴バンドの環とゴムシート（頭が環の外面より内側にかかる）、耳、腕、脚、フレーム
    （頭が正方形の内面より外にかかる）。どれの下に入るかは頭の方位（`bolt_phase`）で決まる。
    """
    z, r, c = levels(spec), radii(spec), spec.cradle
    screw = lookup_screw(spec.flange.bolt)
    head = float(screw.head_dia) / 2
    need = float(screw.head_height) + float(spec.flange.bolt_length) - float(spec.flange.thickness) - float(spec.gasket.thickness)
    over: dict[str, float] = {}
    for centre in flange_bolt_points(spec):
        dist = math.hypot(*centre)
        # ゴムシートが胴の外面からバンドの内面までを埋めるので、頭がバンドの外面より内側にかかれば下に入る。
        # 胴の外面にかかる頭は `bolt_clearances` が fatal にする
        if dist - head < r.band_outer - EPS:
            over["胴バンド"] = z.band_bottom
        for name, poly, bottom in _above_the_flange(spec):
            if circle_overlaps(centre, head, poly):
                over[name] = bottom
        if max(abs(centre[0]), abs(centre[1])) + head > r.frame_inner + EPS:
            over["クレードルのフレーム"] = z.frame_centre - float(c.bar.thickness) / 2
    return [issue for name, bottom in over.items()
            for issue in at_least(f"{name}の下でフランジのボルトを抜けない（{name}の下端とフランジ上面の距離 < 頭の高さ + ねじ込み長）",
                                  bottom - z.flange_top, need)]
