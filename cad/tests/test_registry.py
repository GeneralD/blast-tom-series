import sys
from pathlib import Path

import pytest
from drumcad.contract import REQUIRED, Model
from drumcad.registry import discover

TESTS = Path(__file__).parent


def test_discover_finds_the_demo_package_and_reads_its_contract():
    models = discover(TESTS)
    assert "demo" in models
    m = models["demo"]
    assert isinstance(m, Model)
    assert m.name() == "demo-6-6"
    assert set(m.assembly()) == {"shell", "plate", "stud"}
    assert [p.name for p in m.parts()] == ["shell", "plate", "stud"]


def test_discover_ignores_directories_that_are_not_model_packages():
    assert set(discover(TESTS)) == {"demo"}     # __pycache__ や conftest.py は拾わない


def test_a_package_missing_a_required_name_is_reported_not_silently_skipped(tmp_path):
    (tmp_path / "broken").mkdir()
    (tmp_path / "broken" / "__init__.py").write_text("SPEC = object()\n", encoding="utf-8")
    with pytest.raises(TypeError, match="broken.*name"):
        discover(tmp_path)


def test_required_names_match_the_spec_contract():
    assert REQUIRED == ("SPEC", "name", "override", "assembly", "parts", "bom", "issues")


def test_optional_hooks_read_as_none_when_absent():
    m = discover(TESTS)["demo"]
    assert m.drawing is None and m.acoustic_model is None


def test_optional_hooks_are_bound_to_the_spec_like_the_required_ones():
    import dataclasses
    from types import SimpleNamespace

    demo = discover(TESTS)["demo"]
    module = SimpleNamespace(drawing=lambda spec: ("drawing", spec),
                             acoustic_model=lambda spec: ("acoustic", spec))
    m = dataclasses.replace(demo, _module=module)
    assert m.drawing() == ("drawing", demo.spec)           # 引数なしで呼べる
    assert m.acoustic_model() == ("acoustic", demo.spec)


def _write_model(root: Path, label: str) -> None:
    """契約の最小実装。`label` で root ごとの違いを区別する。"""
    pkg = root / "twin"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text(
        "SPEC = object()\n"
        f"def name(spec): return {label!r}\n"
        "def override(*a, **k): return None\n"
        "def assembly(): return {}\n"
        "def parts(): return []\n"
        "def bom(): return []\n"
        "def issues(): return []\n",
        encoding="utf-8",
    )


def test_discover_leaves_sys_path_untouched(tmp_path):
    _write_model(tmp_path, "a")
    before = list(sys.path)
    discover(tmp_path)
    assert sys.path == before


def test_same_named_models_in_two_roots_are_not_mixed_up(tmp_path):
    _write_model(tmp_path / "r1", "first")
    _write_model(tmp_path / "r2", "second")
    assert discover(tmp_path / "r1")["twin"].name() == "first"
    assert discover(tmp_path / "r2")["twin"].name() == "second"


def test_rediscovering_a_rewritten_model_reads_the_new_source(tmp_path):
    _write_model(tmp_path, "old")
    assert discover(tmp_path)["twin"].name() == "old"
    (tmp_path / "twin" / "__init__.py").write_text(
        (tmp_path / "twin" / "__init__.py").read_text(encoding="utf-8").replace("old", "new"),
        encoding="utf-8",
    )
    assert discover(tmp_path)["twin"].name() == "new"


def test_a_model_can_use_relative_imports_inside_its_package(tmp_path):
    _write_model(tmp_path, "unused")
    (tmp_path / "twin" / "params.py").write_text("LABEL = 'from-params'\n", encoding="utf-8")
    init = tmp_path / "twin" / "__init__.py"
    init.write_text(
        init.read_text(encoding="utf-8").replace(
            "def name(spec): return 'unused'",
            "from .params import LABEL\ndef name(spec): return LABEL",
        ),
        encoding="utf-8",
    )
    assert discover(tmp_path)["twin"].name() == "from-params"


def test_rediscovering_picks_up_a_submodule_rewritten_with_the_same_length_in_the_same_second(tmp_path):
    import os

    _write_model(tmp_path, "unused")
    params = tmp_path / "twin" / "params.py"
    init = tmp_path / "twin" / "__init__.py"
    init.write_text(
        init.read_text(encoding="utf-8").replace(
            "def name(spec): return 'unused'",
            "from .params import LABEL\ndef name(spec): return LABEL",
        ),
        encoding="utf-8",
    )
    params.write_text("LABEL = 'aaaa'\n", encoding="utf-8")
    assert discover(tmp_path)["twin"].name() == "aaaa"
    stamp = params.stat().st_mtime_ns
    params.write_text("LABEL = 'bbbb'\n", encoding="utf-8")       # 同じ長さ
    os.utime(params, ns=(stamp, stamp))                           # 同じ更新時刻 = .pyc の検証をすり抜ける
    assert discover(tmp_path)["twin"].name() == "bbbb"


@pytest.mark.parametrize("statement", ["from .shapes import leaf", "from . import sibling"])
def test_a_model_can_import_a_module_with_from_import_inside_its_package(tmp_path, statement):
    """`from .sub import mod` と `from . import mod` は、親の名前空間まで import しにいく。"""
    _write_model(tmp_path, "unused")
    pkg = tmp_path / "twin"
    (pkg / "shapes").mkdir()
    (pkg / "shapes" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "shapes" / "leaf.py").write_text("LABEL = 'from-leaf'\n", encoding="utf-8")
    (pkg / "sibling.py").write_text("LABEL = 'from-sibling'\n", encoding="utf-8")
    module = statement.split()[-1]
    init = pkg / "__init__.py"
    init.write_text(
        init.read_text(encoding="utf-8").replace(
            "def name(spec): return 'unused'",
            f"{statement}\ndef name(spec): return {module}.LABEL",
        ),
        encoding="utf-8",
    )
    assert discover(tmp_path)["twin"].name() == f"from-{module}"
