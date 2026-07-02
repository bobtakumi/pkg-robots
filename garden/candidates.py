"""garden candidates — 埋め込み類似によるリンク候補生成（実装プラン M2）。

純機械パス（LLM 不使用）。第一弾は層跨ぎ（zettel × 文献ノート）のみ。
--eval で eval/gold_pairs.yaml（6/26 レポート由来）に対する top-k recall を測定する。
この recall ≥ 0.8 が埋め込みモデル選定（O2）のゲート。
"""

import json
import re
import sqlite3
import sys
from pathlib import Path

import numpy as np


def load_vectors(con: sqlite3.Connection):
    rows = con.execute(
        """SELECT c.note_path, n.title, n.layer, c.heading, c.text, c.embedding
           FROM chunks c JOIN notes n ON n.path = c.note_path
           WHERE c.embedding IS NOT NULL"""
    ).fetchall()
    zettel, lit = [], []
    for path, title, layer, heading, text, emb in rows:
        rec = (path, title, heading, text, np.array(json.loads(emb), dtype=np.float32))
        if layer == "zettel":
            zettel.append(rec)
        elif layer in ("literature_section", "literature_index") and "/Archive/" not in path:
            lit.append(rec)
    return zettel, lit


def existing_pairs(con: sqlite3.Connection) -> set[tuple[str, str]]:
    """zettel⇄文献の既存リンク（双方向）を (zettel_path, lit_path) で返す。"""
    pairs = set()
    for src, resolved in con.execute(
        "SELECT src, resolved_path FROM links WHERE resolved_path IS NOT NULL"
    ):
        a, b = sorted([src, resolved])
        for z, l in ((src, resolved), (resolved, src)):
            if z.startswith("2_Permanent/Zettelkasten/") and l.startswith("1_Literature/"):
                pairs.add((z, l))
    return pairs


def rejected_pairs(root: Path) -> set[tuple[str, str]]:
    f = root / "data" / "decisions.jsonl"
    if not f.exists():
        return set()
    out = set()
    for line in f.read_text(encoding="utf-8").splitlines():
        d = json.loads(line)
        if d.get("human") == "rejected":
            out.add((d["zettel_path"], d["lit_path"]))
    return out


def generate(cfg: dict) -> list[dict]:
    root: Path = cfg["_root"]
    con = sqlite3.connect(root / cfg["index"]["db_path"])
    zettel, lit = load_vectors(con)
    if not zettel or not lit:
        sys.exit("埋め込みが空。Ollama を起動して `garden index` を先に実行すること")
    skip = existing_pairs(con) | rejected_pairs(root)
    con.close()

    z_mat = np.stack([r[4] for r in zettel])
    l_mat = np.stack([r[4] for r in lit])
    z_mat /= np.linalg.norm(z_mat, axis=1, keepdims=True)
    l_mat /= np.linalg.norm(l_mat, axis=1, keepdims=True)
    sim = z_mat @ l_mat.T  # (n_zettel, n_lit_chunks)

    top_k = cfg["candidates"]["top_k"]
    min_sim = cfg["candidates"]["min_similarity"]
    results = []
    for zi, (z_path, z_title, _h, _t, _v) in enumerate(zettel):
        # ノートレベル類似度 = チャンク類似度の max
        best: dict[str, tuple[float, int]] = {}
        for li, s in enumerate(sim[zi]):
            path = lit[li][0]
            if s > best.get(path, (-1.0, -1))[0]:
                best[path] = (float(s), li)
        ranked = sorted(best.items(), key=lambda kv: -kv[1][0])[:top_k]
        for lit_path, (score, li) in ranked:
            if score < min_sim or (z_path, lit_path) in skip:
                continue
            _p, l_title, heading, text, _v2 = lit[li]
            results.append({
                "zettel_path": z_path, "zettel_title": z_title,
                "lit_path": lit_path, "lit_title": l_title,
                "score": round(score, 4), "best_chunk_heading": heading,
                "best_chunk_excerpt": re.sub(r"\s+", " ", text)[:200],
            })
    results.sort(key=lambda r: -r["score"])
    out = root / "data" / "candidates.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"候補 {len(results)} ペア（zettel {len(zettel)} × 文献チャンク {len(lit)}、"
          f"top_k={top_k}, θ={min_sim}）→ {out.relative_to(root)}")
    return results


def parse_gold(path: Path) -> list[dict]:
    """gold_pairs.yaml の positives を読む（自前生成の固定形式のみ対応）。"""
    entries, cur = [], None
    in_pos = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("positives:"):
            in_pos = True
            continue
        if in_pos and line and not line.startswith(" "):
            break
        m = re.match(r'  - zettel: "(.*)"$', line)
        if m:
            cur = {"zettel": m.group(1), "targets": []}
            entries.append(cur)
            continue
        m = re.match(r'      - "(.*)"$', line)
        if m and cur is not None:
            cur["targets"].append(m.group(1))
    return entries


def _norm(s: str) -> str:
    """表記ゆれ対策: 空白を無視して比較（例: 「CUDA バックエンド」vs「CUDAバックエンド」）。"""
    return re.sub(r"\s+", "", s)


def evaluate(cfg: dict, results: list[dict]) -> None:
    root: Path = cfg["_root"]
    gold = parse_gold(root / "eval" / "gold_pairs.yaml")
    top_by_zettel: dict[str, set[str]] = {}
    for r in results:
        top_by_zettel.setdefault(_norm(r["zettel_title"]), set()).add(_norm(r["lit_title"]))

    hits, misses, skipped = [], [], []
    for g in gold:
        cands = top_by_zettel.get(_norm(g["zettel"]))
        if cands is None:
            skipped.append(g["zettel"])  # 索引に無い（改名等）or 候補ゼロ
            continue
        if any(_norm(t) in cands for t in g["targets"]):
            hits.append(g["zettel"])
        else:
            misses.append(g)
    n_eval = len(hits) + len(misses)
    recall = len(hits) / n_eval if n_eval else 0.0
    print(f"\n== recall ゲート（O2）== 正解 {len(gold)} 件中 評価対象 {n_eval}（対象外 {len(skipped)}）")
    print(f"top-{cfg['candidates']['top_k']} recall = {recall:.1%} {'✓ 合格(≥80%)' if recall >= 0.8 else '✗ 不合格(<80%)'}")
    for g in misses:
        print(f"  miss: {g['zettel']} → {g['targets']}")
    for z in skipped:
        print(f"  skip: {z}（候補ゼロ or 索引に不在）")


def run(cfg: dict, do_eval: bool) -> None:
    results = generate(cfg)
    if do_eval:
        evaluate(cfg, results)
