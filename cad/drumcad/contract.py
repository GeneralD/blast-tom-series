"""機種パッケージが `build.py` に渡すものの型（仕様 §4.4）。"""

from __future__ import annotations

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
    explode: tuple[float, float, float] = (0.0, 0.0, 0.0)   # viewer の分解方向（単位ベクトル）
    standard: str = ""             # BOM「規格・型番の系統」。製作品の行は機種がここに書く
    dimensions: str = ""           # BOM「寸法」（例: φ38.1 × t1.2 × L450）。同上


@dataclass(frozen=True)
class BomRow:
    """部品表の 1 行。製作品は build が形状から作る。既製品は機種が書く。"""

    name: str
    made: Made
    material: Material | None
    standard: str          # 規格・型番の系統（例: DW タレットラグ、手すり用 #400 研磨管）
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
    def drawing(self) -> Callable | None:
        return getattr(self._module, "drawing", None)

    @property
    def acoustic_model(self) -> Callable | None:
        return getattr(self._module, "acoustic_model", None)
