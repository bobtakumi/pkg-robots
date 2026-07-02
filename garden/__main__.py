import argparse

from . import config, index


def main() -> None:
    ap = argparse.ArgumentParser(prog="garden", description="PKG robots CLI（実装プラン Phase 1）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_index = sub.add_parser("index", help="Vault を走査して索引・統計を全再構築（M1）")
    p_index.add_argument("--no-embed", action="store_true", help="埋め込みパスを省略")
    p_cand = sub.add_parser("candidates", help="埋め込み類似によるリンク候補生成（M2）")
    p_cand.add_argument("--eval", action="store_true", help="gold_pairs.yaml で recall を測定（O2 ゲート）")
    sub.add_parser("judge", help="LLM 判定（M3・未実装）")
    sub.add_parser("report", help="提案レポート生成（M4・未実装）")
    args = ap.parse_args()

    cfg = config.load()
    if args.cmd == "index":
        index.run(cfg, do_embed=not args.no_embed)
    elif args.cmd == "candidates":
        from . import candidates
        candidates.run(cfg, do_eval=args.eval)
    else:
        raise SystemExit(f"garden {args.cmd}: 未実装（実装プラン M3–M4 参照）")


main()
