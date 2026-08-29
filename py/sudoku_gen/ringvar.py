"""Probe the ring's real capacity constraint: does it need 6+6, and must it be symmetric?

The ring holds nine word-tokens, distributed across both pipes plus whatever the two
men are holding. Undersizing it deadlocks rather than failing (see the vault note
[[Delay line ring]]), so this sweeps lengths and routings and reports which pass.

    uv run python ringvar.py sym 6        # both pipes straight, length 6
    uv run python ringvar.py asym 2 8     # ring-in 2 cells, ring-out folded to 8
"""

import sys

from gen import col, emit, put
from head import M3_IN_COL, RING_IN_COL, RING_OUT_COL, head, relay
from lay import hpipe, io_room, vpipe
from rooms import m1_room, m2_room, m3


def build(mode: str, a: int, b: int) -> None:
    """`a` = ring-in length (RELAY -> HEAD), `b` = ring-out length (HEAD -> RELAY)."""
    head()
    relay_top = 11 + a  # a straight ring-in fixes where RELAY sits
    vpipe(RING_IN_COL, relay_top - 1, 11)

    if mode == "sym":
        vpipe(RING_OUT_COL, 11, relay_top - 1)
    else:
        # Fold the outgoing pipe west into the empty columns so it can be longer than
        # the incoming one without moving RELAY.  Capacity depends on length, not route.
        put(11, RING_OUT_COL, "v")
        put(12, RING_OUT_COL, "<")
        put(12, RING_OUT_COL - 1, "-")
        put(12, 2, "v")
        run = b - 4  # cells already spent: the v, the bend, the body, the turn down
        col(2, 13, "|" * (run - 1))
        put(12 + run, 2, ">")  # points into RELAY's west wall

    relay(relay_top, 3)

    hpipe(9, 20, 21)
    io_room(8, 22, "O")

    # M3 sits at a fixed row: its pipe to HEAD's south wall is two cells and does not
    # move with RELAY.  Its columns (9+) never overlap RELAY's (3..8).
    m3_r1, _ = m3(13, 9)
    vpipe(M3_IN_COL, 12, 11)
    m2_r1, _ = m2_room(m3_r1 + 3, 9)
    vpipe(M3_IN_COL, m3_r1 + 2, m3_r1 + 1)
    m1_r1, m1_c1 = m1_room(m2_r1 + 3, 9)
    vpipe(M3_IN_COL, m2_r1 + 2, m2_r1 + 1)
    io_room(m1_r1 - 4, m1_c1 + 3, "I")
    hpipe(m1_r1 - 3, m1_c1 + 2, m1_c1 + 1)


if __name__ == "__main__":
    mode = sys.argv[1]
    a = int(sys.argv[2])
    b = int(sys.argv[3]) if len(sys.argv) > 3 else a
    build(mode, a, b)
    emit(sys.argv[4] if len(sys.argv) > 4 else "ringvar.man")
    print(f"{mode} ring-in={a} ring-out={b} capacity={a + b}")
