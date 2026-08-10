"""Communities: determinism within a run, steadiness across runs.

The across-run half is measured against the real canon when it is present, and
skipped when it is not, so the suite still runs on a machine with no ~/.brain.
"""

import os
import unittest

from gossip import community, confidence
from gossip.canon import load_entries, slug_index
from gossip.graph import build

CANON = os.path.expanduser("~/.brain/memory")
HAVE_CANON = os.path.isdir(os.path.join(CANON, "projects"))

# two tight triangles joined by one thin bridge — the shape connected components
# cannot tell apart from a single blob
EDGES = {
    ("a", "b"): None, ("b", "c"): None, ("a", "c"): None,
    ("d", "e"): None, ("e", "f"): None, ("d", "f"): None,
    ("c", "d"): None,
}
SCORES = {
    ("a", "b"): 0.9, ("b", "c"): 0.9, ("a", "c"): 0.9,
    ("d", "e"): 0.9, ("e", "f"): 0.9, ("d", "f"): 0.9,
    ("c", "d"): 0.05,
}


class TestDetect(unittest.TestCase):
    def test_splits_what_components_cannot(self):
        from gossip.graph import components
        self.assertEqual(len(components(EDGES)), 1)
        part = community.detect(EDGES, SCORES)
        self.assertEqual(len(part), 2)
        self.assertEqual([sorted(m) for _, m in part],
                         [["a", "b", "c"], ["d", "e", "f"]])

    def test_deterministic_across_repeated_runs(self):
        first = community.detect(EDGES, SCORES)
        for _ in range(5):
            self.assertEqual(community.detect(EDGES, SCORES), first)

    def test_unambiguous_graph_needs_no_consensus(self):
        """When every traversal agrees, the consensus costs nothing."""
        self.assertEqual(community.agreement(EDGES, SCORES), 1.0)

    def test_consensus_never_asserts_more_than_a_traversal_found(self):
        """The defining guarantee: a printed co-membership was found by ALL
        traversals, so it can never be an artefact of any one of them."""
        consensus = community.copairs(
            {n: lb for lb, members in community.detect(EDGES, SCORES) for n in members})
        for order in community.traversals(EDGES, SCORES):
            from gossip.graph import adjacency
            run = community._propagate(order, adjacency(EDGES), SCORES)
            self.assertTrue(consensus <= community.copairs(run))

    def test_modularity_beats_the_single_blob(self):
        split = community.modularity(EDGES, SCORES, community.detect(EDGES, SCORES))
        blob = community.modularity(EDGES, SCORES, [("all", sorted({n for e in EDGES for n in e}))])
        self.assertGreater(split, blob)
        self.assertAlmostEqual(blob, 0.0, places=9)

    def test_zero_confidence_edges_do_not_bind(self):
        scores = dict(SCORES)
        scores[("c", "d")] = 0.0
        part = community.detect(EDGES, scores)
        members = {lb: set(m) for lb, m in part}
        self.assertEqual(sorted(len(m) for m in members.values()), [3, 3])


class TestChurn(unittest.TestCase):
    def test_identical_partitions_have_no_churn(self):
        lb = {"a": "x", "b": "x", "c": "y"}
        self.assertEqual(community.churn(lb, dict(lb)), 0.0)

    def test_relabelling_alone_is_not_churn(self):
        """Labels are node names and will change; relationships are what matter."""
        before = {"a": "a", "b": "a", "c": "c"}
        after = {"a": "b", "b": "b", "c": "c"}
        self.assertEqual(community.churn(before, after), 0.0)

    def test_a_split_registers_as_churn(self):
        before = {"a": "a", "b": "a", "c": "a"}
        after = {"a": "a", "b": "a", "c": "c"}
        self.assertGreater(community.churn(before, after), 0.0)

    def test_nodes_absent_from_one_run_are_ignored(self):
        before = {"a": "a", "b": "a"}
        after = {"a": "a", "b": "a", "z": "z"}
        self.assertEqual(community.churn(before, after), 0.0)


@unittest.skipUnless(HAVE_CANON, "no ~/.brain/memory on this machine")
class TestAgainstRealCanon(unittest.TestCase):
    """The two claims the design rests on, measured on the live graph."""

    @classmethod
    def setUpClass(cls):
        cls.entries = load_entries([CANON])
        cls.idx = slug_index([CANON])

    def partition(self, entries, asof, prior=None, margin=0.0):
        """The shipped path — consensus, flattened back to {node: label}."""
        edges, _, _ = build(entries, self.idx)
        kept, scores = confidence.confident(edges, asof)
        part = community.detect(kept, scores, prior, margin)
        return {n: lb for lb, members in part for n in members}

    def test_a_single_traversal_would_not_have_been_trustworthy(self):
        """The measurement that forced the consensus design. One traversal
        agrees with another on roughly half its co-memberships; printing any
        one of them as 'the communities' would be presenting a coin-flip."""
        edges, _, _ = build(self.entries, self.idx)
        kept, scores = confidence.confident(edges, "2026-08-05")
        self.assertLess(community.agreement(kept, scores), 0.9)

    def test_consensus_is_deterministic_on_real_canon(self):
        edges, _, _ = build(self.entries, self.idx)
        kept, scores = confidence.confident(edges, "2026-08-05")
        first = community.detect(kept, scores)
        self.assertEqual(community.detect(kept, scores), first)

    def test_consensus_holds_only_what_every_traversal_found(self):
        from gossip.graph import adjacency
        edges, _, _ = build(self.entries, self.idx)
        kept, scores = confidence.confident(edges, "2026-08-05")
        consensus = community.copairs(
            {n: lb for lb, members in community.detect(kept, scores) for n in members})
        adj = adjacency(kept)
        for order in community.traversals(kept, scores):
            run = community.copairs(community._propagate(order, adj, scores))
            self.assertTrue(consensus <= run)

    def test_prior_reduces_churn_as_canon_grows(self):
        """Canon growth simulated by date truncation — the axis that oscillates."""
        for cutoff in ("2026-07-13", "2026-07-20", "2026-07-26", "2026-08-01"):
            older = [e for e in self.entries if e["date"] and e["date"][:10] <= cutoff]
            before = self.partition(older, cutoff)
            free = community.churn(before, self.partition(self.entries, "2026-08-05"))
            held = community.churn(
                before,
                self.partition(self.entries, "2026-08-05", prior=before, margin=0.2))
            with self.subTest(cutoff=cutoff):
                self.assertLess(held, free)

    def test_communities_are_not_one_blob(self):
        from gossip.graph import components
        edges, _, _ = build(self.entries, self.idx)
        kept, scores = confidence.confident(edges, "2026-08-05")
        self.assertEqual(len(components(kept)), 1)          # brain's view
        sized = [g for g in community.detect(kept, scores) if len(g[1]) > 1]
        self.assertGreater(len(sized), 1)                   # gossip's


if __name__ == "__main__":
    unittest.main()
