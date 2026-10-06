"""検査（ラグの取付穴と円盤、受金・ラグの個数の上限）。"""

from __future__ import annotations

from gatling.checks import lug_fits, spacing
from gatling.params import SPEC, override


def _fatal(issues):
    return [i.what for i in issues if i.fatal]


def test_the_mounting_hole_that_runs_past_the_ends_of_the_shell_is_fatal():
    # 円盤の中心の高さ（既定 79.79 = 上端 − 円盤の径 / 2）に穴が 1 つ。下端はフランジ上面 7、上端は胴の上端 107
    assert not any("フランジ" in w for w in _fatal(lug_fits(override(SPEC, lug__body_dia=170))))       # 中心 9.79、穴の下縁 7.29 > 7
    assert any("フランジ" in w for w in _fatal(lug_fits(override(SPEC, lug__body_dia=180))))           # 中心 4.79、穴の下縁 2.29 < 7
    high = {"hoop.outer.od": 5, "head.collar_height": 1}                                         # ラグの上端が 111.19 に上がる
    assert any("胴の上端" in w for w in _fatal(lug_fits(override(SPEC, lug__body_dia=10, **high))))     # 中心 106.19、穴の上縁 108.69 > 107
    assert not any("胴の上端" in w for w in _fatal(lug_fits(override(SPEC, lug__body_dia=40, **high))))


def test_the_mounting_hole_must_fall_inside_the_disc():
    """取付穴（φ5）は円盤（φ30）の中に収まる。円盤が穴以下だと、ねじの座が円盤に残らない。"""
    assert any("円盤" in w and "穴" in w for w in _fatal(lug_fits(override(SPEC, lug__hole_dia=30))))
    assert any("円盤" in w and "穴" in w for w in _fatal(lug_fits(override(SPEC, lug__hole_dia=31))))
    assert not any("円盤" in w and "穴" in w for w in _fatal(lug_fits(override(SPEC, lug__hole_dia=29.9))))


def test_the_rod_must_pass_inside_the_disc_depth():
    """ロッドの通る位置（胴の外面から standoff 11.75、ロッドの半径 2.75）が円盤の厚み depth 20 の中。外縁 14.5 を超えると円盤の外面から出る。"""
    assert lug_fits(SPEC) == []
    assert any("厚み" in w for w in _fatal(lug_fits(override(SPEC, lug__depth=14.4))))
    assert any("厚み" in w for w in _fatal(lug_fits(override(SPEC, lug__standoff=17.3))))
    assert not any("厚み" in w for w in _fatal(lug_fits(override(SPEC, lug__depth=14.5))))
    assert not any("厚み" in w for w in _fatal(lug_fits(override(SPEC, lug__standoff=17.2))))
    assert any("厚み" in w for w in _fatal(lug_fits(override(SPEC, lug__thread="M5", lug__depth=14.2))))      # M5 は φ5、外縁 14.25


def test_the_disc_must_leave_a_wall_around_the_rod_bore():
    """円盤（φ30）にロッドの穴（#12-24 = φ5.5）を通す。円盤の径が穴径以下だと、ロッドの外縁が円盤の幅の外に出て肉が残らない。"""
    assert lug_fits(SPEC) == []
    assert any("円盤" in w and "ロッド" in w for w in _fatal(lug_fits(override(SPEC, lug__body_dia=5.5, lug__hole_dia=2))))
    assert any("円盤" in w and "ロッド" in w for w in _fatal(lug_fits(override(SPEC, lug__body_dia=5, lug__hole_dia=2))))
    assert not any("円盤" in w and "ロッド" in w for w in _fatal(lug_fits(override(SPEC, lug__body_dia=5.6, lug__hole_dia=2))))
    assert any("円盤" in w and "ロッド" in w for w in _fatal(lug_fits(override(SPEC, lug__thread="M5", lug__body_dia=4.9, lug__hole_dia=2))))
    assert not any("円盤" in w and "ロッド" in w for w in _fatal(lug_fits(override(SPEC, lug__thread="M5", lug__body_dia=5.1, lug__hole_dia=2))))


def test_too_many_ears_and_lugs_run_into_each_other():
    """隣り合う矩形は内側の端で先に当たる。幅 ≤ 2 × 内端の半径 × tan(180° / 個数)。
    受金（幅 20、内端 = 内リングの外面 r 80.7）は 25 個まで。ラグは円盤の径 d が幅で、内端は胴の外面の円で切られる側縁の根元
    （半径 √(76² − (d / 2)²)）。d = 19.5 なら 24 個まで（19.5 ≤ 2 × 75.37 × tan 7.5° = 19.85）、25 個（19.04）で当たる。既定の d = 30 は 12 個まで。"""
    found = _fatal(spacing(override(SPEC, **{"lug__body_dia": 19.5, "lug__count": 26, "hoop__ear__count": 26})))
    assert any("受金" in w for w in found) and any("ラグ" in w for w in found), found
    found = _fatal(spacing(override(SPEC, lug__body_dia=19.5, lug__count=25, hoop__ear__count=25)))
    assert any("ラグ" in w for w in found) and not any("受金" in w for w in found), found
    assert spacing(override(SPEC, lug__body_dia=19.5, lug__count=24, hoop__ear__count=24)) == []
    assert any("ラグ" in w for w in _fatal(spacing(override(SPEC, lug__count=24, hoop__ear__count=24))))      # 既定の円盤 φ30 は 24 個で隣と重なる
    assert spacing(override(SPEC, lug__count=12, hoop__ear__count=12)) == []
    # 内端が側縁の根元（75.35）か胴の半径（76）かで分かれる径: 24 個の許容幅は 19.84 と 20.01。19.9 は根元なら重なる
    assert any("ラグ" in w for w in _fatal(spacing(override(SPEC, lug__body_dia=19.9, lug__count=24, hoop__ear__count=24))))
    assert spacing(SPEC) == [] and spacing(override(SPEC, lug__count=2, hoop__ear__count=2)) == []
