"""寸法どうしの噛み合わせの検査（仕様 §5.3）。`issues(spec)` が契約の入口。

`_build` は `issues()` を `assembly()` より先に呼び、fatal があれば `assembly()` を呼ばない。
だから **ここでは形状を作らず、例外も投げない**。個数・規格表・正値の検査（`structure`）に
引っかかったら、その場で返す（`derive()` が `sin(180°/個数)` で割るため）。

部品どうしの干渉（平面形と z の範囲の重なり）は `interference.py`、平面の幾何は `planar.py` に置く。
"""

from __future__ import annotations

import math

from drumcad.checks import Issue
from drumcad.dims import walk
from drumcad.stock import nearest

from .bounds import at_least, at_most
from .derived import derive
from .fasteners import HOLDER_RODS, ROD_THREADS, SCREWS, lookup_holder, lookup_rod, lookup_screw
from .interference import ear_clear, flange_bolts_removable, hoop_rings, mount_clear
from .params import GatlingSpec
from .placement import flange_bolt_points, levels, pipe_inner_radius, radii, tip_bolt_points, tube_points
from .planar import EPS, z_overlap

MIN_ENGAGEMENT = 0.75         # ねじ込み長 / 呼び径の下限（下回ると警告）
MIN_CRADLE_CLEARANCE = 5.0    # クレードルとフープの逃げがこれ未満なら警告（mm）

