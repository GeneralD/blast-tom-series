# Blast Tom Series — プロジェクトの決まり

オリジナル設計のタム 3 機種（Gatling / Vulcan / Magnum）の公開リポ。日本語で書く。

## まず読むもの

- 設計仕様: `docs/superpowers/specs/2026-10-01-blast-tom-series-design.md`（承認済み。§7 が PR の順序）
- 決定ログ: `docs/decisions.md`（D-01〜。覆した判断も残す。新しい決定は番号を足す）
- 実装計画: `docs/superpowers/plans/`（1 PR 1 計画。PR 2 = `2026-10-01-drumcad-base.md`）

## 進め方

- main は PR 経由のみ（ルールセット）。1 PR 1 計画、計画は superpowers:executing-plans か subagent-driven-development で実行する。
- 後続 PR の計画は、前の PR が main に入ってから書く（基盤の実際の API に依存するため）。
- テスト: `uv run --project cad pytest cad/tests -q`。build: `uv run --project cad python cad/build.py`。
- 寸法は必ず出典つき（`drumcad.dims` の `Dim` / `Choice`）。素の float を寸法に使わない。

## 公開リポの決まり（仕様 §3.1）

- 非公開の資料・リポ・道具への言及・リンク・URL を置かない。「以前に自分用に書いた非公開の道具」より具体的に書かない。
- 他者の製品に由来する実測値・写真・特許解析・証言を持ち込まない。固有語は `cad/tests/test_no_private_terms.py` の grep で止める。
- 第三者の画像（参考にしたミニガンの画像など）はコミットしない。
