"""出力の置き換えかたの回帰テスト。

形状ではなく**成果物ディレクトリの状態**を見る。守りたいのは
「一式そろっているように見えるが中身が混ざっている」を作らないこと。
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import cadquery as cq
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
    for f in ("shell.step", "shell.stl", "shell.svg", "plate.step", "stud.step",
              "assembly.step", "assembly.stl", "assembly.svg", "viewer.html", "bom.md"):
        assert (out / f).exists(), f


def test_a_failed_swap_puts_the_previous_output_back(tmp_path, monkeypatch, demo):
    out = tmp_path / "demo-6-6-PROVISIONAL"
    out.mkdir()
    (out / "shell.step").write_text("前回の成果物", encoding="utf-8")
    real = Path.rename

    def flaky(self, target):
        if self.name.endswith(".staging"):
            raise OSError("差し替え中の失敗")
        return real(self, target)

    monkeypatch.setattr(Path, "rename", flaky)
    with pytest.raises(OSError):
        build._export_all(demo, out)
    assert (out / "shell.step").read_text(encoding="utf-8") == "前回の成果物"
    assert not (tmp_path / "demo-6-6-PROVISIONAL.stale").exists()
    assert not (tmp_path / "demo-6-6-PROVISIONAL.staging").exists()


def test_the_previous_output_is_set_aside_while_swapping_and_dropped_after(tmp_path, monkeypatch, demo):
    out = tmp_path / "demo-6-6-PROVISIONAL"
    out.mkdir()
    (out / "shell.step").write_text("前回の成果物", encoding="utf-8")
    seen = []
    real = Path.rename

    def spy(self, target):
        if self.name.endswith(".staging"):
            seen.append((tmp_path / "demo-6-6-PROVISIONAL.stale" / "shell.step").read_text(encoding="utf-8"))
            assert not out.exists()
        return real(self, target)

    monkeypatch.setattr(Path, "rename", spy)
    build._export_all(demo, out)
    assert seen == ["前回の成果物"]          # staging を置く瞬間、古い方は .stale に残っている
    assert not (tmp_path / "demo-6-6-PROVISIONAL.stale").exists()
    assert (out / "assembly.step").exists()


def _solids(step: Path) -> int:
    return cq.importers.importStep(str(step)).solids().size()


def test_assembly_outputs_every_placed_solid_not_only_the_first_of_each_part(tmp_path, demo):
    out = tmp_path / "demo-6-6-PROVISIONAL"
    build._export_all(demo, out)
    placed = {n: p.solids().size() for n, p in demo.assembly().items()}
    assert placed["stud"] == 3
    assert _solids(out / "assembly.step") == sum(placed.values())
    assert _solids(out / "stud.step") == 3


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


class _Module:
    """機種モジュールの `parts()` だけを差し替える（員数を solid 数とずらすため）。"""

    def __init__(self, module, parts):
        self._module, self._parts = module, parts

    def parts(self, spec):
        return self._parts

    def __getattr__(self, name):
        return getattr(self._module, name)


def test_build_with_a_part_count_that_differs_from_its_solids_is_fatal_and_exports_nothing(tmp_path, demo):
    wrong = [dataclasses.replace(p, count=2) if p.name == "stud" else p for p in demo.parts()]
    broken = dataclasses.replace(demo, _module=_Module(demo._module, wrong))
    assert build.build(broken) == 1
    assert list(tmp_path.iterdir()) == []


def test_main_rejects_an_unknown_model_before_building_anything(monkeypatch, capsys):
    monkeypatch.setattr(build, "ROOT", TESTS)
    assert build.main(["build.py", "nope"]) == 2
    assert "nope" in capsys.readouterr().err


def test_main_builds_every_model_by_default(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "OUT", tmp_path)
    monkeypatch.setattr(build, "ROOT", TESTS)
    assert build.main(["build.py"]) == 0
    assert (tmp_path / "demo-6-6-PROVISIONAL" / "viewer.html").exists()


def test_an_exception_during_the_checks_hides_the_previous_output_and_names_the_model(tmp_path, capsys, demo):
    build.build(demo)

    class Boom(_Module):
        def issues(self, spec):
            raise RuntimeError("検査中の失敗")

    broken = dataclasses.replace(demo, _module=Boom(demo._module, demo.parts()))
    with pytest.raises(RuntimeError, match="検査中の失敗"):
        build.build(broken)
    assert not (tmp_path / "demo-6-6-PROVISIONAL").exists()
    assert (tmp_path / "demo-6-6-PROVISIONAL.stale" / "assembly.step").exists()
    assert "demo" in capsys.readouterr().out


def test_an_exception_during_the_export_hides_the_previous_output(tmp_path, monkeypatch, demo):
    build.build(demo)

    def boom(*args, **kwargs):
        raise RuntimeError("エクスポート中の失敗")

    monkeypatch.setattr(build, "_export_part", boom)
    with pytest.raises(RuntimeError, match="エクスポート中の失敗"):
        build.build(demo)
    assert not (tmp_path / "demo-6-6-PROVISIONAL").exists()
    assert (tmp_path / "demo-6-6-PROVISIONAL.stale" / "assembly.step").exists()


def test_main_goes_on_to_the_next_model_after_one_raises_and_exits_nonzero(monkeypatch, capsys):
    monkeypatch.setattr(build, "discover", lambda root: {"a": object(), "b": object()})
    seen = []

    def fake_build(model):
        seen.append(model)
        if len(seen) == 1:
            raise RuntimeError("a の失敗")
        return 0

    monkeypatch.setattr(build, "build", fake_build)
    assert build.main(["build.py"]) == 1
    assert len(seen) == 2
    captured = capsys.readouterr()
    assert "RuntimeError" in captured.err and "a の失敗" in captured.err     # トレースバックは出す
    assert "a" in captured.err.splitlines()[-1]                              # 最後に失敗した機種を並べる
