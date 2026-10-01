# 共通基盤 `drumcad`（PR 2）実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 機種パッケージを差し込めば STEP・STL・SVG・`viewer.html`・`bom.md` が `-PROVISIONAL` 規約つきで出る共通基盤 `cad/drumcad/` と `cad/build.py` を、テストと一緒に作る。

**Architecture:** 出典つき寸法 `Dim` / `Choice`（`dims.py`）を葉に持つ frozen dataclass を機種が `SPEC` として公開し、`registry.py` が `cad/<機種>/` を発見して契約（仕様 §4.4）を検査する。`build.py` は検査 → 未決判定 → stage-and-swap の順で出力する。図面（PR 5）と音響（PR 4）はこの PR では出力しない。契約のうち `drawing` / `acoustic_model` は任意属性として読むだけにし、PR 4 / 5 で必須化する。

**Tech Stack:** Python 3.12（uv）、CadQuery 2.5、numpy、pytest。three.js（cdnjs）を viewer が読む。

**仕様:** `docs/superpowers/specs/2026-10-01-blast-tom-series-design.md` §3, §4.1, §4.2（materials / stock / bom）, §4.4, §5.6（基盤のテスト）, §1.2(4)。

**ブランチ:** `feature/drumcad-base`（main から）。全タスク完了後に PR を 1 本。

---

## ファイル構成

| パス | 責務 |
|---|---|
| `cad/pyproject.toml` | uv プロジェクト。Python 3.12 固定、依存、pytest 設定 |
| `cad/README.md` | 使い方（build / viewer / テスト） |
| `cad/drumcad/__init__.py` | 空。パッケージの印 |
| `cad/drumcad/dims.py` | `Source` `Dim` `Choice`、`measured/spec/design/derived/provisional`、`walk` `unsettled` `as_provisional` `override` |
| `cad/drumcad/checks.py` | `Issue(fatal, what)`、`fatal_count` |
| `cad/drumcad/materials.py` | `Material`、`SUS304` `A6063`、`mass_g(part, material)` |
| `cad/drumcad/stock.py` | 規格パイプ表 `TUBES`、`nearest(od, thickness)` |
| `cad/drumcad/contract.py` | 機種契約の型 `PartInfo` `BomRow` `Model`、`REQUIRED` |
| `cad/drumcad/registry.py` | `discover(root)`: 機種パッケージの発見と契約検査 |
| `cad/drumcad/bom.py` | `full_bom(model)`、`bom_markdown(title, rows)` |
| `cad/drumcad/viewer.py` | `viewer_html(title, note, parts, infos)`、分解表示つき |
| `cad/build.py` | CLI。検査 → 未決判定 → stage-and-swap → STEP/STL/SVG/viewer/bom |
| `cad/tests/conftest.py` | `demo` 機種パッケージを `sys.path` に載せる |
| `cad/tests/demo/__init__.py` | テスト用の最小機種（筒 1 本＋円盤 1 枚） |
| `cad/tests/test_dims.py` | Dim / Choice / walk / unsettled / as_provisional / override |
| `cad/tests/test_checks.py` | Issue の表示 |
| `cad/tests/test_materials.py` | 質量 |
| `cad/tests/test_stock.py` | 丸めと警告 |
| `cad/tests/test_registry.py` | 発見と契約検査 |
| `cad/tests/test_bom.py` | bom.md |
| `cad/tests/test_viewer.py` | 埋め込みメッシュ・分解ベクトル・自己完結 |
| `cad/tests/test_build.py` | stage-and-swap・接尾辞・fatal 時の退避・CLI |
| `cad/tests/test_no_private_terms.py` | 仕様 §1.2(4) の固有語 grep |

すべてのコマンドはリポのルート（`blast-tom-series/`）で実行する。テストは `uv run --project cad pytest cad/tests -q`。

---

### Task 1: プロジェクトの骨格

**Files:**

- Create: `cad/pyproject.toml`
- Create: `cad/README.md`
- Create: `cad/drumcad/__init__.py`
- Create: `cad/tests/conftest.py`

- [ ] **Step 1: ブランチを切る**

```bash
git switch -c feature/drumcad-base
```

- [ ] **Step 2: `cad/pyproject.toml` を書く**

```toml
[project]
name = "blast-tom-cad"
version = "0.1.0"
description = "Blast Tom Series のパラメトリック CAD（STEP / 図面 / viewer / 音響）"
readme = "README.md"

# CadQuery が依存する OCP のホイールは 3.12 までしか無い。3.12 で固定する。
requires-python = ">=3.12,<3.13"

dependencies = [
    "cadquery>=2.5",
    "ezdxf>=1.4",
    "matplotlib>=3.9",
    "numpy>=2.0",
]

[dependency-groups]
dev = [
    "pytest>=8",
]

[tool.uv]
# ロックファイルを必ず使う。寸法が同じなら誰が回しても同一の STEP が出ること。
package = false

[tool.pytest.ini_options]
# パッケージとしてインストールしない（package = false）ので、
# テストから drumcad と build を import できるよう cad/ を通す。
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 3: 空のパッケージと conftest を置く**

`cad/drumcad/__init__.py` は空ファイル。`cad/tests/conftest.py`:

```python
"""テスト用の機種パッケージ `demo` を、機種の置き場（cad/）と同じ扱いで import できるようにする。"""

from __future__ import annotations

import sys
from pathlib import Path

TESTS = Path(__file__).parent
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))
```

- [ ] **Step 4: `cad/README.md` を書く**

```markdown
# CAD

機種ごとの寸法（`params.py`）から、入稿用の STEP と 2D 図面、確認用の `viewer.html`、部品表を毎回同じように再生成する。

## 使い方

    uv run --project cad python cad/build.py            # 全機種
    uv run --project cad python cad/build.py gatling    # 1 機種
    uv run --project cad pytest cad/tests -q            # テスト

出力は `cad/out/<機種>-<径inch>-<ラグ数>/`。まだ決めきっていない値（`provisional`）が 1 つでも残っていると `-PROVISIONAL` が付く。

`viewer.html` はブラウザで開く（three.js を cdnjs から読む以外は自己完結）:

    python3 -m http.server -d cad/out 8000
    # → http://localhost:8000/<出力ディレクトリ>/viewer.html

## 機種を足すには

`cad/<機種>/__init__.py` が仕様書 §4.4 の契約（`SPEC`, `name`, `override`, `assembly`, `parts`, `bom`, `issues`）を公開していれば `build.py` が見つける。`cad/tests/demo/` が最小の例。
```

- [ ] **Step 5: 依存を解決してロックを作る**

Run: `uv sync --project cad`
Expected: `cad/.venv/` と `cad/uv.lock` ができる。エラー無し。

- [ ] **Step 6: pytest が空で通ることを確認**

Run: `uv run --project cad pytest cad/tests -q`
Expected: `no tests ran` で終了コード 5（テストが無いだけ）。

- [ ] **Step 7: Commit**

```bash
git add cad/pyproject.toml cad/uv.lock cad/README.md cad/drumcad/__init__.py cad/tests/conftest.py
git commit -m "build: cad/ の uv プロジェクトと drumcad パッケージの骨格"
```

---

### Task 2: `dims.py` — 出典つき寸法 `Dim`

**Files:**

- Create: `cad/drumcad/dims.py`
- Test: `cad/tests/test_dims.py`

- [ ] **Step 1: 失敗するテストを書く**

`cad/tests/test_dims.py`:

```python
"""出典つき寸法の回帰テスト。守りたいのは「仮の値が出典検査を素通りしない」こと。"""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from drumcad.dims import Dim, Source, design, derived, measured, provisional, spec


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
```

- [ ] **Step 2: 失敗を確認**

Run: `uv run --project cad pytest cad/tests/test_dims.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'drumcad.dims'`

- [ ] **Step 3: `cad/drumcad/dims.py` を書く**

```python
"""寸法値と、その値がどこから来たのかを一緒に運ぶ型。

設計中の寸法は出どころの強さがまちまちで、決めた値・カタログ値・実測値と、
まだ決めきっていない仮置きが同じ数式に混ざる。数値だけを持ち回ると
「どれが仮だったか」が数手で分からなくなり、仮値のまま入稿しかねない。

そこで値そのものに出典を貼る。`Dim` は float の派生なので、幾何計算の
コードは普通の数値と同じように書ける。数値でない選択肢（型番・ねじ規格・
仕上げ）は `Choice` で同じ出典を持つ。
"""

