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
