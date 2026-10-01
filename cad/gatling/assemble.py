"""組立。部品名 → 形状（組立座標系、員数ぶんの solid をすべて置く）。"""

from __future__ import annotations

import cadquery as cq

from .params import GatlingSpec
from .shapes import body, bundle, hoop, mount, purchased


def assembly(spec: GatlingSpec) -> dict[str, cq.Workplane]:
    """上から順。キーは `parts()` の `PartInfo.name` と 1:1。"""
    return {
        "head": purchased.head(spec),
        "hoop_inner": hoop.hoop_inner(spec),
        "hoop_outer": hoop.hoop_outer(spec),
        "ear": hoop.ear(spec),
        "edge": body.edge(spec),
        "shell": body.shell(spec),
        "lug": purchased.lug(spec),
        "rod": purchased.rod(spec),
        "band": mount.band(spec),
        "bolt_band": purchased.bolt_band(spec),
        "cradle": mount.cradle(spec),
        "pad": mount.pad(spec),
        "holder": purchased.holder(spec),
        "flange": bundle.flange(spec),
        "bolt_flange": purchased.bolt_flange(spec),
        "gasket": bundle.gasket(spec),
        "header": bundle.header(spec),
        "tube": bundle.tube(spec),
        "clamp_mid": bundle.clamp_mid(spec),
        "clamp_tip": bundle.clamp_tip(spec),
        "bolt_tip": purchased.bolt_tip(spec),
    }