from __future__ import annotations

from enum import Enum


class Source(Enum):
    """値の出どころ。"""

    SPEC = "仕様書"          # メーカーの仕様書・カタログ値（ヘッド、ラグ、ロッド、ボルト）
    MEASURED = "実測"         # 現物を測った値（購入した既製品など）
    DERIVED = "導出"          # 上記や設計判断から計算で出る値
    DESIGN = "設計判断"        # decisions.md で決めた値
    PROVISIONAL = "仮"        # ⚠️ まだ決めきっていない値。入稿前に必ず潰す

    @property
    def is_settled(self) -> bool:
        return self is not Source.PROVISIONAL


class Dim(float):
    """出典つきの寸法値（mm、または個数・角度・比）。"""

    source: Source
    note: str

    def __new__(cls, value: float, source: Source, note: str = "") -> "Dim":
        self = super().__new__(cls, value)
        self.source = source
        self.note = note
        return self

    def __repr__(self) -> str:
        tail = f" — {self.note}" if self.note else ""
        return f"{float(self):g} [{self.source.value}{tail}]"


def measured(value: float, note: str = "") -> Dim:
    return Dim(value, Source.MEASURED, note)


def spec(value: float, note: str = "") -> Dim:
    return Dim(value, Source.SPEC, note)


def design(value: float, note: str = "") -> Dim:
    return Dim(value, Source.DESIGN, note)


def derived(value: float, note: str = "") -> Dim:
    return Dim(value, Source.DERIVED, note)


def provisional(value: float, note: str = "") -> Dim:
    """まだ決めきっていない値。1 つでも残っている限り入稿データとは呼べない。"""
    return Dim(value, Source.PROVISIONAL, note)
```

- [ ] **Step 4: 通ることを確認**

Run: `uv run --project cad pytest cad/tests/test_dims.py -q`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add cad/drumcad/dims.py cad/tests/test_dims.py
git commit -m "feat(drumcad): 出典つき寸法 Dim と Source"
```

---

### Task 3: `dims.py` — `Choice`、`walk`、`unsettled`、`as_provisional`

**Files:**

- Modify: `cad/drumcad/dims.py`
- Test: `cad/tests/test_dims.py`

- [ ] **Step 1: 失敗するテストを追記**

`cad/tests/test_dims.py` の末尾に:

```python
from drumcad.dims import Choice, as_provisional, unsettled, walk  # noqa: E402


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
```

- [ ] **Step 2: 失敗を確認**

Run: `uv run --project cad pytest cad/tests/test_dims.py -q`
Expected: FAIL — `ImportError: cannot import name 'Choice'`

- [ ] **Step 3: `cad/drumcad/dims.py` に追記**

`from enum import Enum` の下に import を足し、ファイル末尾に追加する:

```python
import dataclasses
from typing import Any, Iterator


class Choice:
    """出典つきの選択肢（型番・ねじ規格・仕上げなど、数値でない値）。

    文字列のままだと出典を持てず、`unsettled()` にも見えないので、
    未決の型番が `-PROVISIONAL` の付かない出力に紛れる。
    """

    __slots__ = ("value", "source", "note")

    def __init__(self, value: str, source: Source, note: str = "") -> None:
        self.value = value
        self.source = source
        self.note = note

    def __repr__(self) -> str:
        tail = f" — {self.note}" if self.note else ""
        return f"{self.value!r} [{self.source.value}{tail}]"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Choice) and (self.value, self.source, self.note) == \
            (other.value, other.source, other.note)

    def __hash__(self) -> int:
        return hash((self.value, self.source, self.note))


Leaf = Dim | Choice


def walk(obj: Any, prefix: str = "") -> Iterator[tuple[str, Leaf]]:
    """dataclass を再帰的に辿って、含まれる `Dim` と `Choice` を全部拾う。

    **タプル／リストの中まで降りる。** 降りないと、断面の点列のような
    「配列に入った寸法」が出典検査を素通りする。

    dataclass が `dormant_fields()` を持っていれば、そこに挙がったフィールドは
    辿らない。使われないフィールドの仮値のせいで出力が `-PROVISIONAL` のままに
    なると、それを消すために嘘の出典を付ける動機が生まれる。
    """
    if isinstance(obj, (Dim, Choice)):
        yield prefix, obj
        return
    if isinstance(obj, (tuple, list)):
        for i, item in enumerate(obj):
            yield from walk(item, f"{prefix}[{i}]")
        return
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        dormant = obj.dormant_fields() if hasattr(obj, "dormant_fields") else frozenset()
        for f in dataclasses.fields(obj):
            if f.name in dormant:
                continue
            name = f"{prefix}.{f.name}" if prefix else f.name
            yield from walk(getattr(obj, f.name), name)


def unsettled(obj: Any) -> list[tuple[str, Leaf]]:
    """まだ決めきっていない値の一覧。"""
    return [(path, d) for path, d in walk(obj) if not d.source.is_settled]


def as_provisional(obj: Any, note: str) -> Any:
    """別の個体の spec から**値だけ**を写し、出典は全部 `provisional` に落とす。

    `replace()` で流用すると `Dim` そのものを共有するので、元が確定した瞬間に
    写した側まで確定に化ける。値は継ぐが出典は継がない。

    `Dim` / `Choice` 以外（名前・密度のような素の値・None）はそのまま返す。
    葉を 1 つも含まない dataclass（`Material` など）は**元のオブジェクトのまま**返す —
    同一性（`is`）で材質を見る箇所があるため。
    """
    if isinstance(obj, Dim):
        tail = f"。元の注記: {obj.note}" if obj.note else ""
        return Dim(float(obj), Source.PROVISIONAL, f"{note}{tail}")
    if isinstance(obj, Choice):
        tail = f"。元の注記: {obj.note}" if obj.note else ""
        return Choice(obj.value, Source.PROVISIONAL, f"{note}{tail}")
    if isinstance(obj, tuple):
        return tuple(as_provisional(item, note) for item in obj)
    if isinstance(obj, list):
        return [as_provisional(item, note) for item in obj]
    if not dataclasses.is_dataclass(obj) or isinstance(obj, type):
        return obj
    copied = {f.name: as_provisional(getattr(obj, f.name), note)
              for f in dataclasses.fields(obj) if f.init}
    if all(value is getattr(obj, name) for name, value in copied.items()):
        return obj
    return dataclasses.replace(obj, **copied)
```

- [ ] **Step 4: 通ることを確認**

Run: `uv run --project cad pytest cad/tests/test_dims.py -q`
Expected: 14 passed

- [ ] **Step 5: Commit**

```bash
git add cad/drumcad/dims.py cad/tests/test_dims.py
git commit -m "feat(drumcad): Choice と walk / unsettled / as_provisional"
```

---

### Task 4: `dims.py` — `override`（sweep 用の属性パス差し替え）

**Files:**

- Modify: `cad/drumcad/dims.py`
- Test: `cad/tests/test_dims.py`

- [ ] **Step 1: 失敗するテストを追記**

```python
from drumcad.dims import override  # noqa: E402


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
```

- [ ] **Step 2: 失敗を確認**

Run: `uv run --project cad pytest cad/tests/test_dims.py -q`
Expected: FAIL — `ImportError: cannot import name 'override'`

- [ ] **Step 3: `cad/drumcad/dims.py` の末尾に追記**

