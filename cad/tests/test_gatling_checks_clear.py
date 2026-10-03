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
    """ラグ数 4・8・12 では −Y（270°）にラグが来て、ホルダー受け（中心 y −110.5、半径 20）にラグの円盤（外側の面 u 96）が 5.5 食い込む。"""
    found = _fatal(override(SPEC, lug__count=count, hoop__ear__count=count))
    assert any("ラグ" in w and "ホルダー受け" in w for w in found), found


def test_a_lug_that_just_clears_the_holder_passes():
    # 逃げ 20.5: ホルダー中心 y −116、内縁 −96 = ラグの円盤の外側の面 −96（接するだけ）
    assert not any("ホルダー受け" in w for w in _fatal(override(SPEC, lug__count=12, hoop__ear__count=12, cradle__clearance=20.5)))
    assert any("ホルダー受け" in w for w in _fatal(override(SPEC, lug__count=12, hoop__ear__count=12, cradle__clearance=20.4)))


def test_a_lug_that_reaches_down_to_the_pad_is_fatal():
    # ラグ 12 個。ラグ（z 64.79〜94.79）は当て板（z 60〜66）と z が重なり、270° のラグ（y −74〜−96 の円盤。当て板の帯では半幅 5.9）が当て板（y −80.5〜）に入る。
    # ホルダーは逃げ 21 で避けておく
    found = _fatal(override(SPEC, lug__count=12, hoop__ear__count=12, cradle__clearance=21))
    assert any("ラグ" in w and "当て板" in w for w in found), found
    assert not any("当て板" in w for w in _fatal(override(SPEC, lug__count=12, hoop__ear__count=12, cradle__clearance=31)))


def test_a_holder_that_rises_into_the_outer_ring_is_fatal():
    """ホルダー受けの内縁 r 90.5 は外リングの管の外面 r 116.1 の内側。上端 66 + 高さが管の下端 99.79 を超えると当たる。"""
    assert any("ホルダー受け" in w and "外リング" in w for w in _fatal(override(SPEC, mount__body_height=60)))
    assert any("ホルダー受け" in w and "外リング" in w for w in _fatal(override(SPEC, mount__body_height=33.8)))
    assert _fatal(override(SPEC, mount__body_height=33.7)) == []          # 上端 99.7 < 99.79


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
    """円盤の径 50（下端 44.79）でフレーム（z 54〜60）と z が重なる。0° のラグの外側の面（u = 76 + 20 = 96）が
    フレーム内面 83 + 逃げ の外に出ると当たる（逃げ 13 でちょうど接する）。"""
    tall = {"lug.body_dia": 50}
    assert any("ラグ" in w and "フレーム" in w for w in _fatal(override(SPEC, cradle__clearance=8, **tall)))
    assert any("ラグ" in w and "フレーム" in w for w in _fatal(override(SPEC, cradle__clearance=12.9, **tall)))
    assert not any("フレーム" in w for w in _fatal(override(SPEC, cradle__clearance=13, **tall)))     # 外側の面がちょうど内面に接する


def test_a_lug_on_the_diagonal_that_reaches_down_to_an_arm_is_fatal():
    """腕はフレームの内側（対角線上、胴バンドの外面から隅まで）にある。フレームの平角材を厚くすると腕が胴バンドの上端より上に出て、
    45° のラグ（ラグ 8 個）の下端に届く。脚はフレームの内面より外にあるので、脚に届くラグはフレームの検査で先に止まる。"""
    values = {"lug.count": 8, "hoop.ear.count": 8, "cradle.bar.thickness": 40, "lug.body_dia": 60}
    assert any("ラグ" in w and "腕" in w for w in _fatal(override(SPEC, **values)))
    assert not any("腕" in w for w in _fatal(override(SPEC, **{**values, "lug.body_dia": 43.2})))     # 下端 51.59 > 腕の上端 51.5


@pytest.mark.parametrize("values", [{"band.bar.width": 36}, {"band.above_flange": 23}, {"shell.plenum_height": 76}])
def test_a_band_tab_that_rises_into_the_frame_is_fatal(values):
    """耳の外端（バンド外面 83 + 耳の長さ 20 = 103）はフレームの内面 98 より外にある。既定では z が離れている
    （バンド 19〜44、フレーム 54〜60）だけで、バンドを広げる・上げる、胴を低くしてフレームを下げると当たる。"""
    assert any("耳" in w and "フレーム" in w for w in _fatal(override(SPEC, **values))), values


def test_a_band_tab_inside_the_frame_passes():
    """逃げ 21 でフレームの内面 104 > 耳の外端 103。"""
    assert not any("耳" in w for w in _fatal(override(SPEC, cradle__clearance=21, band__bar__width=36)))


def test_a_rod_that_runs_out_of_the_lug_down_to_a_band_tab_is_fatal():
    """軸の先がラグの下端（64.79）より下に出るのは警告だが、さらに下の胴バンドの耳（0° と 180°、上端 44）に届けば干渉。
    軸の先 = 受金の上面 120.19 − 長さ。長さ 76 で 44.19、82 で 38.19。"""
    assert any("ロッド" in w and "耳" in w for w in _fatal(override(SPEC, lug__rod_length=82)))
    assert not any("ロッド" in w for w in _fatal(override(SPEC, lug__rod_length=76)))


