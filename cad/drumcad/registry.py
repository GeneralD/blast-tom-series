"""`cad/<機種>/` を発見して契約を検査する。

見つけ方は「`__init__.py` を持つ直下のディレクトリ」。`drumcad` 自身と
`tests`、`_` や `.` で始まる名前は除く。契約に欠けがあれば黙って飛ばさず
TypeError で止める — 機種を足したつもりで build に出てこない、を防ぐ。

読み込みは `spec_from_file_location` で行い、`sys.path` は変えない。`import_module` だと
root を `sys.path` に挿しっぱなしになり、同名の機種が別の root にあっても `sys.modules`
のキャッシュが先に当たって古いものを返す。ここでは root ごとに別名で登録し、読むたびに
置き換える（`from .params import ...` のような相対 import はパッケージ名で解決される）。
下位モジュールも `_FreshLoader` で読む（読み込み中だけ `_FreshFinder` を `sys.meta_path` の先頭に置く）。
本体だけ .pyc を避けても、`params.py` のような下位モジュールが古い .pyc に当たっては意味がない。
読み込みが終わった後に関数の中で遅れて import するものは対象外（機種は先頭で import する）。
機種側の `import drumcad` は従来どおり、呼び出し側が `cad/` を通している前提で動く。
"""

from __future__ import annotations

import hashlib
import importlib.abc
import importlib.util
import sys
from importlib.machinery import PathFinder, SourceFileLoader
from types import ModuleType
from pathlib import Path

from .contract import REQUIRED, Model

_SKIP = {"drumcad", "tests", "out", "release"}


class _FreshLoader(SourceFileLoader):
    """.pyc を使わず毎回ソースから読む。

    .pyc の妥当性は更新時刻とサイズで決まるので、同じ秒に同じ長さで書き換えた機種は
    古いバイトコードが当たる。読み直しの意味がなくなるため避ける。
    """

    def get_code(self, fullname):
        path = self.get_filename(fullname)
        return self.source_to_code(self.get_data(path), path)


class _FreshFinder(importlib.abc.MetaPathFinder):
    """`prefix` 配下の名前だけ、標準の探索結果のローダーを `_FreshLoader` に差し替える。"""

    def __init__(self, prefix: str) -> None:
        self._prefix = prefix + "."

    def find_spec(self, fullname, path=None, target=None):
        if not fullname.startswith(self._prefix):
            return None
        spec = PathFinder.find_spec(fullname, path, target)
        if spec is not None and type(spec.loader) is SourceFileLoader:
            spec.loader = _FreshLoader(spec.loader.name, spec.loader.path)
        return spec


def _load(root: Path, name: str) -> ModuleType:
    # root の絶対パスから名前空間を作る。別 root の同名機種と衝突させない。
    tag = hashlib.sha1(str(root.resolve()).encode("utf-8")).hexdigest()[:10]
    qualname = f"_drumcad_models_{tag}.{name}"
    # 前回読んだ本体と下位モジュールを捨てる。書き換えた機種を読み直すため。
    for key in [k for k in sys.modules if k == qualname or k.startswith(qualname + ".")]:
        del sys.modules[key]
    pkg_dir = root / name
    init = str(pkg_dir / "__init__.py")
    spec = importlib.util.spec_from_file_location(
        qualname, init, loader=_FreshLoader(qualname, init), submodule_search_locations=[str(pkg_dir)]
    )
    module = importlib.util.module_from_spec(spec)
    # `from .sub import leaf` は `__import__("<名前空間>.<機種>.sub.leaf")` を呼び、先頭の名前空間も
    # import しようとする。空の親モジュールを置いておかないと、そこで ModuleNotFoundError になる
    space = qualname.rpartition(".")[0]
    if space not in sys.modules:
        sys.modules[space] = ModuleType(space)
        sys.modules[space].__path__ = []
    sys.modules[qualname] = module      # 相対 import が親を引けるよう、実行前に登録する
    finder = _FreshFinder(qualname)
    sys.meta_path.insert(0, finder)
    try:
        spec.loader.exec_module(module)
    except BaseException:
        del sys.modules[qualname]
        raise
    finally:
        sys.meta_path.remove(finder)    # 他の import に影響を残さない
    return module


def discover(root: Path) -> dict[str, Model]:
    root = Path(root)
    models: dict[str, Model] = {}
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        if d.name in _SKIP or d.name[0] in "._" or not (d / "__init__.py").exists():
            continue
        module = _load(root, d.name)
        missing = [n for n in REQUIRED if not hasattr(module, n)]
        if missing:
            raise TypeError(f"{d.name}: 契約に無い名前がある: {', '.join(missing)}")
        models[d.name] = Model(d.name, module.SPEC, module)
    return models
