"""検査と形の突き合わせ: レビューで見つかった override。

1. 形が干渉する（または `assembly()` が例外を投げる）override は、`issues()` が fatal を返す（軽い）。
2. 境界の内側（干渉しない側）の override は、`issues()` が fatal 0 で、`assembly()` の部品どうしの重なりも 0（重い。代表だけ）。
   ボルトとねじ込む相手（下穴）は既定でも重なるので除く（`gatling_overlap.py`）。
"""

from __future__ import annotations

from drumcad.checks import fatal_count
from gatling.checks import issues
from gatling.interference import ear_clear
from gatling.params import SPEC, override
from gatling_overlap import overlaps


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
