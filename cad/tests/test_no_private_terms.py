"""公開リポに、他者の製品や非公開資料に固有の語が紛れていないことを、リポ全体で確かめる。

固有語の一覧はこのファイルにだけ置く（仕様書や README には書かない）。
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TERMS = ("kitano", "北野", "testimony", "本人談", "明細書", "実用新案")
_SELF = Path(__file__).resolve()


def private_term_hits(repo: Path, exclude: Path | None = None) -> list[str]:
    """追跡中の全テキストファイルから固有語を探し、`パス:行番号: 内容` を返す。

    拡張子の許可リストで絞ると LICENSE・.gitignore・uv.lock や今後増える
    .step/.dxf/.svg/.json を素通りする（仕様 §1.2(4) はリポ全体を求める）。
    そこで対象は「追跡中の全ファイルからバイナリを除いたもの」とし、判定は git に任せる
    （-I がバイナリを除く）。大文字小文字は無視する。
    """
    pathspec = ["--", "."] + ([f":(exclude){exclude.relative_to(repo).as_posix()}"] if exclude else [])
    cmd = ["git", "grep", "-I", "-n", "-i", "-F", *(a for t in TERMS for a in ("-e", t)), *pathspec]
    proc = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace")
    # 1 は「一致なし」。それ以外の失敗を「一致なし」と読むと、検査が黙って無効になる。
    if proc.returncode not in (0, 1):
        raise RuntimeError(f"git grep が失敗した (exit {proc.returncode}): {proc.stderr.strip()}")
    return [line[:120] for line in proc.stdout.splitlines()]


def test_no_private_terms_in_any_tracked_text_file():
    hits = private_term_hits(REPO, exclude=_SELF)
    assert not hits, "固有語が残っている:\n" + "\n".join(hits)


def _tmp_repo(tmp_path: Path, name: str, body: str) -> Path:
    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    git("init", "-q")
    (tmp_path / name).write_text(body, encoding="utf-8")
    git("add", "-A")
    return tmp_path


def test_catches_terms_in_files_outside_the_old_extension_allowlist(tmp_path):
    # 以前の許可リスト（.md .py .toml …）に無い名前・拡張子でも捕まること。語は TERMS から取る。
    for name in ("LICENSE", ".gitignore", "uv.lock", "part.step", "drawing.dxf", "view.svg", "bom.json"):
        sub = tmp_path / name.replace(".", "_")
        sub.mkdir()
        repo = _tmp_repo(sub, name, f"x\n{TERMS[0].upper()} y\n")
        hits = private_term_hits(repo)
        assert [h.split(":")[0] for h in hits] == [name], name


def test_catches_non_ascii_term(tmp_path):
    repo = _tmp_repo(tmp_path, "notes.txt", f"前文{TERMS[1]}後文\n")
    assert len(private_term_hits(repo)) == 1


def test_skips_binary_files(tmp_path):
    repo = _tmp_repo(tmp_path, "blob.bin", "")
    (repo / "blob.bin").write_bytes(b"\x00\x01" + TERMS[0].encode() + b"\x00")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    assert private_term_hits(repo) == []


def test_excludes_only_the_given_file(tmp_path):
    repo = _tmp_repo(tmp_path, "self.py", f"{TERMS[0]}\n")
    (repo / "other.md").write_text(f"{TERMS[0]}\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    hits = private_term_hits(repo, exclude=repo / "self.py")
    assert [h.split(":")[0] for h in hits] == ["other.md"]


def test_ignores_untracked_files(tmp_path):
    repo = _tmp_repo(tmp_path, "ok.md", "clean\n")
    (repo / "new.md").write_text(f"{TERMS[0]}\n", encoding="utf-8")
    assert private_term_hits(repo) == []
