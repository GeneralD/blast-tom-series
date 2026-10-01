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
