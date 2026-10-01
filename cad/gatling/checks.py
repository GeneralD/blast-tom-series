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
from .placement import (band_tab_length, cradle_corner, cradle_y_rear, flange_bolt_points, grip_y, levels, lug_angles, lug_box, radii,
                        tip_bolt_points, tube_points)

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
# 符号は問わないが有限であること。inf / nan は三角関数や配置の計算を割る（`bolt_phase = inf` で `cos` が ValueError）。
_FINITE = (
    "head.f01_range[0]", "head.f01_range[1]",   # 周波数の目標範囲。形状に入らず、音の検査（PR 4）が見る
    "head.loss_factor",                         # 膜の損失係数。形状に入らない
    "tube.gap_ratio", "tube.protrusion_ratio",  # od に掛ける比。符号の決まりは配置の検査（tubes_apart・tube_clamps）が見る
    "clamp.mid_position",                       # 管長に対する比。0〜1 は tube_clamps が見る
    "flange.bolt_phase",                        # 位相（度）。負でも 360 超でも形は作れる
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
    found += [Issue(True, f"{p} = {float(leaves[p]):g} は有限でなければならない")
              for p in _FINITE if not math.isfinite(float(leaves[p]))]
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


def _at_least(what: str, value: float, floor: float, fatal: bool = True) -> list[Issue]:
    """`value` が `floor` 以上であること（縁ちょうどは通す）。"""
    return [] if value >= floor - EPS else [Issue(fatal, f"{what}（{value:.2f} < {floor:.2f}）")]


def _at_most(what: str, value: float, ceiling: float, fatal: bool = True) -> list[Issue]:
    return [] if value <= ceiling + EPS else [Issue(fatal, f"{what}（{value:.2f} > {ceiling:.2f}）")]


# ---- 平面の幾何。形状を作らずに、形状と同じ placement の値から重なりを見る ----

Point = tuple[float, float]


def _rect(u0: float, u1: float, v0: float, v1: float, angle_deg: float = 0.0) -> list[Point]:
    """局所座標の矩形 u∈[u0, u1]、v∈[v0, v1] を Z 軸周りに `angle_deg` 回した 4 隅（反時計回り）。

    x = u cos a − v sin a、y = u sin a + v cos a。形状の `rotate((0,0,0), (0,0,1), a)` と同じ向き。
    """
    c, s = math.cos(math.radians(angle_deg)), math.sin(math.radians(angle_deg))
    return [(u * c - v * s, u * s + v * c) for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1))]


def _edges(poly: list[Point]) -> list[tuple[Point, Point]]:
    return [(poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly))]


def _polygons_overlap(p: list[Point], q: list[Point]) -> bool:
    """2 つの凸多角形が EPS を超えて重なる（分離軸判定。接するだけなら重ならない）。"""
    for (x0, y0), (x1, y1) in _edges(p) + _edges(q):
        nx, ny = y0 - y1, x1 - x0
        norm = math.hypot(nx, ny)
        a = [(x * nx + y * ny) / norm for x, y in p]
        b = [(x * nx + y * ny) / norm for x, y in q]
        if min(max(a), max(b)) - max(min(a), min(b)) <= EPS:
            return False
    return True


def _segment_distance(p: Point, a: Point, b: Point) -> float:
    ax, ay, bx, by = *a, *b
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def _circle_overlaps(centre: Point, radius: float, poly: list[Point]) -> bool:
    """円と凸多角形（反時計回り）が EPS を超えて重なる。中心が内側にあるか、辺までの距離が半径未満。"""
    inside = all((b[0] - a[0]) * (centre[1] - a[1]) - (b[1] - a[1]) * (centre[0] - a[0]) >= 0 for a, b in _edges(poly))
    return inside or min(_segment_distance(centre, a, b) for a, b in _edges(poly)) < radius - EPS


def _z_overlap(a0: float, a1: float, b0: float, b1: float) -> bool:
    return min(a1, b1) - max(a0, b0) > EPS


