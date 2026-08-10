"""Pre-mortem: does it rank the empty cell above the full one?"""

import os
import unittest

from gossip import hazard
from gossip.canon import load_entries

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "canon")
LEDGER = os.path.join(FIXTURE, "tension-ledger.md")


class TestTags(unittest.TestCase):
    def setUp(self):
        self.entries = load_entries([FIXTURE])
        self.universe = hazard.tag_universe(self.entries)

    def test_counts_every_tag(self):
        self.assertEqual(self.universe["state"], len(self.entries))
        self.assertIn("determinism", self.universe)

    def test_exact_and_fuzzy_tags_resolve(self):
        known, unknown = hazard.resolve_tags(["state", "determin"], self.universe)
        self.assertEqual(known, ["state", "determinism"])
        self.assertEqual(unknown, [])

    def test_unknown_words_are_reported_not_guessed(self):
        known, unknown = hazard.resolve_tags(["state", "quantumfoo"], self.universe)
        self.assertEqual(known, ["state"])
        self.assertEqual(unknown, ["quantumfoo"])

    def test_duplicates_collapse(self):
        known, _ = hazard.resolve_tags(["state", "state"], self.universe)
        self.assertEqual(known, ["state"])


class TestBlindSpots(unittest.TestCase):
    def setUp(self):
        self.entries = load_entries([FIXTURE])

    def test_a_never_paired_combination_is_a_blind_spot(self):
        """`state` and `testing` co-occur here; a tag that meets neither does not."""
        cov = hazard.coverage(self.entries, ["state", "testing"])
        self.assertGreater(cov[("state", "testing")], 0)
        self.assertNotIn(("state", "testing"),
                         [p for p, _ in hazard.blind_spots(self.entries, ["state", "testing"])])

    def test_well_documented_holes_rank_above_obscure_ones(self):
        """Two heavily-used tags that never met is a bigger hole than two rare
        ones — the plan is combining things the project does constantly and has
        still never tested together."""
        entries = [
            {"tags": ["big1"] * 1, "block": "", "provenance": "", "file": "f", "id": "E1"},
        ]
        entries = [dict(tags=t, block="", provenance="Verified", file="f", id="E1")
                   for t in ([["big1"]] * 20 + [["big2"]] * 20 + [["rare1"], ["rare2"]])]
        holes = hazard.blind_spots(entries, ["big1", "big2", "rare1", "rare2"])
        self.assertEqual(holes[0][0], ("big1", "big2"))


class TestHazards(unittest.TestCase):
    def setUp(self):
        self.entries = load_entries([FIXTURE])

    def test_needs_two_matching_tags(self):
        self.assertEqual(hazard.hazards(self.entries, ["state"]), [])

    def test_a_recorded_failure_outranks_mere_coverage(self):
        covers = dict(tags=["x", "y"], block="- Rule of thumb: c", file="a.md",
                      id="E1", provenance="Verified first-hand.")
        bites = dict(tags=["x", "y"], block="- Where/why it failed: boom\n"
                                            "- Rule of thumb: b",
                     file="b.md", id="E1", provenance="Verified first-hand.")
        ranked = hazard.hazards([covers, bites], ["x", "y"])
        self.assertEqual(ranked[0][1]["file"], "b.md")

    def test_unverified_lessons_are_discounted_not_dropped(self):
        solid = dict(tags=["x", "y"], block="", file="a.md", id="E1",
                     provenance="Verified first-hand.")
        shaky = dict(tags=["x", "y"], block="", file="b.md", id="E1",
                     provenance="Assumed — never re-run.")
        ranked = hazard.hazards([solid, shaky], ["x", "y"])
        self.assertEqual([r[1]["file"] for r in ranked], ["a.md", "b.md"])
        self.assertEqual(len(ranked), 2)

    def test_deterministic(self):
        first = hazard.hazards(self.entries, ["state", "testing", "determinism"])
        again = hazard.hazards(self.entries, ["state", "testing", "determinism"])
        self.assertEqual([(s, e["id"]) for s, e, _ in first],
                         [(s, e["id"]) for s, e, _ in again])


class TestTensions(unittest.TestCase):
    def test_resolved_forks_are_not_surfaced(self):
        forks = hazard.open_tensions(["state", "audio"], LEDGER)
        heads = [h for h, _ in forks]
        self.assertTrue(any("state" in h.lower() for h in heads))
        self.assertFalse(any("🟢" in h or "⚪" in h for h in heads))

    def test_missing_ledger_is_not_an_error(self):
        self.assertEqual(hazard.open_tensions(["state"], "/nonexistent/ledger.md"), [])


if __name__ == "__main__":
    unittest.main()
