"""出典つき寸法の回帰テスト。守りたいのは「仮の値が出典検査を素通りしない」こと。"""

from __future__ import annotations

import copy
import io
import pickle
from dataclasses import asdict, dataclass, field

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


# --- コピー・直列化 ---------------------------------------------------------


def _round_trip(obj, protocol=pickle.HIGHEST_PROTOCOL):
    """自分で作ったバイト列だけを戻す。信頼できない入力には使わない。"""
    return pickle.Unpickler(io.BytesIO(pickle.dumps(obj, protocol))).load()


def test_a_dim_survives_deepcopy_with_source_and_note():
    d = provisional(450, "結合モデルで振ってから決める")
    c = copy.deepcopy(d)
    assert c == 450 and c.source is Source.PROVISIONAL and c.note == d.note


@pytest.mark.parametrize("protocol", range(2, pickle.HIGHEST_PROTOCOL + 1))
def test_a_dim_survives_a_pickle_round_trip(protocol):
    d = measured(12.7, "ノギスで測った")
    c = _round_trip(d, protocol)
    assert c == 12.7 and c.source is Source.MEASURED and c.note == "ノギスで測った"


def test_a_choice_survives_deepcopy_and_pickle():
    c = Choice("DW turret", Source.PROVISIONAL, "実物を測るまで")
    assert copy.deepcopy(c) == c
    assert _round_trip(c) == c


def test_asdict_keeps_every_leaf_value_source_and_note():
    s = _spec()
    d = asdict(s)
    assert d["tube"]["length"] == 450 and d["tube"]["length"].source is Source.PROVISIONAL
    assert d["tube"]["finish"] == s.tube.finish
    assert d["profile"][1][0].source is Source.PROVISIONAL


# --- override が walk のパスを受け付ける ------------------------------------


@dataclass(frozen=True)
class _Holder:
    pts: list
    ring: tuple
    nested: tuple


def _holder() -> _Holder:
    return _Holder(
        pts=[design(1, "点 0"), provisional(2, "点 1")],
        ring=(Choice("a", Source.DESIGN, "輪 0"), Choice("b", Source.PROVISIONAL)),
        nested=(_Tube(od=design(10), length=provisional(20), finish=Choice("x", Source.DESIGN)),),
    )


def test_override_accepts_an_index_into_a_tuple_and_keeps_the_container_type():
    s = _spec()
    t = override(s, {"profile[1][0]": 9})
    assert float(t.profile[1][0]) == 9
    assert t.profile[1][0].source is Source.PROVISIONAL, "出典を継ぐ"
    assert isinstance(t.profile, tuple) and isinstance(t.profile[1], tuple)
    assert t.profile[0] == s.profile[0], "ほかの要素は変えない"
    assert float(s.profile[1][0]) == 3, "元は変えない"


def test_override_accepts_an_index_into_a_list_and_keeps_the_container_type():
    h = _holder()
    t = override(h, {"pts[1]": 5})
    assert isinstance(t.pts, list) and t.pts is not h.pts
    assert float(t.pts[1]) == 5 and t.pts[1].note == "点 1"
    assert float(h.pts[1]) == 2, "元の list は変えない"


def test_override_accepts_a_path_that_goes_through_an_index_into_a_dataclass():
    t = override(_holder(), {"nested[0].length": 99})
    assert float(t.nested[0].length) == 99 and t.nested[0].length.source is Source.PROVISIONAL


def test_override_replaces_a_choice_inside_a_tuple():
    t = override(_holder(), {"ring[0]": "z"})
    assert t.ring[0].value == "z" and t.ring[0].note == "輪 0"


def test_override_applies_several_indexed_paths_into_the_same_container():
    t = override(_holder(), {"pts[0]": 7, "pts[1]": 8})
    assert [float(p) for p in t.pts] == [7, 8]


def _leaf_at(obj, path):
    return dict(walk(obj))[path]


@pytest.mark.parametrize("root", [_spec, _holder])
def test_override_round_trips_every_path_walk_emits(root):
    s = root()
    for path, leaf in walk(s):
        new = "ZZ" if isinstance(leaf, Choice) else float(leaf) + 1000
        t = override(s, {path: new})
        changed = [p for p, _ in walk(t) if _leaf_at(t, p) != _leaf_at(s, p)]
        assert changed == [path], path
        got = _leaf_at(t, path)
        assert (got.value if isinstance(got, Choice) else float(got)) == new
        assert (got.source, got.note) == (leaf.source, leaf.note)


def test_override_rejects_an_index_out_of_range():
    with pytest.raises(IndexError, match=r"profile\[5\]"):
        override(_spec(), {"profile[5][0]": 1})


def test_override_rejects_an_index_into_something_that_is_not_a_sequence():
    with pytest.raises(AttributeError, match=r"lugs\[0\]"):
        override(_spec(), {"lugs[0]": 1})


def test_override_rejects_an_unknown_attribute_after_an_index():
    with pytest.raises(AttributeError, match=r"nested\[0\]\.nope"):
        override(_holder(), {"nested[0].nope": 1})


# --- as_provisional は init=False の葉を黙って落とさない -----------------------


@dataclass(frozen=True)
class _Derived:
    base: Dim
    twice: Dim = field(init=False)
    label: str = field(init=False, default="導出")

    def __post_init__(self):
        object.__setattr__(self, "twice", derived(float(self.base) * 2, "base の 2 倍"))


def test_as_provisional_rejects_a_leaf_in_an_init_false_field_and_names_its_path():
    with pytest.raises(TypeError, match=r"twice.*__post_init__"):
        as_provisional(_Derived(design(3)), "別径から写した")


def test_as_provisional_names_the_full_path_of_an_init_false_leaf_nested_in_a_container():
    @dataclass(frozen=True)
    class _Outer:
        items: tuple

    with pytest.raises(TypeError, match=r"items\[1\]\.twice"):
        as_provisional(_Outer((design(1), _Derived(design(3)))), "x")


def test_as_provisional_still_copies_an_init_false_field_without_leaves():
    @dataclass(frozen=True)
    class _Plain:
        base: Dim
        tag: str = field(init=False, default="固定")

    copied = as_provisional(_Plain(design(3)), "x")
    assert copied.base.source is Source.PROVISIONAL and copied.tag == "固定"
