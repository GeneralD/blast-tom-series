"""検査と形の突き合わせ: レビューで見つかった override。

1. 形が干渉する（または `assembly()` が例外を投げる）override は、`issues()` が fatal を返す（軽い）。
2. 境界の内側（干渉しない側）の override は、`issues()` が fatal 0 で、`assembly()` の部品どうしの重なりも 0（重い。代表だけ）。
   ボルトとねじ込む相手（下穴）は既定でも重なるので除く。
"""

from __future__ import annotations

import itertools

import cadquery as cq
import pytest
from drumcad.checks import fatal_count
from gatling.assemble import assembly
from gatling.checks import issues
from gatling.params import SPEC, override

THREADED = {frozenset(p) for p in [("band", "bolt_band"), ("bolt_flange", "header"), ("clamp_tip", "bolt_tip")]}


@pytest.mark.parametrize("values", [
    {"band.gap": 200}, {"band.gap": 7}, {"band.bolt_length": 5},                                      # 1. バンドのボルトが届かない
    {"flange.bolt_phase": float("inf")},                                                              # 2. 非有限の位相
    {"lug.count": 4, "hoop.ear.count": 4}, {"lug.count": 8, "hoop.ear.count": 8},                     # 3. ラグとホルダー受け
    {"lug.count": 12, "hoop.ear.count": 12},
    {"lug.height": 60, "cradle.clearance": 8, "lug.rod_length": 120},                                 # 4. ラグとフレーム
    {"hoop.inner.thickness": 0.5, "hoop.seat": 1.5, "lug.standoff": 4},                               # 5. ロッドとフレッシュフープ
    {"hoop.ear.width": 5},                                                                            # 6. 受金が割れる
    {"tube.gap_ratio": 0.1}, {"tube.gap_ratio": 0.18},                                                # 7. 先端のボルトと管
    {"mount.body_height": 60},                                                                        # 8. ホルダー受けと外リング
    {"cradle.handle_length": 5},                                                                      # 9. グリップ
    {"flange.bolt_seat": 12, "flange.bolt_phase": 5, "band.above_flange": 1},                         # 10. ボルトの頭と耳
    {"flange.bolt_seat": 12, "flange.bolt_phase": 45, "band.bar.width": 10, "band.above_flange": 1},  # 10. ボルトの頭と腕
    {"lug.count": 30, "hoop.ear.count": 30},                                                          # 11. 個数の上限
    {"band.bar.width": 36}, {"band.above_flange": 23}, {"shell.plenum_height": 76},                   # 12. 胴バンドの耳とフレーム
    {"lug.height": 60, "lug.rod_length": 120, "cradle.clearance": 21,                                 # 13. 耳のボルトの頭とラグ
     "band.bar.width": 6, "band.above_flange": 31.1905},
])
def test_an_override_that_breaks_the_shape_is_fatal(values):
    assert fatal_count(issues(override(SPEC, **values))) >= 1, values


def _overlaps(spec) -> list[str]:
    shapes = {n: cq.Compound.makeCompound(p.solids().vals()) for n, p in assembly(spec).items()}
    found = []
    for a, b in itertools.combinations(shapes, 2):
        if frozenset((a, b)) in THREADED:
            continue
        volume = shapes[a].intersect(shapes[b]).Volume()
        if volume > 1e-3:
            found.append(f"{a}∩{b} = {volume:.1f}")
    return found


@pytest.mark.parametrize("values", [
    {"lug.count": 24, "hoop.ear.count": 24, "cradle.clearance": 17},                                  # 3・11 の内側
    {"cradle.handle_length": 31.2, "mount.body_height": 51},                                          # 8・9 の内側
    {"tube.gap_ratio": 0.19},                                                                         # 7 の内側
    {"flange.bolt_seat": 12, "flange.bolt_phase": 33, "band.bar.width": 10, "band.above_flange": 1},  # 10 の内側
    {"hoop.inner.thickness": 0.5, "hoop.seat": 1.5, "lug.standoff": 4.5,                              # 4・5 の内側
     "lug.height": 60, "cradle.clearance": 10.5, "lug.rod_length": 120},
    {"cradle.clearance": 21, "band.bar.width": 36},                                                   # 12 の内側
    {"lug.height": 60, "lug.rod_length": 120, "cradle.clearance": 21,                                 # 13 の内側
     "band.bar.width": 6, "band.above_flange": 29.19},
])
def test_an_override_just_inside_the_checks_builds_without_any_overlap(values):
    spec = override(SPEC, **values)
    assert fatal_count(issues(spec)) == 0, [i.what for i in issues(spec)]
    assert _overlaps(spec) == []
