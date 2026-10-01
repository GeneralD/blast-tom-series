"""Gatling Tom — 6" ヘッド＋短いプレナム胴の下に SUS パイプ 6 本の管束（仕様 §5）。

`build.py` が見つける契約（仕様 §4.4）の名前をここで公開する。サブモジュールの名前は契約の
関数名（`assembly` `parts` `bom` `drawing` `acoustic_model`）と重ねない — 重なると、最初に
import した時点で `gatling.assembly` が関数ではなくモジュールになり、`registry.discover` の
`hasattr` は通るのに `Model.assembly()` が落ちる。
"""

from .assemble import assembly
from .bill import bom
from .catalog import parts
from .checks import issues
from .derived import name
from .params import SPEC, override

__all__ = ["SPEC", "name", "override", "assembly", "parts", "bom", "issues"]
