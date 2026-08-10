"""Printed reports. Every number here is recomputed from canon on each run."""

from . import community, confidence, seams
from .canon import short
from .graph import HEARSAY, WITNESS, components, entry_refs


def _bar(frac, width=28):
    filled = int(round(frac * width))
    return "█" * filled + "·" * (width - filled)


def summary(ctx):
    edges, scores = ctx["edges"], ctx["scores"]
    kept = {k: v for k, v in edges.items() if scores[k] > 0}
    vetoed = len(edges) - len(kept)
    part = ctx["partition"]
    sized = [g for g in part if len(g[1]) > 1]

    print(f"gossip — {len(ctx['entries'])} lessons · {len(ctx['node_tags'])} systems "
          f"· as of {ctx['asof']} (newest entry in canon)")
    print(f"  edges       : {len(edges)} mined · {len(kept)} confident · "
          f"{vetoed} vetoed (single hearsay assertion, T26)")
    w = sum(1 for e in edges.values() if e["witness"] and not e["hearsay"])
    h = sum(1 for e in edges.values() if e["hearsay"] and not e["witness"])
    m = len(edges) - w - h
    print(f"  provenance  : {w} witness-only · {h} hearsay-only · {m} mixed")
    print(f"  components  : {len(components(edges))} (brain's `groups`; "
          f"largest {len(components(edges)[0]) if edges else 0})")
    print(f"  communities : {len(sized)} of size>1 "
          f"(largest {len(sized[0][1]) if sized else 0}) · "
          f"Q={ctx['modularity']:.3f} · agreement={ctx['agreement']:.2f}")
    top = seams.rank(kept, ctx["node_tags"], ctx["node_entries"], limit=1)
    if top:
        _, a, b, sh, _ = top[0]
        print(f"  next seam   : {short(a)} + {short(b)} ({len(sh)} shared tags)")
    print("  (gossip <report> for detail: provenance · edges · communities · "
          "seams · compare)")


def provenance(ctx):
    edges = ctx["edges"]
    print("## edge provenance — declared composition vs mined name-drop\n")
    print("  witness : the entry's `Composed:` field named the other system")
    print("  hearsay : mined from prose, and may be an illustrative mention (T26)\n")

    w = sum(1 for e in edges.values() if e["witness"] and not e["hearsay"])
    h = sum(1 for e in edges.values() if e["hearsay"] and not e["witness"])
    m = len(edges) - w - h
    total = max(1, len(edges))
    for name, count in (("witness-only", w), ("mixed", m), ("hearsay-only", h)):
        print(f"  {name:13} {count:4}  {_bar(count / total)}  {count / total:5.1%}")

    veto = sorted(k for k, e in edges.items() if confidence.vetoed(e))
    print(f"\n  vetoed: {len(veto)} edge(s) asserted exactly once, by prose alone —")
    print("  the precise shape T26 describes. Listed, not silently dropped:\n")
    for a, b in veto[:20]:
        print(f"    {short(a)} — {short(b)}")
    if len(veto) > 20:
        print(f"    … and {len(veto) - 20} more")

    n_na = ctx["na_with_prose"]
    print(f"\n  `Composed: N/A` entries whose prose DOES cite another system: {n_na}")
    print("  brain reads the literal 'N/A' as a declaration and mines no prose for")
    print("  these; gossip treats it as absent and falls through. That is the only")
    print("  intake difference between the two tools.")


def edges_report(ctx):
    edges, scores = ctx["edges"], ctx["scores"]
    ranked = sorted(edges, key=lambda k: (-scores[k], k))
    print("## edges by confidence — witness × independence × corroboration × recency\n")
    print(f"  {'conf':>5}  {'w':>2} {'src':>3}  flags     pair\n")
    for key in ranked[:30]:
        e = edges[key]
        flags = []
        flags.append("W" if e["witness"] and not e["hearsay"] else
                     ("H" if e["hearsay"] and not e["witness"] else "M"))
        if e["safe"]:
            flags.append("safe")
        if len(e["sources"]) == 1:
            flags.append("1src")
        a, b = key
        print(f"  {scores[key]:5.3f}  {e['weight']:2} {len(e['sources']):3}  "
              f"{' '.join(flags):9} {short(a)} — {short(b)}")

    by_weight = sorted(edges, key=lambda k: (-edges[k]["weight"], k))[:10]
    by_conf = ranked[:10]
    moved = [k for k in by_weight if k not in by_conf]
    print(f"\n  top-10 by raw weight vs by confidence: {len(moved)} pair(s) drop out")
    for a, b in moved:
        print(f"    {short(a)} — {short(b)}  "
              f"(w={edges[(a, b)]['weight']}, sources={len(edges[(a, b)]['sources'])}, "
              f"conf={scores[(a, b)]:.3f})")