# 軸の先（受金の上面 120.19 − 長さ）がラグの下端（64.79。24 個の _ARM は円盤を細くして 75.29）より下に出る override。ロッドとラグの外の部品との干渉は、
# それぞれの部品にだけ当たる値で、境界の 2 点（当たる・当たらない）を押さえる。
_ARM = {"lug.count": 24, "hoop.ear.count": 24, "lug.body_dia": 19.5, "cradle.clearance": 31, "cradle.bar.thickness": 40, "mount.body_height": 15}
_HOLDER = {"lug.count": 12, "hoop.ear.count": 12, "cradle.clearance": 13, "cradle.bar.thickness": 1, "cradle.pad.thickness": 1,
           "mount.body_height": 1}
_FRAME = {"cradle.clearance": 5, "cradle.pad.depth": 40, "cradle.pad.width": 40, "cradle.bar.thickness": 5}
_BAND = {"lug.standoff": 9.5}


def _rod_hits(spec, part):
    return [w for w in _fatal(spec) if w.startswith("ロッドが") and part in w]


def test_a_rod_that_runs_down_to_a_cradle_arm_is_fatal():
    """腕（対角線、厚み 40 のバンドの中心 ± 20 で上端 51.5）に、45° のロッド（ラグ 24 個）の先が届く。軸の先 = 120.19 − 長さ。
    長さ 68.5 で 51.69（腕の上）、69 で 51.19（腕の中）。ホルダー受けは高さ 15 にして、管の下端 99.79 より下に収める。"""
    assert _rod_hits(override(SPEC, **_ARM, lug__rod_length=69), "腕")
    assert _fatal(override(SPEC, **_ARM, lug__rod_length=68.5)) == []


def test_a_rod_that_runs_down_to_a_body_band_is_fatal():
    """胴バンド（上端 44、外面 83）に、ロッド（半径 86 の円周上）が届く。standoff 9.5 で既定の長さ 50 より下へ。
    長さ 76 で軸の先 44.19（バンドの上）、76.5 で 43.69（バンドの中）。"""
    assert _rod_hits(override(SPEC, **_BAND, lug__rod_length=76.5), "胴バンドに")
    assert _fatal(override(SPEC, **_BAND, lug__rod_length=76)) == []


def test_a_rod_that_runs_down_to_the_holder_seat_is_fatal():
    """ホルダー受け（z 58.5〜59.5。フレームの厚み 1 の上面 57.5 + 当て板厚 1 の上に高さ 1）に、270° のロッド（ラグ 12 個。管 6 本と
    方位が揃う）が届く。ラグの下端 64.79 はホルダー受けの上端 59.5 より上なので、ロッドの軸だけが当たる（フレームを薄くして下げた）。
    長さ 60 で軸の先 60.19（ホルダー受けの上）、61 で 59.19（中）。"""
    assert _rod_hits(override(SPEC, **_HOLDER, lug__rod_length=61), "ホルダー受け")
    assert _fatal(override(SPEC, **_HOLDER, lug__rod_length=60)) == []


def test_a_rod_that_runs_down_to_the_cradle_frame_is_fatal():
    """フレーム（厚み 5 で z 54.5〜59.5、内面 83 + 逃げ）に、0°・180° のロッド（中心半径 86、軸の半径 3 → 外側 89）が届く。逃げ 5 で内面 88 < 89。
    ラグの下端 64.79 がフレームの上面 59.5 より上になるよう薄くしてある。長さ 60.6 で軸の先 59.59（フレームの上）、60.8 で 59.39（中）。
    逃げ 6 なら内面 89 に収まる。"""
    assert _rod_hits(override(SPEC, **_FRAME, lug__rod_length=60.8), "フレーム")
    assert _fatal(override(SPEC, **_FRAME, lug__rod_length=60.6)) == []
    assert not _rod_hits(override(SPEC, **{**_FRAME, "cradle.clearance": 6}, lug__rod_length=70), "フレーム")


def test_a_holder_seat_that_reaches_the_ear_beside_a_thin_tube_is_fatal():
    """受金の外半径は外端の隅 hypot(管の中心半径 95.7, 幅の半分 10) = 96.22（内リングの外面ではない）。管の外径 10 だと管の下端
    （125.19 − 10 = 115.19）が受金の下面（114.19）より上がり、ホルダー受けの上端が 115.19 より低ければ管には届かず、受金（z 114.19〜120.19）
    だけに当たる。ホルダー受けの上端は 66 + 高さで、48.3 で 114.3（受金の下面 114.19 より上）、48.1 で 114.1（下）。"""
    found = [w for w in _fatal(override(SPEC, hoop__outer__od=10, mount__body_height=48.3))]
    assert len(found) == 1 and "受金" in found[0] and "外半径 96.22" in found[0], found
    assert _fatal(override(SPEC, hoop__outer__od=10, mount__body_height=48.1)) == []
