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
from drumcad.checks import count_issues, fatal_count         # noqa: E402
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
        combined = cq.Workplane(obj=cq.Compound.makeCompound([s for p in parts.values() for s in p.solids().vals()]))
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
    # 古い出力は消さずに退避し、置き換えが済んでから捨てる。rmtree してから rename だと、
    # その間に落ちたとき新旧どちらも手元に残らない（仕様 §4.1: 古い出力は `.stale/` へ退避）
    backup = _quarantine(out_dir) if out_dir.exists() else None
    try:
        staging.rename(out_dir)
    except BaseException:
        if backup is not None:
            backup.rename(out_dir)
        shutil.rmtree(staging, ignore_errors=True)
        raise
    if backup is not None:
        shutil.rmtree(backup)


def build(model: Model) -> int:
    """1 機種分を出力する。致命的な問題の件数を返す。"""
    print(f"\n=== {model.name()} ===")
    # 検査はエクスポートより先。後ろに置くと、致命的な問題を抱えた STEP が残ったまま終わる。
    found = [*model.issues(), *count_issues(model.assembly(), model.parts())]
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