def _round_parts(spec: GatlingSpec) -> list[tuple[str, float, float, float]]:
    """胴まわりの回転体の外半径と z の範囲（名前, 外半径, 下端, 上端）。平面視ではこの半径の円の内側を占めるとみなす。"""
    z, r = levels(spec), radii(spec)
    return [
        ("胴・エッジ環", r.shell, z.flange_top, z.edge_top),
        ("フレッシュフープ", r.collar, z.collar_bottom, z.head_top),
        ("内リング", r.hoop_in_outer, z.head_top, z.hoop_top),
        ("外リング", r.hoop_out_outer, z.hoop_top - float(spec.hoop.outer.height), z.hoop_top),
        ("胴バンド", r.band_outer, z.band_bottom, z.band_top),
        ("フランジ・ヘッダープレート", float(derive(spec).plate_od) / 2, z.header_bottom, z.flange_top),
    ]


def _origin_distance(poly: list[Point]) -> float:
    """原点（胴の軸）から凸多角形までの距離。原点が内側なら 0。"""
    return 0.0 if _circle_overlaps((0.0, 0.0), 0.0, poly) else min(_segment_distance((0.0, 0.0), a, b) for a, b in _edges(poly))


def mount_clear(spec: GatlingSpec) -> list[Issue]:
    """ホルダー受け・当て板・グリップが、胴まわりの部品とラグ・ロッドに食い込まない。

    z の範囲が重なり、かつ平面視でも重なれば干渉（fatal）。平面視の形は形状と同じ placement の値から作る:
    ホルダー受けは中心 (0, `cradle_y_rear`)・半径 body_dia/2 の円、当て板は同じ中心の軸平行な矩形、ラグは
    `lug_box` を `lug_angles` の方位へ回した矩形、ロッドは半径 `rod` の円周上の円。胴まわりの回転体は
    外半径の円で見る（中は空いていても、外から来る部品は外面で当たる）。グリップは X 方向の丸棒なので、
    YZ 面の円（中心 (`grip_y`, frame_centre)、半径 grip_dia/2）と、当て板・ホルダー受けの YZ 面の矩形で見る。
    """
    z, r, m, p = levels(spec), radii(spec), spec.mount, spec.cradle.pad
    y0, rb = cradle_y_rear(spec), float(m.body_dia) / 2
    pw, pd = float(p.width), float(p.depth)
    pad = _rect(-pw / 2, pw / 2, y0 - pd / 2, y0 + pd / 2)
    holder_z, pad_z = (z.holder_bottom, z.holder_top), (z.frame_top, z.pad_top)
    found = []
    for name, radius, z0, z1 in _round_parts(spec):
        if _z_overlap(z0, z1, *holder_z) and abs(y0) - rb < radius - EPS:
            found.append(Issue(True, f"ホルダー受けが{name}に食い込む（平面視で内縁 {abs(y0) - rb:.2f} < 外半径 {radius:.2f}、z も重なる）"))
        if _z_overlap(z0, z1, *pad_z) and _origin_distance(pad) < radius - EPS:
            found.append(Issue(True, f"当て板が{name}に食い込む（平面視で内縁 {_origin_distance(pad):.2f} < 外半径 {radius:.2f}、z も重なる）"))
    box, rod_r = lug_box(spec), float(lookup_rod(spec.lug.thread)) / 2
    lug_z, rod_z = (z.lug_bottom, z.lug_top), (z.lug_bottom, z.lug_bottom + float(spec.lug.rod_length))
    # クレードル: フレームの内面（正方形の半幅 frame_inner）、腕（対角線上、胴バンドの外面から隅まで、幅 = 平角材の幅）。
    # 脚はフレームの内面より外、フレームの下にあり、ラグの上端はフレームより上なので、脚に届くラグはフレームの z にも
    # かかって内面の外に出る（フレームの検査で止まる）。
    c = spec.cradle
    t, w = float(c.bar.thickness), float(c.bar.width)
    zb = (z.band_bottom + z.band_top) / 2
    arms = [_rect(r.band_outer, cradle_corner(spec), -w / 2, w / 2, a) for a in (45, 135, 225, 315)]
    hits: dict[str, list[float]] = {}
    for a in lug_angles(spec):
        lug = _rect(*box, a)
        out_of_frame = max(max(abs(x), abs(y)) for x, y in lug) > r.frame_inner + EPS
        rod = (r.rod * math.cos(math.radians(a)), r.rod * math.sin(math.radians(a)))
        for what, hit in (
            ("ラグがホルダー受けに当たる", _z_overlap(*lug_z, *holder_z) and _circle_overlaps((0.0, y0), rb, lug)),
            ("ラグが当て板に当たる", _z_overlap(*lug_z, *pad_z) and _polygons_overlap(lug, pad)),
            ("ロッドがホルダー受けに当たる", _z_overlap(*rod_z, *holder_z) and math.dist(rod, (0.0, y0)) < rb + rod_r - EPS),
            ("ロッドが当て板に当たる", _z_overlap(*rod_z, *pad_z) and _circle_overlaps(rod, rod_r, pad)),
            ("ラグがクレードルのフレームの内面から外に出て当たる", _z_overlap(*lug_z, z.frame_centre - t / 2, z.frame_top) and out_of_frame),
            ("ラグがクレードルの腕に当たる", _z_overlap(*lug_z, zb - t / 2, zb + t / 2) and any(_polygons_overlap(lug, arm) for arm in arms)),
        ):
            if hit:
                hits.setdefault(what, []).append(a)
    found += [Issue(True, f"{what}（方位 {', '.join(f'{a:g}°' for a in angles)}）") for what, angles in hits.items()]
    # グリップ（YZ 面の円）と、当て板・ホルダー受け（YZ 面の矩形）。グリップは X 方向にフレームの幅いっぱい通る
    grip = (grip_y(spec), z.frame_centre)
    grip_r = float(spec.cradle.grip_dia) / 2
    for what, (ya, yb), (za, zb) in (("当て板", (y0 - pd / 2, y0 + pd / 2), pad_z), ("ホルダー受け", (y0 - rb, y0 + rb), holder_z)):
        if _circle_overlaps(grip, grip_r, _rect(ya, yb, za, zb)):
            found.append(Issue(True, f"ハンドルのグリップが{what}に食い込む（cradle.handle_length = {float(spec.cradle.handle_length):g} が短い）"))
    return found


