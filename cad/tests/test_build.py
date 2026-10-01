"""出力の置き換えかたの回帰テスト。

形状ではなく**成果物ディレクトリの状態**を見る。守りたいのは
「一式そろっているように見えるが中身が混ざっている」を作らないこと。
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

import build
from drumcad.dims import Dim, Source
from drumcad.registry import discover

TESTS = Path(__file__).parent


@pytest.fixture
def demo(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "OUT", tmp_path)
    return discover(TESTS)["demo"]


def _settled(model):
    """demo の唯一の仮値（底板の厚み）を設計判断に置き換えた Model。"""
    plate = dataclasses.replace(model.spec.plate, thickness=Dim(6, Source.DESIGN))
    return dataclasses.replace(model, spec=dataclasses.replace(model.spec, plate=plate))


def test_failed_export_leaves_the_previous_output_untouched(tmp_path, monkeypatch, demo):
    out = tmp_path / "demo-6-6-PROVISIONAL"
    out.mkdir()
    (out / "shell.step").write_text("前回の成果物", encoding="utf-8")

    def boom(*args, **kwargs):
        raise RuntimeError("エクスポート中の失敗")

    monkeypatch.setattr(build, "_export_part", boom)
    with pytest.raises(RuntimeError):
        build._export_all(demo, out)
    assert (out / "shell.step").read_text(encoding="utf-8") == "前回の成果物"
    assert not (tmp_path / "demo-6-6-PROVISIONAL.staging").exists()


def test_successful_export_replaces_the_directory_wholesale(tmp_path, demo):
    out = tmp_path / "demo-6-6-PROVISIONAL"
    out.mkdir()
    (out / "leftover-x8.dxf").write_text("取り残し", encoding="utf-8")
    build._export_all(demo, out)
    assert not (out / "leftover-x8.dxf").exists()
    for f in ("shell.step", "shell.stl", "shell.svg", "plate.step",
              "assembly.step", "assembly.stl", "assembly.svg", "viewer.html", "bom.md"):
        assert (out / f).exists(), f


def test_build_uses_the_provisional_suffix_while_any_leaf_is_unsettled(tmp_path, demo):
    assert build.build(demo) == 0
    assert (tmp_path / "demo-6-6-PROVISIONAL" / "assembly.step").exists()
    assert not (tmp_path / "demo-6-6").exists()


def test_build_drops_the_suffix_once_everything_is_settled_and_quarantines_the_old_one(tmp_path, demo):
    build.build(demo)
    assert build.build(_settled(demo)) == 0
    assert (tmp_path / "demo-6-6" / "assembly.step").exists()
    assert (tmp_path / "demo-6-6-PROVISIONAL.stale").exists()
    assert not (tmp_path / "demo-6-6-PROVISIONAL").exists()


def test_build_with_a_fatal_issue_exports_nothing_and_hides_the_previous_output(tmp_path, demo):
    build.build(demo)
    broken = demo.override(plate__od=100)
    assert build.build(broken) == 1
    assert not (tmp_path / "demo-6-6-PROVISIONAL").exists()
    assert (tmp_path / "demo-6-6-PROVISIONAL.stale" / "assembly.step").exists()
    assert not (tmp_path / "demo-6-6").exists()


def test_main_rejects_an_unknown_model_before_building_anything(monkeypatch, capsys):
    monkeypatch.setattr(build, "ROOT", TESTS)
    assert build.main(["build.py", "nope"]) == 2
    assert "nope" in capsys.readouterr().err


def test_main_builds_every_model_by_default(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "OUT", tmp_path)
    monkeypatch.setattr(build, "ROOT", TESTS)
    assert build.main(["build.py"]) == 0
    assert (tmp_path / "demo-6-6-PROVISIONAL" / "viewer.html").exists()
