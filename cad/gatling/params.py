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
    body_dia: Dim            # 円盤（胴の外から見て丸いタレット形のラグ。軸は胴の半径方向）の径 = ラグの高さ。胴の取付穴はその中心
    depth: Dim               # 円盤の厚み（半径方向。胴の外面から外側の面まで）。胴の内側から 1 本のねじで中心を留める
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
class Pad:
    """当て板（左右 2 枚）。胴の外面に沿って曲げた SUS304 板を、胴に全周すみ肉溶接する（胴に穴を開けない。D-22）。"""

    angle: Dim               # 方位: ±X 軸から後ろ（−Y）へ測る角度（度）。左右対称で、ラグを避けて置く
    width: Dim               # 板幅（曲げる前。ほぼ周方向）
    height: Dim              # 高さ。中心は胴（プレナム）の中ほど
    thickness: Dim
    corner: Dim              # 角の R（レーザー切りの角）


@dataclass(frozen=True)
class ArmPipe:
    """腕・グリップの管。外リングと同じ手すり用の研磨管。"""

    od: Dim
    thickness: Dim


@dataclass(frozen=True)
class Arm:
    """コの字の管の腕。左右の当て板から半径方向に出て、後ろへ平行に伸び、後ろで横に渡ってつながる。角は曲げで丸める。"""

    pipe: ArmPipe
    bend_radius: Dim         # 曲げ半径（管の中心線）
    stub: Dim                # 当て板の外面から、最初の曲がりの頂点（半径方向の線と後ろへの脚の交点）まで
    rear: Dim                # 胴の中心から、後ろの横渡しの管の中心線まで


@dataclass(frozen=True)
class Block:
    """ホルダー受けのブロック。後ろの横渡しの中央に溶接する四角い箱（機関部の見立て）。"""

    width: Dim               # X 方向
    depth: Dim               # Y 方向
    height: Dim              # 管の中心の高さから上面まで


@dataclass(frozen=True)
class Grip:
    """スペードグリップ（左右 2 本）。コの字の後ろの角から、斜め下・後ろ・外へ張り出す握り。端は丸い端板（キャップ）。"""

    length: Dim              # 管の長さ（付け根の中心線から端板の手前まで）
    drop: Dim                # 水平から下へ傾ける角度（度）
    out: Dim                 # 後ろ（−Y）から外へ開く角度（度）
    cap: Dim                 # 端板の厚み


@dataclass(frozen=True)
class Mount:
    type: Choice             # ホルダー受けの型（L ロッド径）
    body_dia: Dim            # 簡略形状の径
    body_height: Dim
    knob_dia: Dim            # 締めるつまみ（後ろへ水平に出す）の径
    knob_length: Dim         # つまみの長さ（本体の外面から）


@dataclass(frozen=True)
class Load:
    """付け根の強度の概算の入力（`strength.root_load`。検査ではなく仕様と D-22 の根拠）。"""

    mass: Dim                # ドラム全体の質量（kg）
    impact: Dim              # 衝撃係数


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
    pad: Pad
    arm: Arm
    block: Block
    grip: Grip
    mount: Mount
    load: Load
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
        model=Choice("単穴の丸形ラグ（型番未定）", Source.PROVISIONAL, "実物 1 セットを測るまで。メーカーは固定しない（D-21）"),
        body_dia=provisional(30, _REAL),
        depth=provisional(20, _REAL),
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
    pad=Pad(
        angle=design(30, "ラグ 6 個の間（ラグは 60° おき）。D-22"),
        width=design(40, "付け根の曲げの概算から（D-22）"), height=design(60, "付け根の曲げの概算から（D-22）"),
        thickness=provisional(2.5, "胴（1.2）への溶接で歪まないかを試作で確かめるまで"),
        corner=design(5, "レーザー切りの角 R"),
    ),
    arm=Arm(
        pipe=ArmPipe(od=design(25.4, _HOOP_PIPE), thickness=design(1.5, _HOOP_PIPE)),
        bend_radius=provisional(50.8, "曲げ屋の治具に合わせる。管径の 2 倍を置いた"),
        stub=provisional(45, "viewer で見て決める"),
        rear=provisional(160, "viewer で見て決める"),
    ),
    block=Block(
        width=provisional(60, "ホルダー受けの型が決まるまで"), depth=provisional(50, "ホルダー受けの型が決まるまで"),
        height=provisional(30, "viewer で見て決める"),
    ),
    grip=Grip(
        length=provisional(110, "viewer で握りを見て決める"), drop=provisional(30, "viewer で握りを見て決める"),
        out=provisional(15, "viewer で握りを見て決める"), cap=design(3, "溶接の端板"),
    ),
    mount=Mount(
        type=Choice("L ロッド 12.7", Source.PROVISIONAL, "手持ちのホルダーに合わせる"),
        body_dia=provisional(40, "ホルダー受けの型が決まるまで"),
        body_height=provisional(30, "ホルダー受けの型が決まるまで"),
        knob_dia=provisional(12, "ホルダー受けの型が決まるまで"),
        knob_length=provisional(25, "ホルダー受けの型が決まるまで"),
    ),
    load=Load(
        mass=provisional(10, "部品表の製作品の合計（約 8.0 kg）に既製品の概算（約 1 kg）を足して切り上げた置き値。実物の質量を測るまで"),
        impact=design(3, "ホルダーに載せるとき・運搬の衝撃の見込み"),
    ),
    tuning_target=Choice("unison", Source.DESIGN, "§5.4 で定義（PR 4）"),
    finish=Choice("#400 サテン", Source.DESIGN, "D-15"),
)


def override(spec: GatlingSpec, **values: Any) -> GatlingSpec:
    """`override(spec, **{"tube.length": 500})`、または `override(spec, tube__length=500)`。

    `__` は `.` に読み替える（キーワード引数に `.` は書けない）。差し替えた葉は元の出典を継ぐ。
    """
    return _override(spec, {k.replace("__", "."): v for k, v in values.items()})
