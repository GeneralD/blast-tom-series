---
paths:
  - "cad/**/*.py"
---

# 寸法は出典つきで書く

- 寸法は `drumcad.dims` の `Dim`（数値）か `Choice`（文字列の選択）で持つ。素の float を寸法に使わない。
- 出典は 仕様書 / 実測 / 導出 / 設計判断 / 仮 の 5 種（`spec` / `measured` / `derived` / `design` / `provisional`）。
- まだ決めきれない値は `provisional(値, "何を待っているか")` にする。
- 理由: `build.py` は仮の値が 1 つでも残る間、出力名に `-PROVISIONAL` を付けて入稿を止める。素の float はこの検査をすり抜け、仮の数字が入稿データに紛れ込む。
- 機種パッケージ（`cad/<機種>/__init__.py`）は仕様 §4.4 の契約 `SPEC, name, override, assembly, parts, bom, issues` を公開する。欠けると `registry.discover` が TypeError で止める。
