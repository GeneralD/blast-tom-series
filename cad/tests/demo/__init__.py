"""テスト用の最小機種: 筒 1 本と、その下に置く円盤 1 枚。

契約（仕様 §4.4）を満たす最小限の例。実機種はこれと同じ 7 つの名前を公開する。
"""

from __future__ import annotations

from dataclasses import dataclass

import cadquery as cq
from drumcad.checks import Issue
from drumcad.contract import BomRow, PartInfo
from drumcad.dims import Choice, Dim, Source, design, override as _override, provisional
from drumcad.materials import SUS304


@dataclass(frozen=True)
class Shell:
    od: Dim
    thickness: Dim
    height: Dim


@dataclass(frozen=True)
class Plate:
    od: Dim
    thickness: Dim


@dataclass(frozen=True)
class DemoSpec:
    shell: Shell
    plate: Plate
    lugs: Dim
    finish: Choice


SPEC = DemoSpec(
    shell=Shell(od=design(152.4), thickness=design(1.2), height=design(100)),
    plate=Plate(od=design(160), thickness=provisional(6, "3 か 6 か決めていない")),
    lugs=design(6),
    finish=Choice("#400", Source.DESIGN),
)


def name(spec: DemoSpec) -> str:
    return f"demo-{round(spec.shell.od / 25.4)}-{int(spec.lugs)}"


def override(spec: DemoSpec, **values: object) -> DemoSpec:
    return _override(spec, {k.replace("__", "."): v for k, v in values.items()})


def assembly(spec: DemoSpec) -> dict[str, cq.Workplane]:
    r, t, h = float(spec.shell.od) / 2, float(spec.shell.thickness), float(spec.shell.height)
    shell = cq.Workplane("XY").circle(r).circle(r - t).extrude(h)
    plate = (cq.Workplane("XY").circle(float(spec.plate.od) / 2)
             .extrude(float(spec.plate.thickness)).translate((0, 0, -float(spec.plate.thickness))))
    # 同じ形を 3 個、組立座標系の別々の位置に置く（員数 > 1 の部品の例）。
    # eachpoint は置いた個数ぶんの solid を Workplane に積む（`val()` は先頭の 1 個しか返さない）
    studs = (cq.Workplane("XY").pushPoints([(r + 10, 0), (-(r + 10), 0), (0, r + 10)])
             .eachpoint(lambda loc: cq.Solid.makeCylinder(4, h).moved(loc)))
    return {"shell": shell, "plate": plate, "stud": studs}


def parts(spec: DemoSpec) -> list[PartInfo]:
    return [
        PartInfo("shell", "胴", "#c9ced6", SUS304, "fabricated", 1, "radial", (0, 0, 1),
                 standard="手すり用 #400 研磨管", dimensions="φ152.4 × t1.2 × L100"),
        PartInfo("plate", "底板", "#8f99a6", SUS304, "fabricated", 1, "outline", (0, 0, -1)),
        PartInfo("stud", "スタッド", "#b0b6c0", SUS304, "fabricated", 3, "none", (1, 0, 0)),
    ]


def bom(spec: DemoSpec) -> list[BomRow]:
    return [
        BomRow("ラグ", "purchased", None, "DW タレットラグ", "", int(spec.lugs), "DWSM2200", 100.0),
    ]


def issues(spec: DemoSpec) -> list[Issue]:
    found = []
    if spec.plate.od < spec.shell.od:
        found.append(Issue(True, "底板が胴より小さく、蓋にならない"))
    if spec.shell.height < 50:
        found.append(Issue(False, "胴が低い"))
    return found
