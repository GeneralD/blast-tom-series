"""機種パッケージが `build.py` に渡すものの型（仕様 §4.4）。"""

from __future__ import annotations

import numbers
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from .materials import Material

Section = Literal["radial", "outline", "plan", "none"]
Made = Literal["fabricated", "purchased"]

# 機種パッケージが必ず公開する名前。無ければ registry が TypeError で止める。
REQUIRED: tuple[str, ...] = ("SPEC", "name", "override", "assembly", "parts", "bom", "issues")
# 後の PR で必須にする名前。今は無ければ None。
OPTIONAL: tuple[str, ...] = ("drawing", "acoustic_model")


@dataclass(frozen=True)
class PartInfo:
    """製作品 1 種類の表示と扱い。`assembly()` の部品名と 1:1。"""

    name: str                      # assembly() のキー
    label: str                     # 表示名（viewer・BOM）
    color: str                     # viewer の色（#rrggbb）
    material: Material
    made: Made                     # fabricated = 製作品、purchased = 既製品の簡略形状
    count: int = 1
    section: Section = "none"      # 2D 図面の切り方（PR 5 で使う）
    explode: tuple[float, float, float] = (0.0, 0.0, 0.0)   # viewer の分解の方向と相対距離（単位ベクトルではない。長さが分解の距離の比）
    standard: str = ""             # BOM「規格・型番の系統」。製作品の行は機種がここに書く
    dimensions: str = ""           # BOM「寸法」（例: φ38.1 × t1.2 × L450）。同上
    opacity: float = 1.0           # viewer の不透明度（0 < opacity ≤ 1）。1 未満は半透明に描く。見た目だけで、形・質量・BOM には効かない

    def __post_init__(self) -> None:
        # 数値以外（文字列・None・複素数・bool）は比較が生の TypeError になるので先に弾く。
        # nan は比較がすべて偽になるので、「範囲内」を肯定形で書いて弾く
        if isinstance(self.opacity, bool) or not isinstance(self.opacity, numbers.Real) or not 0 < self.opacity <= 1:
            raise ValueError(f"部品 {self.label} の opacity {self.opacity} は 0 より大きく 1 以下でなければならない")


@dataclass(frozen=True)
class BomRow:
    """部品表の 1 行。製作品は build が形状から作る。既製品は機種が書く。"""

    name: str
    made: Made
    material: Material | None
    standard: str          # 規格・型番の系統（例: 丸形ラグ、手すり用 #400 研磨管）
    dimensions: str        # 例: φ38.1 × t1.2 × L450
    count: int
    part_number: str = ""
    mass_g: float | None = None


@dataclass(frozen=True)
class Model:
    """発見した機種パッケージ。契約の関数を SPEC を束縛した形で持つ。"""

    key: str
    spec: Any
    _module: Any = field(repr=False)

    def name(self) -> str:
        return self._module.name(self.spec)

    def override(self, **values: Any) -> "Model":
        return Model(self.key, self._module.override(self.spec, **values), self._module)

    def assembly(self) -> dict[str, Any]:
        return self._module.assembly(self.spec)

    def parts(self) -> list[PartInfo]:
        return self._module.parts(self.spec)

    def bom(self) -> list[BomRow]:
        return self._module.bom(self.spec)

    def issues(self) -> list[Any]:
        return self._module.issues(self.spec)

    @property
    def drawing(self) -> Callable[[], Any] | None:
        return self._bound("drawing")

    @property
    def acoustic_model(self) -> Callable[[], Any] | None:
        return self._bound("acoustic_model")

    def _bound(self, hook: str) -> Callable[[], Any] | None:
        """任意の関数を SPEC に束縛した無引数の callable にする。無ければ None。
        必須の 7 つと同じく、呼ぶ側は SPEC を渡さなくてよい。"""
        fn = getattr(self._module, hook, None)
        return None if fn is None else (lambda: fn(self.spec))
