"""出典つき寸法の回帰テスト。守りたいのは「仮の値が出典検査を素通りしない」こと。"""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from drumcad.dims import (Choice, Dim, Source, as_provisional, design, derived, measured,
                          override, provisional, spec, unsettled, walk)


def test_a_dim_behaves_like_a_float_in_arithmetic():
    d = design(38.1, "手すり用 #400 研磨管")
    assert d + 1.9 == pytest.approx(40.0)
    assert isinstance(d * 2, float)
    assert d.source is Source.DESIGN
    assert d.note == "手すり用 #400 研磨管"


@pytest.mark.parametrize("factory, source", [
    (measured, Source.MEASURED), (spec, Source.SPEC), (design, Source.DESIGN),
    (derived, Source.DERIVED), (provisional, Source.PROVISIONAL),
])
def test_each_factory_stamps_its_source(factory, source):
    assert factory(1.0).source is source


def test_only_provisional_is_unsettled():
    assert not Source.PROVISIONAL.is_settled
    assert all(s.is_settled for s in Source if s is not Source.PROVISIONAL)


def test_repr_shows_value_source_and_note():
    assert repr(provisional(450, "結合モデルで振ってから決める")) == "450 [仮 — 結合モデルで振ってから決める]"
    assert repr(design(6)) == "6 [設計判断]"


@dataclass(frozen=True)
class _Tube:
    od: Dim
    length: Dim
    finish: Choice


@dataclass(frozen=True)
class _Spec:
    tube: _Tube
    lugs: Dim
    profile: tuple[tuple[Dim, Dim], ...]
    label: str = "固定の文字列"


def _spec() -> _Spec:
    return _Spec(
        tube=_Tube(od=design(38.1), length=provisional(450), finish=Choice("#400", Source.DESIGN)),
        lugs=design(6),
        profile=((design(0), design(0)), (provisional(3), design(25))),
    )


def test_a_choice_carries_a_value_and_a_source():
    c = Choice("DW turret", Source.PROVISIONAL, "実物を測るまで")
    assert c.value == "DW turret"
    assert c.source is Source.PROVISIONAL
    assert repr(c) == "'DW turret' [仮 — 実物を測るまで]"


def test_walk_visits_dims_and_choices_by_attribute_path():
    paths = dict(walk(_spec()))
    assert set(paths) == {"tube.od", "tube.length", "tube.finish", "lugs",
                          "profile[0][0]", "profile[0][1]", "profile[1][0]", "profile[1][1]"}
    assert isinstance(paths["tube.finish"], Choice)


def test_walk_skips_plain_strings_and_dormant_fields():
    @dataclass(frozen=True)
    class _WithDormant:
        used: Dim
        unused: Dim

        def dormant_fields(self) -> frozenset[str]:
            return frozenset({"unused"})

    assert [p for p, _ in walk(_WithDormant(design(1), provisional(2)))] == ["used"]
    assert "label" not in dict(walk(_spec()))


def test_unsettled_lists_every_provisional_leaf_including_choices():
    s = _Spec(tube=_Tube(od=design(38.1), length=provisional(450),
                         finish=Choice("#400", Source.PROVISIONAL)),
              lugs=design(6), profile=())
    assert [p for p, _ in unsettled(s)] == ["tube.length", "tube.finish"]


def test_as_provisional_keeps_values_but_drops_every_source():
    copied = as_provisional(_spec(), "別径から写した")
    assert all(d.source is Source.PROVISIONAL for _, d in walk(copied))
    assert copied.tube.od == 38.1 and copied.tube.finish.value == "#400"
    assert copied.tube.od.note == "別径から写した"
    assert copied.label == "固定の文字列"


def test_as_provisional_returns_the_same_object_when_nothing_changes():
    @dataclass(frozen=True)
    class _NoDims:
        name: str
        density: float

    m = _NoDims("SUS304", 7.93e-3)
    assert as_provisional(m, "x") is m


def test_override_replaces_a_leaf_by_attribute_path_and_keeps_the_rest():
    s = _spec()
    t = override(s, {"tube.length": 500, "lugs": 8})
    assert float(t.tube.length) == 500 and float(t.lugs) == 8
    assert t.tube.od is s.tube.od
    assert s.tube.length == 450, "元は変えない"


def test_override_keeps_the_source_and_note_of_the_replaced_dim():
    t = override(_spec(), {"tube.length": 500})
    assert t.tube.length.source is Source.PROVISIONAL


def test_override_replaces_a_choice_with_a_string():
    t = override(_spec(), {"tube.finish": "鏡面"})
    assert t.tube.finish.value == "鏡面" and t.tube.finish.source is Source.DESIGN


def test_override_rejects_an_unknown_path():
    with pytest.raises(AttributeError, match="tube.nope"):
        override(_spec(), {"tube.nope": 1})
