# M6 回帰結果: LLM-jp-4 vs 凍結較正セット（2026-07-04）

## 実行条件

- コマンド: `garden judge --regress eval/calibration_export.json`
- 判定モデル: `llm-jp-4-32b-a3b-thinking-Q4_K_M.gguf`（DGX Spark / llama.cpp llama-server）
- 較正セット: 35ペア（gold 20 + 非gold 層化15）。Claude 代役判定を基準とする。

## 結果サマリ

| 指標 | Claude 代役（基準） | LLM-jp-4 実測 | 評価 |
|---|---|---|---|
| JSON 妥当率 | 35/35 (100%) | 29/35 (82.9%) | リトライ後も6件 invalid |
| gold 一致（正解を link） | 19/20 | 17/20 | やや低下 |
| 非gold link 率（過剰リンク） | **1/15** | **11/15** | **大幅悪化＝過剰リンク傾向** |

## 所見

### 1. 過剰リンク（最重要）
LLM-jp-4 は「関係がある」と言いたがる傾向が強く、無関係ペアの 11/15 を link と判定した
（例: 「BuJoで意思決定」→「多層ウォッチドッグ」を"階層的"という表層一致で link）。
Claude 代役は 1/15 だったので、モデル固有の傾向。

### 2. confidence でゲート可能
- 誤リンク11件の confidence: `[4×9, 5×2]`
- 正リンク17件の confidence: `[4×8, 5×9]`
- **conf>=5 ゲート適用時: 偽リンク 11→2、正リンク 17→9**
- → `report.py` に `min_confidence=5`（config `[report]`）を実装。ゲート後の上位5件は**全て gold・理由も的確**と確認。
- precision 優先の判断（週5件の提案では、正解を取りこぼすより誤提案を減らす方が価値が高い＝頓挫防止）。

### 3. JSON 妥当率 82.9%
- invalid 6件の内訳: evidence 逐語ずれ4件（thinking モデルが引用を微妙に言い換える）、TimeoutError 2件。
- 逐語検証は幻覚ガードとして正しく機能している（言い換え＝根拠の捏造リスクなので弾いて正しい）。
- Timeout 2件は thinking の長考。judge のタイムアウトは 600s だが、混雑時に超過しうる → リトライ間隔やタイムアウト調整の余地。

## 対処（実装済み / 残）

- [x] `report.py` に confidence ゲート（既定 conf>=5）
- [x] `judge_pair` のパースリトライ（invalid を減らす。逐語ずれには一定有効）
- [ ] evidence 逐語ずれの緩和: プロンプトで「引用は一字一句コピー」を強調 or 逐語検証を「正規化後の部分一致」に緩める案（要検討・over-fit 注意）
- [ ] Timeout: judge のタイムアウト延長 or 並列度を落とす
- [ ] 本番運用では candidates→judge を全件回すと過剰リンクが大量に出るため、confゲート + 件数上限で最終段を守る（実装済み）

## 結論

**M6 判定側は「接続済み・実用可能」だが、LLM-jp-4 は過剰リンク傾向があるため confidence>=5 ゲートが必須。**
ゲート適用後の提案品質は良好（上位5件が全て gold）。Claude 代役ほどの precision は出ないが、
週次レビューで人間が最終判断する運用（read+propose）なら十分機能する。
