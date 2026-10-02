"""検査（部品どうしの平面視の重なり）: ラグ・ロッドとホルダー受け・当て板、ホルダー受け・当て板と胴まわりの回転体、
グリップと当て板・ホルダー受け。z が重なり、平面視（グリップは YZ 面）でも重なれば干渉（fatal）。"""

from __future__ import annotations

import pytest
from gatling.interference import mount_clear
from gatling.params import SPEC, override


def _fatal(spec):
    return [i.what for i in mount_clear(spec) if i.fatal]


def test_the_default_spec_has_nothing_in_the_way():
    assert mount_clear(SPEC) == []


@pytest.mark.parametrize("count", [4, 8, 12])
def test_a_lug_under_the_holder_is_fatal(count):
    """ラグ数 4・8・12 では −Y（270°）にラグが来て、ホルダー受け（中心 y −110.5、半径 20）にラグの箱（u 76〜96）が 5.5 食い込む。"""
    found = _fatal(override(SPEC, lug__count=count, hoop__ear__count=count))
    assert any("ラグ" in w and "ホルダー受け" in w for w in found), found


def test_a_lug_that_just_clears_the_holder_passes():
    # 逃げ 20.5: ホルダー中心 y −116、内縁 −96 = ラグの外端 −96（接するだけ）
    assert not any("ホルダー受け" in w for w in _fatal(override(SPEC, lug__count=12, hoop__ear__count=12, cradle__clearance=20.5)))
    assert any("ホルダー受け" in w for w in _fatal(override(SPEC, lug__count=12, hoop__ear__count=12, cradle__clearance=20.4)))


def test_a_lug_that_reaches_down_to_the_pad_is_fatal():
    # ラグ 12 個。ラグ（z 63.79〜98.79）は当て板（z 60〜66）と z が重なり、270° のラグ（y −76〜−96）が当て板（y −86〜）に入る。
    # ホルダーは逃げ 21 で避けておく
    found = _fatal(override(SPEC, lug__count=12, hoop__ear__count=12, cradle__clearance=21))
    assert any("ラグ" in w and "当て板" in w for w in found), found
    assert not any("当て板" in w for w in _fatal(override(SPEC, lug__count=12, hoop__ear__count=12, cradle__clearance=31)))


def test_a_holder_that_rises_into_the_outer_ring_is_fatal():
    """ホルダー受けの内縁 r 90.5 は外リングの管の外面 r 116.1 の内側。上端 66 + 高さが管の下端 103.79 を超えると当たる。"""
    assert any("ホルダー受け" in w and "外リング" in w for w in _fatal(override(SPEC, mount__body_height=60)))
    assert any("ホルダー受け" in w and "外リング" in w for w in _fatal(override(SPEC, mount__body_height=37.8)))
    assert _fatal(override(SPEC, mount__body_height=37.7)) == []          # 上端 103.7 < 103.79


def test_a_pad_that_reaches_over_the_shell_is_fatal():
    """当て板の内縁 y = −(83 + 逃げ + 12.5) + 30。胴の外面 r 76 より内側に入ると胴に食い込む（逃げ 10.5 未満）。"""
    assert any("当て板" in w and "胴" in w for w in _fatal(override(SPEC, cradle__clearance=8)))
    assert not any("当て板" in w for w in _fatal(override(SPEC, cradle__clearance=10.5)))


def test_a_grip_too_close_to_the_frame_runs_into_the_pad_and_the_holder():
    """グリップ（φ28、中心 z 57）は当て板の下の角（y −140.5、z 60）から 14 離す。handle_length の下限は約 31.17。"""
    found = _fatal(override(SPEC, cradle__handle_length=5))
    assert any("グリップ" in w and "当て板" in w for w in found) and any("グリップ" in w and "ホルダー受け" in w for w in found), found
    assert any("グリップ" in w for w in _fatal(override(SPEC, cradle__handle_length=31.1)))
    assert _fatal(override(SPEC, cradle__handle_length=31.2)) == []


def test_a_lug_that_reaches_down_to_the_frame_and_sticks_out_of_it_is_fatal():
    """ラグ高さ 50（下端 48.79）でフレーム（z 54〜60）と z が重なる。0° のラグの外の隅 (96, ±10) がフレーム内面 83 + 逃げ の外に出ると当たる。"""
    tall = {"lug.height": 50}
    assert any("ラグ" in w and "フレーム" in w for w in _fatal(override(SPEC, cradle__clearance=8, **tall)))
    assert any("ラグ" in w and "フレーム" in w for w in _fatal(override(SPEC, cradle__clearance=12.9, **tall)))
    assert not any("フレーム" in w for w in _fatal(override(SPEC, cradle__clearance=13, **tall)))     # 隅がちょうど内面に接する


def test_a_lug_on_the_diagonal_that_reaches_down_to_an_arm_is_fatal():
    """腕はフレームの内側（対角線上、胴バンドの外面から隅まで）にある。フレームの平角材を厚くすると腕が胴バンドの上端より上に出て、
    45° のラグ（ラグ 8 個）の下端に届く。脚はフレームの内面より外にあるので、脚に届くラグはフレームの検査で先に止まる。"""
    values = {"lug.count": 8, "hoop.ear.count": 8, "cradle.bar.thickness": 40, "lug.height": 60}
    assert any("ラグ" in w and "腕" in w for w in _fatal(override(SPEC, **values)))
    assert not any("腕" in w for w in _fatal(override(SPEC, **{**values, "lug.height": 47.2})))     # 下端 51.59 > 腕の上端 51.5


