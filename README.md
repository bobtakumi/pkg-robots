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

- **M0–M2 完了**。索引 2,589チャンク全埋め込み・候補生成・recall 評価基盤（`eval/build_gold.py` / `eval/rank_diag.py`）が動作
- **O2 決着**: `bge-m3-8k` 採用（recall@10=51.1% / @30=63.8%）。ruri-large は 512tok 制約→600字チャンクで 25.5% に劣後
- 実測知見: 日本語+markdown はトークン膨張が激しく 3450字で 8192tok を超過 → chunk 2000字＋400時の段階切り詰めフォールバック
- gold の深い miss ≈36% は語彙が重ならない概念的接続＝純ベクトルの射程外（Phase 2 GraphRAG / M2.5 FTS5+RRF の定量的改善余地）
- 次: **M3 `garden judge`**（`prompts/connector_judge.md` の Ch7 原則文はユーザー記入）→ M4 `garden report`
