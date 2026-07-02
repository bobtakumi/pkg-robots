# pkg_robots — Robots in the Garden 実装（Phase 1）

PKG（`~/pkg_vault`）に対する Connector robot とその土台。設計・経緯は Vault 側の
`_Reports/2026-07-02 Robots実装プラン Phase1（インデクサ+Connector）.md` と
プロジェクトノート v4 を正とする。**Vault へは読み取り専用**（書き込みは `_Reports/suggest-YYYYMMDD.md` のみ、M4 で実装）。

## 使い方

```sh
.venv/bin/python -m garden index              # 索引＋統計の全再構築（埋め込み込み。Ollama 未起動なら自動スキップ）
.venv/bin/python -m garden candidates --eval  # 候補生成 + recall ゲート測定（M2）
.venv/bin/python eval/rank_diag.py            # 正解ペアの順位分布診断（モデル比較用）
.venv/bin/python -m garden judge              # M3（未実装）
.venv/bin/python -m garden report             # M4（未実装）
```

依存: index は標準ライブラリのみ（Python 3.11+）、candidates 以降は `.venv`（numpy）。
埋め込みは Ollama + `bge-m3-8k`（`ollama create bge-m3-8k -f Modelfile.bge-m3-8k` で作成）。
設定は `config.toml`。出力は `data/`（git 管理外）。

## 状態（2026-07-03）

- **M0–M3 完了**。索引 2,589チャンク全埋め込み・候補生成 3,631ペア・judge（OpenAI 互換＋evidence 逐語検証）が動作
- **O2 決着**: `bge-m3-8k` 採用（recall@10=51.1% / @30=63.8%）。ruri-large は 512tok 制約→600字チャンクで 25.5% に劣後
- **M3 較正済み**（Claude が judge 役）: 35ペアで妥当率100%・gold一致19/20・非gold link 1/15。
  較正セット（`eval/calibration_export.json` + `calibration_labels.jsonl`）は凍結——DGX 配線後の LLM-jp-4 回帰テストに使う
- 【U】モデル類は MacBook Neo では動かさない。DGX Spark でホスト（config.toml の endpoint はプレースホルダ、ローカル Ollama は停止済み）
- 実測知見: 日本語+markdown のトークン膨張（3450字で 8192tok 超過→chunk 2000字＋段階切り詰め）。
  gold の深い miss ≈36% は概念的接続＝純ベクトルの射程外（Phase 2 GraphRAG / M2.5 FTS5+RRF の改善余地）
- **M4 完了**: 初回レポート `_Reports/suggest-20260703.md` 生成済み（較正 findings から上位5件）
- 次: **M5 週次運用**（compile → index → candidates → judge → report → 週末レビュー、採否を decisions.jsonl へ）。
  M6（Hermes/DGX 配線・LLM-jp-4）は O1/O10 待ち——配線後、凍結済み較正セットで回帰確認してから運用に載せる
