"""Gatling の寸法（仕様 §5.2）。導出値は test_gatling_derived.py。"""

from __future__ import annotations

import dataclasses

import pytest
from drumcad.dims import Choice, Dim, Source, unsettled, walk
from gatling.params import SPEC, GatlingSpec, override


def _leaves_or_containers(obj, path="spec"):
    """SPEC の全フィールドを辿り、葉でも dataclass でも tuple でもない値（素の数値など）の位置を返す。"""
    if isinstance(obj, (Dim, Choice)):
        return []
    if isinstance(obj, tuple):
        return [bad for i, item in enumerate(obj) for bad in _leaves_or_containers(item, f"{path}[{i}]")]
    if dataclasses.is_dataclass(obj):
        return [bad for f in dataclasses.fields(obj) for bad in _leaves_or_containers(getattr(obj, f.name), f"{path}.{f.name}")]
    return [f"{path} = {obj!r}（{type(obj).__name__}）"]


def test_no_dimension_is_a_bare_number():
    assert _leaves_or_containers(SPEC) == []


def test_the_default_spec_has_unsettled_values_and_each_says_what_it_waits_for():
    pending = dict(unsettled(SPEC))
    assert {"head.model", "head.fit_id", "lug.pitch", "lug.height", "lug.thread", "tube.length", "tube.gap_ratio",
            "mount.type", "hoop.inner.height", "hoop.inner.thickness", "lug.rod_head_dia", "lug.rod_head_height"} <= set(pending)
    assert all(leaf.note for leaf in pending.values())
    assert "実物" in pending["lug.pitch"].note and "PR 4" in pending["tube.length"].note


def test_the_sources_follow_the_section_5_2_table():
    pending = {path for path, _ in unsettled(SPEC)}
    settled_by_design = {"tube.od", "tube.thickness", "tube.count", "tube.protrusion_ratio", "tube.trim_allowance",
                         "lug.count", "clamp.mid_position", "clamp.tip_thickness", "clamp.mid_thickness",
                         "header.thickness", "flange.thickness", "flange.bolt_phase", "flange.bolt_seat",
                         "plate.margin", "gasket.thickness", "hoop.gap", "hoop.ear.count", "shell.thickness",
                         "shell.plenum_height", "edge.angle", "edge.radius", "edge.height", "tuning_target", "finish",
                         "band.bar.width", "band.bar.thickness", "band.bolt",
                         "cradle.bar.width", "cradle.bar.thickness", "cradle.clearance", "cradle.handle_length",
                         "cradle.pad.width", "cradle.pad.depth", "cradle.pad.thickness",
                         "flange.bolt_count", "flange.bolt", "clamp.bolt",
                         "hoop.outer.od", "hoop.outer.thickness",
                         "head.f01_range[0]", "head.f01_range[1]"}
    leaves = dict(walk(SPEC))
    assert settled_by_design <= set(leaves)                  # 綴りの誤りで検査が空振りしない
    assert not (settled_by_design & pending)
    assert all(leaves[p].source is Source.DESIGN for p in settled_by_design)


def test_the_defaults_are_the_section_5_2_values():
    s = SPEC
    assert (float(s.tube.od), float(s.tube.thickness), float(s.tube.length), float(s.tube.gap_ratio)) == (38.1, 1.2, 450, 0.4)
    assert (float(s.tube.protrusion_ratio), float(s.tube.trim_allowance), float(s.tube.count)) == (1.0, 30, 6)
    assert (float(s.clamp.mid_position), float(s.clamp.tip_thickness), float(s.clamp.mid_thickness)) == (0.55, 6, 3)
    assert (float(s.header.thickness), float(s.flange.thickness), float(s.gasket.thickness)) == (6, 6, 1)
    assert (float(s.flange.bolt_count), float(s.flange.bolt_phase), float(s.flange.bolt_seat)) == (6, 30, 10)
    assert (float(s.plate.margin), float(s.hoop.gap), float(s.hoop.ear.count), float(s.lug.count)) == (8, 10, 6, 6)
    assert (float(s.hoop.inner.height), float(s.hoop.inner.thickness)) == (8, 4)                      # D-20: リムを浅く（12 → 8）
    assert (float(s.hoop.outer.od), float(s.hoop.outer.thickness)) == (25.4, 1.5)                    # 手すり用 #400 研磨管
    assert (float(s.lug.rod_head_dia), float(s.lug.rod_head_height), float(s.lug.rod_length)) == (9, 5, 50)
    assert (float(s.shell.thickness), float(s.shell.plenum_height)) == (1.2, 100)
    assert (float(s.edge.angle), float(s.edge.radius), float(s.edge.height)) == (45, 1.5, 10)
    assert [float(x) for x in s.head.f01_range] == [250, 400] and float(s.head.loss_factor) == 0.02
    assert (s.clamp.bolt.value, s.flange.bolt.value, s.band.bolt.value) == ("M5", "M6", "M6")
    assert (s.tuning_target.value, s.finish.value) == ("unison", "#400 サテン")


def test_override_swaps_a_leaf_and_keeps_its_source_and_note():
    longer = override(SPEC, **{"tube.length": 500})
    assert float(longer.tube.length) == 500 and longer.tube.length.source is Source.PROVISIONAL
    assert longer.tube.length.note == SPEC.tube.length.note
    assert float(SPEC.tube.length) == 450                              # 元は変わらない
    assert float(override(SPEC, tube__gap_ratio=0.3).tube.gap_ratio) == 0.3     # `__` は `.` の代わり
    assert float(override(SPEC, **{"head.f01_range[1]": 380}).head.f01_range[1]) == 380


def test_override_rejects_a_path_that_is_not_in_the_spec():
    with pytest.raises(AttributeError):
        override(SPEC, tube__no_such_thing=1)


def test_a_spec_is_a_frozen_dataclass():
    assert isinstance(SPEC, GatlingSpec) and dataclasses.is_dataclass(SPEC)
    with pytest.raises(dataclasses.FrozenInstanceError):
        SPEC.tube = None  # type: ignore[misc]