def tubes_apart(spec: GatlingSpec) -> list[Issue]:
    """隣り合う管穴の間に肉が残る（管の中心間 − (管外径 + 穴の逃げ) > 0）。中心間は形状と同じ derive の値。"""
    pitch = float(derive(spec).tube_pitch)
    hole = float(spec.tube.od) + float(spec.header.hole_clearance)
    web = pitch - hole
    return [] if web > 0 else [Issue(True, f"管同士が干渉する（管の中心間 {pitch:.2f} − 穴径 {hole:.2f} = {web:.2f} は正でなければならない。"
                                           f"tube.gap_ratio = {float(spec.tube.gap_ratio):g}）")]


def plate_size(plate_od: float, shell_id: float, shell_od: float, max_over_shell: float) -> list[Issue]:
    """ヘッダープレートの外径が胴内径以上（蓋になる）で、胴外径 + 上限以下。"""
    return (_at_least("ヘッダープレートが胴の内径より小さく、蓋にならない", plate_od, shell_id)
            + _at_most("ヘッダープレートが大きすぎる（胴外径 + 上限を超える）", plate_od, shell_od + max_over_shell))


def _angle_apart(a: float, b: float) -> float:
    """2 つの方位（rad）の差。2π で折り返した最小値。"""
    diff = (a - b) % (2 * math.pi)
    return min(diff, 2 * math.pi - diff)


