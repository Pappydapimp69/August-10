"""Command line. `gossip [report] [--canon DIR] [--asof YYYY-MM-DD] ...`"""

import argparse
import json
import os
import sys

from . import community, confidence, report
from .canon import load_entries, newest_date, slug_index
from .graph import build

DEFAULT_CANON = os.path.expanduser("~/.brain/memory")


def context(canon_dirs, asof=None, cfg=None, margin=community.DEFAULT_MARGIN,
            prior=None):
    """Everything every report needs, computed once."""
    entries = load_entries(canon_dirs)
    idx = slug_index(canon_dirs)
    edges, node_tags, node_entries = build(entries, idx)
    asof = asof or newest_date(entries)

    kept, scores = confidence.confident(edges, asof, cfg)
    partition = community.detect(kept, scores, prior, margin)

    return {
        "entries": entries,
        "idx": idx,
        "edges": edges,
        "kept": kept,
        "scores": scores,
        "node_tags": node_tags,
        "node_entries": node_entries,
        "asof": asof,
        "partition": partition,
        "modularity": community.modularity(kept, scores, partition),
        "agreement": community.agreement(kept, scores, prior, margin),
        "na_with_prose": report.na_with_prose(entries, idx),
    }


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="gossip",
        description="Read Brain's co-verification graph as a social network.",
    )
    p.add_argument("report", nargs="?", default="summary",
                   choices=sorted(report.REPORTS), help="which report to print")
    p.add_argument("--canon", action="append", default=None,
                   help=f"canon base holding projects/ (default {DEFAULT_CANON})")
    p.add_argument("--asof", default=None,
                   help="date for recency decay (default: newest entry in canon)")
    p.add_argument("--margin", type=float, default=community.DEFAULT_MARGIN,
                   help="across-run hysteresis: how hard a node resists leaving "
                        "the community --prior left it in (no effect without one)")
    p.add_argument("--prior", default=None,
                   help="partition from an earlier run, to hold the report steady "
                        "as canon grows (written by --save-prior)")
    p.add_argument("--save-prior", default=None,
                   help="write this run's partition for a later --prior")
    p.add_argument("--half-life", type=float, default=None,
                   help="recency half-life in days")
    p.add_argument("--single-source", type=float, default=None,
                   help="independence weight for a one-project edge (T20's dial)")
    args = p.parse_args(argv)

    canon = args.canon or [DEFAULT_CANON]
    missing = [d for d in canon if not os.path.isdir(os.path.join(d, "projects"))]
    if missing:
        print(f"gossip: no projects/ under {', '.join(missing)}", file=sys.stderr)
        return 2

    cfg = {}
    if args.half_life is not None:
        cfg["half_life_days"] = args.half_life
    if args.single_source is not None:
        cfg["single_source"] = args.single_source

    prior = None
    if args.prior:
        if not os.path.isfile(args.prior):
            print(f"gossip: no prior partition at {args.prior}", file=sys.stderr)
            return 2
        with open(args.prior, encoding="utf-8") as fh:
            prior = json.load(fh)

    ctx = context(canon, args.asof, cfg or None, args.margin, prior)
    report.REPORTS[args.report](ctx)

    if args.save_prior:
        flat = {n: lb for lb, members in ctx["partition"] for n in members}
        with open(args.save_prior, "w", encoding="utf-8") as fh:
            json.dump(flat, fh, indent=1, sort_keys=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
