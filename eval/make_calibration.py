"""較正セット生成（M3）: candidates.json から判定対象ペアを層化抽出し、
判定に必要な全テキストを同梱した eval/calibration_export.json を書き出す。

構成: gold 一致ペア（正例期待・最大20）＋ 非 gold をスコア帯で層化（高/中/低 × 各5）。
judge 役（較正時は Claude、本配線後は LLM-jp-4）はこのファイルだけで判定できる。
"""

import json
import random
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from garden import config
from garden.candidates import parse_gold
from garden.judge import fetch_pair_texts


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s)


def main() -> None:
    cfg = config.load()
    root = cfg["_root"]
    cands = json.loads((root / "data" / "candidates.json").read_text(encoding="utf-8"))
    gold = parse_gold(Path(__file__).parent / "gold_pairs.yaml")
    gold_set = {(norm(g["zettel"]), norm(t)) for g in gold for t in g["targets"]}

    for c in cands:
        c["gold"] = (norm(c["zettel_title"]), norm(c["lit_title"])) in gold_set

    gold_hits = [c for c in cands if c["gold"]]
    nongold = sorted((c for c in cands if not c["gold"]), key=lambda c: -c["score"])
    n = len(nongold)
    rng = random.Random(42)
    strata = (rng.sample(nongold[: n // 3], 5)
              + rng.sample(nongold[n // 3: 2 * n // 3], 5)
              + rng.sample(nongold[2 * n // 3:], 5))
    picked = gold_hits[:20] + strata
    # 較正 v1 の教訓: 選択順のまま ID を振ると cal-00..19=gold と分かってしまう。
    # 判定者へのバイアス防止のため ID 割当前にシャッフルする
    rng.shuffle(picked)

    con = sqlite3.connect(root / cfg["index"]["db_path"])
    export = []
    for i, p in enumerate(picked):
        z_body, chunks = fetch_pair_texts(con, p["zettel_path"], p["lit_path"],
                                          p.get("best_chunk_seq"))
        export.append({
            "id": f"cal-{i:02d}", "gold": p["gold"], "score": p["score"],
            "zettel_title": p["zettel_title"], "zettel_path": p["zettel_path"],
            "zettel_body": z_body,
            "lit_title": p["lit_title"], "lit_path": p["lit_path"],
            "chunks": [c[:1800] for c in chunks],
        })
    out = Path(__file__).parent / "calibration_export.json"
    out.write_text(json.dumps(export, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"較正セット {len(export)} ペア（gold {len(gold_hits[:20])} / 非gold {len(strata)}）→ {out}")


main()
