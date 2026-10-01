"""形状関数が共有する小さな部品。"""

from __future__ import annotations

import cadquery as cq


def disc(r: float, z0: float, z1: float) -> cq.Workplane:
    return cq.Workplane("XY").workplane(offset=z0).circle(r).extrude(z1 - z0)


def ring(r_out: float, r_in: float, z0: float, z1: float) -> cq.Workplane:
    return cq.Workplane("XY").workplane(offset=z0).circle(r_out).circle(r_in).extrude(z1 - z0)


def cylinders(points: list[tuple[float, float]], dia: float, z0: float, z1: float) -> cq.Workplane:
    """`points` の各点に立てた円柱（穴あけの刃物にも、ボルトの軸にも使う）。"""
    return cq.Workplane("XY").workplane(offset=z0).pushPoints(points).circle(dia / 2).extrude(z1 - z0)


def cylinder(origin: tuple[float, float, float], direction: tuple[float, float, float],
             dia: float, length: float) -> cq.Workplane:
    """`origin` から `direction`（単位ベクトル）へ `length` 伸びる円柱。軸が Z でないボルトや穴に使う。"""
    return cq.Workplane("XY").newObject([cq.Solid.makeCylinder(dia / 2, length, cq.Vector(*origin), cq.Vector(*direction))])


def compound(solids: list[cq.Workplane]) -> cq.Workplane:
    """別々の solid を、数を保ったまま 1 つの Workplane にまとめる（`union` は接していれば 1 つに融合する）。"""
    return cq.Workplane("XY").newObject([cq.Compound.makeCompound([s for w in solids for s in w.solids().vals()])])


def around_z(part: cq.Workplane, angles: list[float]) -> cq.Workplane:
    """Z 軸の周りに `angles`（度）ぶん回した複製を、1 つの Workplane に集める。"""
    return compound([part.rotate((0, 0, 0), (0, 0, 1), a) for a in angles])