@pytest.mark.parametrize("values", [{"band.bar.width": 36}, {"band.above_flange": 23}, {"shell.plenum_height": 76}])
def test_a_band_tab_that_rises_into_the_frame_is_fatal(values):
    """耳の外端（バンド外面 83 + 耳の長さ 20 = 103）はフレームの内面 98 より外にある。既定では z が離れている
    （バンド 19〜44、フレーム 54〜60）だけで、バンドを広げる・上げる、胴を低くしてフレームを下げると当たる。"""
    assert any("耳" in w and "フレーム" in w for w in _fatal(override(SPEC, **values))), values


def test_a_band_tab_inside_the_frame_passes():
    """逃げ 21 でフレームの内面 104 > 耳の外端 103。"""
    assert not any("耳" in w for w in _fatal(override(SPEC, cradle__clearance=21, band__bar__width=36)))


def test_a_rod_that_runs_out_of_the_lug_down_to_a_band_tab_is_fatal():
    """軸の先がラグの下端（63.79）より下に出るのは警告だが、さらに下の胴バンドの耳（0° と 180°、上端 44）に届けば干渉。
    軸の先 = 受金の上面 123.19 − 長さ。長さ 79 で 44.19、85 で 38.19。"""
    assert any("ロッド" in w and "耳" in w for w in _fatal(override(SPEC, lug__rod_length=85)))
    assert not any("ロッド" in w for w in _fatal(override(SPEC, lug__rod_length=79)))


# 軸の先（受金の上面 123.19 − 長さ）がラグの下端（63.79）より下に出る override。ロッドとラグの外の部品との干渉は、
# それぞれの部品にだけ当たる値で、境界の 2 点（当たる・当たらない）を押さえる。
_ARM = {"lug.count": 24, "hoop.ear.count": 24, "cradle.clearance": 31, "cradle.bar.thickness": 40, "mount.body_height": 20}
_HOLDER = {"lug.count": 12, "hoop.ear.count": 12, "cradle.clearance": 13, "cradle.pad.thickness": 1, "mount.body_height": 2}
_FRAME = {"cradle.clearance": 5, "cradle.pad.depth": 40, "cradle.pad.width": 40}
_BAND = {"lug.standoff": 9.5}


def _rod_hits(spec, part):
    return [w for w in _fatal(spec) if w.startswith("ロッドが") and part in w]


def test_a_rod_that_runs_down_to_a_cradle_arm_is_fatal():
    """腕（対角線、厚み 40 のバンドの中心 ± 20 で上端 51.5）に、45° のロッド（ラグ 24 個）の先が届く。軸の先 = 123.19 − 長さ。
    長さ 71.5 で 51.69（腕の上）、72 で 51.19（腕の中）。"""
    assert _rod_hits(override(SPEC, **_ARM, lug__rod_length=72), "腕")
    assert _fatal(override(SPEC, **_ARM, lug__rod_length=71.5)) == []


def test_a_rod_that_runs_down_to_a_body_band_is_fatal():
    """胴バンド（上端 44、外面 83）に、ロッド（半径 86 の円周上）が届く。standoff 9.5 で既定の長さ 50 より下へ。
    長さ 79 で軸の先 44.19（バンドの上）、79.5 で 43.69（バンドの中）。"""
    assert _rod_hits(override(SPEC, **_BAND, lug__rod_length=79.5), "胴バンドに")
    assert _fatal(override(SPEC, **_BAND, lug__rod_length=79)) == []


def test_a_rod_that_runs_down_to_the_holder_seat_is_fatal():
    """ホルダー受け（z 61〜63。フレーム上面 60 + 当て板厚 1 の上に高さ 2）に、270° のロッド（ラグ 12 個。管 6 本と方位が揃う）が届く。
    当て板（z 60〜61）は薄く、ラグの下端 63.79 はホルダー受けの上端 63 より上なので、ロッドの軸だけが当たる。
    長さ 60 で軸の先 63.19（ホルダー受けの上）、61 で 62.19（中）。"""
    assert _rod_hits(override(SPEC, **_HOLDER, lug__rod_length=61), "ホルダー受け")
    assert _fatal(override(SPEC, **_HOLDER, lug__rod_length=60)) == []


def test_a_rod_that_runs_down_to_the_cradle_frame_is_fatal():
    """フレーム（z 54〜60、内面 83 + 逃げ）に、0°・180° のロッド（中心半径 86、軸の半径 3 → 外側 89）が届く。逃げ 5 で内面 88 < 89。
    長さ 63 で軸の先 60.19（フレームの上）、64 で 59.19（フレームの中）。逃げ 6 なら内面 89 に収まる。"""
    assert _rod_hits(override(SPEC, **_FRAME, lug__rod_length=64), "フレーム")
    assert _fatal(override(SPEC, **_FRAME, lug__rod_length=63)) == []
    assert not _rod_hits(override(SPEC, **{**_FRAME, "cradle.clearance": 6}, lug__rod_length=70), "フレーム")


def test_a_holder_seat_that_reaches_the_ear_beside_a_thin_tube_is_fatal():
    """受金の外半径は外端の隅 hypot(管の中心半径 95.7, 幅の半分 10) = 96.22（内リングの外面ではない）。管の外径 10 だと管の下端
    （129.19 − 10 = 119.19）が受金の上面（123.19）より下がり、ホルダー受けの上端が 119.19 より低ければ管には届かず、受金（z 117.19〜123.19）
    だけに当たる。ホルダー受けの上端は 66 + 高さで、51.5 で 117.5（受金の下面 117.19 より上）、51 で 117（下）。"""
    found = [w for w in _fatal(override(SPEC, hoop__outer__od=10, mount__body_height=51.5))]
    assert len(found) == 1 and "受金" in found[0] and "外半径 96.22" in found[0], found
    assert _fatal(override(SPEC, hoop__outer__od=10, mount__body_height=51)) == []
