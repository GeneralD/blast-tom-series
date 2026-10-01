"""胴バンド（2 分割）の形状。"""

from __future__ import annotations

import cadquery as cq
import pytest
from gatling.params import SPEC
from gatling.placement import BAND_SPLIT, band_bolt_x, band_tab_length
from gatling.shapes.mount import band


def _inside(part, x, y, z):
    return any(s.isInside(cq.Vector(x, y, z)) for s in part.solids().vals())


def test_the_band_is_two_separate_halves_around_the_shell():
    b = band(SPEC)
    assert BAND_SPLIT == 2 and b.solids().size() == 2
    box = b.val().BoundingBox()
    assert (box.zmin, box.zmax) == pytest.approx((19, 44))
    assert box.ylen == pytest.approx(166, abs=1e-3)                           # 外径 φ166（胴 152 + ゴム 2 + 帯 6 × 2）
    assert box.xlen == pytest.approx(2 * (83 + band_tab_length(SPEC)), abs=1e-3)      # 両側の耳


def test_the_halves_leave_a_gap_at_each_split_so_the_bolts_can_squeeze_the_rubber():
    b = band(SPEC)
    zc = 31.5
    assert not _inside(b, 80, 0, zc) and not _inside(b, -80, 0, zc)               # 分割面（y = 0）の帯は空き
    assert not _inside(b, band_bolt_x(SPEC) + 5, 0, zc)                            # 耳どうしの間も空き
    assert _inside(b, 80, 1.0, zc) and _inside(b, 80, -1.0, zc)                     # 隙間は ±0.75（band.gap 1.5）
    assert _inside(b, band_bolt_x(SPEC) + 5, 0.8, zc) and _inside(b, band_bolt_x(SPEC) + 5, -0.8, zc)


def test_the_halves_split_on_the_xz_plane_and_hug_the_rubber_sheet():
    b = band(SPEC)
    assert _inside(b, 0, 80, 25) and _inside(b, 0, -80, 25)                   # 帯の肉（r = 77〜83）
    assert not _inside(b, 0, 70, 25) and not _inside(b, 0, 84, 25)            # 胴とゴムの側、外側
    low, high = sorted(solid.Center().y for solid in b.solids().vals())
    assert low < 0 < high                                                     # +Y 側と −Y 側の半環


def test_each_tab_has_a_clearance_hole_in_one_half_and_a_tap_drill_in_the_other():
    b = band(SPEC)
    x, zc = band_bolt_x(SPEC), 31.5
    for side in (1, -1):
        assert not _inside(b, side * x, 3, zc) and not _inside(b, side * x, -3, zc)          # 軸の位置は穴
        assert _inside(b, side * x + 3.2, 3, zc) is False                                    # +Y 側は φ6.6（中心から 3.3）
        assert _inside(b, side * x + 3.2, -3, zc) is True                                    # −Y 側は下穴 φ5（中心から 2.5）


def test_the_tab_is_as_long_as_two_bolt_heads():
    assert band_tab_length(SPEC) == pytest.approx(20) and band_bolt_x(SPEC) == pytest.approx(93)
