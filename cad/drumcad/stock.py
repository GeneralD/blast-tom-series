"""規格パイプ表と、設計値の規格径への丸め。

採用する径・肉厚は `docs/vendors.md` に実在品番で登録してから使う（仕様 §4.2）。
この表は「規格として存在する組み合わせ」の一覧であって、在庫の保証ではない。
"""

from __future__ import annotations

from dataclasses import dataclass

from .checks import Issue
from .dims import Dim, derived


@dataclass(frozen=True)
class Tube:
    od: float          # 外径 mm
    thickness: float   # 肉厚 mm
    family: str        # 規格・用途

    @property
    def od_dim(self) -> Dim:
        return derived(self.od, f"{self.family} φ{self.od:g} × t{self.thickness:g}")

    @property
    def thickness_dim(self) -> Dim:
        return derived(self.thickness, f"{self.family} φ{self.od:g} × t{self.thickness:g}")


_HANDRAIL = "手すり用 #400 研磨管"
_G3446 = "JIS G3446 機械構造用"
_G3459 = "JIS G3459 配管用"

TUBES: tuple[Tube, ...] = tuple(
    [Tube(od, t, _HANDRAIL) for od in (25.4, 31.8, 38.1, 42.7, 50.8) for t in (1.2, 1.5)]
    + [Tube(od, t, _G3446) for od in (19.1, 22.2, 25.4, 31.8, 38.1, 42.7, 50.8) for t in (1.0, 1.2, 1.5, 2.0)]
    + [Tube(od, t, _G3459) for od, t in ((21.7, 2.0), (27.2, 2.0), (34.0, 2.0), (42.7, 2.0), (48.6, 2.0))]
)


def nearest(od: float, thickness: float, tolerance: float = 1.0) -> tuple[Tube, Issue | None]:
    """設計値に最も近い規格管と、ずれが `tolerance` を超えたときの警告。

    外径のずれを優先し、同じ外径の中で肉厚が最も近いものを選ぶ。
    """
    best = min(TUBES, key=lambda t: (abs(t.od - od), abs(t.thickness - thickness)))
    delta = abs(best.od - od)
    issue = None
    if delta > tolerance:
        issue = Issue(False, f"外径 {od:g} は規格径から {delta:.1f} mm ずれている"
                             f"（最寄り {best.family} φ{best.od:g} × t{best.thickness:g}）")
    return best, issue
