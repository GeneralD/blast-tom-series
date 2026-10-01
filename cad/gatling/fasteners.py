"""ねじ・ロッド・ホルダーの規格表。寸法は規格値なので `spec`（仕様書・規格）の出典で持つ。

表に無い呼びは `lookup_*` が `KeyError` を投げる。`issues()` が先に表を引いて fatal にするので、
`assembly()` まで届くのは表にある呼びだけ。
"""

from __future__ import annotations

from dataclasses import dataclass

from drumcad.dims import Choice, Dim, spec


@dataclass(frozen=True)
class Screw:
    """六角穴付きボルト（ISO 4762）と、その下穴・通し穴（ISO 273 中級）。"""

    major: Dim
    tap_drill: Dim
    clearance: Dim
    head_dia: Dim
    head_height: Dim


SCREWS: dict[str, Screw] = {
    "M5": Screw(spec(5.0, "ISO 262"), spec(4.2, "ISO 261 の下穴"), spec(5.5, "ISO 273 中級"),
                spec(8.5, "ISO 4762"), spec(5.0, "ISO 4762")),
    "M6": Screw(spec(6.0, "ISO 262"), spec(5.0, "ISO 261 の下穴"), spec(6.6, "ISO 273 中級"),
                spec(10.0, "ISO 4762"), spec(6.0, "ISO 4762")),
}

# テンションロッドのねじの呼び径。ラグに合う規格を実物で確かめるまで、ラグ側の `Choice` が仮。
ROD_THREADS: dict[str, Dim] = {
    "#12-24": spec(5.5, "ASME B1.1 の #12（0.216 in）"),
    "M5": spec(5.0, "ISO 262"),
}

# ホルダー受けが受ける L ロッドの径。
HOLDER_RODS: dict[str, Dim] = {
    "L ロッド 10.5": spec(10.5, "ロッド径"),
    "L ロッド 12.7": spec(12.7, "ロッド径（1/2 インチ）"),
}


def lookup_screw(choice: Choice) -> Screw:
    return SCREWS[choice.value]


def lookup_rod(choice: Choice) -> Dim:
    return ROD_THREADS[choice.value]


def lookup_holder(choice: Choice) -> Dim:
    return HOLDER_RODS[choice.value]