```python
def override(obj: Any, values: dict[str, Any]) -> Any:
    """`"tube.length": 500` のような属性パスで葉を差し替えた新しい spec を返す。

    sweep（仕様 §5.5）が使う。差し替えた葉は**元の出典と注記を継ぐ** — sweep は
    「同じ出典のまま値だけ振る」操作で、値を変えたからといって仮になる
    わけでも確定するわけでもない。
    """
    result = obj
    for path, value in values.items():
        result = _override_one(result, path.split("."), path, value)
    return result


def _override_one(obj: Any, keys: list[str], full: str, value: Any) -> Any:
    head, rest = keys[0], keys[1:]
    if not dataclasses.is_dataclass(obj) or not hasattr(obj, head):
        raise AttributeError(f"{full}: そのパスは spec に無い")
    current = getattr(obj, head)
    if rest:
        new = _override_one(current, rest, full, value)
    elif isinstance(current, Dim):
        new = Dim(float(value), current.source, current.note)
    elif isinstance(current, Choice):
        new = Choice(str(value), current.source, current.note)
    else:
        raise AttributeError(f"{full}: Dim でも Choice でもない")
    return dataclasses.replace(obj, **{head: new})
```

- [ ] **Step 4: 通ることを確認**

Run: `uv run --project cad pytest cad/tests/test_dims.py -q`
Expected: 18 passed

- [ ] **Step 5: Commit**

```bash
git add cad/drumcad/dims.py cad/tests/test_dims.py
git commit -m "feat(drumcad): 属性パスで葉を差し替える override"
```

---

### Task 5: `checks.py` — `Issue`

**Files:**

- Create: `cad/drumcad/checks.py`
- Test: `cad/tests/test_checks.py`

- [ ] **Step 1: 失敗するテストを書く**

`cad/tests/test_checks.py`:

```python
from drumcad.checks import Issue, fatal_count


def test_an_issue_prints_with_a_severity_mark():
    assert str(Issue(True, "管同士が干渉する")) == "❌ 管同士が干渉する"
    assert str(Issue(False, "規格径から 1.2 mm ずれている")) == "⚠️  規格径から 1.2 mm ずれている"


def test_fatal_count_counts_only_fatal_issues():
    assert fatal_count([Issue(True, "a"), Issue(False, "b"), Issue(True, "c")]) == 2
    assert fatal_count([]) == 0
```

- [ ] **Step 2: 失敗を確認**

Run: `uv run --project cad pytest cad/tests/test_checks.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: `cad/drumcad/checks.py` を書く**

```python
"""寸法どうしの噛み合わせの検査結果。

`dims` の出典追跡が「その数字は本物か」を見るのに対し、機種の `issues(spec)` は
「数字どうしが物理的に成立するか」を見る。**fatal が 0 件なら出力可。警告は
表示して続行する**（仕様 §4.1）。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Issue:
    fatal: bool
    what: str

    def __str__(self) -> str:
        return f"{'❌' if self.fatal else '⚠️ '} {self.what}"


def fatal_count(issues: list[Issue]) -> int:
    return sum(1 for i in issues if i.fatal)
```

- [ ] **Step 4: 通ることを確認**

Run: `uv run --project cad pytest cad/tests/test_checks.py -q`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add cad/drumcad/checks.py cad/tests/test_checks.py
git commit -m "feat(drumcad): 検査結果 Issue"
```

---

### Task 6: `materials.py` — 材質と質量

**Files:**

- Create: `cad/drumcad/materials.py`
- Test: `cad/tests/test_materials.py`

- [ ] **Step 1: 失敗するテストを書く**

`cad/tests/test_materials.py`:

```python
import cadquery as cq
import pytest
from drumcad.materials import A6063, SUS304, Material, mass_g


def test_materials_carry_name_and_density():
    assert SUS304.density == pytest.approx(7.93e-3)
    assert A6063.density == pytest.approx(2.70e-3)
    assert "SUS304" in SUS304.name


def test_mass_of_a_known_block():
    block = cq.Workplane("XY").box(10, 20, 30)   # 6000 mm³
    assert mass_g(block, SUS304) == pytest.approx(6000 * 7.93e-3)


def test_mass_sums_every_solid_in_the_workplane():
    two = cq.Workplane("XY").box(10, 10, 10).union(cq.Workplane("XY").box(10, 10, 10).translate((50, 0, 0)))
    assert mass_g(two, Material("test", 1.0)) == pytest.approx(2000)
```

- [ ] **Step 2: 失敗を確認**

Run: `uv run --project cad pytest cad/tests/test_materials.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: `cad/drumcad/materials.py` を書く**

```python
"""材質。密度は g/mm³。"""

from __future__ import annotations

from dataclasses import dataclass

import cadquery as cq


@dataclass(frozen=True)
class Material:
    name: str
    density: float  # g/mm³


SUS304 = Material("ステンレス SUS304", 7.93e-3)
A6063 = Material("アルミ A6063", 2.70e-3)


def mass_g(part: cq.Workplane, material: Material) -> float:
    """部品（Workplane 上の全ソリッド）の質量（g）。"""
    volume = sum(shape.Volume() for shape in part.vals())
    return volume * material.density
```

- [ ] **Step 4: 通ることを確認**

Run: `uv run --project cad pytest cad/tests/test_materials.py -q`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add cad/drumcad/materials.py cad/tests/test_materials.py
git commit -m "feat(drumcad): 材質と質量計算"
```

---

### Task 7: `stock.py` — 規格パイプ表と丸め

**Files:**

- Create: `cad/drumcad/stock.py`
- Test: `cad/tests/test_stock.py`

- [ ] **Step 1: 失敗するテストを書く**

`cad/tests/test_stock.py`:

```python
import pytest
from drumcad.dims import Source, design
from drumcad.stock import TUBES, Tube, nearest


def test_the_table_has_the_handrail_polished_38_1_by_1_2():
    assert Tube(38.1, 1.2, "手すり用 #400 研磨管") in TUBES


def test_nearest_returns_the_closest_standard_tube_as_a_derived_dim():
    tube, issue = nearest(design(38.0), design(1.2))
    assert (tube.od, tube.thickness) == (38.1, 1.2)
    assert tube.od_dim.source is Source.DERIVED
    assert issue is None


def test_nearest_warns_when_the_design_value_is_far_from_any_standard():
    tube, issue = nearest(design(36.0), design(1.2))
    assert (tube.od, tube.thickness) == (38.1, 1.2)
    assert issue is not None and not issue.fatal
    assert "2.1 mm" in issue.what


def test_nearest_prefers_the_requested_thickness_within_the_same_od():
    tube, _ = nearest(design(38.1), design(1.6))
    assert (tube.od, tube.thickness) == (38.1, 1.5)


def test_tolerance_is_configurable():
    _, issue = nearest(design(36.0), design(1.2), tolerance=3.0)
    assert issue is None
```

- [ ] **Step 2: 失敗を確認**

Run: `uv run --project cad pytest cad/tests/test_stock.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: `cad/drumcad/stock.py` を書く**

```python
"""規格パイプ表と、設計値の規格径への丸め。