def bolt_clearances(spec: GatlingSpec) -> list[Issue]:
    """フランジのボルト穴: 管外面・板縁・胴への距離が縁以上、管の方位からずれている。"""
    d, margin = derive(spec), float(spec.plate.margin)
    od, screw = float(spec.tube.od), lookup_screw(spec.flange.bolt)
    bolts, tubes = flange_bolt_points(spec), tube_points(spec)
    to_tube = min(math.hypot(bx - tx, by - ty) for bx, by in bolts for tx, ty in tubes) - od / 2
    to_edge = float(d.plate_od) / 2 - float(d.bolt_circle) / 2
    to_shell = float(spec.flange.bolt_seat) - float(screw.head_dia) / 2
    pitch = 360.0 / float(spec.tube.count)
    shifted = min(_angle_apart(math.atan2(by, bx), math.atan2(ty, tx)) for bx, by in bolts for tx, ty in tubes) > EPS
    found = (_at_least("ボルト穴と管外面の距離が縁に足りない", to_tube, margin)
             + _at_least("ボルト穴と板縁の距離が縁に足りない", to_edge, margin)
             + _at_least("ボルトの頭が胴の外面にかかる（ボルト座が頭の半径に足りない）", to_shell, 0.0))
    if not shifted:
        found.append(Issue(True, f"フランジのボルトが管と同じ方位にある（bolt_phase = {float(spec.flange.bolt_phase):g}° は管の間隔 {pitch:g}° の倍数）"))
    return found


def tubes_inside_bore(spec: GatlingSpec) -> list[Issue]:
    """管の外面が胴の内径に収まる。はみ出すとフランジが管の開口を塞ぐ（警告）。"""
    d = derive(spec)
    reach = float(d.pcd) / 2 + float(spec.tube.od) / 2
    return _at_most("管の外面が胴の内径からはみ出し、開口の一部をフランジが塞ぐ", reach, float(d.shell_id) / 2, fatal=False)


def tube_clamps(spec: GatlingSpec) -> list[Issue]:
    """先端の突き出しが 0 以上、中間クランプの比が 0〜1、中間クランプがヘッダープレートにも先端クランプにも重ならない。"""
    z, c = levels(spec), spec.clamp
    found = _at_least("先端クランプの突き出しが負", float(spec.tube.protrusion_ratio), 0.0)
    found += _at_least("中間クランプの位置の比が 0 未満", float(c.mid_position), 0.0)
    found += _at_most("中間クランプの位置の比が 1 を超える", float(c.mid_position), 1.0)
    found += _at_least("中間クランプがヘッダープレートに重なる（ヘッダー下面と中間クランプの距離）", z.header_bottom - z.mid_top, 0.0)
    found += _at_least("中間クランプが先端クランプに重なる（クランプ間の距離）", z.mid_bottom - z.tip_top, 0.0)
    d = derive(spec)
    found += _at_least("中間クランプ中央の穴径が 0 以下（管が詰まりすぎ）", float(d.clamp_hole_d), EPS)
    return found


def tip_bolts_clear(spec: GatlingSpec) -> list[Issue]:
    """先端クランプの意匠ボルトの頭が管の外面に当たらない（ボルトと管の中心間 ≥ 管の半径 + 頭の半径）。

    頭はクランプの下面に座り、管はクランプの下へ突き出す（突き出し ≥ 0）ので、軸ではなく頭の径で見る。
    """
    head = float(lookup_screw(spec.clamp.bolt).head_dia) / 2
    gap = min(math.dist(b, t) for b in tip_bolt_points(spec) for t in tube_points(spec))
    return _at_least("先端クランプのボルトの頭が管に当たる（ボルトと管の中心間 < 管の半径 + 頭の半径）", gap,
                     float(spec.tube.od) / 2 + head)


def aligned(tube_count: int, lug_count: int, ear_count: int) -> list[Issue]:
    """管・ラグ・受金の方位が揃う。管の本数がラグ数の倍数または約数で、受金はラグと同数。"""
    found = []
    if tube_count % lug_count and lug_count % tube_count:
        found.append(Issue(True, f"管 {tube_count} 本とラグ {lug_count} 個の方位が揃わない（一方が他方の倍数でない）"))
    if ear_count != lug_count:
        found.append(Issue(True, f"受金 {ear_count} 枚がラグ {lug_count} 個と同数でない"))
    return found


