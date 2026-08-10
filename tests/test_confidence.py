"""Scoring: the veto, and the four factors it multiplies."""

import unittest

from gossip import confidence


def edge(weight=1, sources=1, witness=1, hearsay=0, newest="2026-08-01", safe=False):
    return {
        "weight": weight,
        "sources": {f"src{i}.md" for i in range(sources)},
        "witness": witness,
        "hearsay": hearsay,
        "newest": newest,
        "safe": safe,
    }


ASOF = "2026-08-01"


class TestVeto(unittest.TestCase):
    def test_single_hearsay_assertion_is_vetoed(self):
        """T26's exact shape: asserted once, by prose alone."""
        self.assertTrue(confidence.vetoed(edge(weight=1, witness=0, hearsay=1)))
        self.assertEqual(confidence.score(edge(weight=1, witness=0, hearsay=1), ASOF), 0.0)

    def test_single_declared_assertion_survives(self):
        e = edge(weight=1, witness=1, hearsay=0)
        self.assertFalse(confidence.vetoed(e))
        self.assertGreater(confidence.score(e, ASOF), 0.0)

    def test_corroborated_hearsay_survives_discounted(self):
        """T20 is open; a weak edge is scored low, never deleted by fiat."""
        e = edge(weight=2, sources=2, witness=0, hearsay=2)
        self.assertFalse(confidence.vetoed(e))
        self.assertGreater(confidence.score(e, ASOF), 0.0)
        self.assertLess(confidence.score(e, ASOF),
                        confidence.score(edge(weight=2, sources=2, witness=2), ASOF))

    def test_a_zero_factor_collapses_the_product(self):
        """The reason the combination is multiplicative at all."""
        strong = edge(weight=9, sources=9, witness=9, safe=True)
        self.assertGreater(confidence.score(strong, ASOF), 0.8)
        crippled = dict(strong, weight=1, sources={"a.md"}, witness=0, hearsay=1)
        self.assertEqual(confidence.score(crippled, ASOF), 0.0)


class TestFactors(unittest.TestCase):
    def test_independence_rises_with_distinct_sources(self):
        cfg = confidence.DEFAULTS
        vals = [confidence.independence_factor(edge(sources=n), cfg) for n in (1, 2, 5, 20)]
        self.assertEqual(vals, sorted(vals))
        self.assertAlmostEqual(vals[0], cfg["single_source"])
        self.assertLess(vals[-1], 1.0)

    def test_witness_beats_hearsay_monotonically(self):
        cfg = confidence.DEFAULTS
        pure_hearsay = confidence.witness_factor(edge(witness=0, hearsay=4), cfg)
        mixed = confidence.witness_factor(edge(witness=2, hearsay=2), cfg)
        pure_witness = confidence.witness_factor(edge(witness=4, hearsay=0), cfg)
        self.assertLess(pure_hearsay, mixed)
        self.assertLess(mixed, pure_witness)
        self.assertAlmostEqual(pure_witness, 1.0)

    def test_recency_decays_but_never_to_zero(self):
        cfg = confidence.DEFAULTS
        fresh = confidence.recency_factor(edge(newest="2026-08-01"), ASOF, cfg)
        stale = confidence.recency_factor(edge(newest="2025-01-01"), ASOF, cfg)
        self.assertAlmostEqual(fresh, 1.0)
        self.assertAlmostEqual(stale, cfg["recency_floor"])
        self.assertGreater(stale, 0.0)

    def test_safe_edges_do_not_decay(self):
        """`non-decaying-pivotal-events`: a confirmed-compatible pair is pivotal."""
        cfg = confidence.DEFAULTS
        ancient_safe = confidence.recency_factor(
            edge(newest="2020-01-01", safe=True), ASOF, cfg)
        ancient_plain = confidence.recency_factor(
            edge(newest="2020-01-01", safe=False), ASOF, cfg)
        self.assertEqual(ancient_safe, 1.0)
        self.assertLess(ancient_plain, ancient_safe)

    def test_single_source_dial_is_the_open_fork(self):
        """T20 is unresolved, so the weight it turns on stays a parameter."""
        e = edge(weight=3, sources=1, witness=3)
        lenient = confidence.score(e, ASOF, {"single_source": 1.0})
        strict = confidence.score(e, ASOF, {"single_source": 0.1})
        self.assertGreater(lenient, strict)


class TestScoreAll(unittest.TestCase):
    def test_confident_filters_only_vetoed_at_floor_zero(self):
        edges = {
            ("a", "b"): edge(weight=1, witness=0, hearsay=1),   # vetoed
            ("a", "c"): edge(weight=1, witness=1),
        }
        kept, scores = confidence.confident(edges, ASOF)
        self.assertEqual(sorted(kept), [("a", "c")])
        self.assertEqual(scores[("a", "b")], 0.0)

    def test_scoring_is_pure(self):
        e = edge(weight=4, sources=3, witness=4)
        self.assertEqual(confidence.score(e, ASOF), confidence.score(e, ASOF))


if __name__ == "__main__":
    unittest.main()
