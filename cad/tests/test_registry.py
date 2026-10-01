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
