"""寸法値と、その値がどこから来たのかを一緒に運ぶ型。

設計中の寸法は出どころの強さがまちまちで、決めた値・カタログ値・実測値と、
まだ決めきっていない仮置きが同じ数式に混ざる。数値だけを持ち回ると
「どれが仮だったか」が数手で分からなくなり、仮値のまま入稿しかねない。

そこで値そのものに出典を貼る。`Dim` は float の派生なので、幾何計算の
コードは普通の数値と同じように書ける。数値でない選択肢（型番・ねじ規格・
仕上げ）は `Choice` で同じ出典を持つ。
"""

from __future__ import annotations

import dataclasses
from enum import Enum
from typing import Any, Iterator


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

    def __getnewargs__(self) -> tuple[float, Source, str]:
        # float の派生は pickle / deepcopy が `__new__(cls, 値)` だけで復元しようとし、
        # 必須の source で落ちる。asdict も内部で deepcopy するので、ここで引数を渡す。
        return float(self), self.source, self.note

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
