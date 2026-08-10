"""The co-verification graph, with every edge carrying its provenance.

Brain mines an edge and forgets where it came from. Tension **T26** is open on
exactly the cost of that: an entry that name-drops another system as an
*illustrative example* is indistinguishable, downstream, from one that genuinely
composed against it. So gossip keeps the distinction the whole way:

    witness  — the reference was DECLARED, in the entry's `Composed:` field
    hearsay  — the reference was MINED from prose, and may be a name-drop

This is the `ideas` kernel *rumor as traveling token, not broadcast:
witness -> carry -> mutate*, applied to the graph that kernel lives in.

One deliberate departure from `brain`: brain tests `if composed:` truthily, so an
entry written `Composed: N/A` takes the declared branch, resolves nothing, and
suppresses prose mining entirely. gossip treats `N/A` as *absent* and falls
through to prose. The count of entries this changes is reported by
`gossip provenance`, so the departure is visible rather than assumed harmless.
"""

import re
from itertools import combinations

from .canon import NULL_COMPOSED, resolve_slug

WITNESS = "witness"
HEARSAY = "hearsay"


def declared_refs(entry, idx):
    """Files named in an explicit `Composed:` field."""
    composed = entry["composed"]
    if composed.strip().lower() in NULL_COMPOSED:
        return set()
    files = set()
    for tok in re.split(r"[,\s]+", composed):
        slug = re.sub(r"\.md$", "", re.split(r"[/#]", tok)[0])
        f = resolve_slug(slug, idx) if slug else None
        if f:
            files.add(f)
    files.discard(entry["file"])
    return files


def prose_refs(entry, idx):
    """Files mined from the entry's prose — the same three shapes brain mines."""
    block = entry["block"]
    files = set()
    patterns = (
        r"([a-z][a-z0-9-]{2,})/E\d+",
        r"([a-z][a-z0-9-]{2,})'s\s+[^.]{0,80}?\(E\d+",
        r"([a-z][a-z0-9-]{2,})\.md#E\d+",
    )
    for pat in patterns:
        for slug in re.findall(pat, block):
            f = resolve_slug(slug, idx)
            if f:
                files.add(f)
    files.discard(entry["file"])
    return files


def entry_refs(entry, idx):
    """(files, kind) — declared references win; prose is the fallback."""
    declared = declared_refs(entry, idx)
    if declared:
        return declared, WITNESS
    return prose_refs(entry, idx), HEARSAY


def build(entries, idx):
    """Undirected graph keyed by sorted (file_a, file_b).

    Each edge records how many entries assert it, how many DISTINCT source files
    do (`sources` — T20's independence question), the witness/hearsay split, the
    newest supporting date, and whether some entry's `Got right` names both ends
    (a positive/compatible edge rather than merely a co-tested one).
    """
    edges = {}
    node_tags = {}
    node_entries = {}

    for entry in entries:
        node_tags.setdefault(entry["file"], set()).update(entry["tags"])
        node_entries.setdefault(entry["file"], []).append(entry)

        refs, kind = entry_refs(entry, idx)
        if not refs:
            continue
        for f in refs:
            node_tags.setdefault(f, set()).update(entry["tags"])

        parts = sorted(refs | {entry["file"]})
        gotright = entry["gotright"].lower()
        for a, b in combinations(parts, 2):
            rec = edges.setdefault((a, b), {
                "weight": 0,
                "sources": set(),
                "witness": 0,
                "hearsay": 0,
                "newest": "",
                "safe": False,
            })
            rec["weight"] += 1
            rec["sources"].add(entry["file"])
            rec[kind] += 1
            if entry["date"] > rec["newest"]:
                rec["newest"] = entry["date"]
            if _both_named_in(a, b, gotright):
                rec["safe"] = True

    return edges, node_tags, node_entries


def _both_named_in(a, b, text):
    """Does `text` name both endpoints? Matches brain's `safe` heuristic."""
    if not text:
        return False
    for fn in (a, b):
        slug = fn.split("__")[-1][:-3]
        if slug not in text and slug.replace("sandbox-", "") not in text:
            return False
    return True


def adjacency(edges):
    adj = {}
    for a, b in edges:
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    return adj


def components(edges):
    """Connected components — what brain calls `groups`. Kept for comparison."""
    adj = adjacency(edges)
    seen, comps = set(), []
    for node in sorted(adj):
        if node in seen:
            continue
        stack, comp = [node], set()
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            comp.add(cur)
            stack.extend(sorted(adj[cur] - seen))
        comps.append(comp)
    return sorted(comps, key=lambda c: (-len(c), sorted(c)[0]))