# 個数 → 下限。整数であること、かつ下限以上であること。
_COUNTS = {"tube.count": 3, "lug.count": 1, "flange.bolt_count": 1, "hoop.ear.count": 1}
_POSITIVE = (
    "head.fit_id", "head.film_mil", "head.collar_wall", "head.collar_height", "shell.thickness", "shell.plenum_height",
    "edge.angle", "edge.radius", "edge.height", "edge.width",
    "hoop.inner.thickness", "hoop.inner.height", "hoop.outer.od", "hoop.outer.thickness", "hoop.gap",
    "hoop.seat", "hoop.takeup", "hoop.ear.width", "hoop.ear.thickness",
    "lug.body_dia", "lug.foot_dia", "lug.height", "lug.standoff", "lug.hole_dia", "lug.rod_length", "lug.rod_head_dia", "lug.rod_head_height",
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
    pipe = spec.hoop.outer
    if float(pipe.thickness) * 2 >= float(pipe.od):
        found.append(Issue(True, f"外リングの管の肉厚 {float(pipe.thickness):g} が外径 {float(pipe.od):g} の半分以上で、穴が無い"))
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


def tubes_apart(spec: GatlingSpec) -> list[Issue]:
    """隣り合う管穴の間に肉が残る（管の中心間 − (管外径 + 穴の逃げ) > 0）。中心間は形状と同じ derive の値。"""
    pitch = float(derive(spec).tube_pitch)
    hole = float(spec.tube.od) + float(spec.header.hole_clearance)
    web = pitch - hole
    return [] if web > 0 else [Issue(True, f"管同士が干渉する（管の中心間 {pitch:.2f} − 穴径 {hole:.2f} = {web:.2f} は正でなければならない。"
                                           f"tube.gap_ratio = {float(spec.tube.gap_ratio):g}）")]


def plate_size(plate_od: float, shell_id: float, shell_od: float, max_over_shell: float) -> list[Issue]:
    """ヘッダープレートの外径が胴内径以上（蓋になる）で、胴外径 + 上限以下。

    `issues()` から `derive()` の値で呼ぶと、下限側は常に通る（恒真）: `plate_od` は max の項に胴外径を含み、
    胴内径 = 胴外径 − 2 × 肉厚（肉厚 > 0 は `structure()` が見る）なので、`plate_od` ≥ 胴外径 > 胴内径。
    値を直に渡して呼ぶとき（テスト）のために、下限の検査も残す。
    """
    return (at_least("ヘッダープレートが胴の内径より小さく、蓋にならない", plate_od, shell_id)
            + at_most("ヘッダープレートが大きすぎる（胴外径 + 上限を超える）", plate_od, shell_od + max_over_shell))


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
    found = (at_least("ボルト穴と管外面の距離が縁に足りない", to_tube, margin)
             + at_least("ボルト穴と板縁の距離が縁に足りない", to_edge, margin)
             + at_least("ボルトの頭が胴の外面にかかる（ボルト座が頭の半径に足りない）", to_shell, 0.0))
    if not shifted:
        found.append(Issue(True, f"フランジのボルトのどれかが管と同じ方位にある（bolt_phase = {float(spec.flange.bolt_phase):g}°、"
                                 f"ボルト {len(bolts)} 本（間隔 {360 / len(bolts):g}°）・管 {len(tubes)} 本（間隔 {pitch:g}°））"))
    return found


def tubes_inside_bore(spec: GatlingSpec) -> list[Issue]:
    """管の外面が胴の内径に収まる。はみ出すとフランジが管の開口を塞ぐ（警告）。"""
    d = derive(spec)
    reach = float(d.pcd) / 2 + float(spec.tube.od) / 2
    return at_most("管の外面が胴の内径からはみ出し、開口の一部をフランジが塞ぐ", reach, float(d.shell_id) / 2, fatal=False)


def tube_clamps(spec: GatlingSpec) -> list[Issue]:
    """先端の突き出しが 0 以上、中間クランプの比が 0〜1、中間クランプがヘッダープレートにも先端クランプにも重ならない。"""
    z, c = levels(spec), spec.clamp
    found = at_least("先端クランプの突き出しが負", float(spec.tube.protrusion_ratio), 0.0)
    found += at_least("中間クランプの位置の比が 0 未満", float(c.mid_position), 0.0)
    found += at_most("中間クランプの位置の比が 1 を超える", float(c.mid_position), 1.0)
    found += at_least("中間クランプがヘッダープレートに重なる（ヘッダー下面と中間クランプの距離）", z.header_bottom - z.mid_top, 0.0)
    found += at_least("中間クランプが先端クランプに重なる（クランプ間の距離）", z.mid_bottom - z.tip_top, 0.0)
    d = derive(spec)
    found += at_least("中間クランプ中央の穴径が 0 以下（管が詰まりすぎ）", float(d.clamp_hole_d), EPS)
    return found


def tip_bolts_clear(spec: GatlingSpec) -> list[Issue]:
    """先端クランプの意匠ボルトの頭が管の外面に当たらない（ボルトと管の中心間 ≥ 管の半径 + 頭の半径）。

    頭はクランプの下面に座り、管はクランプの下へ突き出す（突き出し ≥ 0）ので、軸ではなく頭の径で見る。
    """
    head = float(lookup_screw(spec.clamp.bolt).head_dia) / 2
    gap = min(math.dist(b, t) for b in tip_bolt_points(spec) for t in tube_points(spec))
    return at_least("先端クランプのボルトの頭が管に当たる（ボルトと管の中心間 < 管の半径 + 頭の半径）", gap,
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
    """テンションロッドが内外リングの間を通り、頭が受金の上面に載り、軸の先がラグにねじ込める。

    軸の内側の相手は内リングとフレッシュフープの外面の大きいほう、外側の相手は外リングの管の内面
    （軸が通る高さで最も軸に近い所。管の中心の高さを通れば内側の接線）。頭（受金の上面からその上）は内リングの
    外面と、頭の高さでの管の内面の間に収まり、受金の穴より大きい（小さいと穴を抜ける）。
    軸の先（受金の上面 − 軸の長さ）は、ラグの上端からねじ込み代（呼び径 × `MIN_ENGAGEMENT`）まで届かなければ fatal、
    ラグの下端より下に出れば警告。頭の上面がフープの上端より上ならリムショットの邪魔なので警告。
    必要長（受金の上面からラグの下端まで）は式の項を並べず、`levels()` の高さから出す（仕様 §5.3）。
    """
    r, z, s = radii(spec), levels(spec), spec.lug
    major, head = float(lookup_rod(s.thread)), float(s.rod_head_dia) / 2
    # 内側の下限: ロッドはフープの高さだけでなくフレッシュフープの高さも通る。内リングを薄くして掛かりを増やすと、
    # フレッシュフープの外面のほうが外に出る
    inner, what = max((r.hoop_in_outer, "内リング"), (r.collar, "フレッシュフープ"))
    found = at_least(f"ロッドが{what}に当たる（中心半径が足りない）", r.rod - major / 2, inner)
    found += at_most("ロッドが外リング（管）に当たる（中心半径が大きすぎる）", r.rod + major / 2,
                     pipe_inner_radius(spec, z.rod_tip, z.ear_top))
    if z_overlap(z.ear_top, z.rod_top, z.head_top, z.hoop_top):
        found += at_least("ロッドの頭が内リングに当たる（頭の内縁 < 内リングの外面）", r.rod - head, r.hoop_in_outer)
    found += at_most("ロッドの頭が外リング（管）に当たる（頭の外縁 > 頭の高さでの管の内面）", r.rod + head,
                     pipe_inner_radius(spec, z.ear_top, z.rod_top))
    hole = major + float(spec.hoop.ear.hole_clearance)
    if 2 * head <= hole + EPS:
        found.append(Issue(True, f"ロッドの頭が受金の穴を抜ける（頭の径 {2 * head:.2f} ≤ 穴径 {hole:.2f}）"))
    found += at_most("ロッドが短い（軸の先がラグの上端からねじ込み代まで届かない）", z.rod_tip, z.lug_top - MIN_ENGAGEMENT * major)
    found += at_least("ロッドが長い（軸の先がラグの下端より下に出る）", z.rod_tip, z.lug_bottom, fatal=False)
    return found + at_most("ロッドの頭がフープの上端より上に出て、リムショットの邪魔になる", z.rod_top, z.hoop_top, fatal=False)


def hoop_seat(spec: GatlingSpec) -> list[Issue]:
    """内リングがフレッシュフープの環の上面だけに載る（掛かりが環の肉厚を超えると、膜に載って膜を押す）。"""
    return at_most("内リングがフレッシュフープの内側まで掛かり、膜に載る（hoop.seat が環の肉厚を超える）",
                    float(spec.hoop.seat), float(spec.head.collar_wall))


def spacing(spec: GatlingSpec) -> list[Issue]:
    """周に並ぶ受金・ラグが隣どうしで重ならない（個数の上限）。

    幅 w の矩形を方位の線に沿って並べると、隣り合う 2 つは内側の端（半径 r0）の角で先に当たる。重ならない条件は
    w ≤ 2 × r0 × tan(180° / 個数)。ロッドの半径での弦長で比べると、内端の角の重なりを見落とす（内端はロッドより内側）。
    受金の内端は内リングの外面（受金はリングの間に沈む）、ラグの内端は胴の外面。2 個以下は向かい合うので重ならない。
    """
    r = radii(spec)
    found = []
    for what, n, width, r0 in (
        ("受金", int(float(spec.hoop.ear.count)), float(spec.hoop.ear.width), r.hoop_in_outer),
        ("ラグ", int(float(spec.lug.count)), 2 * float(spec.lug.standoff), r.shell),
    ):
        if n >= 3:
            found += at_most(f"{what} {n} 個が隣どうしで重なる（幅 > 2 × 内端の半径 × tan(180° / 個数)）",
                              width, 2 * r0 * math.tan(math.pi / n))
    return found


def ear_fits(spec: GatlingSpec) -> list[Issue]:
    """受金がフープの上端から突き出ず、内リングと外リングの管の両方に溶接できる（fatal）。
    受金の幅がロッド通し穴より広い（fatal）。穴の両側に板厚ぶんの肉が無ければ警告。
    ロッド通し穴の径方向の肉（内側と外側）が正（fatal）。板厚の半分ぶん無ければ警告。

    受金の上面は「フープの上端 − ロッドの頭の高さ」（頭の上面がリムの上端に揃う。`placement.levels`）で、板厚はそこから下へ
    伸びる。下面は膜面より下（フレッシュフープの外側）に出てよい。突き出し（上面 > フープの上端）は頭の高さが負のときだけ起きる。
    内リングとの溶接は、受金の z の帯と内リングの z の帯 [膜面, フープの上端] の重なり。0 以下なら溶接できず（fatal）、
    板厚の半分に足りなければ警告。受金の外端は管の中心半径で、管の形で切り欠く。受金の上面が管の下端以下だと管に接せず、
    溶接できない（fatal）。

    幅が穴径以下だと受金が 2 片に割れるので fatal。肉の下限（穴径 + 2 × 板厚）は、打ち抜きや穴あけで縁が
    割れたり曲がったりしない一般的な目安で、受金を新しい寸法で増やさずに済むよう板厚を流用する。目安なので
    警告にとどめる（fatal にすると、板厚 8 で既定の幅 20 が出力できなくなる）。`plate.margin`（8）は削り出しの
    板の縁で、既定の幅 20 では足りない（6.5 + 16 = 22.5）ので使わない。
    """
    e, z = spec.hoop.ear, levels(spec)
    found = at_most("受金がフープの上端から突き出る（受金の上面 > フープの上端）", z.ear_top, z.hoop_top)
    weld = z.ear_top - max(z.ear_bottom, z.head_top)
    if weld <= EPS:
        found.append(Issue(True, f"受金が内リングに溶接できない（受金と内リングの z の重なり {weld:.2f} ≤ 0。リムが浅いか、受金が下すぎる）"))
    else:
        found += at_least("受金と内リングの溶接の重なり（z）が板厚の半分に足りない", weld, float(e.thickness) / 2, fatal=False)
    pipe_bottom = z.hoop_top - float(spec.hoop.outer.od)
    if z.ear_top <= pipe_bottom + EPS:
        found.append(Issue(True, f"受金が外リング（管）に届かない（受金の上面 {z.ear_top:.2f} ≤ 管の下端 {pipe_bottom:.2f}）"))
    hole = float(lookup_rod(spec.lug.thread)) + float(e.hole_clearance)
    r = radii(spec)
    inner_wall = (r.rod - hole / 2) - r.hoop_in_outer
    outer_wall = min(pipe_inner_radius(spec, z.ear_bottom, z.ear_top), r.hoop_out_centre) - (r.rod + hole / 2)
    guide = float(e.thickness) / 2
    for side, wall in (("内側", inner_wall), ("外側", outer_wall)):
        found += at_least(f"受金のロッド通し穴が受金の{side}の端を破る（{side}の肉）", wall, EPS)
        if wall > EPS:
            found += at_least(f"受金のロッド通し穴の{side}の肉（径方向）が板厚の半分に足りない", wall, guide, fatal=False)
    width = float(e.width)
    if width <= hole + EPS:
        return found + [Issue(True, f"受金の幅がロッド通し穴の径以下で、受金が 2 片に割れる（{width:.2f} ≤ {hole:.2f}）")]
    return found + at_least("受金の幅がロッド通し穴の両側の肉（板厚）に足りない（穴径 + 2 × 板厚）", width,
                     hole + 2 * float(e.thickness), fatal=False)


def lug_fits(spec: GatlingSpec) -> list[Issue]:
    """胴の取付穴（ラグ 1 個に 1 つ、ラグの高さの中心）が胴の高さと台座に収まり、台座がラグの高さに収まる。
    ラグの本体にロッドの穴の肉が残り、台座に穴の肉が残る。ラグが胴バンドに重ならない。"""
    z, s = levels(spec), spec.lug
    zc = (z.lug_top + z.lug_bottom) / 2
    hole, foot = float(s.hole_dia) / 2, float(s.foot_dia) / 2
    found = (at_least("ラグの取付穴が胴の下端（フランジ）にかかる", zc - hole, z.flange_top)
             + at_most("ラグの取付穴が胴の上端にかかる", zc + hole, z.shell_top)
             # 台座の軸はラグの高さの中心にあり上下対称なので、下側だけ見れば上側も同じ
             + at_least("ラグの台座がラグの高さから出る", zc - foot, z.lug_bottom)
             + at_most("ラグの本体が胴の外面にかかり、胴の外面で切られる（本体の半径 > standoff）", float(s.body_dia) / 2, float(s.standoff), fatal=False)
             + at_least("ラグが胴バンドに重なる（ラグ下端とバンド上端の距離）", z.lug_bottom, z.band_top))
    bore = float(lookup_rod(s.thread))
    if float(s.body_dia) <= bore + EPS:
        found.append(Issue(True, f"ラグの本体の径がロッドの穴径以下で、肉が残らない（{float(s.body_dia):.2f} ≤ {bore:.2f}）"))
    if foot <= hole + EPS:
        found.append(Issue(True, f"ラグの台座の径が胴の取付穴の径以下で、穴が台座に収まらない（{2 * foot:.2f} ≤ {2 * hole:.2f}）"))
    return found


def cradle_fits(spec: GatlingSpec) -> list[Issue]:
    """クレードルとフープの逃げ（負なら fatal、小さければ警告）、脚の高さ、胴バンド・耳・クレードルの下でフランジのボルトを抜けること。

    フープの逃げは、フレームと z の範囲が重なるリング（内リング、外リングの管）だけを見る（`interference.hoop_rings`）。
    既定ではフレームはプレナム胴の高さにあり、フープより下なので、管の外面がフレームの内面より外に出ていてもよい。
    """
    z, r, c = levels(spec), radii(spec), spec.cradle
    frame_z = (z.frame_centre - float(c.bar.thickness) / 2, z.frame_top)
    found = []
    for name, radius, z0, z1 in hoop_rings(spec):
        if not z_overlap(z0, z1, *frame_z):
            continue
        clearance = r.frame_inner - radius
        hit = at_least(f"クレードルがフープの外径と干渉する（フレーム内面と{name}外面の逃げ）", clearance, 0.0)
        found += hit or at_least(f"クレードルとフープの逃げが小さい（フレーム内面と{name}外面）", clearance, MIN_CRADLE_CLEARANCE, fatal=False)
    leg = z.frame_centre - float(c.bar.thickness) / 2 - z.band_centre
    found += at_least("クレードルの脚の高さが無い（フレームがバンドより上になければならない）", leg, EPS)
    return found + flange_bolts_removable(spec)


def holder_fits(spec: GatlingSpec) -> list[Issue]:
    """ホルダー受けの本体が L ロッド穴の両側に縁（`plate.margin`）を残せる太さで、当て板に載る。"""
    m, p = spec.mount, spec.cradle.pad
    return (at_least("ホルダー受けの本体が L ロッド穴 + 両側の縁に足りない", float(m.body_dia),
                      float(lookup_holder(m.type)) + 2 * float(spec.plate.margin))
            + at_most("ホルダー受けが当て板からはみ出す", float(m.body_dia), min(float(p.width), float(p.depth))))


def bolt_lengths(spec: GatlingSpec) -> list[Issue]:
    """ボルトの長さ: ヘッダー・先端クランプ・バンドの耳を突き抜けない。ねじ込みが短ければ警告。"""
    f, c, b = spec.flange, spec.clamp, spec.band
    stack = float(f.thickness) + float(spec.gasket.thickness)
    major = lambda choice: float(lookup_screw(choice).major)
    found = at_least("フランジのボルトがヘッダープレートに届かない", float(f.bolt_length), stack)
    found += at_most("フランジのボルトがヘッダープレートを突き抜ける", float(f.bolt_length), stack + float(spec.header.thickness))
    found += at_least("フランジのボルトのねじ込みが短い", float(f.bolt_length) - stack, MIN_ENGAGEMENT * major(f.bolt), fatal=False)
    found += at_most("先端クランプのボルトが板を突き抜ける", float(c.bolt_length), float(c.tip_thickness))
    found += at_least("先端クランプのボルトのねじ込みが短い", float(c.bolt_length), MIN_ENGAGEMENT * major(c.bolt), fatal=False)
    # 胴バンドのボルトは、+Y 側の耳・分割面の締め代・−Y 側の耳（タップ）の順に通る
    found += at_least("胴バンドのボルトが −Y 側の耳に届かない（+Y 側の耳 + 締め代）", float(b.bolt_length),
                       float(b.bar.thickness) + float(b.gap))
    found += at_most("胴バンドのボルトが耳を突き抜ける", float(b.bolt_length), 2 * float(b.bar.thickness) + float(b.gap))
    found += at_least("胴バンドのボルトのねじ込みが短い", float(b.bolt_length) - float(b.bar.thickness) - float(b.gap),
                       MIN_ENGAGEMENT * major(b.bolt), fatal=False)
    # 耳（x ≥ バンド内面、分割面から gap/2 の所）が半環の肉に重なるのは、y = gap/2 で環の外面が x > 内半径まで
    # 来るとき（(gap/2)² < 外半径² − 内半径²）。重ならないと耳が半環から離れた別の solid になる
    r = radii(spec)
    found += at_most("胴バンドの締め代が広すぎて、耳が半環から離れる（締め代の半分）", float(b.gap) / 2,
                      math.sqrt(r.band_outer ** 2 - r.band_inner ** 2) - EPS)
    return found


def stock_warning(spec: GatlingSpec) -> list[Issue]:
    """管束の管と外リングの管の外径・肉厚が規格からずれていれば警告（`stock.nearest`）。"""
    _, tube = nearest(float(spec.tube.od), float(spec.tube.thickness))
    _, pipe = nearest(float(spec.hoop.outer.od), float(spec.hoop.outer.thickness))
    return ([tube] if tube else []) + ([Issue(False, f"外リングの管: {pipe.what}")] if pipe else [])


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
    found += rod_fits(spec) + hoop_seat(spec) + ear_fits(spec) + spacing(spec) + lug_fits(spec) + cradle_fits(spec) + holder_fits(spec) + bolt_lengths(spec)
    found += ear_clear(spec) + mount_clear(spec)
    return found + stock_warning(spec)
