# pkg_robots — Robots in the Garden 実装（Phase 1）

PKG（`~/pkg_vault`）に対する Connector robot とその土台。設計・経緯は Vault 側の
`_Reports/2026-07-02 Robots実装プラン Phase1（インデクサ+Connector）.md` と
プロジェクトノート v4 を正とする。**Vault へは読み取り専用**（書き込みは `_Reports/suggest-YYYYMMDD.md` のみ、M4 で実装）。

## 使い方

```sh
python3 -m garden index            # 索引＋統計の全再構築（埋め込み込み。Ollama 未起動なら自動スキップ）
python3 -m garden index --no-embed # 埋め込みなし
python3 -m garden candidates       # M2（未実装）
python3 -m garden judge            # M3（未実装）
python3 -m garden report           # M4（未実装）
```

依存: Python 3.11+ 標準ライブラリのみ。設定は `config.toml`。出力は `data/`（git 管理外）。

## 状態（2026-07-02）

- M1 `garden index` 実装済み・受け入れ基準クリア（孤立 zettel 31 が手動計測と一致、zettel→文献リンク 5 が 6/26 レポート実測と一致）
- 埋め込み実行には Ollama + `bge-m3` の導入が必要（M0 の残作業。実行マシン＝MBP 想定）
- 次: `eval/gold_pairs.yaml`（6/26 レポートから較正データ化）→ M2 `candidates`
