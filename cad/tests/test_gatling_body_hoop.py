"""胴・ベアリングエッジ環・ダブルフープの形状。"""

from __future__ import annotations

import math

import cadquery as cq
import pytest
from gatling.params import SPEC, override
from gatling.placement import radii
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
    assert _volume(s) == pytest.approx(ring - 6 * math.pi * 2.5**2 * 1.2, rel=2e-3)      # 肉厚 1.2、取付穴 6（ラグ 1 個に 1 つ）


def test_the_shell_has_one_mounting_hole_per_lug_at_the_centre_of_the_lug_disc():
    s = shell(SPEC)
    zc = (64.7905 + 94.7905) / 2                                   # 円盤の中心の高さ
    for angle in (0, 60, 120, 180, 240, 300):
        c, sn = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        assert not _inside(s, 75.4 * c, 75.4 * sn, zc)               # 穴（壁の中ほど）は空き
        assert _inside(s, 75.4 * c, 75.4 * sn, zc + 12.5)            # 上下の旧い穴の位置は肉（穴は 1 つだけ）
        assert _inside(s, 75.4 * c, 75.4 * sn, zc - 12.5)
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


def test_the_inner_ring_is_a_shallow_flat_bar_ring_on_the_collar():
    inner = hoop_inner(SPEC)
    box = _box(inner)
    assert inner.solids().size() == 1 and (box.zmin, box.zmax) == pytest.approx((117.1905, 125.1905))   # リムの高さ 8
    assert box.xlen == pytest.approx(2 * 80.7, abs=1e-3)
    assert _volume(inner) == pytest.approx(math.pi * (80.7**2 - 76.7**2) * 8, rel=1e-6)


def test_the_outer_ring_is_a_hollow_pipe_bent_into_a_ring_level_with_the_rim():
    """φ25.4 × t1.5 の管の環。中心半径 107.4、上端を内リングの上端 125.19 に揃える。"""
    outer = hoop_outer(SPEC)
    box = _box(outer)
    assert outer.solids().size() == 1 and (box.zmin, box.zmax) == pytest.approx((99.7905, 125.1905), abs=1e-3)
    assert box.xlen == pytest.approx(2 * 120.1, abs=1e-3)
    solid = 2 * math.pi * 107.4 * math.pi * 12.7**2
    assert _volume(outer) < solid / 2                                                    # 中空
    assert _volume(outer) == pytest.approx(2 * math.pi * 107.4 * math.pi * (12.7**2 - 11.2**2), rel=1e-4)
    zc = 125.1905 - 12.7
    assert not _inside(outer, 107.4, 0, zc)                                              # 管の中は空き
    assert _inside(outer, 107.4 + 11.95, 0, zc) and _inside(outer, 107.4 - 11.95, 0, zc)  # 肉厚 1.5 の壁
    assert not _inside(outer, 87.75, 0, 120) and not _inside(hoop_inner(SPEC), 87.75, 0, 120)   # ロッドの通り道は空き


def test_the_inner_ring_stands_on_the_top_of_the_collar_inside_the_head_outer_diameter():
    inner = hoop_inner(SPEC)
    assert _inside(inner, 77.2, 0, 117.1905 + 0.1)                 # フレッシュフープ（r 76.2〜77.7）の真上に肉がある
    assert _box(inner).zmin == pytest.approx(117.1905)               # 下面 = フレッシュフープの上端（膜の上面）


def test_six_ears_sink_between_the_rings_below_the_hoop_top_with_a_hole_for_the_rod():
    e = ear(SPEC)
    box = _box(e)
    assert e.solids().size() == 6 and (box.zmin, box.zmax) == pytest.approx((114.1905, 120.1905))   # 上面 = フープの上端 125.19 − 頭の高さ 5、下面は板厚 6 下（膜面 117.19 より下）
    assert _inside(e, 82, 0, 120) and not _inside(e, 87.75, 0, 120)                                      # 内リングの外面 80.7 から、穴はロッドの半径
    assert _inside(e, 92, 0, 119.5) and not _inside(e, 100, 0, 119.5)                                # 管に沿って切り欠く（管の中には無い）
    assert _inside(e, 82, 0, 115) and not _inside(e, 82, 0, 113.5) and not _inside(e, 82, 0, 121)    # 膜面 117.19 より下まで伸びる
    assert not _inside(e, 87.75 * math.cos(math.pi / 3), 87.75 * math.sin(math.pi / 3), 120)               # 60° のロッド穴も空き


def test_the_ear_hole_is_centred_on_the_rod_radius():
    """穴 φ6.5（ロッド 5.5 + 逃げ 1）の中心がロッドの半径 87.75 にある。両側から縁を挟んで確かめる。"""
    e, rod = ear(SPEC), radii(SPEC).rod
    assert rod == pytest.approx(87.75)
    for side in (1, -1):
        assert not _inside(e, rod + side * 3.0, 0, 120)                  # 縁（中心から 3.25）の内側は空き
        assert _inside(e, rod + side * 3.5, 0, 120)                      # 縁の外側は肉


def test_the_ears_are_welded_to_both_rings_without_overlapping_them():
    ears = cq.Compound.makeCompound(ear(SPEC).solids().vals())
    for ring in (hoop_inner(SPEC), hoop_outer(SPEC)):
        other = cq.Compound.makeCompound(ring.solids().vals())
        assert ears.intersect(other).Volume() == pytest.approx(0, abs=1e-6)
        assert ears.distance(other) == pytest.approx(0, abs=1e-6)        # 接する（溶接する面がある）


def test_the_ear_hugs_the_inner_ring_along_its_round_outer_face_without_a_gap():
    """受金の内端は平らではなく、内リングの外面（R 80.7）の円柱で切って円弧で沿わせる。幅 20 の端（y = 10）でも隙間が無い。"""
    e, r = ear(SPEC), radii(SPEC).hoop_in_outer
    y = 10 - 1e-3                                                           # 幅の端（20 / 2）の内側
    edge_x = math.sqrt(r * r - y * y)                                       # 内リングの外面が y でいる x（80.07）
    assert _inside(e, edge_x + 0.05, y, 120) and not _inside(e, edge_x - 0.05, y, 120)    # 円弧に沿う。平らな端なら x = 80.7 まで空く
    assert _inside(e, r + 0.05, 0, 120) and not _inside(e, r - 0.05, 0, 120)             # 中央（y = 0）は内リングの外面


def test_the_hoop_follows_the_head_size():
    bigger = override(SPEC, head__fit_id=165.1)
    assert _box(hoop_inner(bigger)).xlen > _box(hoop_inner(SPEC)).xlen


def test_the_ear_hole_follows_the_hole_dia_that_the_check_reads():
    """穴径は placement の `ear_hole_dia` 1 か所。逃げを変えると、受金の体積が穴の面積ぶんだけ変わる（穴は板の中に収まる）。"""
    from gatling.placement import ear_hole_dia, levels
    z = levels(SPEC)
    height = z.ear_top - z.ear_bottom
    small, big = override(SPEC, hoop__ear__hole_clearance=0.5), override(SPEC, hoop__ear__hole_clearance=2.0)
    assert (_volume(ear(small)) - _volume(ear(big))) == pytest.approx(
        6 * height * math.pi / 4 * (ear_hole_dia(big) ** 2 - ear_hole_dia(small) ** 2), rel=1e-6)
