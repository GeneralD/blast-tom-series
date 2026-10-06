# Blast Tom Series — プロジェクトの決まり

オリジナル設計のタム 3 機種（Gatling / Vulcan / Magnum）の公開リポ。日本語で書く。

## まず読むもの

- 設計仕様: `docs/superpowers/specs/2026-10-01-blast-tom-series-design.md`（承認済み。§7 が PR の順序）
- 決定ログ: `docs/decisions.md`（D-01〜。覆した判断も残す。新しい決定は番号を足す）
- 実装計画: `docs/superpowers/plans/`（1 PR 1 計画。PR 2 = `2026-10-01-drumcad-base.md`、PR 3 = `2026-10-01-gatling.md`）
- 作業中の状態（ブランチ・PR・次の一手）はこのファイルに書かない。Claude の memory にある。

## 進め方

- main は PR 経由のみ。ルールセットで直接 push と削除を止めている。
- 1 PR 1 計画。計画は superpowers:executing-plans か subagent-driven-development で実行する。
- 後続 PR の計画は、前の PR が main に入ってから書く。基盤の実際の API に依存するため。
- テスト: `uv run --project cad pytest cad/tests -q`。初回は cadquery の読み込みで 1〜2 分かかる。形状を作るテストが多く、全体で 2〜3 分（約 160 秒）かかる。
- build: `uv run --project cad python cad/build.py`。
- `cad/` の Python を書くときの決まりは `.claude/rules/cad-dimensions.md`（寸法は出典つき）。

## 公開リポの決まり（仕様 §3.1）

- 非公開の資料・リポ・道具への言及・リンク・URL を置かない。「以前に自分用に書いた非公開の道具」より具体的に書かない。公開した瞬間に、存在そのものが漏れるため。
- 他者の製品に由来する実測値・写真・特許解析・証言を持ち込まない。固有語は `cad/tests/test_no_private_terms.py` の grep で止める。この grep は計画書を含む全 `.md` を見るので、固有語の一覧をドキュメントに写さない。
- 第三者の画像（参考にしたミニガンの画像など）はコミットしない。権利がこちらに無いため。
