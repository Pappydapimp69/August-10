"""How much an edge is worth believing.

Brain ranks edges by raw weight — how many entries mention the pair. That treats
nine independent confirmations and one entry repeated nine times as the same
fact, and it is the reason `analyze graph`'s top list is dominated by whichever
project wrote the most.

The scoring here is **multiplicative**, straight off the `ideas` kernel
*multiplicative-combination-preserves-vetoes / one-zero-collapses-the-whole-
score*. Four factors, each in (0, 1], each traceable to a recorded lesson:

  witness       T26 — declared beats mined
  independence  T20 — how many DISTINCT projects assert it
  corroboration       repetition within a project is worth something, not much
  recency             recency-weighted retrieval, with one exception

The exception is the good part. *non-decaying-pivotal-events-scoped-per-
relationship / traumatic-memories-dont-fade* says some memories are exempt from
decay. The graph's pivotal event is a `Got right` that names both systems — a
pair confirmed COMPATIBLE, not merely co-tested. Those edges do not decay.

And one hard veto, which is the whole point of choosing a multiplicative form:
an edge asserted by exactly one entry, by hearsay alone, scores 0. That is
precisely the shape T26 describes — a single illustrative name-drop — and it is
the only configuration where the graph has no evidence of composition at all.
Every other weak edge is *scored* low, not deleted: T20 is an OPEN fork, and a
tool has no business closing it by fiat.
"""

from .canon import days_between

DEFAULTS = {
    "hearsay_weight": 0.40,   # floor for a fully-mined edge that IS corroborated
    "single_source": 0.50,    # independence of a one-project edge (T20's dial)
    "half_life_days": 45.0,   # recency half-life
    "recency_floor": 0.25,    # age alone never drives an edge to nothing
}


def witness_factor(edge, cfg):
    """Share of assertions that were declared rather than mined."""
    total = edge["witness"] + edge["hearsay"]
    if not total:
        return cfg["hearsay_weight"]
    declared = edge["witness"] / total
    return cfg["hearsay_weight"] + (1.0 - cfg["hearsay_weight"]) * declared


def independence_factor(edge, cfg):
    """Distinct asserting projects. One project vouching for itself is the
    weakest admissible evidence; each further independent source approaches 1."""
    div = len(edge["sources"])
    if div <= 1:
        return cfg["single_source"]
    return 1.0 - (1.0 - cfg["single_source"]) / div


def corroboration_factor(edge, cfg):
    """Repetition inside an already-counted project: a real but small signal."""
    extra = edge["weight"] - len(edge["sources"])
    return min(1.0, 0.85 + 0.05 * extra)


def recency_factor(edge, asof, cfg):
    """Half-life decay, floored — except a `safe` edge, which never fades."""
    if edge["safe"]:
        return 1.0
    age = days_between(edge["newest"], asof)
    decayed = 0.5 ** (age / cfg["half_life_days"]) if cfg["half_life_days"] > 0 else 1.0
    return max(cfg["recency_floor"], decayed)


def vetoed(edge):
    """The one configuration with no evidence of composition: asserted once,
    by prose alone. See T26."""
    return edge["weight"] == 1 and edge["witness"] == 0


def score(edge, asof, cfg=None):
    cfg = {**DEFAULTS, **(cfg or {})}
    if vetoed(edge):
        return 0.0
    return (
        witness_factor(edge, cfg)
        * independence_factor(edge, cfg)
        * corroboration_factor(edge, cfg)
        * recency_factor(edge, asof, cfg)
    )


def score_all(edges, asof, cfg=None):
    """{edge_key: confidence} for every edge, vetoed ones included at 0.0."""
    return {key: score(edge, asof, cfg) for key, edge in edges.items()}


def confident(edges, asof, cfg=None, floor=0.0):
    """The surviving graph: edges scoring strictly above `floor`."""
    scores = score_all(edges, asof, cfg)
    return {k: v for k, v in edges.items() if scores[k] > floor}, scores
