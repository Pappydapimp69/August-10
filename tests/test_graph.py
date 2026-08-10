"""Edge intake: what counts as a composition, and who said so."""

import os
import unittest

from gossip.canon import load_entries, slug_index
from gossip.graph import HEARSAY, WITNESS, build, entry_refs, prose_refs

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "canon")


def fixture():
    entries = load_entries([FIXTURE])
    return entries, slug_index([FIXTURE])


def by_id(entries, fn, eid):
    return next(e for e in entries if e["file"] == fn and e["id"] == eid)


class TestRefs(unittest.TestCase):
    def test_declared_field_is_witness(self):
        entries, idx = fixture()
        refs, kind = entry_refs(by_id(entries, "local__alpha.md", "E1"), idx)
        self.assertEqual(kind, WITNESS)
        self.assertEqual(refs, {"local__beta.md", "local__gamma.md"})

    def test_prose_only_is_hearsay(self):
        entries, idx = fixture()
        refs, kind = entry_refs(by_id(entries, "local__gamma.md", "E1"), idx)
        self.assertEqual(kind, HEARSAY)
        self.assertEqual(refs, {"local__delta.md"})

    def test_na_composed_falls_through_to_prose(self):
        """The one intake difference from brain, pinned so it cannot drift."""
        entries, idx = fixture()
        entry = by_id(entries, "local__delta.md", "E1")
        self.assertEqual(entry["composed"], "N/A")
        self.assertEqual(prose_refs(entry, idx), {"local__epsilon.md"})
        refs, kind = entry_refs(entry, idx)
        self.assertEqual((refs, kind), ({"local__epsilon.md"}, HEARSAY))

    def test_na_with_no_prose_yields_nothing(self):
        entries, idx = fixture()
        refs, _ = entry_refs(by_id(entries, "local__beta.md", "E1"), idx)
        self.assertEqual(refs, set())


class TestBuild(unittest.TestCase):
    def setUp(self):
        entries, idx = fixture()
        self.edges, self.tags, self.node_entries = build(entries, idx)

    def test_declared_triple_makes_three_edges(self):
        for pair in (("local__alpha.md", "local__beta.md"),
                     ("local__alpha.md", "local__gamma.md"),
                     ("local__beta.md", "local__gamma.md")):
            self.assertIn(pair, self.edges)

    def test_second_project_raises_independence(self):
        """delta/E1 and delta/E2 both assert delta-epsilon, from one file."""
        edge = self.edges[("local__delta.md", "local__epsilon.md")]
        self.assertEqual(edge["weight"], 2)
        self.assertEqual(len(edge["sources"]), 1)
        self.assertEqual((edge["witness"], edge["hearsay"]), (1, 1))

    def test_repeated_assertion_from_one_file_does_not_add_a_source(self):
        edge = self.edges[("local__alpha.md", "local__beta.md")]
        self.assertEqual(edge["weight"], 2)          # alpha E1 and E2
        self.assertEqual(len(edge["sources"]), 1)    # both from alpha

    def test_safe_requires_both_ends_named_in_got_right(self):
        self.assertTrue(self.edges[("local__alpha.md", "local__beta.md")]["safe"])
        self.assertFalse(self.edges[("local__alpha.md", "local__gamma.md")]["safe"])

    def test_tags_propagate_to_referenced_systems(self):
        self.assertIn("determinism", self.tags["local__gamma.md"])

    def test_newest_date_tracked(self):
        self.assertEqual(
            self.edges[("local__alpha.md", "local__beta.md")]["newest"], "2026-07-20")


if __name__ == "__main__":
    unittest.main()
