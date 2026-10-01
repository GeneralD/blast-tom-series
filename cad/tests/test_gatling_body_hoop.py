"""胴・ベアリングエッジ環・ダブルフープの形状。"""

from __future__ import annotations

import math

import cadquery as cq
import pytest
from gatling.params import SPEC, override
from gatling.shapes.body import edge, shell
from gatling.shapes.hoop import ear, hoop_inner, hoop_outer


def _volume(part):
    return sum(s.Volume() for s in part.vals())


def _box(part):
    return part.val().BoundingBox()


def _inside(part, x, y, z):
    return any(s.isInside(cq.Vector(x, y, z)) for s in part.solids().vals())


def test_the_shell_is_a_thin_ring_between_the_flange_top_and_the_edge_ring():
    s = shell(SPEC)
    box = _box(s)
    assert s.solids().size() == 1 and (box.zmin, box.zmax) == pytest.approx((7, 107))
    assert box.xlen == pytest.approx(152, abs=1e-3)
    ring = math.pi / 4 * 100 * (152**2 - 149.6**2)
    assert _volume(s) == pytest.approx(ring - 12 * math.pi * 2.5**2 * 1.2, rel=2e-3)     # 肉厚 1.2、取付穴 12


def test_the_shell_has_two_mounting_holes_per_lug_at_the_lug_pitch():
    s = shell(SPEC)
    zc = (69.1905 + 104.1905) / 2                                   # ラグの高さの中央
    for angle in (0, 60, 120, 180, 240, 300):
        c, sn = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        for dz in (-12.5, 12.5):                                    # pitch 25
            assert not _inside(s, 75.4 * c, 75.4 * sn, zc + dz)      # 穴（壁の中ほど）は空き
        assert _inside(s, 75.4 * c, 75.4 * sn, zc)                   # 穴と穴の間は肉
    fewer = shell(override(SPEC, lug__count=3, hoop__ear__count=3))
    assert _volume(fewer) > _volume(s)                              # 穴が減れば肉は増える


def test_the_edge_ring_is_cut_to_a_45_degree_face_that_falls_toward_the_bore():
    e = edge(SPEC)
    box = _box(e)
    assert e.solids().size() == 1 and (box.zmin, box.zmax) == pytest.approx((107, 117))
    assert box.xlen == pytest.approx(152, abs=1e-3)
    for r in (72.5, 73.5, 74.0):                                  # 45° の面: 頂部（r = 74.5、z = 117）から内側へ 1 mm ごとに 1 mm 落ちる
        z_face = 117 - (74.5 - r)
        assert _inside(e, r, 0, z_face - 0.1) and not _inside(e, r, 0, z_face + 0.1)
    assert _inside(e, 75.9, 0, 115.0) and not _inside(e, 75.9, 0, 116.5)      # 外側の小 R（面取り 1.5 で近似）


def test_the_edge_ring_sits_on_the_shell_top_with_the_same_outside():
    assert _box(edge(SPEC)).xlen == pytest.approx(_box(shell(SPEC)).xlen, abs=1e-3)


def test_the_hoop_rings_are_flat_bars_rolled_into_rings_with_the_rod_gap_between():
    inner, outer = hoop_inner(SPEC), hoop_outer(SPEC)
    for ring, (r_in, r_out) in ((inner, (76.7, 79.7)), (outer, (87.7, 90.7))):
        box = _box(ring)
        assert ring.solids().size() == 1 and (box.zmin, box.zmax) == pytest.approx((117.1905, 142.1905))
        assert box.xlen == pytest.approx(2 * r_out, abs=1e-3)
        assert _volume(ring) == pytest.approx(math.pi * (r_out**2 - r_in**2) * 25, rel=1e-6)
    assert not _inside(inner, 84, 0, 130) and not _inside(outer, 84, 0, 130)        # ロッドの通り道は空き


def test_the_inner_ring_stands_on_the_top_of_the_collar_inside_the_head_outer_diameter():
    inner = hoop_inner(SPEC)
    assert _inside(inner, 77.2, 0, 117.1905 + 0.1)                 # フレッシュフープ（r 76.2〜77.7）の真上に肉がある
    assert _box(inner).zmin == pytest.approx(117.1905)               # 下面 = フレッシュフープの上端（膜の上面）


def test_six_ears_sit_on_the_rings_and_join_them_with_a_hole_for_the_rod():
    e = ear(SPEC)
    box = _box(e)
    assert e.solids().size() == 6 and (box.zmin, box.zmax) == pytest.approx((142.1905, 148.1905))
    assert _volume(e) == pytest.approx(6 * (20 * 14 * 6 - math.pi * (6.5 / 2) ** 2 * 6), rel=1e-6)   # 幅 20、リングをまたぐ 14、穴 φ6.5
    assert not _inside(e, 84, 0, 145) and _inside(e, 78, 0, 145) and _inside(e, 89.5, 0, 145)
    assert not _inside(e, 84 * math.cos(math.pi / 3), 84 * math.sin(math.pi / 3), 145)               # 60° のロッド穴も空き


def test_the_ears_bridge_the_rings_without_overlapping_them():
    rings = cq.Compound.makeCompound(hoop_inner(SPEC).solids().vals() + hoop_outer(SPEC).solids().vals())
    assert cq.Compound.makeCompound(ear(SPEC).solids().vals()).intersect(rings).Volume() == pytest.approx(0, abs=1e-6)


def test_the_hoop_follows_the_head_size():
    bigger = override(SPEC, head__fit_id=165.1)
    assert _box(hoop_inner(bigger)).xlen > _box(hoop_inner(SPEC)).xlen
