"""正解ペアの順位分布診断。recall ゲート不合格時の切り分け用（M2）。

「惜しい miss（rank 11-30 → top_k 拡大で救える）」と
「深い miss（概念的接続 → 埋め込み以外のチャネルが必要）」を分けて数える。
usage: .venv/bin/python eval/rank_diag.py
"""

import collections
import re
import sqlite3
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
from garden import config
from garden.candidates import load_vectors, parse_gold


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s)


def main() -> None:
    cfg = config.load()
    con = sqlite3.connect(cfg["_root"] / cfg["index"]["db_path"])
    zettel, lit = load_vectors(con)
    model = con.execute("SELECT embed_model FROM chunks WHERE embed_model IS NOT NULL LIMIT 1").fetchone()
    print(f"model: {model[0] if model else '?'} / zettel {len(zettel)} / 文献チャンク {len(lit)}\n")

    z_by_title = {norm(r[1]): i for i, r in enumerate(zettel)}
    z_mat = np.stack([r[4] for r in zettel])
    l_mat = np.stack([r[4] for r in lit])
    z_mat /= np.linalg.norm(z_mat, axis=1, keepdims=True)
    l_mat /= np.linalg.norm(l_mat, axis=1, keepdims=True)
    sim = z_mat @ l_mat.T

    gold = parse_gold(Path(__file__).parent / "gold_pairs.yaml")
    ranks = []
    for g in gold:
        zi = z_by_title.get(norm(g["zettel"]))
        if zi is None:
            ranks.append((None, g))
            continue
        best: dict[str, float] = {}
        for li, s in enumerate(sim[zi]):
            t = norm(lit[li][1])
            if s > best.get(t, -1.0):
                best[t] = float(s)
        order = sorted(best, key=lambda t: -best[t])
        pos = [order.index(norm(t)) + 1 for t in g["targets"] if norm(t) in best]
        ranks.append((min(pos) if pos else None, g))

    buckets = collections.Counter()
    for r, _g in ranks:
        buckets["top10" if r and r <= 10 else "r11-30" if r and r <= 30
                else "r31-100" if r and r <= 100 else "r>100" if r else "不在"] += 1
    n = len(ranks)
    r10 = buckets["top10"]
    r30 = r10 + buckets["r11-30"]
    print(f"recall@10 = {r10/n:.1%} / recall@30 = {r30/n:.1%} / 分布 {dict(buckets)}")
    print("\n-- top-10 圏外 --")
    for r, g in sorted(ranks, key=lambda x: x[0] or 9999):
        if not r or r > 10:
            print(f"rank={r} {g['zettel'][:30]} → {g['targets'][0][:44]}")


main()
