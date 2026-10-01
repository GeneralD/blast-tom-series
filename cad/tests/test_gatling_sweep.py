"""検査の性質: `issues()` の fatal が 0 なら、`assembly()` は例外を投げず、部品どうしの交差体積が 0。

検査の見逃し（fatal 0 なのに形が重なる）をレビューで 1 件ずつ見つけて塞ぐのを繰り返したので、個々の override ではなく
性質そのものを、固定 seed の乱数で作った override で確かめる。override は既定値の周りの現実的な範囲で、複数の葉を
同時に振る（1 つずつ振ると、2 つの寸法の組み合わせで起きる重なりを見落とす）。fatal になった override は形を作らずに
除く（既定の 40 件のうち 20 件が fatal 0 で、形を作って確かめる）。ボルトとねじ込む相手（下穴）の 3 組は既定でも重なるので除く（`gatling_overlap.py`）。

件数は全テスト（`pytest cad/tests`）が約 100〜110 秒（実測）で終わる数にしてある。環境変数 `GATLING_SWEEP_CASES` で増やせる（ローカルで数百件を回して
見逃しを探すとき）。見つかった見逃しは、塞いだうえで `test_gatling_interference.py` に回帰テストとして足す。
"""

from __future__ import annotations

import os
import random

import pytest
from drumcad.checks import fatal_count
from drumcad.dims import Choice, walk
from gatling.checks import issues
from gatling.fasteners import HOLDER_RODS, ROD_THREADS, SCREWS
from gatling.params import SPEC, override
from gatling_overlap import overlaps

SEED = 20261001
CASES = int(os.environ.get("GATLING_SWEEP_CASES", "40"))

# 形状に入らない葉（振っても形が変わらない）と、個数（下で揃えて振る）
_NOT_SHAPE = {"head.f01_range[0]", "head.f01_range[1]", "head.loss_factor"}
_COUNTS = {"tube.count", "lug.count", "hoop.ear.count", "flange.bolt_count"}
_NUMERIC = [path for path, leaf in walk(SPEC)
            if not isinstance(leaf, Choice) and path not in _NOT_SHAPE and path not in _COUNTS]
_CHOICES = {"flange.bolt": SCREWS, "clamp.bolt": SCREWS, "band.bolt": SCREWS, "lug.thread": ROD_THREADS, "mount.type": HOLDER_RODS}


def random_override(rng: random.Random) -> dict[str, object]:
    """既定値の 0.5〜1.5 倍の範囲で 2〜6 個の寸法を同時に振る。ときどき個数（ラグ・受金は揃える）と規格の呼びも振る。"""
    leaves = dict(walk(SPEC))
    values: dict[str, object] = {}
    for path in rng.sample(_NUMERIC, rng.randint(2, 6)):
        values[path] = round(float(leaves[path]) * rng.uniform(0.5, 1.5), 3)
    if rng.random() < 0.25:
        n = rng.choice([2, 3, 6, 12])
        values["lug.count"] = values["hoop.ear.count"] = n
    if rng.random() < 0.15:
        values["tube.count"] = rng.choice([3, 4, 6, 8])
    if rng.random() < 0.15:
        values["flange.bolt_count"] = rng.choice([3, 4, 6, 8, 12])
    if rng.random() < 0.2:
        path = rng.choice(sorted(_CHOICES))
        values[path] = rng.choice(sorted(_CHOICES[path]))
    return values


def sweep(count: int, seed: int = SEED) -> list[dict[str, object]]:
    rng = random.Random(seed)
    return [random_override(rng) for _ in range(count)]


_SWEEP = sweep(CASES)
# fatal 0 の override だけを形にする（fatal なら `assembly()` を呼ばない契約なので、性質の前提を満たさない）
_BUILDABLE = [values for values in _SWEEP if fatal_count(issues(override(SPEC, **values))) == 0]


@pytest.mark.parametrize("values", _BUILDABLE, ids=[f"case{i}" for i in range(len(_BUILDABLE))])
def test_no_fatal_means_the_assembly_builds_without_any_overlap(values):
    assert overlaps(override(SPEC, **values)) == [], values


def test_the_sweep_is_not_vacuous():
    """sweep の 3 分の 1 以上が fatal 0 で、実際に形を作って確かめている（全部 fatal なら性質の確認が空振りになる）。"""
    assert len(_BUILDABLE) >= len(_SWEEP) / 3, f"{len(_BUILDABLE)} / {len(_SWEEP)}"
