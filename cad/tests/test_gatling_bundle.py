"""管束まわり（ヘッダープレート・フランジ・ガスケット・管・管クランプ）の形状。"""

from __future__ import annotations

import math

import cadquery as cq
import pytest
from gatling.params import SPEC, override
from gatling.shapes.bundle import clamp_mid, clamp_tip, flange, gasket, header, tube


def _volume(part):
    return sum(s.Volume() for s in part.vals())


def _z(part):
    box = part.val().BoundingBox()
    return round(box.zmin, 6), round(box.zmax, 6)


def _inside(part, x, y, z):
    return any(s.isInside(cq.Vector(x, y, z)) for s in part.solids().vals())


def test_the_header_is_a_disc_with_tube_holes_and_m6_tap_drills():
    h = header(SPEC)
    assert h.solids().size() == 1 and _z(h) == (-6, 0)
    assert h.val().BoundingBox().xlen == pytest.approx(188, abs=1e-3)
    expected = math.pi / 4 * 6 * (188**2 - 6 * 38.3**2 - 6 * 5.0**2)      # 管の穴 φ38.3（逃げ 0.2）、M6 の下穴 φ5
    assert _volume(h) == pytest.approx(expected, rel=1e-6)
    assert not _inside(h, 53.34, 0, -3) and _inside(h, 0, 0, -3)           # 管の穴は空き、中心は肉


def test_the_header_tap_drills_sit_on_the_flange_bolt_circle_between_the_tubes():
    """M6 の下穴 φ5 は、ボルト円 φ172 の上で管から 30° ずれた方位（D-17）。穴の縁は中心から 2.5。"""
    h = header(SPEC)
    for k in range(6):
        a = math.radians(30 + 60 * k)
        c, s = math.cos(a), math.sin(a)
        for r in (86, 86 - 2.4, 86 + 2.4):
            assert not _inside(h, r * c, r * s, -3), (k, r)                   # 下穴は空き
        assert _inside(h, (86 - 2.6) * c, (86 - 2.6) * s, -3) and _inside(h, (86 + 2.6) * c, (86 + 2.6) * s, -3)
        b = math.radians(60 * k)
        assert _inside(h, 86 * math.cos(b), 86 * math.sin(b), -3)            # 管の方位のボルト円上は肉


def test_the_flange_is_an_outward_ring_whose_bore_is_the_shell_bore():
    f = flange(SPEC)
    assert f.solids().size() == 1 and _z(f) == (1, 7)
    assert f.val().BoundingBox().xlen == pytest.approx(188, abs=1e-3)
    expected = math.pi / 4 * 6 * (188**2 - 149.6**2 - 6 * 6.6**2)          # 内径 = 胴の内径、M6 の通し穴 φ6.6
    assert _volume(f) == pytest.approx(expected, rel=1e-6)
    assert not _inside(f, 0, 0, 4) and _inside(f, 90, 0, 4) and not _inside(f, 86 * math.cos(math.pi / 6), 43, 4)


def test_the_gasket_has_the_flange_outline_and_is_1_mm_thick():
    g = gasket(SPEC)
    assert _z(g) == (0, 1)
    assert _volume(g) / 1 == pytest.approx(_volume(flange(SPEC)) / 6, rel=1e-6)    # 同形（厚みだけ 1/6）


def test_the_six_tubes_hang_from_the_header_top_to_the_tip():
    t = tube(SPEC)
    assert t.solids().size() == 6 and _z(t) == (-450, 0)
    assert _volume(t) == pytest.approx(6 * math.pi * (19.05**2 - 17.85**2) * 450, rel=1e-6)
    longer = tube(override(SPEC, tube__length=500))
    assert _z(longer) == (-500, 0)


def test_the_tubes_are_hollow_and_leave_the_gap_between_them():
    t = tube(SPEC)
    assert not _inside(t, 53.34, 0, -100) and _inside(t, 53.34 + 18.5, 0, -100)
    assert not _inside(t, 53.34 + 19.05 + 7, 0, -100)


def test_the_mid_clamp_is_a_ring_with_a_centre_hole_and_six_tube_holes():
    c = clamp_mid(SPEC)
    assert c.solids().size() == 1 and _z(c) == (pytest.approx(-250.5), pytest.approx(-247.5))
    assert c.val().BoundingBox().xlen == pytest.approx(160.78, abs=1e-3)
    expected = math.pi / 4 * 3 * (160.78**2 - 52.58**2 - 6 * 38.3**2)
    assert _volume(c) == pytest.approx(expected, rel=1e-4)
    assert not _inside(c, 0, 0, -249) and not _inside(c, 53.34, 0, -249)     # 中央の穴、管の穴
    assert _inside(c, 30, 0, -249)                                           # 2 つの穴の間は肉（縁 8 mm）


def test_the_tip_clamp_is_a_disc_with_six_tube_holes_and_six_m5_tap_drills_between_them():
    c = clamp_tip(SPEC)
    assert c.solids().size() == 1 and _z(c) == (pytest.approx(-411.9), pytest.approx(-405.9))
    expected = math.pi / 4 * 6 * (160.78**2 - 6 * 38.3**2 - 6 * 4.2**2)
    assert _volume(c) == pytest.approx(expected, rel=1e-4)
    assert _inside(c, 0, 0, -409) and not _inside(c, 53.34 * math.cos(math.pi / 6), 53.34 * 0.5, -409)   # 管の間の下穴は空き


def test_the_tubes_pass_through_the_header_and_both_clamps_without_overlapping_them():
    t = cq.Compound.makeCompound(tube(SPEC).solids().vals())
    for plate in (header(SPEC), clamp_mid(SPEC), clamp_tip(SPEC)):
        assert t.intersect(cq.Compound.makeCompound(plate.solids().vals())).Volume() == pytest.approx(0, abs=1e-6)
