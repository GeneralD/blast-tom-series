"""平面（と z の区間）の幾何。spec に依存しない素の計算で、干渉の検査が形状を作らずに重なりを見るのに使う。

多角形はすべて凸で、頂点を反時計回りに並べる。接するだけ（重なりが `EPS` 以下）は重ならないとみなす。
"""

from __future__ import annotations

import math

EPS = 1e-6                    # 縁ちょうどの値が浮動小数の誤差で fatal にならないように

Point = tuple[float, float]


def rect(u0: float, u1: float, v0: float, v1: float, angle_deg: float = 0.0) -> list[Point]:
    """局所座標の矩形 u∈[u0, u1]、v∈[v0, v1] を Z 軸周りに `angle_deg` 回した 4 隅（反時計回り）。

    x = u cos a − v sin a、y = u sin a + v cos a。形状の `rotate((0,0,0), (0,0,1), a)` と同じ向き。
    """
    c, s = math.cos(math.radians(angle_deg)), math.sin(math.radians(angle_deg))
    return [(u * c - v * s, u * s + v * c) for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1))]


def edges(poly: list[Point]) -> list[tuple[Point, Point]]:
    return [(poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly))]


def polygons_overlap(p: list[Point], q: list[Point]) -> bool:
    """2 つの凸多角形が EPS を超えて重なる（分離軸判定。接するだけなら重ならない）。"""
    for (x0, y0), (x1, y1) in edges(p) + edges(q):
        nx, ny = y0 - y1, x1 - x0
        norm = math.hypot(nx, ny)
        a = [(x * nx + y * ny) / norm for x, y in p]
        b = [(x * nx + y * ny) / norm for x, y in q]
        if min(max(a), max(b)) - max(min(a), min(b)) <= EPS:
            return False
    return True


def segment_distance(p: Point, a: Point, b: Point) -> float:
    """点 `p` と線分 ab の距離。"""
    ax, ay, bx, by = *a, *b
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def circle_overlaps(centre: Point, radius: float, poly: list[Point]) -> bool:
    """円と凸多角形（反時計回り）が EPS を超えて重なる。中心が内側にあるか、辺までの距離が半径未満。"""
    inside = all((b[0] - a[0]) * (centre[1] - a[1]) - (b[1] - a[1]) * (centre[0] - a[0]) >= 0 for a, b in edges(poly))
    return inside or min(segment_distance(centre, a, b) for a, b in edges(poly)) < radius - EPS


def origin_distance(poly: list[Point]) -> float:
    """原点（胴の軸）から凸多角形までの距離。原点が内側なら 0。"""
    return 0.0 if circle_overlaps((0.0, 0.0), 0.0, poly) else min(segment_distance((0.0, 0.0), a, b) for a, b in edges(poly))


def square_reach(polys: list[list[Point]]) -> float:
    """多角形の頂点の max(|x|, |y|) の最大。原点を中心とする正方形（クレードルのフレームの内面）から出るかを見る。"""
    return max(max(abs(x), abs(y)) for poly in polys for x, y in poly)


def z_overlap(a0: float, a1: float, b0: float, b1: float) -> bool:
    """2 つの z の区間が EPS を超えて重なる。"""
    return min(a1, b1) - max(a0, b0) > EPS
