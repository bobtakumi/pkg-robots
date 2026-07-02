"""garden report — 提案レポート生成（実装プラン M4）。

findings（judge の link 判定）から上位数件を選び、Vault の
`_Reports/suggest-YYYYMMDD.md` に提案レポートを書く（plan/20 の形式を継承）。

Ch9 トーン: 少数（上限5件）・非一括・使い捨てレポート。リンクの実挿入は常に人間。
Vault への書き込みはこのファイルのみ（read+propose の唯一の例外パス）。
"""

import json
import sys
from datetime import date
from pathlib import Path

MAX_PROPOSALS = 5

HEADER = """---
type: report
title: "リンク提案 {today}（Connector robot）"
created: {today}
modified: {today}
tags: [report, PKG運用, suggest]
---

# リンク提案 {today} — Connector robot

> 週次のリンク提案（上限{cap}件）。**採否の判断とリンクの記入は常に人間**。
> このレポートは使い捨て——読んだらアーカイブ/削除してよい。採用する知識はリンクとして Vault に書く。
> 生成: pkg_robots `garden report`（判定: {judge_note}）
"""

ENTRY = """
## 候補{n}: [[{zettel}]] ⇄ [[{lit}]]（確度: {conf}/5・{relation}）

- 接続理由: {reason}
- zettel 側の根拠: 「{ev_z}」
- 文献側の根拠: 「{ev_l}」
- 提案リンク文（zettel 本文 or 文献索引ノートの `zettel_linked` へ・記入は人間）:
  - `[[{lit}]]`（{relation}）
"""


def run(cfg: dict, findings_path: Path | None, judge_note: str = "config の judge モデル") -> None:
    root: Path = cfg["_root"]
    src = findings_path or (root / "data" / "findings.json")
    findings = json.loads(src.read_text(encoding="utf-8"))
    links = [f for f in findings if f.get("verdict") == "link"]
    if not links:
        sys.exit("link 判定が0件。judge を先に実行すること")
    links.sort(key=lambda f: (-f.get("confidence", 0), -f.get("score", 0)))
    picked = links[:MAX_PROPOSALS]

    today = date.today().isoformat()
    parts = [HEADER.format(today=today, cap=MAX_PROPOSALS, judge_note=judge_note)]
    for i, f in enumerate(picked, 1):
        parts.append(ENTRY.format(
            n=i, zettel=f["zettel_title"], lit=f["lit_title"],
            conf=f.get("confidence", "?"), relation=f.get("relation", "?"),
            reason=f.get("reason", ""),
            ev_z=f.get("evidence_zettel", ""), ev_l=f.get("evidence_lit", "")))
    parts.append(f"\n---\n残り候補 {len(links) - len(picked)} 件は次回以降に持ち越し"
                 f"（少数・非一括の原則）。生成元 findings: `{src.name}`\n")

    out = Path(cfg["vault"]["path"]) / "_Reports" / f"suggest-{today.replace('-', '')}.md"
    out.write_text("".join(parts), encoding="utf-8")
    print(f"提案 {len(picked)} 件（link {len(links)} 件中）→ {out}")