def rod_fits(spec: GatlingSpec) -> list[Issue]:
    """ロッドが内外リングの間を通り、ラグの下端から受金の上面まで届く。

    内側は内リングとフレッシュフープの外面の大きいほう、外側は外リングの内面。
    必要長は式の項を並べず、`levels()` の高さから出す（受金の上面 − ラグの下端）。その間には
    ラグ・締め代・フレッシュフープの高さ・フープ・受金の厚みが入る（仕様 §5.3 もこの測り方で
    書く。仕様側の直しの 6）。
    """
    r, z, major = radii(spec), levels(spec), float(lookup_rod(spec.lug.thread))
    # 内側の下限: ロッドはフープの高さだけでなくフレッシュフープの高さも通る。内リングを薄くして掛かりを増やすと、
    # フレッシュフープの外面のほうが外に出る
    inner, what = max((r.hoop_in_outer, "内リング"), (r.collar, "フレッシュフープ"))
    found = _at_least(f"ロッドが{what}に当たる（中心半径が足りない）", r.rod - major / 2, inner)
    found += _at_most("ロッドが外リングに当たる（中心半径が大きすぎる）", r.rod + major / 2, r.hoop_out_inner)
    need = z.ear_top - z.lug_bottom
    return found + _at_least("ロッドが短い（ラグの下端から受金の上面まで届かない）", float(spec.lug.rod_length), need)


def hoop_seat(spec: GatlingSpec) -> list[Issue]:
    """内リングがフレッシュフープの環の上面だけに載る（掛かりが環の肉厚を超えると、膜に載って膜を押す）。"""
    return _at_most("内リングがフレッシュフープの内側まで掛かり、膜に載る（hoop.seat が環の肉厚を超える）",
                    float(spec.hoop.seat), float(spec.head.collar_wall))


def ear_fits(spec: GatlingSpec) -> list[Issue]:
    """受金の幅が、ロッド通し穴の両側に肉を残す（幅 ≥ 穴径 + 2 × 板厚）。幅が穴径以下だと受金が 2 片に割れる。

    肉の下限は受金の板厚を流用する。穴の縁から板の縁までを板厚以上取るのは、打ち抜きや穴あけで縁が割れたり
    曲がったりしない一般的な目安で、受金を新しい寸法で増やさずに済む。`plate.margin`（8）は削り出しの板の
    縁で、既定の幅 20 では足りない（6.5 + 16 = 22.5）ので使わない。
    """
    e = spec.hoop.ear
    hole = float(lookup_rod(spec.lug.thread)) + float(e.hole_clearance)
    return _at_least("受金の幅がロッド通し穴の両側の肉（板厚）に足りない（穴径 + 2 × 板厚）", float(e.width),
                     hole + 2 * float(e.thickness))


def lug_fits(spec: GatlingSpec) -> list[Issue]:
    """胴の取付穴がラグの高さと胴の高さに収まり、ラグが胴バンドに重ならない。"""
    z = levels(spec)
    zc, half = (z.lug_top + z.lug_bottom) / 2, float(spec.lug.pitch) / 2 + float(spec.lug.hole_dia) / 2
    return (_at_least("ラグの取付穴が胴の下端（フランジ）にかかる", zc - half, z.flange_top)
            + _at_most("ラグの取付穴が胴の上端にかかる", zc + half, z.shell_top)
            + _at_least("ラグの取付穴がラグの高さから下に外れる", zc - half, z.lug_bottom)
            + _at_most("ラグの取付穴がラグの高さから上に外れる", zc + half, z.lug_top)
            + _at_least("ラグが胴バンドに重なる（ラグ下端とバンド上端の距離）", z.lug_bottom, z.band_top))


def cradle_fits(spec: GatlingSpec) -> list[Issue]:
    """クレードルとフープの逃げ（負なら fatal、小さければ警告）、脚の高さ、胴バンド・耳・クレードルの下でフランジのボルトを抜けること。"""
    z, r, c = levels(spec), radii(spec), spec.cradle
    clearance = r.frame_inner - r.hoop_out_outer
    found = _at_least("クレードルがフープの外径と干渉する（フレーム内面と外リング外面の逃げ）", clearance, 0.0)
    if not found:
        found = _at_least("クレードルとフープの逃げが小さい", clearance, MIN_CRADLE_CLEARANCE, fatal=False)
    leg = z.frame_centre - float(c.bar.thickness) / 2 - (z.band_bottom + z.band_top) / 2
    found += _at_least("クレードルの脚の高さが無い（フレームがバンドより上になければならない）", leg, EPS)
    return found + flange_bolts_removable(spec)


