"""Communities that are actually communities.

`brain analyze groups` takes connected components of the edge graph. On this
canon that returns ONE cluster of 98 systems at density 0.06 — technically
correct and informationally empty. A single shared entry welds two otherwise
unrelated subgraphs together permanently, and connected components has no way to
say so.

The replacement is confidence-weighted label propagation. Determinism is not
incidental: canonical label propagation breaks ties at random, which would make
every run disagree with the last. Nodes are visited in sorted order and ties
break on the lexicographically smallest label, so a given canon has exactly one
answer. `stability()` re-runs under a reversed visit order and reports the
agreement rate, because a partition that moves when you walk the nodes backwards
has not found real structure.

## Where the hysteresis went, and why

This module first applied the kernel *thrashing-oscillation-hysteresis-fixes /
require-a-real-margin-before-switching* to the propagation loop: a node adopts a
neighbour's label only if it wins by a margin. Measured, that made things worse,
and the convergence counts said why — every margin, including 0, settles in 4-6
rounds. There is no oscillation in this graph at all, so the margin has no
thrashing to damp and its only remaining effect is to pin each node to whichever
label it met first. That is the visit order. Hysteresis did not stabilise the
answer; it laundered an arbitrary ordering into it.

The kernel is not wrong, it was aimed at the wrong axis. Its precondition is
oscillation, and what oscillates here is **time**: the report re-shuffling every
time canon grows between syncs. So the margin applies *across runs* — a node
keeps its prior community unless a challenger beats it by a real margin — and
within a run propagation is greedy.

## Why one traversal is not enough

Greedy propagation is still order-dependent: on the live graph a single
alphabetical pass agrees with its own reversal on only about half of its
co-memberships. Turning that into a printed cluster list would be presenting a
coin-flip as structure.

The fix is the tool's own thesis turned on itself. gossip refuses to trust an
edge asserted by one source; a partition found by one traversal deserves exactly
the same skepticism. So the graph is clustered under several deterministic
traversals and only co-memberships that **every** traversal agrees on survive.
What gets printed is the consensus, and `agreement()` reports how much the
individual runs disagreed underneath it — uncertainty shown, not smoothed away.
"""

from .graph import adjacency

DEFAULT_MARGIN = 0.20
MAX_ROUNDS = 50


def _propagate(nodes, adj, scores, prior=None, margin=0.0, rounds=MAX_ROUNDS):
    """Greedy weighted label propagation.

    `prior` is a {node: label} partition from an earlier run. Where it exists, a
    node must be beaten by `margin` to leave the community it was already in;
    everywhere else the update is greedy. That confines the hysteresis to the
    across-run axis, which is the one that oscillates.
    """
    prior = prior or {}
    label = {n: prior.get(n, n) for n in nodes}
    for _ in range(rounds):
        moved = 0
        for node in nodes:
            pull = {}
            for nb in sorted(adj.get(node, ())):
                key = (node, nb) if node < nb else (nb, node)
                w = scores.get(key, 0.0)
                if w > 0.0:
                    pull[label[nb]] = pull.get(label[nb], 0.0) + w
            if not pull:
                continue
            current = label[node]
            best = min(sorted(pull), key=lambda lb: (-pull[lb], lb))
            if best == current:
                continue
            # sticky only while the node still sits where the last run left it
            required = margin if prior.get(node) == current else 0.0
            if pull[best] > pull.get(current, 0.0) * (1.0 + required):
                label[node] = best
                moved += 1
        if not moved:
            break
    return label


def _strength(edges, scores):
    out = {}
    for (a, b) in edges:
        w = scores.get((a, b), 0.0)
        out[a] = out.get(a, 0.0) + w
        out[b] = out.get(b, 0.0) + w
    return out


def traversals(edges, scores):
    """The fixed set of deterministic visit orders the consensus runs over.

    Chosen to disagree: alphabetical both ways, plus hubs-first and hubs-last by
    degree and by summed confidence. If a co-membership survives all five it is
    not an artefact of any one of them.
    """
    adj = adjacency(edges)
    nodes = sorted(adj)
    strength = _strength(edges, scores)
    return [
        nodes,
        list(reversed(nodes)),
        sorted(nodes, key=lambda n: (-len(adj[n]), n)),
        sorted(nodes, key=lambda n: (len(adj[n]), n)),
        sorted(nodes, key=lambda n: (-strength.get(n, 0.0), n)),
    ]