採用する径・肉厚は `docs/vendors.md` に実在品番で登録してから使う（仕様 §4.2）。
この表は「規格として存在する組み合わせ」の一覧であって、在庫の保証ではない。
"""

from __future__ import annotations

from dataclasses import dataclass

from .checks import Issue
from .dims import Dim, derived


@dataclass(frozen=True)
class Tube:
    od: float          # 外径 mm
    thickness: float   # 肉厚 mm
    family: str        # 規格・用途

    @property
    def od_dim(self) -> Dim:
        return derived(self.od, f"{self.family} φ{self.od:g} × t{self.thickness:g}")

    @property
    def thickness_dim(self) -> Dim:
        return derived(self.thickness, f"{self.family} φ{self.od:g} × t{self.thickness:g}")


_HANDRAIL = "手すり用 #400 研磨管"
_G3446 = "JIS G3446 機械構造用"
_G3459 = "JIS G3459 配管用"

TUBES: tuple[Tube, ...] = tuple(
    [Tube(od, t, _HANDRAIL) for od in (25.4, 31.8, 38.1, 42.7, 50.8) for t in (1.2, 1.5)]
    + [Tube(od, t, _G3446) for od in (19.1, 22.2, 25.4, 31.8, 38.1, 42.7, 50.8) for t in (1.0, 1.2, 1.5, 2.0)]
    + [Tube(od, t, _G3459) for od, t in ((21.7, 2.0), (27.2, 2.0), (34.0, 2.0), (42.7, 2.0), (48.6, 2.0))]
)


def nearest(od: float, thickness: float, tolerance: float = 1.0) -> tuple[Tube, Issue | None]:
    """設計値に最も近い規格管と、ずれが `tolerance` を超えたときの警告。

    外径のずれを優先し、同じ外径の中で肉厚が最も近いものを選ぶ。
    """
    best = min(TUBES, key=lambda t: (abs(t.od - od), abs(t.thickness - thickness)))
    delta = abs(best.od - od)
    issue = None
    if delta > tolerance:
        issue = Issue(False, f"外径 {od:g} は規格径から {delta:.1f} mm ずれている"
                             f"（最寄り {best.family} φ{best.od:g} × t{best.thickness:g}）")
    return best, issue
```

- [ ] **Step 4: 通ることを確認**

Run: `uv run --project cad pytest cad/tests/test_stock.py -q`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add cad/drumcad/stock.py cad/tests/test_stock.py
git commit -m "feat(drumcad): 規格パイプ表と nearest"
```

---

### Task 8: `contract.py` と `registry.py` — 機種パッケージの発見

**Files:**

- Create: `cad/drumcad/contract.py`
- Create: `cad/drumcad/registry.py`
- Create: `cad/tests/demo/__init__.py`
- Test: `cad/tests/test_registry.py`

- [ ] **Step 1: テスト用の最小機種 `demo` を書く**

`cad/tests/demo/__init__.py`:

```python
"""テスト用の最小機種: 筒 1 本と、その下に置く円盤 1 枚。

契約（仕様 §4.4）を満たす最小限の例。実機種はこれと同じ 7 つの名前を公開する。
"""

from __future__ import annotations

from dataclasses import dataclass

import cadquery as cq
from drumcad.checks import Issue
from drumcad.contract import BomRow, PartInfo
from drumcad.dims import Choice, Dim, Source, design, override as _override, provisional
from drumcad.materials import SUS304


@dataclass(frozen=True)
class Shell:
    od: Dim
    thickness: Dim
    height: Dim


@dataclass(frozen=True)
class Plate:
    od: Dim
    thickness: Dim


@dataclass(frozen=True)
class DemoSpec:
    shell: Shell
    plate: Plate
    lugs: Dim
    finish: Choice


SPEC = DemoSpec(
    shell=Shell(od=design(152.4), thickness=design(1.2), height=design(100)),
    plate=Plate(od=design(160), thickness=provisional(6, "3 か 6 か決めていない")),
    lugs=design(6),
    finish=Choice("#400", Source.DESIGN),
)


def name(spec: DemoSpec) -> str:
    return f"demo-{round(spec.shell.od / 25.4)}-{int(spec.lugs)}"


def override(spec: DemoSpec, **values: object) -> DemoSpec:
    return _override(spec, {k.replace("__", "."): v for k, v in values.items()})


def assembly(spec: DemoSpec) -> dict[str, cq.Workplane]:
    r, t, h = float(spec.shell.od) / 2, float(spec.shell.thickness), float(spec.shell.height)
    shell = cq.Workplane("XY").circle(r).circle(r - t).extrude(h)
    plate = (cq.Workplane("XY").circle(float(spec.plate.od) / 2)
             .extrude(float(spec.plate.thickness)).translate((0, 0, -float(spec.plate.thickness))))
    return {"shell": shell, "plate": plate}


def parts(spec: DemoSpec) -> list[PartInfo]:
    return [
        PartInfo("shell", "胴", "#c9ced6", SUS304, "fabricated", 1, "radial", (0, 0, 1)),
        PartInfo("plate", "底板", "#8f99a6", SUS304, "fabricated", 1, "outline", (0, 0, -1)),
    ]


def bom(spec: DemoSpec) -> list[BomRow]:
    return [
        BomRow("ラグ", "purchased", None, "DW タレットラグ", "", int(spec.lugs), "DWSM2200", 100.0),
    ]


def issues(spec: DemoSpec) -> list[Issue]:
    found = []
    if spec.plate.od < spec.shell.od:
        found.append(Issue(True, "底板が胴より小さく、蓋にならない"))
    if spec.shell.height < 50:
        found.append(Issue(False, "胴が低い"))
    return found
```

- [ ] **Step 2: 失敗するテストを書く**

`cad/tests/test_registry.py`:

```python
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
    assert set(m.assembly()) == {"shell", "plate"}
    assert [p.name for p in m.parts()] == ["shell", "plate"]


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
```

- [ ] **Step 3: 失敗を確認**

Run: `uv run --project cad pytest cad/tests/test_registry.py -q`
Expected: FAIL — `ModuleNotFoundError: drumcad.contract`

- [ ] **Step 4: `cad/drumcad/contract.py` を書く**

```python
"""機種パッケージが `build.py` に渡すものの型（仕様 §4.4）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from .materials import Material

Section = Literal["radial", "outline", "plan", "none"]
Made = Literal["fabricated", "purchased"]

# 機種パッケージが必ず公開する名前。無ければ registry が TypeError で止める。
REQUIRED: tuple[str, ...] = ("SPEC", "name", "override", "assembly", "parts", "bom", "issues")
# 後の PR で必須にする名前。今は無ければ None。
OPTIONAL: tuple[str, ...] = ("drawing", "acoustic_model")


@dataclass(frozen=True)
class PartInfo:
    """製作品 1 種類の表示と扱い。`assembly()` の部品名と 1:1。"""

    name: str                      # assembly() のキー
    label: str                     # 表示名（viewer・BOM）
    color: str                     # viewer の色（#rrggbb）
    material: Material
    made: Made                     # fabricated = 製作品、purchased = 既製品の簡略形状
    count: int = 1
    section: Section = "none"      # 2D 図面の切り方（PR 5 で使う）
    explode: tuple[float, float, float] = (0.0, 0.0, 0.0)   # viewer の分解方向（単位ベクトル）


@dataclass(frozen=True)
class BomRow:
    """部品表の 1 行。製作品は build が形状から作る。既製品は機種が書く。"""

    name: str
    made: Made
    material: Material | None
    standard: str          # 規格・型番の系統（例: DW タレットラグ、手すり用 #400 研磨管）
    dimensions: str        # 例: φ38.1 × t1.2 × L450
    count: int
    part_number: str = ""
    mass_g: float | None = None


@dataclass(frozen=True)
class Model:
    """発見した機種パッケージ。契約の関数を SPEC を束縛した形で持つ。"""

    key: str
    spec: Any
    _module: Any = field(repr=False)

    def name(self) -> str:
        return self._module.name(self.spec)

    def override(self, **values: Any) -> "Model":
        return Model(self.key, self._module.override(self.spec, **values), self._module)

    def assembly(self) -> dict[str, Any]:
        return self._module.assembly(self.spec)

    def parts(self) -> list[PartInfo]:
        return self._module.parts(self.spec)

    def bom(self) -> list[BomRow]:
        return self._module.bom(self.spec)

    def issues(self) -> list[Any]:
        return self._module.issues(self.spec)

    @property
    def drawing(self) -> Callable | None:
        return getattr(self._module, "drawing", None)

    @property
    def acoustic_model(self) -> Callable | None:
        return getattr(self._module, "acoustic_model", None)
