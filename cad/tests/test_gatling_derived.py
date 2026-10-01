"""導出値（仕様 §5.2「導出値」）と機種名。"""

from __future__ import annotations

import dataclasses
import math

import pytest
from drumcad.dims import Choice, Dim, Source, design
from gatling.derived import Derived, derive, derived_from, name
from gatling.params import SPEC, override


def _settled(spec, **groups):
    """`tube=...` のようにグループごとに差し替えた spec（出典ごと差し替えるので確定にできる）。"""
    return dataclasses.replace(spec, **groups)


def test_derived_from_is_provisional_when_any_input_is_provisional():
    pending = Dim(1, Source.PROVISIONAL, "待ち")
    out = derived_from(3.0, "a + b", {"x.a": design(1), "x.b": pending})
    assert out.source is Source.PROVISIONAL and float(out) == 3.0
    assert "x.b" in out.note and "x.a" not in out.note       # どの入力が仮かを書く


def test_derived_from_is_derived_when_every_input_is_settled():
    out = derived_from(3.0, "a + b", {"x.a": design(1), "x.b": Choice("M5", Source.SPEC)})
    assert out.source is Source.DERIVED


def test_the_default_derived_values_follow_the_formulas():
    d = derive(SPEC)
    assert isinstance(d, Derived)
    pitch = 38.1 * 1.4
    assert float(d.tube_pitch) == pytest.approx(pitch)                         # 53.34
    assert float(d.pcd) == pytest.approx(pitch / math.sin(math.radians(30)))   # 106.68（≈ 106）
    assert float(d.shell_od) == pytest.approx(152.4 - 0.4)                    # 152
    assert float(d.shell_id) == pytest.approx(152 - 2 * 1.2)
    assert float(d.bolt_circle) == pytest.approx(152 + 2 * 10)                 # 172（≈ 172）
    assert float(d.tube_cut_length) == 480


def test_the_plate_and_clamp_outer_diameters_follow_the_formula_not_the_rounded_numbers():
    """§5.2 の式どおりに計算した値。同じ節の「≈ 192」「≈ 152」は式と合わない（縁 8 だと 188 と 161）。

    式を正とし、概算値の食い違いは計画書の「置いた仮定」に書いてある。
    """
    d = derive(SPEC)
    tube_ring = 106.68 + 38.1 + 2 * 8
    assert float(d.plate_od) == pytest.approx(max(tube_ring, 172 + 2 * 8, 152))             # 188
    assert float(d.plate_od) == pytest.approx(188)
    assert float(d.clamp_od) == pytest.approx(max(tube_ring, 152))                         # 160.78（ボルト円の項なし）
    assert float(d.plate_od) == pytest.approx(192, abs=5)                                  # 仕様の概算の近く
    assert float(d.clamp_hole_d) == pytest.approx(106.68 - 38.1 - 16)                       # 52.58


def test_the_plate_is_bigger_than_the_shell_by_a_step_and_the_clamp_is_not_as_big_as_the_plate():
    d = derive(SPEC)
    assert float(d.plate_od) > float(d.shell_od) + 30           # D-17: 胴より大径で段が付く
    assert float(d.clamp_od) < float(d.plate_od)                # クランプはボルト円の項を含めない


def test_head_derived_values():
    d = derive(SPEC)
    assert float(d.head_od) == pytest.approx(152.4 + 2 * 1.5)
    assert float(d.areal_density) == pytest.approx(7.5 * 0.0254 * 1.39e-3)       # g/mm²（膜厚 × 1.39 g/cm³）


def test_every_default_derived_value_is_provisional_and_names_a_provisional_input():
    d = derive(SPEC)
    for field in dataclasses.fields(d):
        leaf = getattr(d, field.name)
        assert leaf.source is Source.PROVISIONAL, field.name
        assert "仮の入力" in leaf.note, field.name
    assert "tube.gap_ratio" in d.pcd.note and "head.fit_id" in d.shell_od.note
    assert "head.fit_id" not in d.pcd.note                    # 無関係な仮は拾わない


def test_a_derived_value_becomes_derived_once_every_input_that_feeds_it_is_settled():
    tube = dataclasses.replace(SPEC.tube, gap_ratio=design(0.4))
    spec = _settled(SPEC, tube=tube)
    d = derive(spec)
    assert d.tube_pitch.source is Source.DERIVED and d.pcd.source is Source.DERIVED
    assert d.shell_od.source is Source.PROVISIONAL            # ヘッド側はまだ仮
    assert d.plate_od.source is Source.PROVISIONAL            # 胴外径（仮）が入力に効く
    head = dataclasses.replace(SPEC.head, fit_id=design(152.4))
    assert derive(_settled(spec, head=head)).plate_od.source is Source.DERIVED


def test_areal_density_stays_provisional_even_when_the_film_thickness_is_settled():
    head = dataclasses.replace(SPEC.head, film_mil=design(7))
    d = derive(_settled(SPEC, head=head)).areal_density
    assert d.source is Source.PROVISIONAL and "FILM_DENSITY" in d.note   # 密度（PET の一般値）が仮のまま効く


def test_override_moves_the_derived_values_with_it():
    wide = derive(override(SPEC, tube__gap_ratio=0.8))
    assert float(wide.tube_pitch) == pytest.approx(38.1 * 1.8)
    assert float(wide.pcd) == pytest.approx(38.1 * 1.8 * 2)
    assert float(wide.plate_od) == pytest.approx(38.1 * 1.8 * 2 + 38.1 + 16)           # 管の項がボルト円の項（188）を超える側
    assert float(derive(override(SPEC, tube__gap_ratio=0.5)).plate_od) == pytest.approx(188)   # ボルト円の項が効く側
    bigger = derive(override(SPEC, head__fit_id=165.1))
    assert float(bigger.shell_od) == pytest.approx(164.7) and float(bigger.bolt_circle) == pytest.approx(164.7 + 20)
    assert float(derive(override(SPEC, tube__count=8)).pcd) == pytest.approx(53.34 / math.sin(math.radians(22.5)))


def test_name_is_model_inch_and_lug_count():
    assert name(SPEC) == "gatling-6-6"
    assert name(override(SPEC, lug__count=3)) == "gatling-6-3"
    assert name(override(SPEC, head__fit_id=203.2)) == "gatling-8-6"
    assert name(override(SPEC, tube__count=0)) == "gatling-6-6"     # derive() を通さない（個数で割らない）
