"""Gatling Tom の寸法（仕様 §5.2）。葉はすべて `Dim`（数値）か `Choice`（文字列）で、出典を持つ。

導出値（胴外径・管の中心間・PCD・ボルト円径・板の外径）は SPEC に持たない（`derived.py`）。
SPEC は入力の葉だけを持ち、`override()` で振った値から導出値がそのつど計算し直される。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from drumcad.dims import Choice, Dim, Source, design, override as _override, provisional


@dataclass(frozen=True)
class Head:
    model: Choice
    fit_id: Dim              # フレッシュフープ内径
    fit_clearance: Dim       # 胴外径とフレッシュフープ内径の差（直径）
    film_mil: Dim            # 膜厚（mil）
    collar_wall: Dim         # フレッシュフープの肉厚
    collar_height: Dim       # フレッシュフープの高さ
    f01_range: tuple[Dim, Dim]   # 非結合の (0,1) 基音の範囲（Hz）。結合系の周波数は別表（PR 4）
    loss_factor: Dim


@dataclass(frozen=True)
class Shell:
    thickness: Dim
    plenum_height: Dim       # ベアリングエッジ環の下面から胴底フランジの上面まで


@dataclass(frozen=True)
class Edge:
    angle: Dim               # 45° 面の角度（水平から）
    radius: Dim              # 頂部の小 R（形状は同じ大きさの面取りで近似する）
    height: Dim
    width: Dim               # 環の径方向の厚み


@dataclass(frozen=True)
class HoopRing:
    thickness: Dim
    height: Dim


@dataclass(frozen=True)
class HoopPipe:
    """管を丸めた環（外リング）。管束の `Tube` とは別の型（本数・長さを持たない）。"""

    od: Dim                  # 管の外径
    thickness: Dim           # 管の肉厚


@dataclass(frozen=True)
class Ear:
    count: Dim
    width: Dim               # 受金の幅（周方向）
    thickness: Dim
    hole_clearance: Dim      # ロッド通し穴の、ロッド径に対する直径方向の逃げ


@dataclass(frozen=True)
class Hoop:
    inner: HoopRing          # カウンターフープ（リム）。height が膜面から上端までの高さ（リムの高さ）
    outer: HoopPipe          # 質量リング。管を丸めた環で、上端を内リングの上端に揃える
    gap: Dim                 # 内リングの外面から外リング（管）の内側の接線までの間隔（径方向）
    seat: Dim                # 内リングがフレッシュフープの上面に掛かる幅（半径）。内径 = ヘッド外径 − 2 × seat
    takeup: Dim              # 締め代: フレッシュフープとフープの下端からラグの上端まで（ヘッドを引き下ろす余地）
    ear: Ear


@dataclass(frozen=True)
class Lug:
    model: Choice
    body_dia: Dim            # ラグの本体（ロッドと同軸の縦の円筒）の径。ロッドの穴が縦に通る
    foot_dia: Dim            # 台座（胴の外面から本体まで、ねじの軸方向に伸びる短い円柱）の径。胴にねじ 1 本で留める
    height: Dim              # 本体の高さ。台座の軸と胴の取付穴は、この高さの中心
    thread: Choice           # テンションロッドのねじ
    count: Dim
    standoff: Dim            # 胴外面からロッド中心まで
    hole_dia: Dim            # 胴の取付穴の径
    rod_length: Dim          # テンションロッドの軸の長さ（頭の下面から先端まで）
    rod_head_dia: Dim        # テンションロッドの頭の径（受金の上面に載る）
    rod_head_height: Dim


@dataclass(frozen=True)
class Tube:
    count: Dim
    od: Dim
    thickness: Dim
    length: Dim              # ヘッダープレート上面から先端まで
    gap_ratio: Dim           # 隙間 = 比 × od
    protrusion_ratio: Dim    # 突き出し = 比 × od
    trim_allowance: Dim      # 製作時の切り詰め代


@dataclass(frozen=True)
class Clamp:
    mid_position: Dim        # ヘッダープレート上面から、管長に対する比（0〜1）
    tip_thickness: Dim
    mid_thickness: Dim
    bolt: Choice             # 先端の意匠ボルト
    bolt_length: Dim


@dataclass(frozen=True)
class Header:
    thickness: Dim
    hole_clearance: Dim      # 管を通す穴（ヘッダープレート・両クランプ）の、管外径に対する直径方向の逃げ


@dataclass(frozen=True)
class Flange:
    thickness: Dim
    bolt_count: Dim
    bolt: Choice
    bolt_phase: Dim          # 管に対する位相（度）
    bolt_seat: Dim           # 胴外面からボルト中心まで
    bolt_length: Dim


@dataclass(frozen=True)
class Plate:
    margin: Dim              # 管外面・ボルトの中心から板縁までの片側の縁（ボルトの中心と管外面の間もこの値以上）
    max_over_shell: Dim      # 板の外径の上限 = 胴外径 + この値


@dataclass(frozen=True)
class Gasket:
    thickness: Dim


@dataclass(frozen=True)
class Bar:
    width: Dim
    thickness: Dim


@dataclass(frozen=True)
class Band:
    bar: Bar
    bolt: Choice
    bolt_length: Dim
    rubber: Dim              # 胴との間に挟むゴムシートの厚み
    above_flange: Dim        # フランジ上面からバンド下端まで
    gap: Dim                 # 分割面ごとの締め代（2 つの半環の耳の間の隙間）


@dataclass(frozen=True)
class Pad:
    width: Dim
    depth: Dim
    thickness: Dim


@dataclass(frozen=True)
class Cradle:
    bar: Bar
    clearance: Dim           # 胴バンド外面からフレーム内面までの逃げ
    handle_length: Dim       # 後側の横桟の外面から、グリップの中心まで
    grip_dia: Dim
    pad: Pad


@dataclass(frozen=True)
class Mount:
    type: Choice             # ホルダー受けの型（L ロッド径）
    body_dia: Dim            # 簡略形状の径
    body_height: Dim


@dataclass(frozen=True)
class GatlingSpec:
    head: Head
    shell: Shell
    edge: Edge
    hoop: Hoop
    lug: Lug
    tube: Tube
    clamp: Clamp
    header: Header
    flange: Flange
    plate: Plate
    gasket: Gasket
    band: Band
    cradle: Cradle
    mount: Mount
    tuning_target: Choice
    finish: Choice


_REAL = "置き値（実物を測るまで）"
_RIM = "リムを浅く。ユーザーの見立て。試作で詰める（D-20）"
_HOOP_PIPE = "手すり用 #400 研磨管 φ25.4 × t1.5（D-20）"

SPEC = GatlingSpec(
    head=Head(
        model=Choice("6 インチ コンサートタム用ヘッド（型番未定）", Source.PROVISIONAL, "ヘッドの型番を決めるまで"),
        fit_id=provisional(152.4, "ヘッドの型番を決めるまで。6 インチの呼び径を置いた"),
        fit_clearance=design(0.4, "胴に被せる逃げ"),
        film_mil=provisional(7.5, "ヘッドの型番を決めるまで"),
        collar_wall=provisional(1.5, "ヘッドの型番を決めるまで"),
        collar_height=provisional(8, "ヘッドの型番を決めるまで"),
        f01_range=(design(250, "非結合の (0,1)"), design(400, "非結合の (0,1)")),
        loss_factor=provisional(0.02, "膜の損失係数。実測するまで"),
    ),
    shell=Shell(thickness=design(1.2), plenum_height=design(100)),
    edge=Edge(angle=design(45), radius=design(1.5), height=design(10), width=design(4, "胴より厚く取って 45° の面を切る")),
    hoop=Hoop(
        inner=HoopRing(thickness=provisional(4, _RIM), height=provisional(8, _RIM)),
        outer=HoopPipe(od=design(25.4, _HOOP_PIPE), thickness=design(1.5, _HOOP_PIPE)),
        gap=design(10, "ロッドとその頭が通る間隔（D-20）"),
        seat=design(1.0, "フレッシュフープの上面に掛かる幅（環の肉厚 head.collar_wall の内側に収める。hoop_seat が見る）"),
        takeup=design(5, "チューニングでヘッドとフープを引き下ろす代"),
        ear=Ear(count=design(6, "ラグ数と同じ"), width=design(20), thickness=design(6),
                hole_clearance=design(1.0, "ロッド通し穴の逃げ")),
    ),
    lug=Lug(
        model=Choice("単穴の円筒ラグ（型番未定）", Source.PROVISIONAL, "実物 1 セットを測るまで。メーカーは固定しない（D-21）"),
        body_dia=provisional(16, _REAL),
        foot_dia=provisional(12, _REAL),
        height=provisional(35, _REAL),
        thread=Choice("#12-24", Source.PROVISIONAL, _REAL),
        count=design(6, "管の本数と方位を揃える"),
        standoff=provisional(10, _REAL),
        hole_dia=provisional(5, _REAL),
        rod_length=provisional(50, _REAL),
        rod_head_dia=provisional(9, _REAL),
        rod_head_height=provisional(5, _REAL),
    ),
    tube=Tube(
        count=design(6, "D-09"),
        od=design(38.1, "手すり用 #400 研磨管"),
        thickness=design(1.2, "手すり用 #400 研磨管"),
        length=provisional(450, "結合モデルで 400〜600 を振ってから決める（PR 4）"),
        gap_ratio=provisional(0.4, "viewer で見て決める"),
        protrusion_ratio=design(1.0),
        trim_allowance=design(30, "D-14"),
    ),
    clamp=Clamp(
        mid_position=design(0.55), tip_thickness=design(6), mid_thickness=design(3),
        bolt=Choice("M5", Source.DESIGN, "意匠ボルト"), bolt_length=design(6, "先端クランプの厚みに揃える"),
    ),
    header=Header(thickness=design(6, "D-16"), hole_clearance=design(0.2, "溶接前の挿入の逃げ")),
    flange=Flange(
        thickness=design(6, "D-16"), bolt_count=design(6), bolt=Choice("M6", Source.DESIGN),
        bolt_phase=design(30, "管に対する位相。D-17"), bolt_seat=design(10, "D-17"),
        bolt_length=design(12, "ISO 4762 の定尺。フランジ 6 + ガスケット 1 + ヘッダーのねじ込み 5"),
    ),
    plate=Plate(margin=design(8), max_over_shell=design(60)),
    gasket=Gasket(thickness=design(1)),
    band=Band(
        bar=Bar(width=design(25), thickness=design(6)), bolt=Choice("M6", Source.DESIGN),
        bolt_length=design(12, "耳 6 + 締め代 1.5 + ねじ込み 4.5"), rubber=design(1, "胴との間に挟むゴムシート"),
        above_flange=design(12, "フランジのボルトを抜ける空き（頭の高さ 6 + ねじ込み 5 = 11）"),
        gap=design(1.5, "耳どうしが当たる前にゴムと胴を締める代（ゴム 1 mm を 0.4 潰すと分割面 1 つあたり約 1.3 縮む）"),
    ),
    cradle=Cradle(
        bar=Bar(width=design(25), thickness=design(6)), clearance=design(15), handle_length=design(120),
        grip_dia=provisional(28, "viewer で握りを見て決める"),
        pad=Pad(width=design(60), depth=design(60), thickness=design(6)),
    ),
    mount=Mount(
        type=Choice("L ロッド 12.7", Source.PROVISIONAL, "手持ちのホルダーに合わせる"),
        body_dia=provisional(40, "ホルダー受けの型が決まるまで"),
        body_height=provisional(30, "ホルダー受けの型が決まるまで"),
    ),
    tuning_target=Choice("unison", Source.DESIGN, "§5.4 で定義（PR 4）"),
    finish=Choice("#400 サテン", Source.DESIGN, "D-15"),
)


def override(spec: GatlingSpec, **values: Any) -> GatlingSpec:
    """`override(spec, **{"tube.length": 500})`、または `override(spec, tube__length=500)`。

    `__` は `.` に読み替える（キーワード引数に `.` は書けない）。差し替えた葉は元の出典を継ぐ。
    """
    return _override(spec, {k.replace("__", "."): v for k, v in values.items()})
