"""Deterministic randomness, addressed by name instead of by turn.

The ordinary seeded-PRNG discipline — one stream, every roll through it, no
ambient entropy — buys reproducibility but leaves a sharp edge: the stream is an
*ordinal* space. Roll number 41 belongs to whoever happens to ask forty-first, so
inserting one villager, or asking one extra question during generation, shifts
every later draw and silently rewrites unrelated parts of the world. Seeds stay
reproducible and stop being *stable*, which is worse, because the tests still
pass and the content moves.

So nothing here draws in sequence. Every value is a pure function of the seed and
a **symbolic address** — `("villager", 3, "trait")` — via a keyed hash. Adding a
villager cannot perturb an existing one, because no one is standing in a queue.
Generation order stops being part of the world's identity.

The cost is that there is no "next random number", which turns out to be a
feature: every draw has to say what it is for.
"""

import hashlib
import struct

MASK = (1 << 64) - 1


class Rng:
    """Addressed randomness. Same seed + same address = same value, always."""

    __slots__ = ("seed",)

    def __init__(self, seed):
        self.seed = int(seed)

    def _bits(self, address):
        key = f"{self.seed}|" + "|".join(str(a) for a in address)
        digest = hashlib.blake2b(key.encode("utf-8"), digest_size=8).digest()
        return struct.unpack("<Q", digest)[0]

    def unit(self, *address):
        """Float in [0, 1)."""
        return self._bits(address) / (MASK + 1)

    def below(self, n, *address):
        """Integer in [0, n)."""
        if n <= 0:
            raise ValueError("below() needs a positive bound")
        return self._bits(address) % n

    def chance(self, p, *address):
        """True with probability p."""
        return self.unit(*address) < p

    def pick(self, seq, *address):
        seq = list(seq)
        if not seq:
            raise ValueError("pick() from an empty sequence")
        return seq[self.below(len(seq), *address)]

    def shuffled(self, seq, *address):
        """A deterministic permutation, stable under insertion elsewhere.

        Sorts by each item's own keyed hash rather than running Fisher-Yates
        over a positional stream, so the order of two items never depends on how
        many other items exist.
        """
        return [x for _, x in sorted(
            ((self.unit(*address, "sort", str(x)), x) for x in seq),
            key=lambda pair: (pair[0], str(pair[1])),
        )]

    def sample(self, seq, k, *address):
        return self.shuffled(seq, *address)[:k]
