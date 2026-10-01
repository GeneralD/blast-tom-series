"""`cad/<機種>/` を発見して契約を検査する。

見つけ方は「`__init__.py` を持つ直下のディレクトリ」。`drumcad` 自身と
`tests`、`_` や `.` で始まる名前は除く。契約に欠けがあれば黙って飛ばさず
TypeError で止める — 機種を足したつもりで build に出てこない、を防ぐ。

読み込みは `spec_from_file_location` で行い、`sys.path` は変えない。`import_module` だと
root を `sys.path` に挿しっぱなしになり、同名の機種が別の root にあっても `sys.modules`
のキャッシュが先に当たって古いものを返す。ここでは root ごとに別名で登録し、読むたびに
置き換える（`from .params import ...` のような相対 import はパッケージ名で解決される）。
機種側の `import drumcad` は従来どおり、呼び出し側が `cad/` を通している前提で動く。
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from importlib.machinery import SourceFileLoader
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
    sys.modules[qualname] = module      # 相対 import が親を引けるよう、実行前に登録する
    try:
        spec.loader.exec_module(module)
    except BaseException:
        del sys.modules[qualname]
        raise
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
