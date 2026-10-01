"""寸法どうしの噛み合わせの検査結果。

`dims` の出典追跡が「その数字は本物か」を見るのに対し、機種の `issues(spec)` は
「数字どうしが物理的に成立するか」を見る。**fatal が 0 件なら出力可。警告は
表示して続行する**（仕様 §4.1）。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Issue:
    fatal: bool
    what: str

    def __str__(self) -> str:
        return f"{'❌' if self.fatal else '⚠️ '} {self.what}"


def fatal_count(issues: list[Issue]) -> int:
    return sum(1 for i in issues if i.fatal)


def count_issues(parts: dict, infos: list) -> list[Issue]:
    """`assembly()` の solid 数と `PartInfo.count` の食い違い（致命的）。

    `assembly()` は員数ぶんの solid を組立座標系に置いて返す契約で、BOM の質量は
    solid 1 個分 × 員数で出す。数が合わないと質量も組立の出力も黙って狂うので、
    出力の前に止める。員数は 1 以上（員数 0 の部品は `parts()` に載せない）。
    """
    named = {i.name for i in infos}
    found = [Issue(True, f"部品 {n} が parts() に無い") for n in parts if n not in named]
    for info in infos:
        if info.count < 1:
            found.append(Issue(True, f"部品 {info.label} の員数 {info.count} は 1 以上でなければならない"))
        elif info.name not in parts:
            found.append(Issue(True, f"部品 {info.label}（{info.name}）が assembly() に無い"))
        elif (n := parts[info.name].solids().size()) != info.count:
            found.append(Issue(True, f"部品 {info.label} の solid が {n} 個で、員数 {info.count} と合わない"))
    return found
