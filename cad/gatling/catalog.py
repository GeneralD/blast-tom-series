"""部品表の元（`parts(spec)`）。`assembly()` の部品名と 1:1 で、員数・規格・寸法は SPEC から作る（D-18）。"""

from __future__ import annotations

from drumcad.contract import PartInfo
from drumcad.materials import SUS304, Material
from drumcad.stock import nearest

from .derived import derive
from .params import GatlingSpec
from .placement import PAD_COUNT, radii
from .strength import root_load

SILICONE = Material("シリコーンゴム", 1.2e-3)                       # g/mm³（概算。ガスケットの質量用）
PURCHASED = Material("既製品（材質は実物で確認）", 0.0)               # 既製品の質量は部品表に載せない


HEAD_COLOR = "#d0121b"                                                # viewer のヘッドの色（見た目のイメージ）
HEAD_OPACITY = 0.5                                                   # 半透明にして、下のフープと胴が見えるようにする


def fmt(value: float) -> str:
    return f"{float(value):g}"


def parts(spec: GatlingSpec) -> list[PartInfo]:
    """上から順に。員数・規格・寸法は SPEC から作り、リテラルにしない。"""
    d, r = derive(spec), radii(spec)
    t, s, c = spec.tube, spec.shell, spec.clamp
    stock, _ = nearest(float(t.od), float(t.thickness))
    pipe = spec.hoop.outer
    hoop_stock, _ = nearest(float(pipe.od), float(pipe.thickness))
    arm_stock, _ = nearest(float(spec.arm.pipe.od), float(spec.arm.pipe.thickness))
    load = root_load(spec)
    n_tube, n_lug = int(float(t.count)), int(float(spec.lug.count))
    n_bolt = int(float(spec.flange.bolt_count))
    sheet = "SUS304 板"
    bar = "SUS304 平角材"

    def fab(name, label, color, count, section, explode, standard, dimensions, material=SUS304):
        return PartInfo(name, label, color, material, "fabricated", count, section, explode, standard, dimensions)

    def buy(name, label, color, count, explode, standard, dimensions="", opacity=1.0):
        return PartInfo(name, label, color, PURCHASED, "purchased", count, "none", explode, standard, dimensions, opacity)

    return [
        # ヘッドは既製品。赤の半透明は見た目のイメージで、型番・膜厚・面密度とは関係ない
        buy("head", "ヘッド 6\"", HEAD_COLOR, 1, (0, 0, 1.2), spec.head.model.value, f"フレッシュフープ内径 φ{fmt(spec.head.fit_id)}",
            opacity=HEAD_OPACITY),
        fab("hoop_inner", "内リング", "#aab4c0", 1, "radial", (0, 0, 0.8), f"{bar}を丸めて TIG 突合せ",
            f"内径 φ{fmt(2 * r.hoop_in_inner)} × 幅{fmt(spec.hoop.inner.height)} × t{fmt(spec.hoop.inner.thickness)}"),
        fab("hoop_outer", "外リング（質量リング）", "#9aa5b3", 1, "radial", (0, 0, 0.8), f"{hoop_stock.family}を曲げて TIG 突合せ",
            f"φ{fmt(pipe.od)} × t{fmt(pipe.thickness)}、内径 φ{fmt(2 * r.hoop_out_inner)}（中心径 φ{fmt(2 * r.hoop_out_centre)}）"),
        fab("ear", "受金", "#c9ced6", int(float(spec.hoop.ear.count)), "outline", (0, 0, 0.8), f"{sheet} レーザー切り（外端を管の形に切り欠く）",
            f"{fmt(spec.hoop.ear.width)} × {fmt(r.hoop_out_centre - r.hoop_in_outer)} × t{fmt(spec.hoop.ear.thickness)}"),
        fab("edge", "ベアリングエッジ環", "#d3d8df", 1, "none", (0, 0, 0.4), "SUS304 旋削（胴に溶接後、エッジを仕上げ）",
            f"φ{fmt(d.shell_od)} × 幅{fmt(spec.edge.width)} × H{fmt(spec.edge.height)}"),
        fab("shell", "プレナム胴", "#c9ced6", 1, "radial", (0, 0, 0), f"{sheet}を丸めて TIG 突合せ",
            f"φ{fmt(d.shell_od)} × t{fmt(s.thickness)} × H{fmt(s.plenum_height)}"),
        buy("lug", "ラグ", "#6b7280", n_lug, (0, 0, 0), spec.lug.model.value,
            f"φ{fmt(spec.lug.body_dia)} × 厚み{fmt(spec.lug.depth)}"),
        buy("rod", "テンションロッド", "#8b93a0", n_lug, (0, 0, 0.3), f"テンションロッド {spec.lug.thread.value}",
            f"L{fmt(spec.lug.rod_length)}（頭 φ{fmt(spec.lug.rod_head_dia)} × H{fmt(spec.lug.rod_head_height)}）"),
        fab("pad", "当て板", "#c9ced6", PAD_COUNT, "outline", (0, -0.3, 0), f"{sheet}をレーザー切りして胴の外面に沿って曲げ、胴に全周すみ肉溶接",
            f"{fmt(spec.pad.width)} × {fmt(spec.pad.height)} × t{fmt(spec.pad.thickness)}、角 R{fmt(spec.pad.corner)}、方位 ±X 軸から後ろへ {fmt(spec.pad.angle)}°"),
        fab("arm", "腕（コの字の管）", "#9aa5b3", 1, "plan", (0, -0.6, 0), f"{arm_stock.family}を曲げて当て板に溶接",
            f"φ{fmt(spec.arm.pipe.od)} × t{fmt(spec.arm.pipe.thickness)}、曲げ R{fmt(spec.arm.bend_radius)}、後ろの横渡しの中心線まで {fmt(spec.arm.rear)}"
            f"（付け根の曲げ {float(load.moment_impact) / 1000:.1f} N·m、衝撃込み。D-22）"),
        fab("block", "ホルダー受けのブロック", "#b6bcc6", 1, "outline", (0, -0.6, 0.3), f"{sheet}の箱（または角材）を腕に溶接",
            f"{fmt(spec.block.width)} × {fmt(spec.block.depth)} × H{fmt(spec.block.height)}（管の中心から上面）"),
        fab("grip", "スペードグリップ", "#9aa5b3", PAD_COUNT, "none", (0, -0.9, -0.3), f"{arm_stock.family}を斜めに切って腕の後ろの角に溶接",
            f"φ{fmt(spec.arm.pipe.od)} × t{fmt(spec.arm.pipe.thickness)} × L{fmt(spec.grip.length)}、下へ {fmt(spec.grip.drop)}°・外へ {fmt(spec.grip.out)}°"),
        fab("grip_cap", "グリップの端板", "#c9ced6", PAD_COUNT, "outline", (0, -1.0, -0.3), f"{sheet}を円盤に切って管の端に溶接",
            f"φ{fmt(spec.arm.pipe.od)} × t{fmt(spec.grip.cap)}"),
        buy("holder", "ホルダー受け", "#4b5563", 1, (0, -0.6, 0.3), spec.mount.type.value,
            f"φ{fmt(spec.mount.body_dia)} × H{fmt(spec.mount.body_height)}、つまみ φ{fmt(spec.mount.knob_dia)} × {fmt(spec.mount.knob_length)}"),
        fab("flange", "胴底フランジ", "#c9ced6", 1, "radial", (0, 0, -0.25), f"{sheet} レーザー切り（合わせ面は溶接後に平面出し）",
            f"φ{fmt(d.plate_od)} / φ{fmt(d.shell_id)} × t{fmt(spec.flange.thickness)}"),
        buy("bolt_flange", f"ボルト {spec.flange.bolt.value}（フランジ）", "#3a3f47", n_bolt, (0, 0, 0.6),
            f"六角穴付きボルト {spec.flange.bolt.value}", f"L{fmt(spec.flange.bolt_length)}"),
        fab("gasket", "ガスケット", "#7c8aa0", 1, "none", (0, 0, -0.45), "シリコーンシートから抜く",
            f"φ{fmt(d.plate_od)} / φ{fmt(d.shell_id)} × t{fmt(spec.gasket.thickness)}", SILICONE),
        fab("header", "ヘッダープレート", "#c9ced6", 1, "outline", (0, 0, -0.65), f"{sheet} レーザー切り（合わせ面は溶接後に平面出し）",
            f"φ{fmt(d.plate_od)} × t{fmt(spec.header.thickness)}"),
        fab("tube", "管", "#dfe3e8", n_tube, "none", (0, 0, -0.65), stock.family,
            f"φ{fmt(t.od)} × t{fmt(t.thickness)} × L{fmt(d.tube_cut_length)}（組立後に L{fmt(t.length)} へ切り詰め）"),
        fab("clamp_mid", "中間クランプ", "#aab4c0", 1, "outline", (0, 0, -0.65), f"{sheet} レーザー切り",
            f"φ{fmt(d.clamp_od)} / φ{fmt(d.clamp_hole_d)} × t{fmt(c.mid_thickness)}"),
        fab("clamp_tip", "先端クランプ", "#aab4c0", 1, "outline", (0, 0, -0.65), f"{sheet} レーザー切り",
            f"φ{fmt(d.clamp_od)} × t{fmt(c.tip_thickness)}"),
        buy("bolt_tip", f"意匠ボルト {c.bolt.value}（先端）", "#1f2328", n_tube, (0, 0, -0.65),
            f"黒色 SUS 六角穴付きボルト {c.bolt.value}", f"L{fmt(c.bolt_length)}"),
    ]
