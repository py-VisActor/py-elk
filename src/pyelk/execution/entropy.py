"""Native host entropy for source Math.random call sites (ADR-0012).

This is separate from the seeded ELK JavaRandom implementation. It does not
copy V8 state, promise matching random trajectories, or read layout options.
"""
import os


def random_unit():
    """Return a native, unseeded binary64 value in the half-open interval [0,1)."""
    bits=int.from_bytes(os.urandom(8),'big') >> 11
    return bits / (1 << 53)
