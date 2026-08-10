"""An independent check that the puzzle can actually be won.

`world.build` constructs the chain to be traceable. This module never looks at
that construction — it plays the game the way a player does, from the starting
villager, following only attribution pointers, spending interviews — and reports
whether the truth is reachable inside the budget.

Two independent routes to the same claim is the entire point. A generator that
also certifies itself certifies its own bugs, and the way this fails is silent:
an unsolvable board looks exactly as rich as a solvable one, so nothing surfaces
until a player is already stuck in it. The seed sweep in the tests is what turns
"designed to be solvable" into "measured solvable over 300 seeds".
"""

from .world import FACTS


def trace(world, fact="who"):
    """Interviews an ideal player needs to reach the first-hand witness.

    Returns (reached, path). The player starts at `world["start"]`, and may only
    move to someone an interview actually named — no omniscient jumping.
    """
    beliefs = world["beliefs"]
    person = world["start"]
    path = [person]
    seen = {person}

    while True:
        held = beliefs.get(person, {}).get(fact)
        if held is None:
            return False, path
        if held["first_hand"]:
            return True, path
        nxt = held["from"]
        if nxt is None or nxt in seen:
            return False, path
        person, path = nxt, path + [nxt]
        seen.add(nxt)
        if len(path) > len(world["people"]):
            return False, path


def solvable(world, fact="who"):
    """Is the witness reachable within the interview budget?"""
    reached, path = trace(world, fact)
    return reached and len(path) <= world["config"]["budget"]


def interviews_needed(world, fact="who"):
    reached, path = trace(world, fact)
    return len(path) if reached else None


def popular_answer(world, fact="who"):
    """What the village as a whole believes — the trap.

    A mutation close to the source is inherited by everyone downstream, so the
    widely-held answer carries no more evidential weight than the one person it
    came from. Measured across seeds, it is wrong often enough that playing by
    consensus loses.
    """
    tally = {}
    for person in world["people"]:
        held = world["beliefs"][person].get(fact)
        if held:
            tally[held["value"]] = tally.get(held["value"], 0) + 1
    if not tally:
        return None
    return min(sorted(tally), key=lambda v: (-tally[v], v))


def audit(seeds, config=None):
    """Sweep seeds and report the properties the design claims."""
    from .world import build

    total = solved = consensus_right = 0
    lengths = []
    for seed in seeds:
        world = build(seed, config)
        total += 1
        if solvable(world):
            solved += 1
            lengths.append(interviews_needed(world))
        if popular_answer(world) == world["truth"]["who"]:
            consensus_right += 1
    return {
        "seeds": total,
        "solvable": solved,
        "solvable_rate": solved / total if total else 0.0,
        "consensus_right": consensus_right,
        "consensus_rate": consensus_right / total if total else 0.0,
        "mean_interviews": sum(lengths) / len(lengths) if lengths else 0.0,
        "max_interviews": max(lengths) if lengths else 0,
    }


def fingerprint(world):
    """A canonical hash of the whole world, for golden/regression tests.

    Sorted keys and a fixed separator before hashing: a dict that serialises in
    a different key order is the same world, and a fingerprint that disagrees
    about that reports drift on every unrelated refactor until people stop
    trusting it.
    """
    import hashlib
    import json

    payload = json.dumps(
        {k: v for k, v in world.items() if k != "config"},
        sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
