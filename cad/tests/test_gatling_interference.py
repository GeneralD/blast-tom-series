"""検査と形の突き合わせ: レビューで見つかった override。

1. 形が干渉する（または `assembly()` が例外を投げる）override は、`issues()` が fatal を返す（軽い）。
2. 境界の内側（干渉しない側）の override は、`issues()` が fatal 0 で、`assembly()` の部品どうしの重なりも 0（重い。代表だけ）。
   ボルトとねじ込む相手（下穴）は既定でも重なるので除く（`gatling_overlap.py`）。
"""

from __future__ import annotations

import pytest
from drumcad.checks import fatal_count
from gatling.checks import issues
from gatling.interference import ear_clear
from gatling.params import SPEC, override
from gatling_overlap import overlaps


@pytest.mark.parametrize("values", [
    {"band.gap": 200}, {"band.gap": 7}, {"band.bolt_length": 5},                                      # 1. バンドのボルトが届かない
    {"flange.bolt_phase": float("inf")},                                                              # 2. 非有限の位相
    {"lug.count": 4, "hoop.ear.count": 4}, {"lug.count": 8, "hoop.ear.count": 8},                     # 3. ラグとホルダー受け
    {"lug.count": 12, "hoop.ear.count": 12},
    {"lug.body_dia": 50, "cradle.clearance": 8},                                                      # 4. ラグとフレーム
    {"hoop.inner.thickness": 0.5, "hoop.seat": 1.5, "lug.standoff": 4},                               # 5. ロッドとフレッシュフープ
    {"hoop.ear.width": 5},                                                                            # 6. 受金が割れる
    {"tube.gap_ratio": 0.1}, {"tube.gap_ratio": 0.18},                                                # 7. 先端のボルトと管
    {"mount.body_height": 60}, {"mount.body_height": 33.8},                                           # 8. ホルダー受けと外リング（管）
    {"cradle.handle_length": 5},                                                                      # 9. グリップ
    {"flange.bolt_seat": 12, "flange.bolt_phase": 5, "band.above_flange": 1},                         # 10. ボルトの頭と耳
    {"flange.bolt_seat": 12, "flange.bolt_phase": 45, "band.bar.width": 10, "band.above_flange": 1},  # 10. ボルトの頭と腕
    {"lug.count": 30, "hoop.ear.count": 30},                                                          # 11. 個数の上限
    {"band.bar.width": 36}, {"band.above_flange": 23}, {"shell.plenum_height": 76},                   # 12. 胴バンドの耳とフレーム
    {"lug.body_dia": 50.6, "cradle.clearance": 31,                                                    # 13. 耳のボルトの頭とラグ
     "band.bar.width": 6, "band.above_flange": 31.1905},
    {"lug.rod_head_height": 8}, {"hoop.outer.od": 5},                                           # 14. 受金が内リングに溶接できない・管に届かない
    {"lug.rod_head_dia": 10.7}, {"lug.standoff": 11.5, "lug.rod_head_dia": 11.7},                       # 15. ロッドの頭と内リング・管
    {"lug.rod_length": 29.5},                                                                         # 16. ロッドがラグに届かない
    {"shell.plenum_height": 10},                                                                      # 17. フレームと外リング（管）
    {"lug.rod_length": 82},                                                                           # 18. ラグの下に出た軸と胴バンドの耳
    {"lug.count": 24, "hoop.ear.count": 24, "lug.body_dia": 19.5, "cradle.clearance": 31, "cradle.bar.thickness": 40,       # 19. ラグの下に出た軸とクレードルの腕
     "mount.body_height": 15, "lug.rod_length": 69},
    {"lug.standoff": 9.5, "lug.rod_length": 76.5},                                                    # 20. 軸と胴バンド
    {"lug.count": 12, "hoop.ear.count": 12, "cradle.clearance": 13,                                  # 21. 軸とホルダー受け
     "cradle.bar.thickness": 1, "cradle.pad.thickness": 1, "mount.body_height": 1, "lug.rod_length": 61},
    {"cradle.clearance": 5, "cradle.pad.depth": 40, "cradle.pad.width": 40, "cradle.bar.thickness": 5,   # 22. 軸とクレードルのフレーム
     "lug.rod_length": 60.8},
    {"hoop.outer.od": 10, "mount.body_height": 48.3},                                                 # 23. ホルダー受けと受金
    {"hoop.inner.thickness": 0.9, "lug.standoff": 6, "lug.rod_head_dia": 7},                                                                 # 24. 受金とフレッシュフープ（内リングが薄い）
    {"lug.depth": 23, "lug.body_dia": 35},                                                            # 25. 円盤の外側の面（胴の外面から厚みぶん）とフレーム
])
def test_an_override_that_breaks_the_shape_is_fatal(values):
    assert fatal_count(issues(override(SPEC, **values))) >= 1, values


