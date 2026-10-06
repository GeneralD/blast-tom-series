"""Gatling のテンションロッドのねじとホルダーロッドの規格表。寸法は規格値なので `spec`（仕様書・規格）の出典で持つ。

ISO のねじ（`SCREWS`）は機種によらないので `drumcad.fasteners`。表に無い呼びは `lookup_*` が `KeyError` を投げる。
`issues()` が先に表を引いて fatal にするので、`assembly()` まで届くのは表にある呼びだけ。
"""

from __future__ import annotations

from drumcad.dims import Choice, Dim, spec


# テンションロッドのねじの呼び径。ラグに合う規格を実物で確かめるまで、ラグ側の `Choice` が仮。
ROD_THREADS: dict[str, Dim] = {
    "#12-24": spec(5.5, "ASME B1.1 の #12（0.216 in ≈ 5.49 mm を 0.1 mm に丸めた）"),
    "M5": spec(5.0, "ISO 262"),
}

# ホルダー受けが受ける L ロッドの径。
HOLDER_RODS: dict[str, Dim] = {
    "L ロッド 10.5": spec(10.5, "ロッド径（タムホルダーの L ロッドの慣用径。規格値ではない）"),
    "L ロッド 12.7": spec(12.7, "ロッド径（1/2 インチ）"),
}


def lookup_rod(choice: Choice) -> Dim:
    return ROD_THREADS[choice.value]


def lookup_holder(choice: Choice) -> Dim:
    return HOLDER_RODS[choice.value]
