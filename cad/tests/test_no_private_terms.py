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
