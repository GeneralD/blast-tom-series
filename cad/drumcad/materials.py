"""材質。密度は g/mm³。"""

from __future__ import annotations

from dataclasses import dataclass

import cadquery as cq


@dataclass(frozen=True)
class Material:
    name: str
    density: float  # g/mm³


SUS304 = Material("ステンレス SUS304", 7.93e-3)
A6063 = Material("アルミ A6063", 2.70e-3)


def mass_g(part: cq.Workplane, material: Material) -> float:
    """部品（Workplane 上の全ソリッド）の質量（g）。"""
    volume = sum(shape.Volume() for shape in part.vals())
    return volume * material.density
