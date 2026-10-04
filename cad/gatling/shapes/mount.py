"""マウント（D-22）: 胴に溶接した当て板（左右）・コの字の管の腕・ホルダー受けのブロック・スペードグリップと端板。

溶接で接する部品は体積を共有しない。腕は当て板の外面に平らな端で接し、ブロックとグリップは腕の外形の円柱
（`_envelope`）で切って、腕の管の外面に沿わせる（鞍形・魚の口形の突き合わせ溶接の見立て）。
"""

from __future__ import annotations

import cadquery as cq

from ..params import GatlingSpec
from ..placement import arm_path, grip_poses, holder_centre, levels, pad_angles, radii
from ..tubepath import Line
from .common import compound, ring

_V = cq.Vector


def pad(spec: GatlingSpec) -> cq.Workplane:
    """当て板（左右 2 枚）。幅 `width` × 高さ `height` の角を `corner` で丸めた矩形の柱を、胴の外面から板厚ぶんの円筒殻で切った曲げ板。

    胴の外面に沿って全周すみ肉溶接する（胴に穴は開けない）。板の中心の高さは腕の管の中心と同じ（胴の中ほど）。
    """
    z, r, p = levels(spec), radii(spec), spec.pad
    reach = r.pad_outer + 1.0
    blank = (cq.Workplane("XY").box(reach, float(p.width), float(p.height)).edges("|X").fillet(float(p.corner))
             .translate((reach / 2, 0, z.arm_centre)))
    plate = blank.intersect(ring(r.pad_outer, r.shell, z.pad_bottom - 1, z.pad_top + 1))
    return compound([plate.rotate((0, 0, 0), (0, 0, 1), a) for a in pad_angles(spec)])


def _sweep(spec: GatlingSpec, bore: bool) -> cq.Workplane:
    """腕の経路（`placement.arm_path`）に沿って管の断面を掃引した固体。`bore` が偽なら中実（他の部品を切る刃物）。"""
    z, od, wall = levels(spec).arm_centre, float(spec.arm.pipe.od), float(spec.arm.pipe.thickness)
    edges = []
    for part in arm_path(spec):
        if isinstance(part, Line):
            if part.length > 1e-9:
                edges.append(cq.Edge.makeLine(_V(*part.a, z), _V(*part.b, z)))
            continue
        point = lambda t: _V(*part.point(t), z)
        edges.append(cq.Edge.makeThreePointArc(point(0.0), point(0.5), point(1.0)))
    first = next(p for p in arm_path(spec) if isinstance(p, Line) and p.length > 1e-9)
    length = first.length
    direction = ((first.b[0] - first.a[0]) / length, (first.b[1] - first.a[1]) / length, 0.0)
    plane = cq.Plane(origin=(*first.a, z), xDir=(0, 0, 1), normal=direction)
    profile = cq.Workplane(plane).circle(od / 2)
    if bore:
        profile = profile.circle(od / 2 - wall)
    return profile.sweep(cq.Workplane(obj=cq.Wire.assembleEdges(edges)))


def arm(spec: GatlingSpec) -> cq.Workplane:
    """コの字の腕。左右の当て板の外面から半径方向に出て、後ろ（−Y）へ平行に伸び、後ろで横に渡る 1 本の管。角は曲げ（円弧）で丸める。"""
    return _sweep(spec, bore=True)


def _envelope(spec: GatlingSpec) -> cq.Workplane:
    return _sweep(spec, bore=False)


def block(spec: GatlingSpec) -> cq.Workplane:
    """ホルダー受けのブロック（機関部の見立て）。後ろの横渡しの中央に載る四角い箱で、下面は腕の管の外形で切って鞍形に抱く。

    箱は管の中心の高さから上へ `height`。下の半分は管の脇（管の外形の外）に残る。
    """
    z, b = levels(spec), spec.block
    x, y = holder_centre(spec)
    box = cq.Workplane("XY").box(float(b.width), float(b.depth), float(b.height)).translate((x, y, z.arm_centre + float(b.height) / 2))
    return box.cut(_envelope(spec))


def _cylinder(origin: tuple[float, float, float], direction: tuple[float, float, float], radius: float, length: float) -> cq.Workplane:
    return cq.Workplane("XY").newObject([cq.Solid.makeCylinder(radius, length, _V(*origin), _V(*direction))])


def grip(spec: GatlingSpec) -> cq.Workplane:
    """スペードグリップ（左右 2 本）の管。付け根（後ろの角の円弧の中央、中心線の上）から斜め下・後ろ・外へ `length`。
    付け根は腕の管の外形で切って、腕に沿わせる（魚の口形）。端は開いたままで、端板（`grip_cap`）を溶接する。"""
    r, wall = float(spec.arm.pipe.od) / 2, float(spec.arm.pipe.thickness)
    envelope = _envelope(spec)
    tubes = []
    for pose in grip_poses(spec):
        tube = _cylinder(pose.start, pose.direction, r, pose.length).cut(_cylinder(pose.start, pose.direction, r - wall, pose.length))
        tubes.append(tube.cut(envelope))
    return compound(tubes)


def grip_cap(spec: GatlingSpec) -> cq.Workplane:
    """スペードグリップの端板（丸い円盤。溶接）。管の端に載り、管の外径と同じ径。"""
    r = float(spec.arm.pipe.od) / 2
    caps = []
    for pose in grip_poses(spec):
        origin = tuple(s + pose.length * d for s, d in zip(pose.start, pose.direction))
        caps.append(_cylinder(origin, pose.direction, r, pose.cap))
    return compound(caps)
