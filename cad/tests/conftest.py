"""テスト用の機種パッケージ `demo` を、機種の置き場（cad/）と同じ扱いで import できるようにする。"""

from __future__ import annotations

import sys
from pathlib import Path

TESTS = Path(__file__).parent
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))
