"""Whisper: determinism, insertion-stability, and solvability by measurement."""

import json
import re
import unittest

from whisper import export, solver, world
from whisper.rng import Rng


class TestRng(unittest.TestCase):
    def test_same_address_same_value(self):
        a, b = Rng(4), Rng(4)
        self.assertEqual(a.unit("villager", 3, "trait"), b.unit("villager", 3, "trait"))

    def test_different_seed_different_value(self):
        self.assertNotEqual(Rng(1).unit("x"), Rng(2).unit("x"))

    def test_draws_do_not_depend_on_how_many_others_were_taken(self):
        """The property the whole module exists for. In an ordinal stream this
        fails: consuming extra draws shifts everything after them."""
        r = Rng(9)
        first = r.unit("villager", 7, "trait")
        for i in range(50):
            r.unit("noise", i)
        self.assertEqual(r.unit("villager", 7, "trait"), first)

    def test_shuffle_is_stable_under_insertion(self):
        """Adding a member must not reorder the others — the failure mode where
        one new item silently rewrites unrelated outcomes."""
        r = Rng(3)
        small = r.shuffled(["a", "b", "c"], "roster")
        big = r.shuffled(["a", "b", "c", "d"], "roster")
        self.assertEqual([x for x in big if x != "d"], small)

    def test_below_respects_bound(self):
        r = Rng(11)
        self.assertTrue(all(0 <= r.below(5, "i", i) < 5 for i in range(200)))

    def test_zero_bound_refused(self):
        with self.assertRaises(ValueError):
            Rng(1).below(0, "x")


class TestWorld(unittest.TestCase):
    def test_same_seed_is_byte_identical(self):
        self.assertEqual(solver.fingerprint(world.build(21)),
                         solver.fingerprint(world.build(21)))

    def test_different_seeds_differ(self):
        prints = {solver.fingerprint(world.build(s)) for s in range(30)}
        self.assertGreater(len(prints), 25)

    def test_each_fact_has_exactly_one_first_hand_witness(self):
        w = world.build(5)
        for fact in world.FACTS:
            firsts = [p for p in w["people"]
                      if w["beliefs"][p].get(fact, {}).get("first_hand")]
            self.assertEqual(len(firsts), 1, fact)

    def test_the_witness_holds_the_truth(self):
        w = world.build(5)
        for fact in world.FACTS:
            witness = next(p for p in w["people"]
                           if w["beliefs"][p].get(fact, {}).get("first_hand"))
            self.assertEqual(w["beliefs"][witness][fact]["value"], w["truth"][fact])

    def test_every_attribution_chain_terminates_at_the_witness(self):
        """No orphan beliefs and no cycles — the trace must always land."""
        for seed in range(40):
            w = world.build(seed)
            for person in w["people"]:
                for fact, held in w["beliefs"][person].items():
                    hops, cur = 0, person
                    while not w["beliefs"][cur][fact]["first_hand"]:
                        cur = w["beliefs"][cur][fact]["from"]
                        hops += 1
                        self.assertIsNotNone(cur)
                        self.assertLessEqual(hops, len(w["people"]))
                    self.assertEqual(w["beliefs"][cur][fact]["value"],
                                     w["truth"][fact])

    def test_distortion_stays_in_the_right_vocabulary(self):
        """A lie must be the same shape as the truth or it self-announces."""
        for seed in range(30):
            w = world.build(seed)
            for person in w["people"]:
                held = w["beliefs"][person]
                if "who" in held:
                    self.assertIn(held["who"]["value"], w["people"])
                if "where" in held:
                    self.assertIn(held["where"]["value"], world.PLACES)
                if "when" in held:
                    self.assertIn(held["when"]["value"], world.HOURS)

    def test_testimony_names_its_source(self):
        w = world.build(2)
        for claim in world.testimony(w, w["start"]):
            self.assertTrue(claim["first_hand"] or claim["from"])


class TestSolvability(unittest.TestCase):
    """The generator claims solvability; this re-derives it by playing."""

    def test_every_seed_in_the_sweep_is_solvable(self):
        report = solver.audit(range(300))
        self.assertEqual(report["solvable"], report["seeds"])

    def test_the_trace_fits_the_budget(self):
        report = solver.audit(range(300))
        self.assertLessEqual(report["max_interviews"], world.DEFAULT["budget"])

    def test_believing_the_village_is_a_losing_strategy(self):
        """The design target, held as a test. If a change makes consensus a
        winning play the puzzle has quietly stopped being about attribution."""
        report = solver.audit(range(300))
        self.assertLess(report["consensus_rate"], 0.45)

    def test_the_puzzle_is_not_trivially_short(self):
        report = solver.audit(range(300))
        self.assertGreater(report["mean_interviews"], 2.0)


class TestExport(unittest.TestCase):
    def test_placeholder_replaced_with_valid_json(self):
        page = export.render(range(5))
        self.assertNotIn("__WORLDS__", page)
        worlds = json.loads(re.search(r"const WORLDS = (\[.*?\]);\n", page, re.S).group(1))
        self.assertEqual(len(worlds), 5)

    def test_payload_carries_attribution_not_just_values(self):
        p = export.payload(3)
        held = p["beliefs"][p["start"]]
        self.assertTrue(any("f" in v or v.get("w") for v in held.values()))

    def test_deterministic(self):
        self.assertEqual(export.render(range(4)), export.render(range(4)))


if __name__ == "__main__":
    unittest.main()