```

- [ ] **Step 5: `cad/drumcad/registry.py` を書く**

```python
"""`cad/<機種>/` を発見して契約を検査する。

見つけ方は「`__init__.py` を持つ直下のディレクトリ」。`drumcad` 自身と
`tests`、`_` や `.` で始まる名前は除く。契約に欠けがあれば黙って飛ばさず
TypeError で止める — 機種を足したつもりで build に出てこない、を防ぐ。
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from .contract import REQUIRED, Model

_SKIP = {"drumcad", "tests", "out", "release"}


def discover(root: Path) -> dict[str, Model]:
    root = Path(root)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    models: dict[str, Model] = {}
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        if d.name in _SKIP or d.name[0] in "._" or not (d / "__init__.py").exists():
            continue
        module = importlib.import_module(d.name)
        missing = [n for n in REQUIRED if not hasattr(module, n)]
        if missing:
            raise TypeError(f"{d.name}: 契約に無い名前がある: {', '.join(missing)}")
        models[d.name] = Model(d.name, module.SPEC, module)
    return models
```

- [ ] **Step 6: 通ることを確認**

Run: `uv run --project cad pytest cad/tests/test_registry.py -q`
Expected: 5 passed

- [ ] **Step 7: Commit**

```bash
git add cad/drumcad/contract.py cad/drumcad/registry.py cad/tests/demo/__init__.py cad/tests/test_registry.py
git commit -m "feat(drumcad): 機種契約の型と registry.discover、テスト用 demo 機種"
```

---

### Task 9: `bom.py` — 部品表

**Files:**

- Create: `cad/drumcad/bom.py`
- Test: `cad/tests/test_bom.py`

- [ ] **Step 1: 失敗するテストを書く**

`cad/tests/test_bom.py`:

```python
from pathlib import Path

import pytest
from drumcad.bom import bom_markdown, full_bom
from drumcad.registry import discover

TESTS = Path(__file__).parent


def test_full_bom_adds_a_row_per_fabricated_part_with_its_mass():
    m = discover(TESTS)["demo"]
    rows = full_bom(m)
    names = [r.name for r in rows]
    assert names == ["胴", "底板", "ラグ"]
    shell = rows[0]
    assert shell.made == "fabricated" and shell.material.name.startswith("ステンレス")
    assert shell.mass_g == pytest.approx(3.14159 * (76.2**2 - 75.0**2) * 100 * 7.93e-3, rel=1e-3)
    assert rows[2].part_number == "DWSM2200"


def test_bom_markdown_is_a_table_with_a_total_mass():
    m = discover(TESTS)["demo"]
    md = bom_markdown(m.name(), full_bom(m))
    assert md.startswith("# 部品表 — demo-6-6")
    assert "| 胴 | 製作品 | ステンレス SUS304 |" in md
    assert "| ラグ | 既製品 |" in md and "DWSM2200" in md
    assert "合計質量" in md
```

- [ ] **Step 2: 失敗を確認**

Run: `uv run --project cad pytest cad/tests/test_bom.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: `cad/drumcad/bom.py` を書く**

```python
"""部品表。製作品の行は形状と材質から build が作り、既製品の行は機種が書く。"""

from __future__ import annotations

from .contract import BomRow, Model
from .materials import mass_g

_MADE = {"fabricated": "製作品", "purchased": "既製品"}


def full_bom(model: Model) -> list[BomRow]:
    parts = model.assembly()
    rows = []
    for info in model.parts():
        if info.made != "fabricated":
            continue
        rows.append(BomRow(info.label, "fabricated", info.material, "", "", info.count,
                           mass_g=mass_g(parts[info.name], info.material)))
    return rows + list(model.bom())


def bom_markdown(title: str, rows: list[BomRow]) -> str:
    lines = [f"# 部品表 — {title}", "",
             "| 部品 | 区分 | 材質 | 規格・型番の系統 | 寸法 | 員数 | 型番 | 質量 g（1 個） |",
             "|---|---|---|---|---|---|---|---|"]
    total = 0.0
    for r in rows:
        mass = f"{r.mass_g:.0f}" if r.mass_g is not None else ""
        if r.mass_g is not None:
            total += r.mass_g * r.count
        lines.append(f"| {r.name} | {_MADE[r.made]} | {r.material.name if r.material else ''} | "
                     f"{r.standard} | {r.dimensions} | {r.count} | {r.part_number} | {mass} |")
    lines += ["", f"合計質量（質量の分かる行のみ）: **{total / 1000:.2f} kg**", ""]
    return "\n".join(lines)
```

- [ ] **Step 4: 通ることを確認**

Run: `uv run --project cad pytest cad/tests/test_bom.py -q`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add cad/drumcad/bom.py cad/tests/test_bom.py
git commit -m "feat(drumcad): 部品表 bom.md"
```

---

### Task 10: `viewer.py` — 汎用 3D ビューア（分解表示つき）

**Files:**

- Create: `cad/drumcad/viewer.py`
- Test: `cad/tests/test_viewer.py`

- [ ] **Step 1: 失敗するテストを書く**

`cad/tests/test_viewer.py`:

```python
"""3D ビューア（viewer.html）の回帰テスト。

守りたいのは、埋め込んだメッシュが部品の形そのものであること（抜け・別物・壊れた index）、
分解ベクトルが部品表どおりに入っていること、ファイル 1 枚で開けること。
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import replace
from pathlib import Path

import cadquery as cq
import pytest
from drumcad.registry import discover
from drumcad.viewer import THREE_JS, viewer_html

TESTS = Path(__file__).parent


@pytest.fixture(scope="module")
def demo():
    m = discover(TESTS)["demo"]
    parts = m.assembly()
    return m, parts, viewer_html(m.name(), "テスト", parts, {p.name: p for p in m.parts()})


def _embedded(html: str) -> dict:
    m = re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.DOTALL)
    assert m, "埋め込みデータが無い"
    return json.loads(m.group(1).replace("<\\/", "</"))


def test_every_part_is_embedded_as_a_valid_mesh(demo):
    _, parts, html = demo
    data = _embedded(html)
    assert [p["name"] for p in data["parts"]] == list(parts)
    for p in data["parts"]:
        n = len(p["positions"]) // 3
        assert n > 0 and len(p["positions"]) % 3 == 0, p["name"]
        assert p["indices"] and len(p["indices"]) % 3 == 0, p["name"]
        assert 0 <= min(p["indices"]) and max(p["indices"]) < n, f"{p['name']}: index が頂点数を超える"
        assert all(math.isfinite(c) for c in p["positions"]), p["name"]


def test_embedded_mesh_matches_the_part_it_came_from(demo):
    _, parts, html = demo
    for p in _embedded(html)["parts"]:
        box = cq.Compound.makeCompound(parts[p["name"]].vals()).BoundingBox()
        xs, ys, zs = p["positions"][0::3], p["positions"][1::3], p["positions"][2::3]
        assert (min(xs), max(xs)) == pytest.approx((box.xmin, box.xmax), abs=0.5), p["name"]
        assert (min(ys), max(ys)) == pytest.approx((box.ymin, box.ymax), abs=0.5), p["name"]
        assert (min(zs), max(zs)) == pytest.approx((box.zmin, box.zmax), abs=0.5), p["name"]


def test_labels_colors_and_explode_vectors_come_from_the_part_infos(demo):
    _, _, html = demo
    data = _embedded(html)
    by = {p["name"]: p for p in data["parts"]}
    assert by["shell"]["label"] == "胴" and by["shell"]["color"] == "#c9ced6"
    assert by["shell"]["explode"] == [0, 0, 1] and by["plate"]["explode"] == [0, 0, -1]
    assert data["title"] == "demo-6-6" and data["note"] == "テスト"


def test_a_count_above_one_shows_in_the_label():
    m = discover(TESTS)["demo"]
    infos = {p.name: p for p in m.parts()}
    infos["plate"] = replace(infos["plate"], count=6)
    data = _embedded(viewer_html("t", "n", m.assembly(), infos))
    assert next(p for p in data["parts"] if p["name"] == "plate")["label"] == "底板 ×6"


def test_the_html_is_self_contained_except_for_three_js(demo):
    _, _, html = demo
    srcs = re.findall(r'<script[^>]*\ssrc="([^"]+)"', html)
    assert srcs == [THREE_JS]
    assert not re.search(r'<link[^>]*href="https?://', html)
    assert 'id="explode"' in html
```

- [ ] **Step 2: 失敗を確認**

Run: `uv run --project cad pytest cad/tests/test_viewer.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: `cad/drumcad/viewer.py` を書く**

