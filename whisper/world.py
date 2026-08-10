"""A village, a thing that happened, and what everyone thinks they know.

The design question is not "how do I distort testimony" — that part is easy and
produces an unplayable mush. It is: **how do I guarantee the puzzle can be
solved at all**, and know it rather than hope it.

Randomly seeding witnesses and letting rumour spread gives puzzles that are
sometimes unsolvable, and the failure is invisible from the inside — the board
looks exactly as rich as a solvable one. That is the same trap as scattering a
key uniformly over a generated level and shipping ~20% unsolvable seeds: matching
the *appearance* of a good distribution is not the property you need. So the
chain to each fact is **constructed** to be traceable within the interview
budget, and `solver.py` then re-derives that independently over a seed sweep.
Construction guarantees it; the solver is what makes the guarantee checkable.

## The mechanic

Three facts are true about the incident: WHO, WHERE, WHEN. For each fact one
villager is a **witness** — they hold the true value, first-hand. Everyone else
who knows anything holds it as **hearsay**: a value they got from a specific
person, which may have mutated in transit.

Every belief therefore carries the name of whoever supplied it. That pointer is
the whole game. A hearsay claim is worthless on its own and decisive as a step:
follow the attribution back far enough and you reach someone who was actually
there. Majority opinion is a trap — a mutation near the source propagates to
everyone downstream, so the popular answer is often the wrong one, held
confidently, by many.
"""

from .rng import Rng

NAMES = [
    "Alder", "Bryn", "Cass", "Dessa", "Edric", "Fen", "Gale", "Harrow",
    "Isolde", "Jory", "Kell", "Lune", "Mira", "Nyle", "Orla", "Perrin",
    "Quill", "Rook", "Sable", "Thorn",
]
PLACES = [
    "the mill", "the boathouse", "the chapel steps", "the long orchard",
    "the smithy", "the well", "the cold cellar", "the west gate",
]
HOURS = [
    "before dawn", "at first light", "mid-morning", "at noon",
    "in the long afternoon", "at dusk", "after dark", "at midnight",
]
FACTS = ("who", "where", "when")

# Tuned by sweeping 200 seeds per cell, not by feel. The target was a board
# where following attribution always wins and believing the village usually
# loses; at these values the popular answer is correct 38% of the time, so
# consensus is an actively losing strategy rather than a coin flip, and the
# trace takes 2-5 interviews against a budget of 6.
DEFAULT = {
    "villagers": 12,
    "budget": 6,          # interviews allowed
    "chain": 4,           # deepest a rumour travels from its witness
    "mutate": 0.65,       # chance a fact corrupts on a given retelling
    "confidants": 3,      # outgoing relationship edges per villager
}


def build(seed, config=None):
    """A complete, solvable village. Pure function of (seed, config)."""
    cfg = {**DEFAULT, **(config or {})}
    rng = Rng(seed)

    n = min(cfg["villagers"], len(NAMES))
    people = NAMES[:n]

    # --- the sparse relationship graph -----------------------------------
    # Only pairs that actually interact are modelled; a village is not a
    # complete graph and simulating it as one costs O(n^2) for relationships
    # nobody has.
    confidants = {}
    for i, person in enumerate(people):
        others = [p for p in people if p != person]
        confidants[person] = sorted(
            rng.sample(others, cfg["confidants"], "confidants", i, person))

    # --- the truth --------------------------------------------------------
    culprit = rng.pick(people, "truth", "culprit")
    truth = {
        "who": culprit,
        "where": rng.pick(PLACES, "truth", "where"),
        "when": rng.pick(HOURS, "truth", "when"),
    }

    # --- one witness per fact, and a rumour tree spreading from each ------
    # A single chain was the first attempt and it made a poor game: every board
    # took exactly the same number of interviews, and the village consensus
    # matched the truth 55% of the time, so guessing the popular answer was a
    # coin flip rather than a mistake.
    #
    # Branching fixes both, for one reason. A mutation on a single path corrupts
    # the tail; a mutation high in a TREE is inherited by that whole subtree, so
    # a confidently-held wrong answer can outnumber the truth. The trap becomes
    # structural instead of decorative, and depth varies with the shape of each
    # villager's connections rather than being a constant.
    #
    # Every belief still records who supplied it, so following attribution
    # always terminates at the witness. Reachability survives the redesign —
    # it is a property of the pointers, not of the topology.
    beliefs = {p: {} for p in people}
    trees = {}
    for fact in FACTS:
        eligible = [p for p in people if p != culprit] or list(people)
        witness = rng.pick(eligible, "witness", fact)
        beliefs[witness][fact] = {
            "value": truth[fact], "from": None, "hops": 0, "first_hand": True,
        }

        depth = 2 + rng.below(max(1, cfg["chain"] - 1), "depth", fact)
        frontier = [witness]
        holders = {witness}
        for hop in range(1, depth + 1):
            nxt_frontier = []
            for teller in sorted(frontier):
                carried = beliefs[teller][fact]["value"]
                for listener in confidants[teller]:
                    if listener in holders:
                        continue
                    value = carried
                    if rng.chance(cfg["mutate"], "mutate", fact, hop, teller, listener):
                        value = _distort(rng, fact, value, people, culprit, hop)
                    beliefs[listener][fact] = {
                        "value": value, "from": teller, "hops": hop,
                        "first_hand": False,
                    }
                    holders.add(listener)
                    nxt_frontier.append(listener)
            frontier = nxt_frontier
            if not frontier:
                break
        trees[fact] = sorted(holders)

    # Start the player at someone as far from the truth as the rumour reaches,
    # so the trace is worth walking. Deterministic tie-break by name.
    who_holders = [p for p in people if "who" in beliefs[p]]
    start = max(sorted(who_holders), key=lambda p: beliefs[p]["who"]["hops"])

    return {
        "seed": seed,
        "config": cfg,
        "people": people,
        "confidants": confidants,
        "truth": truth,
        "beliefs": beliefs,
        "trees": trees,
        "start": start,
        "places": PLACES,
        "hours": HOURS,
    }


def _distort(rng, fact, value, people, culprit, hop):
    """Corrupt a fact into a *plausible* wrong answer, never into nonsense.

    A mutation that produced an impossible value would be self-announcing and
    the deduction would collapse — the player would just discard anything
    absurd. The lie has to be the same shape as the truth to cost anything.
    """
    if fact == "who":
        pool = [p for p in people if p != value]
    elif fact == "where":
        pool = [p for p in PLACES if p != value]
    else:
        pool = [h for h in HOURS if h != value]
    return rng.pick(pool, "distort", fact, hop, str(value))


def testimony(world, person):
    """What `person` says when interviewed, in the order they'd say it."""
    held = world["beliefs"].get(person, {})
    return [
        {
            "fact": fact,
            "value": held[fact]["value"],
            "from": held[fact]["from"],
            "first_hand": held[fact]["first_hand"],
        }
        for fact in FACTS if fact in held
    ]