@pytest.mark.parametrize("values", [
    {"lug.count": 24, "hoop.ear.count": 24, "lug.body_dia": 19.5, "cradle.clearance": 31},                                  # 3・11 の内側
    {"cradle.handle_length": 31.2, "mount.body_height": 33.7},                                        # 8・9 の内側
    {"tube.gap_ratio": 0.19},                                                                         # 7 の内側
    {"flange.bolt_seat": 12, "flange.bolt_phase": 33, "band.bar.width": 10, "band.above_flange": 1},  # 10 の内側
    {"hoop.inner.thickness": 1.5, "hoop.seat": 1.5, "lug.standoff": 6, "lug.rod_head_dia": 7,         # 4・5 の内側
     "lug.body_dia": 35, "lug.depth": 22},
    {"cradle.clearance": 21, "band.bar.width": 36},                                                   # 12 の内側
    {"lug.body_dia": 50.6, "cradle.clearance": 31,                                                    # 13 の内側
     "band.bar.width": 6, "band.above_flange": 29.19},
    {"lug.rod_head_height": 7.9}, {"hoop.outer.od": 5.1},                                             # 14 の内側（内リングに 0.1 だけ溶接、管に 0.1 だけ届く）
    {"lug.rod_head_dia": 10.6, "lug.rod_length": 29.53},                                              # 15・16 の内側
    {"lug.rod_length": 76},                                                                           # 18 の内側（ラグの下に出るのは警告だけ）
    {"lug.count": 24, "hoop.ear.count": 24, "lug.body_dia": 19.5, "cradle.clearance": 31, "cradle.bar.thickness": 40,       # 19 の内側
     "mount.body_height": 15, "lug.rod_length": 68.5},
    {"lug.standoff": 9.5, "lug.rod_length": 76},                                                      # 20 の内側
    {"lug.count": 12, "hoop.ear.count": 12, "cradle.clearance": 13,                                  # 21 の内側
     "cradle.bar.thickness": 1, "cradle.pad.thickness": 1, "mount.body_height": 1, "lug.rod_length": 60},
    {"cradle.clearance": 5, "cradle.pad.depth": 40, "cradle.pad.width": 40, "cradle.bar.thickness": 5,   # 22 の内側
     "lug.rod_length": 60.6},
    {"hoop.outer.od": 10, "mount.body_height": 48.1},                                                   # 23 の内側
    {"hoop.inner.thickness": 1.0, "lug.standoff": 6, "lug.rod_head_dia": 7},                                                                # 24 の内側（受金の内端がフレッシュフープの外面ちょうど）
    {"lug.depth": 22, "lug.body_dia": 35},                                                            # 25 の内側（円盤の外側の面 98 = フレームの内面ちょうど）
])
def test_an_override_just_inside_the_checks_builds_without_any_overlap(values):
    spec = override(SPEC, **values)
    assert fatal_count(issues(spec)) == 0, [i.what for i in issues(spec)]
    assert overlaps(spec) == []


@pytest.mark.parametrize("values, what", [
    ({"cradle.pad.width": 95}, "ラグが当て板に当たる"),                                               # 当て板だけ（ホルダー受けは外れている）
    ({"lug.count": 12, "hoop.ear.count": 12, "lug.body_dia": 19.5, "cradle.clearance": 16}, "ラグがホルダー受けに当たる"),   # ホルダー受けだけ
])
def test_each_lug_interference_check_alone_is_what_makes_the_override_fatal(values, what):
    """3 つの判定（当て板・ホルダー受け）を、それぞれ単独の理由で fatal にする設定。判定を消すと通ってしまう。"""
    fatals = [i.what for i in issues(override(SPEC, **values)) if i.fatal]
    assert len(fatals) == 1 and fatals[0].startswith(what), fatals


def test_the_default_has_no_fatal_no_overlap_and_only_the_two_known_warnings():
    """既定の警告は受金のロッド通し穴の径方向の肉（内側・外側）の 2 件だけ。リムを浅くしても増えない。"""
    found = issues(SPEC)
    assert fatal_count(found) == 0
    assert sorted(i.what.split("（")[0] for i in found) == ["受金のロッド通し穴の内側の肉", "受金のロッド通し穴の外側の肉"]
    assert overlaps(SPEC) == []


def test_an_ear_must_not_eat_the_fresh_hoop():
    """受金の内端は内リングの外面（既定 80.7）。フレッシュフープの外面（77.7）より内側（内リングを薄くした）で、z も重なれば fatal。
    内リングの内面は 76.7（seat 1）なので、厚み 1 で外面 77.7（縁ちょうどは通す）、0.9 で 77.6。"""
    assert ear_clear(SPEC) == []
    assert ear_clear(override(SPEC, hoop__inner__thickness=1.0)) == []
    found = ear_clear(override(SPEC, hoop__inner__thickness=0.9))
    assert len(found) == 1 and found[0].fatal and "受金" in found[0].what and "フレッシュフープ" in found[0].what


def test_an_ear_above_the_fresh_hoop_in_z_does_not_touch_it_whatever_the_ring_thickness():
    """頭の高さ 1 だと受金（板厚 6）は z 118.19〜124.19 で、フレッシュフープ（〜膜面 117.19）の上。平面視で重なっても z が離れている。"""
    assert ear_clear(override(SPEC, lug__rod_head_height=1, hoop__inner__thickness=0.9)) == []
    assert ear_clear(override(SPEC, lug__rod_head_height=2, hoop__inner__thickness=0.9)) == []          # 下面がちょうど膜面に載る
    assert ear_clear(override(SPEC, lug__rod_head_height=2.1, hoop__inner__thickness=0.9)) != []        # 膜面より下に 0.1 食い込む
