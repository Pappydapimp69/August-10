"""A pre-mortem oracle: what the canon says will bite you, before you build it.

Everything else over this knowledge base is descriptive — `brain query` answers
"what do we know about X", `brain analyze` answers "what is the shape of what we
know". Both look backwards. Neither takes a plan as input.

`hazard` does. You name the tags of the thing you are about to build and it
answers three forward-looking questions:

  1. What has bitten this combination before?  Lessons whose tags overlap the
     plan, ranked so the ones that record an actual failure outrank the ones
     that merely mention the area.

  2. Where is the plan walking on untested ground?  Tag pairs in the plan that
     the canon has NEVER carried together. This is the part that matters: a pair
     with fifty recorded lessons is a solved area, and a pair with zero is not
     safe, it is unmeasured. The absence of evidence reads as reassurance in
     every retrieval tool that ranks by relevance, because nothing comes back.

  3. Which open forks touch it?  An unresolved tension over the plan's own
     ground is a decision the builder is about to make silently.

The ranking deliberately inverts the usual one. A retrieval tool sorts by how
much it found; a pre-mortem has to sort by how much is at stake, and the
emptiest cell in the matrix is the most dangerous one.
"""

import os
import re
from itertools import combinations

from .canon import field, is_verified, short

SEVERITY_FIELDS = ("where/why", "fix")


def tag_universe(entries):
    """Every tag in canon, with how many lessons carry it."""
    counts = {}
    for e in entries:
        for t in e["tags"]:
            counts[t] = counts.get(t, 0) + 1
    return counts


def resolve_tags(words, universe):
    """(known, unknown) — map free words onto real canon tags.

    Accepts exact tags and unambiguous substrings, so `hazard determinism audio`
    works without the caller memorising the tag vocabulary.
    """
    known, unknown = [], []
    for w in words:
        w = w.strip().lower()
        if not w:
            continue
        if w in universe:
            known.append(w)
            continue
        hits = sorted(t for t in universe if w in t or t in w)
        if len(hits) == 1:
            known.append(hits[0])
        else:
            unknown.append(w)
    seen, out = set(), []
    for t in known:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out, unknown


def coverage(entries, tags):
    """{(tag_a, tag_b): lessons carrying both} for every pair in the plan."""
    out = {}
    for a, b in combinations(sorted(tags), 2):
        out[(a, b)] = sum(1 for e in entries if a in e["tags"] and b in e["tags"])
    return out


def blind_spots(entries, tags, threshold=1):
    """Plan pairs the canon has never (or barely) carried together.

    Sorted by how well-trodden each side is on its own: a pair of two heavily
    documented tags that have never met is a bigger hole than two obscure ones,
    because the plan is combining things the project clearly does a lot of and
    has still never tested together.
    """
    universe = tag_universe(entries)
    cov = coverage(entries, tags)
    holes = [(pair, n) for pair, n in cov.items() if n <= threshold]
    return sorted(
        holes,
        key=lambda item: (-(universe.get(item[0][0], 0) + universe.get(item[0][1], 0)),
                          item[0]),
    )


def _bites(entry):
    """Does this lesson record an actual failure, or just cover the area?"""
    return bool(field(entry["block"], "where/why"))


def hazards(entries, tags, limit=12):
    """[(score, entry, matched_tags)] — lessons most likely to bite this plan."""
    wanted = set(tags)
    scored = []
    for e in entries:
        matched = wanted & set(e["tags"])
        if len(matched) < 2:
            continue
        score = len(matched)
        if _bites(e):
            score *= 2.0            # a recorded failure outranks mere coverage
        if not is_verified(e["provenance"]):
            score *= 0.75           # unconfirmed lessons still count, but less
        scored.append((score, e, sorted(matched)))
    scored.sort(key=lambda r: (-r[0], r[1]["file"], r[1]["id"]))
    return scored[:limit]


def open_tensions(tags, ledger_path):
    """Open forks whose heading touches the plan's vocabulary."""
    if not os.path.isfile(ledger_path):
        return []
    out = []
    with open(ledger_path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line.startswith("### "):
                continue
            head = line.strip("# \n")
            low = head.lower()
            if "🟢" in head or "⚪" in head:
                continue
            hits = sorted(t for t in tags if re.search(rf"\b{re.escape(t)}", low))
            if hits:
                out.append((head, hits))
    return out


def report(ctx, words, ledger_path=None):
    entries = ctx["entries"]
    universe = tag_universe(entries)
    tags, unknown = resolve_tags(words, universe)

    print(f"## pre-mortem — {' + '.join(tags) if tags else '(no known tags)'}\n")
    if unknown:
        print(f"  unrecognised: {', '.join(unknown)} "
              f"(canon knows {len(universe)} tags; try `gossip tags`)\n")
    if len(tags) < 2:
        print("  name at least two tags — the whole method is about what happens")
        print("  where they meet.")
        return

    print("  what the canon has on each pair of your plan:\n")
    cov = coverage(entries, tags)
    for (a, b), n in sorted(cov.items(), key=lambda i: (-i[1], i[0])):
        bar = "█" * min(30, n) if n else "·"
        print(f"    {n:4}  {bar:30} {a} + {b}")

    holes = blind_spots(entries, tags)
    print(f"\n  UNTESTED GROUND — {len(holes)} pair(s) the canon has never carried")
    print("  together. Not safe: unmeasured. A relevance-ranked search returns")
    print("  nothing here, which reads exactly like reassurance.\n")
    for (a, b), n in holes[:8]:
        print(f"    {a} + {b}   ({universe.get(a,0)} and {universe.get(b,0)} "
              f"lessons apiece, {n} together)")
    if not holes:
        print("    (none — every pair in this plan has been exercised before)")

    print("\n  what has bitten this combination before:\n")
    for score, e, matched in hazards(entries, tags):
        rule = field(e["block"], "rule of thumb") or field(e["block"], "what")
        mark = "!" if _bites(e) else " "
        print(f"   {mark} [{'+'.join(matched)}] {short(e['file'])}#{e['id']}")
        print(f"     {rule[:150]}{'…' if len(rule) > 150 else ''}")

    ledger = ledger_path or os.path.expanduser("~/.brain/Tension/tension-ledger.md")
    forks = open_tensions(tags, ledger)
    if forks:
        print(f"\n  open forks over your ground ({len(forks)}) — decisions you are")
        print("  about to make silently unless you make them deliberately:\n")
        for head, hits in forks[:6]:
            print(f"    [{'+'.join(hits)}] {head[:110]}")
