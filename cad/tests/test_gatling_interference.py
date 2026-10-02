"""検査と形の突き合わせ: レビューで見つかった override。

1. 形が干渉する（または `assembly()` が例外を投げる）override は、`issues()` が fatal を返す（軽い）。
2. 境界の内側（干渉しない側）の override は、`issues()` が fatal 0 で、`assembly()` の部品どうしの重なりも 0（重い。代表だけ）。
   ボルトとねじ込む相手（下穴）は既定でも重なるので除く（`gatling_overlap.py`）。
"""

from __future__ import annotations

import pytest
from drumcad.checks import fatal_count
from gatling.checks import issues
from gatling.params import SPEC, override
from gatling_overlap import overlaps


@pytest.mark.parametrize("values", [
    {"band.gap": 200}, {"band.gap": 7}, {"band.bolt_length": 5},                                      # 1. バンドのボルトが届かない
    {"flange.bolt_phase": float("inf")},                                                              # 2. 非有限の位相
    {"lug.count": 4, "hoop.ear.count": 4}, {"lug.count": 8, "hoop.ear.count": 8},                     # 3. ラグとホルダー受け
    {"lug.count": 12, "hoop.ear.count": 12},
    {"lug.height": 50, "cradle.clearance": 8},                                                        # 4. ラグとフレーム
    {"hoop.inner.thickness": 0.5, "hoop.seat": 1.5, "lug.standoff": 4},                               # 5. ロッドとフレッシュフープ
    {"hoop.ear.width": 5},                                                                            # 6. 受金が割れる
    {"tube.gap_ratio": 0.1}, {"tube.gap_ratio": 0.18},                                                # 7. 先端のボルトと管
    {"mount.body_height": 60}, {"mount.body_height": 37.8},                                           # 8. ホルダー受けと外リング（管）
    {"cradle.handle_length": 5},                                                                      # 9. グリップ
    {"flange.bolt_seat": 12, "flange.bolt_phase": 5, "band.above_flange": 1},                         # 10. ボルトの頭と耳
    {"flange.bolt_seat": 12, "flange.bolt_phase": 45, "band.bar.width": 10, "band.above_flange": 1},  # 10. ボルトの頭と腕
    {"lug.count": 30, "hoop.ear.count": 30},                                                          # 11. 個数の上限
    {"band.bar.width": 36}, {"band.above_flange": 23}, {"shell.plenum_height": 76},                   # 12. 胴バンドの耳とフレーム
    {"lug.height": 54.6, "cradle.clearance": 21,                                                      # 13. 耳のボルトの頭とラグ
     "band.bar.width": 6, "band.above_flange": 31.1905},
    {"hoop.ear.thickness": 12.1}, {"hoop.outer.od": 6},                                               # 14. 受金がリムから突き出る・管に届かない
    {"lug.rod_head_dia": 10.7}, {"lug.standoff": 11.5, "lug.rod_head_dia": 11},                       # 15. ロッドの頭と内リング・管
    {"lug.rod_length": 28.5},                                                                         # 16. ロッドがラグに届かない
    {"shell.plenum_height": 10},                                                                      # 17. フレームと外リング（管）
    {"lug.rod_length": 85},                                                                           # 18. ラグの下に出た軸と胴バンドの耳
    {"lug.count": 24, "hoop.ear.count": 24, "cradle.clearance": 31, "cradle.bar.thickness": 40,       # 19. ラグの下に出た軸とクレードルの腕
     "mount.body_height": 20, "lug.rod_length": 72},
    {"lug.standoff": 9.5, "lug.rod_length": 79.5},                                                    # 20. 軸と胴バンド
    {"lug.count": 12, "hoop.ear.count": 12, "cradle.clearance": 13,                                  # 21. 軸とホルダー受け
     "cradle.pad.thickness": 1, "mount.body_height": 2, "lug.rod_length": 61},
    {"cradle.clearance": 5, "cradle.pad.depth": 40, "cradle.pad.width": 40, "lug.rod_length": 64},    # 22. 軸とクレードルのフレーム
    {"hoop.outer.od": 10, "mount.body_height": 51.5},                                                 # 23. ホルダー受けと受金
])
def test_an_override_that_breaks_the_shape_is_fatal(values):
    assert fatal_count(issues(override(SPEC, **values))) >= 1, values


@pytest.mark.parametrize("values", [
    {"lug.count": 24, "hoop.ear.count": 24, "cradle.clearance": 31},                                  # 3・11 の内側
    {"cradle.handle_length": 31.2, "mount.body_height": 37.7},                                        # 8・9 の内側
    {"tube.gap_ratio": 0.19},                                                                         # 7 の内側
    {"flange.bolt_seat": 12, "flange.bolt_phase": 33, "band.bar.width": 10, "band.above_flange": 1},  # 10 の内側
    {"hoop.inner.thickness": 0.5, "hoop.seat": 1.5, "lug.standoff": 4.5, "lug.rod_head_dia": 7,       # 4・5 の内側
     "lug.height": 50, "cradle.clearance": 10.5},
    {"cradle.clearance": 21, "band.bar.width": 36},                                                   # 12 の内側
    {"lug.height": 54.6, "cradle.clearance": 21,                                                      # 13 の内側
     "band.bar.width": 6, "band.above_flange": 29.19},
    {"hoop.ear.thickness": 12, "hoop.outer.od": 12.1, "lug.rod_head_height": 0.5},                    # 14 の内側（受金がリムいっぱい、管に届く）
    {"lug.rod_head_dia": 10.6, "lug.rod_length": 28.53},                                              # 15・16 の内側
    {"lug.rod_length": 79},                                                                           # 18 の内側（ラグの下に出るのは警告だけ）
    {"lug.count": 24, "hoop.ear.count": 24, "cradle.clearance": 31, "cradle.bar.thickness": 40,       # 19 の内側
     "mount.body_height": 20, "lug.rod_length": 71.5},
    {"lug.standoff": 9.5, "lug.rod_length": 79},                                                      # 20 の内側
    {"lug.count": 12, "hoop.ear.count": 12, "cradle.clearance": 13,                                  # 21 の内側
     "cradle.pad.thickness": 1, "mount.body_height": 2, "lug.rod_length": 60},
    {"cradle.clearance": 5, "cradle.pad.depth": 40, "cradle.pad.width": 40, "lug.rod_length": 63},    # 22 の内側
    {"hoop.outer.od": 10, "mount.body_height": 51},                                                   # 23 の内側
])
def test_an_override_just_inside_the_checks_builds_without_any_overlap(values):
    spec = override(SPEC, **values)
    assert fatal_count(issues(spec)) == 0, [i.what for i in issues(spec)]
    assert overlaps(spec) == []
