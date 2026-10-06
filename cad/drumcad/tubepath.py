"""管の経路（平面の折れ線を円弧で丸めたもの）。腕の中心線と、その平面形を作る。spec にも CadQuery にも依存しない。

形状（`shapes/mount.py`）は経路を掃引して腕を作り、検査（`interference.py`）は同じ経路から平面形の凸多角形を作る。
形と検査が同じ経路を読むので、曲げの位置がずれて検査だけ通ることがない。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .planar import Point

Vec = tuple[float, float]


@dataclass(frozen=True)
class Line:
    a: Vec
    b: Vec

    @property
    def length(self) -> float:
        return math.dist(self.a, self.b)


@dataclass(frozen=True)
class Arc:
    """中心 `centre`、半径 `radius` の円弧。角度（rad）は `a0` から `a1` へ（符号つき。正が反時計回り）。"""

    centre: Vec
    radius: float
    a0: float
    a1: float

    @property
    def length(self) -> float:
        return self.radius * abs(self.a1 - self.a0)

    def point(self, t: float) -> Vec:
        """弧の上の点。`t` = 0 が始点、1 が終点。"""
        angle = self.a0 + t * (self.a1 - self.a0)
        return self.centre[0] + self.radius * math.cos(angle), self.centre[1] + self.radius * math.sin(angle)


Path = list[Line | Arc]


def _unit(a: Vec, b: Vec) -> Vec:
    length = math.dist(a, b)
    return (b[0] - a[0]) / length, (b[1] - a[1]) / length


def turn_angle(before: Vec, corner: Vec, after: Vec) -> float:
    """頂点 `corner` での曲がり角（rad、0 は直進、π は折り返し）。"""
    d_in, d_out = _unit(before, corner), _unit(corner, after)
    return math.acos(max(-1.0, min(1.0, d_in[0] * d_out[0] + d_in[1] * d_out[1])))


def tangent_length(turn: float, radius: float) -> float:
    """曲がり角 `turn` を半径 `radius` の円弧で丸めるとき、頂点から接点までの長さ。"""
    return radius * math.tan(turn / 2)


def fillet(points: list[Vec], radius: float) -> Path:
    """折れ線 `points` の内側の頂点を半径 `radius` の円弧で丸めた経路（直線・円弧・直線…の順）。

    各頂点の接線の長さが前後の脚に収まることは呼び出し側が先に確かめる（収まらなければ経路は折り返す）。
    脚が接線の長さちょうどなら、長さ 0 の直線が残る（添字を固定するため消さない。形を作るときに読み飛ばす）。
    """
    path: Path = []
    cursor = points[0]
    for i in range(1, len(points) - 1):
        d_in, d_out = _unit(points[i - 1], points[i]), _unit(points[i], points[i + 1])
        turn = math.acos(max(-1.0, min(1.0, d_in[0] * d_out[0] + d_in[1] * d_out[1])))
        reach = tangent_length(turn, radius)
        start = (points[i][0] - d_in[0] * reach, points[i][1] - d_in[1] * reach)
        end = (points[i][0] + d_out[0] * reach, points[i][1] + d_out[1] * reach)
        left = 1.0 if d_in[0] * d_out[1] - d_in[1] * d_out[0] > 0 else -1.0       # 左に曲がるなら正
        centre = (start[0] - left * d_in[1] * radius, start[1] + left * d_in[0] * radius)
        a0 = math.atan2(start[1] - centre[1], start[0] - centre[0])
        path += [Line(cursor, start), Arc(centre, radius, a0, a0 + left * turn)]
        cursor = end
    path.append(Line(cursor, points[-1]))
    return path


def _counterclockwise(poly: list[Point]) -> list[Point]:
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))
    return poly if area > 0 else poly[::-1]


def plan_polygons(path: Path, half_width: float, step_deg: float = 5.0) -> list[list[Point]]:
    """管（半径 `half_width`）の平面形を覆う凸多角形（反時計回り）。

    直線は厳密な矩形（端は平ら）。円弧は `step_deg` ごとに分け、外側は外接する接線、内側は弦で囲む四角形にする
    （管の平面形より大きい側にずれるので、重なりの見落としは出ない）。長さ 0 の直線は飛ばす。
    """
    polys: list[list[Point]] = []
    for part in path:
        if isinstance(part, Line):
            if part.length < 1e-9:
                continue
            ux, uy = _unit(part.a, part.b)
            nx, ny = -uy * half_width, ux * half_width
            (ax, ay), (bx, by) = part.a, part.b
            polys.append([(ax - nx, ay - ny), (bx - nx, by - ny), (bx + nx, by + ny), (ax + nx, ay + ny)])
            continue
        pieces = max(1, math.ceil(abs(part.a1 - part.a0) / math.radians(step_deg) - 1e-9))
        step = (part.a1 - part.a0) / pieces
        outer = (part.radius + half_width) / math.cos(abs(step) / 2)
        inner = max(part.radius - half_width, 0.0)
        cx, cy = part.centre
        for k in range(pieces):
            a, b = part.a0 + k * step, part.a0 + (k + 1) * step
            polys.append(_counterclockwise([
                (cx + inner * math.cos(a), cy + inner * math.sin(a)), (cx + outer * math.cos(a), cy + outer * math.sin(a)),
                (cx + outer * math.cos(b), cy + outer * math.sin(b)), (cx + inner * math.cos(b), cy + inner * math.sin(b))]))
    return polys