```python
"""組立をブラウザで回して確かめる自己完結の HTML（`viewer.html`）。

CAD ソフトを入れずに済むよう、部品を三角形メッシュにして 1 枚の HTML に埋め込み、
three.js で描く。外部に取りに行くのは three.js（cdnjs）だけ。

    python3 -m http.server -d cad/out 8000   # → http://localhost:8000/<出力ディレクトリ>/viewer.html

部品表（表示名・色・分解方向）は機種の `parts()` から受け取る。
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import cadquery as cq

from .contract import PartInfo

THREE_JS = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"
TOLERANCE = 0.05         # 弦の許容差（mm）。円弧が多角形に見えない程度
ANGULAR_TOLERANCE = 0.2  # 角度の許容差（rad）


def _shape(part: cq.Workplane) -> cq.Shape:
    return part.val() if len(part.vals()) == 1 else cq.Compound.makeCompound(part.vals())


def mesh(part: cq.Workplane) -> dict[str, list[float] | list[int]]:
    """部品の三角形メッシュ。頂点座標を平坦に並べた配列と、三角形ごとの頂点 index。"""
    vertices, triangles = _shape(part).tessellate(TOLERANCE, ANGULAR_TOLERANCE)
    return {
        "positions": [round(c, 3) for v in vertices for c in (v.x, v.y, v.z)],
        "indices": [i for tri in triangles for i in tri],
    }


def _label(info: PartInfo) -> str:
    return f"{info.label} ×{info.count}" if info.count > 1 else info.label


def viewer_data(title: str, note: str, parts: dict[str, cq.Workplane],
                infos: dict[str, PartInfo]) -> dict:
    meshes = [{"name": name, "label": _label(infos[name]), "color": infos[name].color,
               "explode": list(infos[name].explode), **mesh(part)}
              for name, part in parts.items()]
    xyz = [m["positions"] for m in meshes]
    return {
        "title": title,
        "note": note,
        "radius": max(math.hypot(x, y) for p in xyz for x, y in zip(p[0::3], p[1::3], strict=True)),
        "zmin": min(z for p in xyz for z in p[2::3]),
        "zmax": max(z for p in xyz for z in p[2::3]),
        "parts": meshes,
    }


def viewer_html(title: str, note: str, parts: dict[str, cq.Workplane],
                infos: dict[str, PartInfo]) -> str:
    data = viewer_data(title, note, parts, infos)
    # JSON を <script> に入れるので "</" を閉じタグとして読まれないようにする
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return (_TEMPLATE.replace("__TITLE__", data["title"]).replace("__NOTE__", data["note"])
            .replace("__THREE__", THREE_JS).replace("__DATA__", payload))


def export_viewer(title: str, note: str, parts: dict[str, cq.Workplane],
                  infos: dict[str, PartInfo], path: Path) -> None:
    Path(path).write_text(viewer_html(title, note, parts, infos), encoding="utf-8")


_TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:,">
<title>__TITLE__</title>
<style>
  html, body { margin: 0; height: 100%; background: #1b1e24; color: #e6e6e6;
               font: 13px/1.45 -apple-system, "Hiragino Sans", "Noto Sans JP", sans-serif; overflow: hidden; }
  canvas { display: block; touch-action: none; }
  #ui { position: fixed; top: 10px; left: 10px; background: rgba(0, 0, 0, .58); padding: 10px 12px;
        border-radius: 8px; max-width: 280px; backdrop-filter: blur(4px); }
  #ui h1 { font-size: 14px; margin: 0 0 6px; font-weight: 600; }
  #ui label { display: block; margin: 2px 0; cursor: pointer; }
  #ui .sw { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin: 0 6px 0 4px;
            vertical-align: middle; }
  #ui button { margin: 4px 4px 0 0; padding: 3px 9px; background: #2f343c; color: #eee;
               border: 1px solid #555; border-radius: 4px; cursor: pointer; }
  #ui button:hover { background: #454b55; }
  #ui input[type=range] { width: 100%; }
  #note { margin-top: 8px; color: #f2b0a8; font-size: 12px; }
  #hint { position: fixed; bottom: 8px; left: 10px; color: #9aa0a8; font-size: 12px; }
</style>
</head>
<body>
<div id="ui">
  <h1>__TITLE__</h1>
  <div id="parts"></div>
  <div id="views"></div>
  <label><input type="checkbox" id="wire"> ワイヤーフレーム</label>
  <label>分解 <input type="range" id="explode" min="0" max="1" step="0.01" value="0"></label>
  <div id="note">__NOTE__</div>
</div>
<div id="hint">左ドラッグ: 回転 ／ 右ドラッグ・Shift＋ドラッグ: 移動 ／ ホイール・ピンチ: 拡大縮小</div>
<script src="__THREE__"></script>
<script id="data" type="application/json">__DATA__</script>
<script>
(() => {
  const data = JSON.parse(document.getElementById("data").textContent);
  const scene = new THREE.Scene();
  // 正投影。図面と同じで、位置は見たまま読める
  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, -20000, 20000);
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  document.body.appendChild(renderer.domElement);

  scene.add(new THREE.HemisphereLight(0xffffff, 0x303030, 0.75));
  const key = new THREE.DirectionalLight(0xffffff, 0.8);
  key.position.set(0.4, 0.3, 1);
  camera.add(key);
  scene.add(camera);

  // 部品 --------------------------------------------------------------
  // ワイヤーフレームは材質の wireframe フラグでは見えない（三角形が多すぎて塗り潰しと
  // 区別が付かない）。稜線だけを線分で描き、面のほうを消す。
  const meshes = [];
  const partsBox = document.getElementById("parts");
  let wire = false;
  let explode = 0;
  const R = data.radius;
  for (const p of data.parts) {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(p.positions, 3));
    g.setIndex(p.indices);
    g.computeVertexNormals();
    const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({
      color: p.color, metalness: 0.55, roughness: 0.45, flatShading: true, side: THREE.DoubleSide }));
    const e = new THREE.LineSegments(new THREE.EdgesGeometry(g, 15),
                                     new THREE.LineBasicMaterial({ color: p.color }));
    e.visible = false;
    scene.add(m, e);
    const it = { mesh: m, edges: e, on: true, explode: new THREE.Vector3(...p.explode) };
    meshes.push(it);
    const row = document.createElement("label");
    const box = document.createElement("input");
    box.type = "checkbox";
    box.checked = true;
    box.addEventListener("change", () => { it.on = box.checked; show(); });
    const swatch = document.createElement("span");
    swatch.className = "sw";
    swatch.style.background = p.color;
    row.append(box, swatch, document.createTextNode(p.label));
    partsBox.appendChild(row);
  }
  function show() {
    for (const it of meshes) {
      it.mesh.visible = it.on && !wire;
      it.edges.visible = it.on && wire;
      // 分解: 部品表の方向ベクトル × スライダー × モデル半径
      const off = it.explode.clone().multiplyScalar(explode * R * 0.8);
      it.mesh.position.copy(off);
      it.edges.position.copy(off);
    }
    place();
  }
  document.getElementById("wire").addEventListener("change", e => { wire = e.target.checked; show(); });
  document.getElementById("explode").addEventListener("input", e => { explode = Number(e.target.value); show(); });

  // 床の格子 ------------------------------------------------------------
  const FIT = R * 1.25 + 10;
  const floor = data.zmin - 3;
  const span = Math.ceil(R * 2.6 / 50) * 50;
  const grid = new THREE.GridHelper(span, span / 50, 0x556070, 0x2c323a);
  grid.rotation.x = Math.PI / 2;
  grid.position.z = floor;
  scene.add(grid);

  // カメラ: z を上にして、注視点の周りを球面座標で回す -----------------------
  const zc = (data.zmin + data.zmax) / 2;
  const target = new THREE.Vector3(0, 0, zc);
  const home = { r: R * 3.2, theta: -Math.PI / 2 + 0.7, phi: 1.05 };
  const sph = { ...home };
  function place() {
    const s = Math.sin(sph.phi);
    camera.position.set(target.x + sph.r * s * Math.cos(sph.theta),
                        target.y + sph.r * s * Math.sin(sph.theta),
                        target.z + sph.r * Math.cos(sph.phi));
    camera.up.set(0, 0, 1);
    camera.lookAt(target);
    // 正投影なので寄り引きは視錐台の大きさで出す。縦長の窓では横が先に切れるので狭い辺で合わせる
    const aspect = window.innerWidth / window.innerHeight;
    const zspan = (data.zmax - data.zmin) / 2 + 10;
    const half = Math.max(FIT, zspan) * (1 + explode) * (sph.r / home.r) / Math.min(1, aspect);
    camera.left = -half * aspect; camera.right = half * aspect;
    camera.top = half; camera.bottom = -half;
    camera.updateProjectionMatrix();
    renderer.render(scene, camera);
  }
  const views = {
    "斜め": home,
    "上から": { theta: -Math.PI / 2, phi: 0.02 },
    "下から": { theta: -Math.PI / 2, phi: Math.PI - 0.02 },
    "真横": { theta: -Math.PI / 2, phi: Math.PI / 2 },
    "真横（90°）": { theta: 0, phi: Math.PI / 2 },
  };
  const viewsBox = document.getElementById("views");
  for (const [name, v] of Object.entries(views)) {
    const b = document.createElement("button");
    b.textContent = name;
    b.addEventListener("click", () => { Object.assign(sph, { r: home.r, ...v }); target.set(0, 0, zc); place(); });
    viewsBox.appendChild(b);
  }

  // 操作: 左ドラッグ回転、右／Shift ドラッグ移動、ホイール拡大縮小、2 本指はピンチ ------
  const el = renderer.domElement;
  const pointers = new Map();
  let gesture = null;
  const spread = () => { const [a, b] = [...pointers.values()]; return Math.hypot(a.x - b.x, a.y - b.y); };
  const begin = e => {
    if (pointers.size === 1) { const [p] = pointers.values(); return { x: p.x, y: p.y, pan: e ? e.button === 2 || e.shiftKey : false }; }
    if (pointers.size === 2) return { d: spread() };
    return null;
  };
  el.addEventListener("contextmenu", e => e.preventDefault());
  el.addEventListener("pointerdown", e => {
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    el.setPointerCapture(e.pointerId);
    gesture = begin(e);
  });
  el.addEventListener("pointermove", e => {
    if (!pointers.has(e.pointerId) || !gesture) return;
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pointers.size === 1) {
      const dx = e.clientX - gesture.x, dy = e.clientY - gesture.y;
      gesture.x = e.clientX; gesture.y = e.clientY;
      if (gesture.pan) pan(dx, dy); else rotate(dx, dy);
    } else if (pointers.size === 2) {
      const d = spread();
      if (d > 0) sph.r = clampR(sph.r * gesture.d / d);
      gesture.d = d;
    }
    place();
  });
  const release = e => { pointers.delete(e.pointerId); gesture = begin(null); };
  el.addEventListener("pointerup", release);
  el.addEventListener("pointercancel", release);
  el.addEventListener("wheel", e => { e.preventDefault(); zoom(Math.sign(e.deltaY)); place(); }, { passive: false });
  function rotate(dx, dy) {
    sph.theta -= dx * 0.006;
    sph.phi = Math.max(0.02, Math.min(Math.PI - 0.02, sph.phi - dy * 0.006));
  }
  function pan(dx, dy) {
    const k = sph.r * 0.0016;
    const right = new THREE.Vector3(), up = new THREE.Vector3();
    camera.matrixWorld.extractBasis(right, up, new THREE.Vector3());
    target.addScaledVector(right, -dx * k).addScaledVector(up, dy * k);
  }
  function clampR(r) { return Math.max(R * 0.3, Math.min(R * 12, r)); }
  function zoom(sign) { sph.r = clampR(sph.r * (sign > 0 ? 1.12 : 1 / 1.12)); }

  function resize() {
    renderer.setSize(window.innerWidth, window.innerHeight);
    show();
  }
  window.addEventListener("resize", resize);
  resize();
})();
</script>
</body>
</html>
"""
```

