"""Lower-bound timing probe for three-values-per-token memory.

This deliberately stores one scalar per 3-address word; use only addresses divisible by three.
It changes the proven fixed-slot drum from 100 to 34 slots without adding field extraction, so its
ticks are an optimistic bound. If this cannot beat the current banked drum after pricing, the full
packed-word design cannot either.
"""

from memory_gen import SLOT_HEAD, build_slots
import memory_gen

memory_gen.SLOT_HEAD = [row.replace("`100`", "` 34`") for row in SLOT_HEAD]
print(build_slots(rows=9, x0=27, x1=29), end="")
