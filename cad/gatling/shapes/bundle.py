"""管束まわり: ヘッダープレート・胴底フランジ・ガスケット・管・管クランプ。"""

from __future__ import annotations

import cadquery as cq

from ..derived import derive
from ..fasteners import lookup_screw
from ..params import GatlingSpec
from ..placement import flange_bolt_points, levels, tip_bolt_points, tube_points
from .common import cylinders, disc, ring


def _tube_hole_d(spec: GatlingSpec) -> float:
    return float(spec.tube.od) + float(spec.header.hole_clearance)


def header(spec: GatlingSpec) -> cq.Workplane:
    """プレナムの蓋。管の穴 6 と、フランジと同じボルト円の M6 下穴 6。"""
    z, d = levels(spec), derive(spec)
    body = disc(float(d.plate_od) / 2, z.header_bottom, 0)
    body = body.cut(cylinders(tube_points(spec), _tube_hole_d(spec), z.header_bottom, 0))
    return body.cut(cylinders(flange_bolt_points(spec), float(lookup_screw(spec.flange.bolt).tap_drill), z.header_bottom, 0))


def _flange_ring(spec: GatlingSpec, z0: float, z1: float) -> cq.Workplane:
    d = derive(spec)
    body = ring(float(d.plate_od) / 2, float(d.shell_id) / 2, z0, z1)
    return body.cut(cylinders(flange_bolt_points(spec), float(lookup_screw(spec.flange.bolt).clearance), z0, z1))


def flange(spec: GatlingSpec) -> cq.Workplane:
    """胴底の外向きフランジ（D-17）。内径は胴の内径、外径はヘッダープレートと同じ。"""
    z = levels(spec)
    return _flange_ring(spec, z.gasket_top, z.flange_top)


def gasket(spec: GatlingSpec) -> cq.Workplane:
    """シリコーン 1 mm。フランジと同形。"""
    return _flange_ring(spec, 0, levels(spec).gasket_top)


def tube(spec: GatlingSpec) -> cq.Workplane:
    """管。上端がヘッダープレートの上面、先端が下。設計長（切り詰め後）で作る。"""
    t = spec.tube
    r = float(t.od) / 2
    z = levels(spec)
    return (cq.Workplane("XY").workplane(offset=z.tube_tip).pushPoints(tube_points(spec))
            .circle(r).circle(r - float(t.thickness)).extrude(-z.tube_tip))


def clamp_mid(spec: GatlingSpec) -> cq.Workplane:
    """中間クランプ（環）。管の穴 6 と中央の穴。"""
    z, d = levels(spec), derive(spec)
    body = ring(float(d.clamp_od) / 2, float(d.clamp_hole_d) / 2, z.mid_bottom, z.mid_top)
    return body.cut(cylinders(tube_points(spec), _tube_hole_d(spec), z.mid_bottom, z.mid_top))


def clamp_tip(spec: GatlingSpec) -> cq.Workplane:
    """先端クランプ（円盤）。管の穴 6 と、管の間の M5 下穴 6（意匠ボルト）。"""
    z, d = levels(spec), derive(spec)
    body = disc(float(d.clamp_od) / 2, z.tip_bottom, z.tip_top)
    body = body.cut(cylinders(tube_points(spec), _tube_hole_d(spec), z.tip_bottom, z.tip_top))
    return body.cut(cylinders(tip_bolt_points(spec), float(lookup_screw(spec.clamp.bolt).tap_drill), z.tip_bottom, z.tip_top))
