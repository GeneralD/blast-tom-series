# CAD

機種ごとの寸法（`SPEC`）から、部品ごと・組立ごとの STEP / STL / SVG（確認用のプレビュー）、確認用の `viewer.html`、部品表 `bom.md` を毎回同じように再生成する。

2D 図面（PR 5 の `drumcad/drawing`）と音響の計算（PR 4）は、まだ出力しない。それぞれの PR で `build.py` に足す。

## 使い方

    uv run --project cad python cad/build.py            # 全機種
    uv run --project cad python cad/build.py gatling    # 1 機種
    uv run --project cad pytest cad/tests -q            # テスト

出力は `cad/out/<機種の name()>/`（`demo` なら `demo-6-6/`）。まだ決めきっていない値（`provisional`）が 1 つでも残っていると `-PROVISIONAL` が付く。

`viewer.html` はブラウザで開く（three.js を cdnjs から読む以外は自己完結）:

    python3 -m http.server -d cad/out 8000
    # → http://localhost:8000/<出力ディレクトリ>/viewer.html

## 機種を足すには

`cad/<機種>/__init__.py` が仕様書 §4.4 の契約（`SPEC`, `name`, `override`, `assembly`, `parts`, `bom`, `issues`）を公開していれば `build.py` が見つける。`cad/tests/demo/` が最小の例。
