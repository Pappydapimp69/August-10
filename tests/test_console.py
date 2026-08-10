"""The interactive page: does the default keep private prose out?"""

import json
import os
import re
import unittest

from gossip import console
from gossip.cli import context

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "canon")
LEDGER = os.path.join(FIXTURE, "tension-ledger.md")


class TestPayload(unittest.TestCase):
    def setUp(self):
        self.ctx = context([FIXTURE])

    def test_default_embeds_no_lesson_text(self):
        """The disclosure boundary, pinned. A default that leaks is an accident
        nobody made; a flag you must set is a decision someone made."""
        p = console.payload(self.ctx, LEDGER)
        self.assertFalse(p["prose"])
        self.assertTrue(all("r" not in row for row in p["entries"]))
        self.assertTrue(all("h" not in fork for fork in p["forks"]))

    def test_flag_opts_into_prose(self):
        p = console.payload(self.ctx, LEDGER, include_prose=True)
        self.assertTrue(p["prose"])
        self.assertTrue(any("r" in row for row in p["entries"]))

    def test_entry_ids_survive_either_mode(self):
        """A citation must stay actionable through `brain query`."""
        for prose in (False, True):
            p = console.payload(self.ctx, LEDGER, include_prose=prose)
            self.assertTrue(all(row["i"].startswith("E") and row["p"] for row in p["entries"]))

    def test_tags_ordered_by_frequency(self):
        p = console.payload(self.ctx, LEDGER)
        self.assertEqual(p["counts"], sorted(p["counts"], reverse=True))

    def test_flags_are_recorded(self):
        p = console.payload(self.ctx, LEDGER)
        self.assertTrue(all(row["b"] in (0, 1) and row["v"] in (0, 1) for row in p["entries"]))

    def test_resolved_forks_excluded(self):
        p = console.payload(self.ctx, LEDGER, include_prose=True)
        self.assertTrue(all("🟢" not in f.get("h", "") for f in p["forks"]))


class TestRender(unittest.TestCase):
    def setUp(self):
        self.ctx = context([FIXTURE])

    def test_placeholder_is_replaced_with_valid_json(self):
        html = console.render(self.ctx, LEDGER)
        self.assertNotIn("__DATA__", html)
        data = json.loads(re.search(r"const D = (\{.*?\});\n", html, re.S).group(1))
        self.assertEqual(len(data["entries"]), len(self.ctx["entries"]))

    def test_deterministic(self):
        self.assertEqual(console.render(self.ctx, LEDGER),
                         console.render(self.ctx, LEDGER))


if __name__ == "__main__":
    unittest.main()
