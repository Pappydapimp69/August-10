# gossip

**Brain's co-verification graph, read as a social network.**

The graph records that two systems were seen together. That is a social fact —
and `ideas` already holds a worked-out theory of social facts: witness versus
hearsay, vetoes that survive combination, hysteresis against thrashing, reach
and drama as independent axes. None of it had ever been pointed back at the
graph it lives in. `gossip` points it back.

Read-only, python3 stdlib, no dependencies. It never writes canon.

```
bin/gossip [report] [--canon DIR] [--asof YYYY-MM-DD] [--prior FILE]

  hazard --plan <tag>...   pre-mortem: what will bite this, before you build it
  summary       one screen (default)
  provenance    declared composition vs mined name-drop
  edges         ranked by confidence rather than raw weight
  communities   consensus clusters, against brain's connected components
  seams         what to test next, ranked by context × novelty × drama
  compare       brain analyze vs gossip, side by side
```

## What it changes

Measured on the live canon — 573 lessons, 125 systems, as of 2026-08-05:

| | `brain analyze` | `gossip` |
|---|---|---|
| edges | 300, all counted alike | 253 confident, 47 vetoed |
| clusters | **1** (largest 100) | **13** of size>1 (largest 24), Q=0.442 |
| edge ranking | raw weight | confidence product |
| single-source edges | 245 counted equally | scored at 0.50 independence |
| hearsay | indistinguishable from declared | vetoed or discounted |
| top seam | `brain + opticon` (reach 15/10 — two hubs) | `test + lockstep` (reach 12/1) |

Its seam ranking overlaps brain's by **2 of 15**.

## `hazard` — the pre-mortem

Everything else over this canon is descriptive. `brain query` answers *what do
we know about X*; `brain analyze` answers *what shape is what we know*. Both look
backwards, and neither takes a plan as input.

`hazard` does. Name the tags of the thing you are about to build:

```
$ gossip hazard --plan determinism audio mobile

       5  █████    audio + determinism
       0  ·        audio + mobile
       0  ·        determinism + mobile

  UNTESTED GROUND — 2 pair(s) the canon has never carried together.
    determinism + mobile   (77 and 12 lessons apiece, 0 together)
    audio + mobile         (22 and 12 lessons apiece, 0 together)
```

The middle block is the reason it exists. **77 lessons on determinism, 12 on
mobile, and not one that carries both.** A relevance-ranked search over that
combination returns nothing — which is indistinguishable, to the person reading
it, from reassurance. The emptiest cell in the matrix is the dangerous one, and
every retrieval tool sorts it last.

It also ranks lessons that record an *actual failure* above ones that merely
cover the area, discounts unverified provenance without dropping it, and surfaces
the open tensions sitting over the plan's own ground — forks you are otherwise
about to settle silently.

## The four mechanisms, and the kernels they come from

**Witness vs hearsay** — *rumor-as-traveling-token / witness-then-carry-then-mutate*.
A reference declared in an entry's `Composed:` field is a **witness**; one mined
from prose is **hearsay**, and may be an illustrative name-drop. That is exactly
the false edge tension **T26** is open on. 216 edges are witness-only, 53
hearsay-only, 31 mixed.

**Multiplicative confidence** — *multiplicative-combination-preserves-vetoes /
one-zero-collapses-the-whole-score*. `witness × independence × corroboration ×
recency`, with one hard veto: an edge asserted **once, by prose alone** scores 0.
That is the only configuration with no evidence of composition at all; 47 edges
match it. Every other weak edge is scored low, never deleted — **T20** is an open
fork and a tool has no business closing it by fiat, so the dial it turns on is a
flag (`--single-source`).

Recency has an exception straight from *non-decaying-pivotal-events / traumatic-
memories-dont-fade*: an edge whose `Got right` names both systems is a pair
confirmed *compatible*, not merely co-tested. Those never decay.

**Consensus communities** — replacing connected components, which welds all 100
connected systems into one cluster and is informationally empty. See below; this
is where the design changed under measurement.

**Reach × drama seams** — *reach-and-drama-as-independent-axes / the-recluse-is-
the-loudest-choice*. Shared-tag ranking has a bias baked in: the more connected a
system is, the more tags it has accumulated, so the top fills with hub–hub pairs.
Brain's current #1 pairs its two most-connected systems, which is the least
surprising experiment available. gossip scores `context × novelty × drama`, where
novelty favours the recluse and drama is the share of the pair's lessons still
unverified — so a seam retires entries from the provenance worklist at the same
time as it adds an edge.

## Two places the data refuted the design

Both are kept in the code as comments rather than tidied away, because the
measurement is the interesting part.

**Hysteresis made clustering worse.** The kernel *require-a-real-margin-before-
switching* went into the propagation loop first. Order-stability *fell* — 0.99 at
margin 0, 0.61 at 0.05–0.30, 0.24 at 0.80. The convergence counts said why: every
margin, including 0, settles in 4–6 rounds, so there is no oscillation to damp
and the margin's only remaining effect is pinning each node to whichever label it
met first — which is the visit order. Hysteresis didn't stabilise the answer, it
laundered an arbitrary ordering into it.

The kernel wasn't wrong, it was aimed at the wrong axis. What oscillates here is
**time** — the report reshuffling as canon grows between syncs. Moved there, it
works: across four simulated growth points, co-membership churn drops from
0.23–0.67 to 0.05–0.55. That is `--prior` / `--save-prior`.

**One traversal was never trustworthy.** After a parser fix (see below) the
single-traversal partition agreed with its own reversal on ~0.51 of its
co-memberships. Printing that as "the communities" would be presenting a
coin-flip as structure. The fix is the tool's own thesis turned on itself: gossip
refuses to trust an edge asserted by one source, so a partition found by one
traversal gets the same skepticism. Five deterministic traversals run, and only
co-memberships **all five** agree on survive. The report prints the consensus and
states the agreement underneath it (0.55) rather than hiding it.

## A bug worth naming

`gossip` first matched field labels exactly. The canon writes provenance as
`Provenance (verified/assumed):`, so every lookup returned `""` — which reads
downstream as *no lesson here is verified* rather than as a parse failure. It
surfaced as `drama=1.00` across an entire top-15, and it had silently corrupted
the `Got right` text that decides which edges are safe. Matching is now
prefix-based with wrapped-line joining, as brain does it.

The lesson generalises past this tool: **a field parser that returns empty on a
miss produces a plausible answer, not an error.** The saturated metric was the
only thing that gave it away.

## One deliberate difference from brain

Brain tests `if composed:` truthily, so an entry written `Composed: N/A` takes
the declared branch, resolves nothing, and suppresses prose mining entirely.
gossip treats `N/A` as absent and falls through to prose. `gossip provenance`
prints how many entries this affects, so the departure stays visible. It is the
only intake difference between the two tools.

## Tests

```
python3 -m unittest discover -s tests -t .    # 55 tests
```

Fixture-based unit tests plus integration tests against the real canon, which
skip cleanly on a machine with no `~/.brain`. The claims the README makes about
the live graph are asserted there, not just printed here.
