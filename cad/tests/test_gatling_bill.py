"""既製品の部品表（`bom(spec)`）。"""

from __future__ import annotations

from gatling.bill import UNDECIDED, bom
from gatling.catalog import parts
from gatling.params import SPEC, override


def test_every_purchased_part_with_a_shape_has_a_row_with_the_same_count():
    rows = {r.name: r for r in bom(SPEC)}
    for info in parts(SPEC):
        if info.made == "purchased":
            assert rows[info.label].count == info.count, info.name
            assert rows[info.label].standard == info.standard and rows[info.label].dimensions == info.dimensions


def test_no_fabricated_part_is_in_the_purchased_rows():
    labels = {i.label for i in parts(SPEC) if i.made == "fabricated"}
    assert not labels & {r.name for r in bom(SPEC)}
    assert all(r.made == "purchased" for r in bom(SPEC))


def test_the_parts_without_a_shape_are_counted_from_the_spec():
    rows = {r.name: r for r in bom(SPEC)}
    assert rows["ラグボルト"].count == 12 and rows["シール座金"].count == 12            # ラグ 6 個 × 2
    assert rows["ゴムシート"].count == 2 and rows["ゴムシート"].dimensions == "t1" and rows["焼き付き防止剤"].count == 1
    assert rows["ボルト M6（クレードルの腕）"].count == 4                              # 腕は溶接せずボルトで留める
    fewer = {r.name: r for r in bom(override(SPEC, lug__count=3, hoop__ear__count=3))}
    assert fewer["ラグボルト"].count == 6 and fewer["ラグ"].count == 3 and fewer["テンションロッド"].count == 3


def test_no_two_rows_share_a_name():
    """行名は部品表の 1 行を指す。同じ名前が 2 行あると、員数がどちらの行のものか読めない。
    部品表の全体は、製作品の行（表示名）と既製品の行（`bom()`）。"""
    names = [i.label for i in parts(SPEC) if i.made == "fabricated"] + [r.name for r in bom(SPEC)]
    assert len(names) == len(set(names)), names


def test_part_numbers_are_undecided_until_the_real_parts_are_measured():
    assert all(r.part_number == UNDECIDED == "未定" for r in bom(SPEC))
    assert all(r.mass_g is None and r.material is None for r in bom(SPEC))            # 既製品の質量は載せない


def test_the_rows_follow_the_choices():
    rows = {r.name: r for r in bom(override(SPEC, lug__thread="M5"))}
    assert rows["テンションロッド"].standard == "テンションロッド M5"