def labels(edges, scores, prior=None, margin=DEFAULT_MARGIN, rounds=MAX_ROUNDS):
    """{node: community label} from the single alphabetical traversal.

    The raw, order-dependent view. `detect()` is what callers want; this is kept
    for measuring how much any one traversal differs from the consensus.
    """
    adj = adjacency(edges)
    return _propagate(sorted(adj), adj, scores, prior, margin, rounds)


def detect(edges, scores, prior=None, margin=DEFAULT_MARGIN, rounds=MAX_ROUNDS,
           agreement=1.0):
    """[(label, sorted members)], largest first.

    Consensus over `traversals()`: a pair shares a community only if at least
    `agreement` of the traversals put it together. The surviving pairs are then
    closed transitively, so the result is a partition. Fully deterministic — the
    traversal set is fixed and the tally does not depend on its order.
    """
    adj = adjacency(edges)
    runs = [_propagate(order, adj, scores, prior, margin, rounds)
            for order in traversals(edges, scores)]

    tally = {}
    for run in runs:
        for pair in copairs(run):
            tally[pair] = tally.get(pair, 0) + 1

    threshold = agreement * len(runs)
    agreed = {p for p, n in tally.items() if n >= threshold}

    parent = {n: n for n in sorted(adj)}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in sorted(agreed):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    groups = {}
    for node in sorted(parent):
        groups.setdefault(find(node), []).append(node)
    return sorted(
        ((lb, sorted(members)) for lb, members in groups.items()),
        key=lambda item: (-len(item[1]), item[0]),
    )


def agreement(edges, scores, prior=None, margin=DEFAULT_MARGIN, rounds=MAX_ROUNDS):
    """Mean pairwise agreement between the individual traversals.

    This is the uncertainty the consensus is absorbing. 1.0 means every
    traversal found the same thing and the consensus was free; a low number
    means the printed communities are the hard core of a much vaguer picture,
    and should be read as such.
    """
    adj = adjacency(edges)
    runs = [copairs(_propagate(order, adj, scores, prior, margin, rounds))
            for order in traversals(edges, scores)]
    pairs, total = 0, 0.0
    for i, x in enumerate(runs):
        for y in runs[i + 1:]:
            total += _jaccard(x, y)
            pairs += 1
    return total / pairs if pairs else 1.0


def copairs(label, nodes=None):
    """The set of node pairs sharing a community — the identity-free view of a
    partition, so two runs can be compared without matching label names."""
    buckets = {}
    for n in sorted(label):
        if nodes is not None and n not in nodes:
            continue
        buckets.setdefault(label[n], []).append(n)
    out = set()
    for members in buckets.values():
        for i, a in enumerate(members):
            for b in members[i + 1:]:
                out.add((a, b))
    return out


def _jaccard(x, y):
    union = x | y
    return len(x & y) / len(union) if union else 1.0


def churn(before, after):
    """Co-membership churn between two runs, over the nodes present in both.

    0.0 = every surviving pair kept its relationship; 1.0 = the report was
    rewritten. This is the number the across-run margin exists to hold down.
    """
    shared = set(before) & set(after)
    if not shared:
        return 0.0
    return 1.0 - _jaccard(copairs(before, shared), copairs(after, shared))


def modularity(edges, scores, partition):
    """Newman modularity of a partition under the confidence weights.

    Reported so the split can be compared against brain's components on one
    number rather than on how the printout feels. Q near 0 means the partition
    is no better than chance; higher is real structure.
    """
    member = {}
    for label, members in partition:
        for n in members:
            member[n] = label

    total = sum(scores.get(k, 0.0) for k in edges)
    if total <= 0:
        return 0.0

    degree = {}
    for (a, b) in edges:
        w = scores.get((a, b), 0.0)
        degree[a] = degree.get(a, 0.0) + w
        degree[b] = degree.get(b, 0.0) + w

    q = sum(scores.get(k, 0.0) for k in edges
            if member.get(k[0]) == member.get(k[1])) / total
    for label in {lb for lb, _ in partition}:
        deg = sum(degree.get(n, 0.0) for n in member if member[n] == label)
        q -= (deg / (2.0 * total)) ** 2
    return q
