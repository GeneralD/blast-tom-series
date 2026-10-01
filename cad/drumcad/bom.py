"""部品表。製作品の行は形状と材質から build が作り（規格・寸法は `PartInfo` に機種が書く）、
既製品の行は機種が書く。"""

from __future__ import annotations

from .contract import BomRow, Model
from .materials import mass_g

_MADE = {"fabricated": "製作品", "purchased": "既製品"}


def full_bom(model: Model) -> list[BomRow]:
    parts = model.assembly()
    rows = []
    for info in model.parts():
        if info.made != "fabricated":
            continue
        rows.append(BomRow(info.label, "fabricated", info.material, info.standard, info.dimensions, info.count,
                           mass_g=mass_g(parts[info.name], info.material)))
    return rows + list(model.bom())


def bom_markdown(title: str, rows: list[BomRow]) -> str:
    lines = [f"# 部品表 — {title}", "",
             "| 部品 | 区分 | 材質 | 規格・型番の系統 | 寸法 | 員数 | 型番 | 質量 g（1 個） |",
             "|---|---|---|---|---|---|---|---|"]
    total = 0.0
    for r in rows:
        mass = f"{r.mass_g:.0f}" if r.mass_g is not None else ""
        if r.mass_g is not None:
            total += r.mass_g * r.count
        lines.append(f"| {r.name} | {_MADE[r.made]} | {r.material.name if r.material else ''} | "
                     f"{r.standard} | {r.dimensions} | {r.count} | {r.part_number} | {mass} |")
    lines += ["", f"合計質量（質量の分かる行のみ）: **{total / 1000:.2f} kg**", ""]
    return "\n".join(lines)