- [ ] **Step 4: 通ることを確認**

Run: `uv run --project cad pytest cad/tests/test_viewer.py -q`
Expected: 5 passed

- [ ] **Step 5: ブラウザで目視**

```bash
uv run --project cad python -c "
from pathlib import Path
import sys; sys.path.insert(0, 'cad/tests')
from drumcad.registry import discover
from drumcad.viewer import export_viewer
m = discover(Path('cad/tests'))['demo']
Path('cad/out').mkdir(exist_ok=True)
export_viewer(m.name(), 'demo', m.assembly(), {p.name: p for p in m.parts()}, Path('cad/out/demo-viewer.html'))
"
python3 -m http.server -d cad/out 8000
```

`http://localhost:8000/demo-viewer.html` を開き、筒と円盤が見え、分解スライダーで円盤が下へ・筒が上へ離れることを確認。確認後に `cad/out/demo-viewer.html` は削除（`cad/out/` は gitignore 済み）。

- [ ] **Step 6: Commit**

```bash
git add cad/drumcad/viewer.py cad/tests/test_viewer.py
git commit -m "feat(drumcad): 汎用 3D ビューア（部品表から表示・分解）"
```

---

### Task 11: `build.py` — 検査 → 未決判定 → stage-and-swap

**Files:**

- Create: `cad/build.py`
- Test: `cad/tests/test_build.py`

- [ ] **Step 1: 失敗するテストを書く**

`cad/tests/test_build.py`:

```python
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
```

- [ ] **Step 2: 失敗を確認**

Run: `uv run --project cad pytest cad/tests/test_build.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'build'`

- [ ] **Step 3: `cad/build.py` を書く**

