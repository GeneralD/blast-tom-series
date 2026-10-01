"""寸法の下限・上限を Issue にする小さな道具。縁ちょうどの値は通す（`planar.EPS` の誤差まで）。"""

from __future__ import annotations

from drumcad.checks import Issue

from .planar import EPS


def at_least(what: str, value: float, floor: float, fatal: bool = True) -> list[Issue]:
    """`value` が `floor` 以上であること（縁ちょうどは通す）。"""
    return [] if value >= floor - EPS else [Issue(fatal, f"{what}（{value:.2f} < {floor:.2f}）")]


def at_most(what: str, value: float, ceiling: float, fatal: bool = True) -> list[Issue]:
    """`value` が `ceiling` 以下であること（縁ちょうどは通す）。"""
    return [] if value <= ceiling + EPS else [Issue(fatal, f"{what}（{value:.2f} > {ceiling:.2f}）")]
