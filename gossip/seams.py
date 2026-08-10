"""Which untested pair to test next.

`brain analyze seams` ranks candidate pairs by shared-tag count, +1 if both ends
are already in the graph. That ranking has a bias built into it: the more
connected a system already is, the more tags it has accumulated, so the top of
the list fills with hub-hub pairs. The current #1 is `brain + opticon` — the two
most-connected systems in the canon. Pairing two hubs is the *least* surprising
experiment available.

The correction comes from `ideas`: *reach-and-drama-as-independent-axes /
the-recluse-is-the-loudest-choice*. Reach (how widely connected) and drama (how
much unsettled material a system carries) are separate, and the loud choice is
the low-reach one. So a seam is scored on three independent axes:

  context   shared tags — without common ground the pair cannot be co-tested
  novelty   1 / (1 + smaller reach) — a recluse pulls the graph somewhere new
  drama     share of the pair's lessons NOT yet verified first-hand

Drama is what makes the ranking pay rent twice: a seam over unverified lessons,
when tested, retires entries from `analyze provenance`'s 41-item worklist at the
same time as it adds an edge. Shared-tag ranking cannot see that at all.
"""

from itertools import combinations

from .canon import is_verified
from .graph import adjacency

DEFAULT_MIN_SHARED_TAGS = 2


def reach(edges):
    """Distinct confident neighbours per node."""
    adj = adjacency(edges)
    return {n: len(nbrs) for n, nbrs in adj.items()}


def drama(node_entries):
    """(unverified, total) lessons per system.

    Kept as counts rather than a ratio because a seam's drama has to be measured
    over the pair's COMBINED body of lessons. Taking max() of two per-system
    ratios saturates at 1.00 for every pair touching any wholly-unverified
    system — measured on the live canon, that pinned the entire top fifteen to
    drama=1.00 and collapsed the axis the ranking was supposed to separate.
    """
    out = {}
    for fn, entries in node_entries.items():
        unverified = sum(1 for e in entries if not is_verified(e["provenance"]))
        out[fn] = (unverified, len(entries))
    return out


def pair_drama(dramas, a, b):
    """Share of the pair's combined lessons still awaiting confirmation — i.e.
    how much recorded-but-unconfirmed material this one experiment puts on the
    line. Volume counts: ten unsettled lessons are a louder target than one."""
    ua, ta = dramas.get(a, (0, 0))
    ub, tb = dramas.get(b, (0, 0))
    total = ta + tb
    return (ua + ub) / total if total else 0.0


def rank(edges, node_tags, node_entries, min_shared=DEFAULT_MIN_SHARED_TAGS, limit=15):
    """[(score, a, b, shared_tags, detail)] for untested pairs, best first."""
    reaches = reach(edges)
    dramas = drama(node_entries)
    in_graph = set(reaches)
    tested = set(edges)

    ranked = []
    for a, b in combinations(sorted(node_tags), 2):
        if (a, b) in tested:
            continue
        # keep brain's precondition: extend proven ground, don't start cold
        if a not in in_graph and b not in in_graph:
            continue
        shared = sorted(node_tags[a] & node_tags[b])
        if len(shared) < min_shared:
            continue

        context = float(len(shared))
        novelty = 1.0 / (1.0 + min(reaches.get(a, 0), reaches.get(b, 0)))
        pd = pair_drama(dramas, a, b)
        score = context * novelty * (0.25 + pd)

        ranked.append((score, a, b, shared, {
            "context": context,
            "novelty": novelty,
            "drama": pd,
            "reach": (reaches.get(a, 0), reaches.get(b, 0)),
        }))

    ranked.sort(key=lambda r: (-r[0], r[1], r[2]))
    return ranked[:limit] if limit else ranked


def brain_rank(edges, node_tags, min_shared=DEFAULT_MIN_SHARED_TAGS, limit=15):
    """Brain's own seam ranking, reimplemented so the two can be diffed."""
    in_graph = set(adjacency(edges))
    tested = set(edges)
    ranked = []
    for a, b in combinations(sorted(node_tags), 2):
        if (a, b) in tested:
            continue
        if a not in in_graph and b not in in_graph:
            continue
        shared = sorted(node_tags[a] & node_tags[b])
        if len(shared) < min_shared:
            continue
        score = len(shared) + (1 if a in in_graph and b in in_graph else 0)
        ranked.append((score, a, b, shared))
    ranked.sort(key=lambda r: (-r[0], r[1], r[2]))
    return ranked[:limit] if limit else ranked