def communities(ctx):
    part = [g for g in ctx["partition"] if len(g[1]) > 1]
    comps = components(ctx["kept"])
    print("## communities — consensus of five deterministic traversals\n")
    print(f"  brain `groups` (connected components): {len(comps)} cluster(s), "
          f"largest {len(comps[0]) if comps else 0}")
    print(f"  gossip communities                  : {len(part)} cluster(s) of size>1, "
          f"largest {len(part[0][1]) if part else 0}")
    print(f"  modularity Q = {ctx['modularity']:.3f}   "
          f"traversal agreement = {ctx['agreement']:.2f}")
    print("  (only co-memberships every traversal found survive; the agreement "
          "number\n   is how much they disagreed underneath — 1.00 = the "
          "consensus cost nothing)\n")
    for i, (label, members) in enumerate(part, 1):
        print(f"  community {i} ({len(members)}) · anchor {short(label)}")
        for m in members:
            print(f"      {short(m)}")
        print()


def seams_report(ctx):
    kept = ctx["kept"]
    mine = seams.rank(kept, ctx["node_tags"], ctx["node_entries"], limit=15)
    theirs = seams.brain_rank(kept, ctx["node_tags"], limit=15)

    print("## seams — context × novelty × drama\n")
    print("  novelty = 1/(1+smaller reach): a recluse pulls the graph somewhere new")
    print("  drama   = share of the pair's lessons not yet verified first-hand\n")
    for score, a, b, shared, d in mine:
        print(f"  {score:5.2f}  {short(a)} + {short(b)}")
        print(f"         tags={len(shared)} reach={d['reach']} "
              f"drama={d['drama']:.2f} :: {' '.join(shared[:8])}")

    mine_pairs = [(a, b) for _, a, b, _, _ in mine]
    their_pairs = [(a, b) for _, a, b, _ in theirs]
    overlap = len(set(mine_pairs) & set(their_pairs))
    print(f"\n  overlap with brain's shared-tag ranking (top 15): {overlap}/15")
    if their_pairs:
        a, b = their_pairs[0]
        print(f"  brain's #1  : {short(a)} + {short(b)}  "
              f"(reach {seams.reach(kept).get(a, 0)}/{seams.reach(kept).get(b, 0)} "
              f"— both hubs)")
    if mine_pairs:
        a, b = mine_pairs[0]
        print(f"  gossip's #1 : {short(a)} + {short(b)}  "
              f"(reach {seams.reach(kept).get(a, 0)}/{seams.reach(kept).get(b, 0)})")


def compare(ctx):
    """The one-screen answer to 'does any of this change the picture?'"""
    edges, scores, kept = ctx["edges"], ctx["scores"], ctx["kept"]
    comps = components(edges)
    part = [g for g in ctx["partition"] if len(g[1]) > 1]

    rows = [
        ("edges", f"{len(edges)}", f"{len(kept)} confident"),
        ("clusters",
         f"{len(comps)} (largest {len(comps[0]) if comps else 0})",
         f"{len(part)} (largest {len(part[0][1]) if part else 0})"),
        ("cluster metric", "density (no threshold)", f"Q={ctx['modularity']:.3f}"),
        ("edge ranking", "raw weight", "confidence product"),
        ("single-source edges",
         f"{sum(1 for e in edges.values() if len(e['sources']) == 1)} counted equally",
         f"scored at {confidence.DEFAULTS['single_source']:.2f} independence"),
        ("hearsay handling", "indistinguishable from declared",
         f"{sum(1 for e in edges.values() if confidence.vetoed(e))} vetoed, rest discounted"),
    ]
    print("## brain analyze  vs  gossip\n")
    print(f"  {'':22} {'brain':38} gossip")
    for label, b, g in rows:
        print(f"  {label:22} {b:38} {g}")
    print(f"\n  traversal agreement underneath the gossip consensus: "
          f"{ctx['agreement']:.2f}")
    print("  (a single traversal is not printed at all — see community.py)")


def na_with_prose(entries, idx):
    """Entries whose `Composed:` is a literal N/A but whose prose cites systems."""
    from .canon import NULL_COMPOSED
    from .graph import prose_refs
    n = 0
    for e in entries:
        c = e["composed"].strip().lower()
        if c and c in NULL_COMPOSED and prose_refs(e, idx):
            n += 1
    return n


REPORTS = {
    "summary": summary,
    "provenance": provenance,
    "edges": edges_report,
    "communities": communities,
    "seams": seams_report,
    "compare": compare,
}
