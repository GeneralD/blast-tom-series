"""ISO のねじの規格表（機種によらない）。寸法は規格値なので `spec`（仕様書・規格）の出典で持つ。

表に無い呼びは `lookup_screw` が `KeyError` を投げる。機種の `issues()` が先に表を引いて fatal にするので、
`assembly()` まで届くのは表にある呼びだけ。
"""

from __future__ import annotations

from dataclasses import dataclass

from .dims import Choice, Dim, spec


@dataclass(frozen=True)
class Screw:
    """六角穴付きボルト（ISO 4762）と、その下穴（慣用値: 呼び径 − 並目ピッチ）・通し穴（ISO 273 中級）。"""

    major: Dim
    tap_drill: Dim
    clearance: Dim
    head_dia: Dim
    head_height: Dim


SCREWS: dict[str, Screw] = {
    "M5": Screw(spec(5.0, "ISO 262"), spec(4.2, "下穴の慣用値（呼び径 − ピッチ = 5 − 0.8。ピッチは ISO 261 の並目）"), spec(5.5, "ISO 273 中級"),
                spec(8.5, "ISO 4762"), spec(5.0, "ISO 4762")),
    "M6": Screw(spec(6.0, "ISO 262"), spec(5.0, "下穴の慣用値（呼び径 − ピッチ = 6 − 1.0。ピッチは ISO 261 の並目）"), spec(6.6, "ISO 273 中級"),
                spec(10.0, "ISO 4762"), spec(6.0, "ISO 4762")),
}


def lookup_screw(choice: Choice) -> Screw:
    return SCREWS[choice.value]