def _above_the_flange(spec: GatlingSpec) -> list[tuple[str, list[Point], float]]:
    """フランジの上にある、胴バンドの環より外の部品の平面形（凸多角形）と下端の z（名前, 多角形, 下端）。

    耳: 分割面の両端、x はバンドの内面から外面 + 耳の長さ、y は −Y 側の耳の外面から +Y 側の耳の外面 + ボルトの頭
    （締め代の隙間も含めて 1 つの矩形で見る）。腕: 対角線上、バンドの外面から脚の中心まで、幅は平角材の幅。
    脚: 4 隅の平角材の断面。値は形状（`shapes/mount.py`）と同じ placement から読む。
    """
    z, r, c, b = levels(spec), radii(spec), spec.cradle, spec.band
    screw = lookup_screw(b.bolt)
    w, t = float(c.bar.width), float(c.bar.thickness)
    zb = (z.band_bottom + z.band_top) / 2
    near, far = float(b.gap) / 2 + float(b.bar.thickness), float(b.gap) / 2 + float(b.bar.thickness) + float(screw.head_height)
    tab_bottom = min(z.band_bottom, zb - float(screw.head_dia) / 2)
    reach = r.band_outer + band_tab_length(spec)
    # ±X の両側。ボルトの頭は両側とも +Y 側に出る（180° 回すと y も裏返るので、回さずに x の範囲を反転する）
    found = [("胴バンドの耳", _rect(r.band_inner, reach, -near, far), tab_bottom),
             ("胴バンドの耳", _rect(-reach, -r.band_inner, -near, far), tab_bottom)]
    found += [("クレードルの腕", _rect(r.band_outer, cradle_corner(spec), -w / 2, w / 2, a), zb - t / 2) for a in (45, 135, 225, 315)]
    k = r.frame_inner + w / 2
    found += [("クレードルの脚", _rect(sx * k - w / 2, sx * k + w / 2, sy * k - t / 2, sy * k + t / 2), zb)
              for sx in (1, -1) for sy in (1, -1)]
    return found


def flange_bolts_removable(spec: GatlingSpec) -> list[Issue]:
    """胴バンド・耳・クレードルを付けたまま、フランジのボルトを抜ける。

    平面視で頭が何かの下に入るなら、ボルトを抜くには頭をねじ込み長ぶん持ち上げる空きが要る（その部品の下端 −
    フランジ上面 ≥ 頭の高さ + ねじ込み長）。頭の高さだけを見ると、締めた状態は当たらなくても、バンド（とクレードル）を
    外さないと管束を外せない。見る相手は胴バンドの環（頭が環の内面と外面の間にかかる）、耳、腕、脚、フレーム
    （頭が正方形の内面より外にかかる）。どれの下に入るかは頭の方位（`bolt_phase`）で決まる。
    """
    z, r, c = levels(spec), radii(spec), spec.cradle
    screw = lookup_screw(spec.flange.bolt)
    head = float(screw.head_dia) / 2
    need = float(screw.head_height) + float(spec.flange.bolt_length) - float(spec.flange.thickness) - float(spec.gasket.thickness)
    over: dict[str, float] = {}
    for centre in flange_bolt_points(spec):
        dist = math.hypot(*centre)
        if dist - head < r.band_outer - EPS and dist + head > r.band_inner + EPS:
            over["胴バンド"] = z.band_bottom
        for name, poly, bottom in _above_the_flange(spec):
            if _circle_overlaps(centre, head, poly):
                over[name] = bottom
        if max(abs(centre[0]), abs(centre[1])) + head > r.frame_inner + EPS:
            over["クレードルのフレーム"] = z.frame_centre - float(c.bar.thickness) / 2
    return [issue for name, bottom in over.items()
            for issue in _at_least(f"{name}の下でフランジのボルトを抜けない（{name}の下端とフランジ上面の距離 < 頭の高さ + ねじ込み長）",
                                   bottom - z.flange_top, need)]


