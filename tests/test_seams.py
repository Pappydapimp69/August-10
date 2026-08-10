"""Seam ranking: does the recluse actually win?"""

import unittest

from gossip import seams

# hub--hub and hub--recluse, with identical shared context, so the only thing
# separating them in the ranking is reach. Keys are sorted, as `graph.build`
# emits them.
EDGES = {
    ("hub_a", "n1"): None, ("hub_a", "n2"): None, ("hub_a", "n3"): None,
    ("hub_b", "n1"): None, ("hub_b", "n2"): None, ("hub_b", "n4"): None,
    ("n5", "recluse"): None,
}
TAGS = {
    "hub_a": {"state", "testing", "gamedev"},
    "hub_b": {"state", "testing", "gamedev"},
    "recluse": {"state", "testing", "gamedev"},
    "n1": {"state"}, "n2": {"state"}, "n3": {"state"},
    "n4": {"state"}, "n5": {"state", "testing", "gamedev"},
    # in the tag map but in no edge — neither end is proven ground
    "cold_x": {"state", "testing", "gamedev"},
    "cold_y": {"state", "testing", "gamedev"},
}


def entries(unverified, total):
    return ([{"provenance": "Assumed — never re-run."}] * unverified
            + [{"provenance": "Verified first-hand."}] * (total - unverified))


NODE_ENTRIES = {
    "hub_a": entries(1, 10), "hub_b": entries(1, 10),
    "recluse": entries(1, 10), "n5": entries(1, 10),
    "n1": entries(0, 1), "n2": entries(0, 1),
    "n3": entries(0, 1), "n4": entries(0, 1),
    "cold_x": entries(1, 1), "cold_y": entries(1, 1),
}


class TestRank(unittest.TestCase):
    def test_recluse_outranks_the_hub_pair_on_equal_context(self):
        ranked = seams.rank(EDGES, TAGS, NODE_ENTRIES, limit=None)
        pairs = [(a, b) for _, a, b, _, _ in ranked]
        self.assertIn(("hub_a", "recluse"), pairs)
        self.assertIn(("hub_a", "hub_b"), pairs)
        self.assertLess(pairs.index(("hub_a", "recluse")), pairs.index(("hub_a", "hub_b")))

    def test_brains_ranking_cannot_separate_them(self):
        """Same context, same in-graph bonus — shared-tag ranking is blind here."""
        theirs = {(a, b): s for s, a, b, _ in
                  seams.brain_rank(EDGES, TAGS, limit=None)}
        self.assertEqual(theirs[("hub_a", "recluse")], theirs[("hub_a", "hub_b")])

    def test_drama_breaks_ties_toward_unsettled_material(self):
        settled = dict(NODE_ENTRIES, recluse=entries(0, 10))
        unsettled = dict(NODE_ENTRIES, recluse=entries(10, 10))

        def score_of(node_entries):
            return next(s for s, a, b, _, _ in
                        seams.rank(EDGES, TAGS, node_entries, limit=None)
                        if (a, b) == ("hub_a", "recluse"))

        self.assertGreater(score_of(unsettled), score_of(settled))

    def test_pair_drama_is_volume_aware(self):
        """max() of two ratios saturates; the combined share does not."""
        dramas = {"big": (10, 10), "small": (0, 100)}
        self.assertAlmostEqual(seams.pair_drama(dramas, "big", "small"), 10 / 110)

    def test_cold_pairs_are_excluded(self):
        """Brain's precondition, kept: extend proven ground, don't start cold.

        cold_x and cold_y share three tags and would otherwise rank at the very
        top — both have reach 0, so novelty is maximal. Neither has ever been
        co-verified with anything, so the pair has no proven ground to extend.
        """
        pairs = {(a, b) for _, a, b, _, _ in
                 seams.rank(EDGES, TAGS, NODE_ENTRIES, limit=None)}
        self.assertNotIn(("cold_x", "cold_y"), pairs)
        self.assertIn(("cold_x", "hub_a"), pairs)   # one warm end is enough

    def test_already_tested_pairs_are_excluded(self):
        pairs = {(a, b) for _, a, b, _, _ in seams.rank(EDGES, TAGS, NODE_ENTRIES, limit=None)}
        self.assertFalse(pairs & set(EDGES))

    def test_deterministic(self):
        first = seams.rank(EDGES, TAGS, NODE_ENTRIES, limit=None)
        self.assertEqual(seams.rank(EDGES, TAGS, NODE_ENTRIES, limit=None), first)


if __name__ == "__main__":
    unittest.main()
