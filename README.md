# Blast Tom Series

<!-- hero: docs/images/hero.jpg（生成予定。ヒーロー画像は README 仕上げの PR で入れる） -->

![status](https://img.shields.io/badge/status-design%20spec-yellow) ![material](https://img.shields.io/badge/material-SUS304%20polished-blue) ![cad](https://img.shields.io/badge/cad-CadQuery%20parametric-blue) ![acoustics](https://img.shields.io/badge/acoustics-1D%20simulation-blue) ![license](https://img.shields.io/badge/code-MIT-green) ![license](https://img.shields.io/badge/drawings-CC%20BY%204.0-green) ![lang](https://img.shields.io/badge/docs-日本語-lightgrey)

キャノンタム（オクタバン）から派生した、**オリジナル設計のタム 3 機種**。
パラメトリック CAD で設計し、町工場へ入稿できる STEP と 2D 図面、
構成を聴き比べるための音響シミュレーションまでを 1 つのリポで扱う。

材質はステンレス SUS304 の研磨仕上げ。図面と 3D データは CC BY 4.0 なので、参考にしてもらって構わない。

## 3 機種

| # | 機種 | 概要 | 状態 |
|---|---|---|---|
| 1 | **Gatling Tom** | 6" ヘッド＋短いプレナム胴の下に SUS パイプ 6 本の管束。ミニガンの意匠。管 6 本を膜・プレナムと結合した共鳴系として鳴らす | **設計仕様あり**（[仕様](docs/superpowers/specs/2026-10-01-blast-tom-series-design.md)）。**形状・部品表・viewer あり**（`cad/gatling/`。寸法は仮値を含む）。音響と図面は未 |
| 2 | Vulcan Tom | 細長い筒に丸穴が多数。バルカン砲のバレルジャケットの意匠 | スケッチのみ |
| 3 | Magnum Tom | 18" シングルヘッドのフロアタム、3 本脚。リボルバーのシリンダーの意匠 | スケッチのみ |

スケッチは [reference/sketches/](reference/sketches/)。

## 進め方

1. **形** — `cad/build.py` が部品ごとの STEP と `viewer.html` を出す。管の本数・隙間・クランプ位置を数値 1 つで変えて、ブラウザで回して決める
2. **音** — 同じ変数から共鳴周波数・Q・インパルス応答 wav を出し、構成を聴き比べる（空気の共鳴のみ。金属の鳴りは現物で確認）
3. **図面** — `drawing.dxf` / `drawing.pdf` に断面・平面・注記・員数。STEP だけでは町工場は受けない
4. **見積もり・製作**

決めたこと（覆したことも）は [docs/decisions.md](docs/decisions.md)。

## ライセンス

- コード（`cad/` 以下の Python）: [MIT](LICENSE)
- 図面・STEP・画像・文書: [CC BY 4.0](LICENSE-CC-BY-4.0)