```python
"""パラメータ → STEP / STL / SVG / viewer / 部品表。

    uv run --project cad python cad/build.py             # 全機種
    uv run --project cad python cad/build.py gatling     # 1 機種

まだ決めきっていない値（provisional）が 1 つでも残っている限り、出力名に
`-PROVISIONAL` が付く。入稿できるのはこれが取れてから。
図面（PR 5）と音響（PR 4）はそれぞれの PR でここに追加する。
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import cadquery as cq
from cadquery import exporters

sys.path.insert(0, str(Path(__file__).parent))

from drumcad.bom import bom_markdown, full_bom          # noqa: E402
from drumcad.checks import fatal_count                  # noqa: E402
from drumcad.contract import Model                      # noqa: E402
from drumcad.dims import unsettled                      # noqa: E402
from drumcad.registry import discover                   # noqa: E402
from drumcad.viewer import export_viewer                # noqa: E402

ROOT = Path(__file__).parent
OUT = ROOT / "out"
_SVG = {"width": 900, "height": 700, "projectionDir": (0.35, -1, 0.4), "showAxes": False}


def _export_part(part: cq.Workplane, out_dir: Path, stem: str) -> None:
    exporters.export(part, str(out_dir / f"{stem}.step"))
    # STL は Blender などメッシュ系の無料ソフトで開くため（STEP は読めない）
    exporters.export(part, str(out_dir / f"{stem}.stl"), tolerance=0.05, angularTolerance=0.2)
    exporters.export(part, str(out_dir / f"{stem}.svg"), opt=_SVG)


def _stale_dirs(model: Model, keep: Path | None) -> list[Path]:
    """この機種が過去に吐いた出力先のうち、今回の結果と食い違うもの。"""
    name = model.name()
    return [d for d in (OUT / name, OUT / f"{name}-PROVISIONAL") if d != keep and d.exists()]


def _quarantine(d: Path) -> Path:
    """出力先を消さずに `.stale` へ退避する。置き換えが成功していない時点で古い方を
    破棄すると手元に何も残らない。名前を汚しておけば掴まれない。"""
    dest = d.with_name(d.name + ".stale")
    if dest.exists():
        shutil.rmtree(dest)
    d.rename(dest)
    return dest


def _export_all(model: Model, out_dir: Path) -> None:
    """**全部そろってから**出力先に置く（stage-and-swap）。

    出力先へ直接書くと、途中の 1 点で落ちたときに新旧が混ざったディレクトリが残る。
    """
    staging = out_dir.with_name(out_dir.name + ".staging")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    try:
        parts = model.assembly()
        infos = {p.name: p for p in model.parts()}
        for name, part in parts.items():
            _export_part(part, staging, name)
        combined = cq.Workplane(obj=cq.Compound.makeCompound([p.val() for p in parts.values()]))
        exporters.export(combined, str(staging / "assembly.step"))
        exporters.export(combined, str(staging / "assembly.stl"), tolerance=0.05, angularTolerance=0.2)
        exporters.export(combined, str(staging / "assembly.svg"), opt={**_SVG, "width": 1100, "height": 800})
        pending = unsettled(model.spec)
        note = (f"未決 {len(pending)} 件（仮値）" if pending else "全寸法が確定")
        export_viewer(model.name(), note, parts, infos, staging / "viewer.html")
        (staging / "bom.md").write_text(bom_markdown(model.name(), full_bom(model)), encoding="utf-8")
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    if out_dir.exists():
        shutil.rmtree(out_dir)
    staging.rename(out_dir)


def build(model: Model) -> int:
    """1 機種分を出力する。致命的な問題の件数を返す。"""
    print(f"\n=== {model.name()} ===")
    # 検査はエクスポートより先。後ろに置くと、致命的な問題を抱えた STEP が残ったまま終わる。
    found = model.issues()
    for issue in found:
        print(f"  {issue}")
    fatal = fatal_count(found)
    if fatal:
        print(f"  ❌ 致命的な問題が {fatal} 件。出力は作らない")
        for d in _stale_dirs(model, keep=None):
            print(f"     前回の出力 {d.name}/ を {_quarantine(d).name}/ へ退避した")
        return fatal
    if not found:
        print("  ✅ 噛み合わせの検査は全て通過")

    pending = unsettled(model.spec)
    out_dir = OUT / f"{model.name()}{'-PROVISIONAL' if pending else ''}"
    for d in _stale_dirs(model, keep=out_dir):
        print(f"  {d.name}/ は今回の接尾辞と食い違うので {_quarantine(d).name}/ へ退避した")
    _export_all(model, out_dir)
    for row in full_bom(model):
        if row.mass_g is not None:
            print(f"  {row.name:12} {row.mass_g:8.1f} g × {row.count}")
    if pending:
        print(f"  ⚠️ 未決 {len(pending)} 件 — このデータは入稿できない")
        for path, leaf in pending:
            print(f"     {path:26} {leaf!r}")
    else:
        print("  ✅ 全寸法が確定している")
    return 0


def main(argv: list[str]) -> int:
    models = discover(ROOT)
    names = argv[1:] or list(models)
    unknown = [n for n in names if n not in models]
    if unknown:
        print(f"知らない機種: {', '.join(unknown)}", file=sys.stderr)
        print(f"使えるのは: {', '.join(models)}", file=sys.stderr)
        return 2
    fatal = sum(build(models[n]) for n in names)
    print(f"\n出力先: {OUT}")
    if fatal:
        print(f"❌ 噛み合わせの致命的な問題が {fatal} 件ある", file=sys.stderr)
    return 1 if fatal else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 4: 通ることを確認**

Run: `uv run --project cad pytest cad/tests/test_build.py -q`
Expected: 7 passed

- [ ] **Step 5: 全テストを通す**

Run: `uv run --project cad pytest cad/tests -q`
Expected: 全件 passed（42 件前後）

- [ ] **Step 6: Commit**

```bash
git add cad/build.py cad/tests/test_build.py
git commit -m "feat(cad): build.py — 検査・未決判定・stage-and-swap で STEP/STL/SVG/viewer/bom を出す"
```

---

### Task 12: 固有語の grep テスト（仕様 §1.2(4)）

**Files:**

- Create: `cad/tests/test_no_private_terms.py`

- [ ] **Step 1: テストを書く**

`cad/tests/test_no_private_terms.py`:

```python
"""公開リポに、他者の製品や非公開資料に固有の語が紛れていないことを、リポ全体で確かめる。

固有語の一覧はこのファイルにだけ置く（仕様書や README には書かない）。
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TERMS = ("kitano", "北野", "testimony", "本人談", "明細書", "実用新案")
_SELF = Path(__file__).resolve()


def _tracked_text_files() -> list[Path]:
    out = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True).stdout
    files = [REPO / line for line in out.splitlines()]
    return [f for f in files if f.suffix in {".md", ".py", ".toml", ".txt", ".html", ".yml", ".yaml"}
            and f.resolve() != _SELF]


def test_no_private_terms_in_any_tracked_text_file():
    pattern = re.compile("|".join(re.escape(t) for t in TERMS), re.IGNORECASE)
    hits = []
    for f in _tracked_text_files():
        for n, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if pattern.search(line):
                hits.append(f"{f.relative_to(REPO)}:{n}: {line.strip()[:80]}")
    assert not hits, "固有語が残っている:\n" + "\n".join(hits)
```

- [ ] **Step 2: 通ることを確認**

Run: `uv run --project cad pytest cad/tests/test_no_private_terms.py -q`
Expected: 1 passed

- [ ] **Step 3: Commit**

```bash
git add cad/tests/test_no_private_terms.py
git commit -m "test: 固有語がリポに紛れていないことを確かめる"
```

---

### Task 13: 仕上げと PR

- [ ] **Step 1: 全テストと build を通す**

```bash
uv run --project cad pytest cad/tests -q
uv run --project cad python cad/build.py
```

Expected: テスト全件 passed。`build.py` は機種が無いので `出力先: …/cad/out` とだけ出て終了コード 0。

- [ ] **Step 2: git status が空であることを確認**

```bash
git status --short
```

- [ ] **Step 3: push と PR**

`git push -u origin feature/drumcad-base` のあと、`make-pr` スキルで PR を開く（`--assignee @me`、draft にしない。本文は日本語なので `mojiemoji-github` スキルを通す）。本文の骨子:

- 1 行目にバッジ行: agent badge、`type-feature`、`scope-cad/drumcad`、`tests-pytest`
- 「仕様 §4（共通基盤）の PR 2。機種パッケージを差し込めば STEP・STL・SVG・viewer・bom が `-PROVISIONAL` 規約つきで出る」
- 入ったもの: dims（Dim / Choice / walk / unsettled / as_provisional / override）、checks、materials、stock、contract と registry、bom、viewer（分解表示）、build.py、tests/demo、固有語 grep テスト
- 入っていないもの: 図面は PR 5、音響は PR 4、機種 gatling は PR 3。契約の `drawing` / `acoustic_model` は今は任意属性
- 確認コマンド: `uv run --project cad pytest cad/tests -q`

---

## 自己レビュー

- **仕様の網羅**: §4.1 の dims（Choice 追加、ラベル書き換え）→ Task 2–4。checks → Task 5。viewer（部品表・分解）→ Task 10。build 骨格（発見・stage-and-swap・接尾辞）→ Task 8, 11。§4.2 の materials → Task 6、stock → Task 7、bom → Task 9。§1.2(4) の grep → Task 12。§4.1 の drawing 一般化と §4.2 の acoustics / process は仕様 §7 どおり PR 4–5。
- **契約のうち `drawing` / `acoustic_model`** は Task 8 で任意属性として読む。PR 4 / 5 で `REQUIRED` に移す。
- **型の一貫性**: `Model.override(**values)` は `plate__thickness=6` の形（`__` を `.` に読み替え）。Task 11 のテストはこれに合わせてある。`PartInfo.explode` は 3 要素タプル、viewer は `list` にして埋め込む（Task 10 のテストは `[0, 0, 1]` と比較）。
- **既知の限界**: `Model.override` は葉の出典を継ぐので、Task 11 の「確定したら接尾辞が外れる」テストは `dataclasses.replace` で出典ごと差し替えている（`_settled` ヘルパー）。