def holder_fits(spec: GatlingSpec) -> list[Issue]:
    """ホルダー受けの本体が L ロッド穴の両側に縁（`plate.margin`）を残せる太さで、当て板に載る。"""
    m, p = spec.mount, spec.cradle.pad
    return (_at_least("ホルダー受けの本体が L ロッド穴 + 両側の縁に足りない", float(m.body_dia),
                      float(lookup_holder(m.type)) + 2 * float(spec.plate.margin))
            + _at_most("ホルダー受けが当て板からはみ出す", float(m.body_dia), min(float(p.width), float(p.depth))))


def bolt_lengths(spec: GatlingSpec) -> list[Issue]:
    """ボルトの長さ: ヘッダー・先端クランプ・バンドの耳を突き抜けない。ねじ込みが短ければ警告。"""
    f, c, b = spec.flange, spec.clamp, spec.band
    stack = float(f.thickness) + float(spec.gasket.thickness)
    major = lambda choice: float(lookup_screw(choice).major)
    found = _at_least("フランジのボルトがヘッダープレートに届かない", float(f.bolt_length), stack)
    found += _at_most("フランジのボルトがヘッダープレートを突き抜ける", float(f.bolt_length), stack + float(spec.header.thickness))
    found += _at_least("フランジのボルトのねじ込みが短い", float(f.bolt_length) - stack, MIN_ENGAGEMENT * major(f.bolt), fatal=False)
    found += _at_most("先端クランプのボルトが板を突き抜ける", float(c.bolt_length), float(c.tip_thickness))
    found += _at_least("先端クランプのボルトのねじ込みが短い", float(c.bolt_length), MIN_ENGAGEMENT * major(c.bolt), fatal=False)
    # 胴バンドのボルトは、+Y 側の耳・分割面の締め代・−Y 側の耳（タップ）の順に通る
    found += _at_least("胴バンドのボルトが −Y 側の耳に届かない（+Y 側の耳 + 締め代）", float(b.bolt_length),
                       float(b.bar.thickness) + float(b.gap))
    found += _at_most("胴バンドのボルトが耳を突き抜ける", float(b.bolt_length), 2 * float(b.bar.thickness) + float(b.gap))
    found += _at_least("胴バンドのボルトのねじ込みが短い", float(b.bolt_length) - float(b.bar.thickness) - float(b.gap),
                       MIN_ENGAGEMENT * major(b.bolt), fatal=False)
    # 耳（x ≥ バンド内面、分割面から gap/2 の所）が半環の肉に重なるのは、y = gap/2 で環の外面が x > 内半径まで
    # 来るとき（(gap/2)² < 外半径² − 内半径²）。重ならないと耳が半環から離れた別の solid になる
    r = radii(spec)
    found += _at_most("胴バンドの締め代が広すぎて、耳が半環から離れる（締め代の半分）", float(b.gap) / 2,
                      math.sqrt(r.band_outer ** 2 - r.band_inner ** 2) - EPS)
    return found


def stock_warning(spec: GatlingSpec) -> list[Issue]:
    """管の外径・肉厚が規格からずれていれば警告（`stock.nearest`）。"""
    _, issue = nearest(float(spec.tube.od), float(spec.tube.thickness))
    return [issue] if issue else []


def issues(spec: GatlingSpec) -> list[Issue]:
    """整合性チェック。fatal が無ければ出力できる。構造の検査に落ちたら、そこで返す。"""
    found = structure(spec)
    if found:
        return found
    d = derive(spec)
    found += tubes_apart(spec)
    found += plate_size(float(d.plate_od), float(d.shell_id), float(d.shell_od), float(spec.plate.max_over_shell))
    found += bolt_clearances(spec) + tubes_inside_bore(spec) + tube_clamps(spec) + tip_bolts_clear(spec)
    found += aligned(int(float(spec.tube.count)), int(float(spec.lug.count)), int(float(spec.hoop.ear.count)))
    found += rod_fits(spec) + hoop_seat(spec) + ear_fits(spec) + lug_fits(spec) + cradle_fits(spec) + holder_fits(spec) + bolt_lengths(spec)
    found += mount_clear(spec)
    return found + stock_warning(spec)
