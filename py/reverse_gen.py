"""Emit the `reverse-a-list` program: an addressable fan of pipes used as a stack.

See docs/vault/heap/Pipe fan stack.md. The short version:

`s` picks the *nearest* outgoing pipe, so a room with 16 pipes on one face is a 16-slot store
addressed by instruction position -- WRITER walks a boustrophedon lane and drops `v[i]` into the
slot its row happens to name.

READER does not address anything. `R` takes from **any** ready pipe, breaking ties in reading
order (top to bottom), so if WRITER fills upwards from the bottom slot, the topmost occupied pipe
always holds the value that must come out next. That turns the whole reader into one 8-cell loop
with no scan, no per-slot geometry, and no cost for the slots a short list never touches.

The gate pipe carries `n`: it blocks READER until every slot is written (otherwise `R` would drain
slot 16 before slot 1 existed) and doubles as the loop counter, so READER never inspects a slot.
"""

from __future__ import annotations

from memory_gen import Canvas

# --- geometry -------------------------------------------------------------------------------
# Rows 0..4 are the I/O band; both big rooms span rows 5..25.
SLOTS = 16
ROOM_TOP, ROOM_BOT = 5, 25
Y_TOP = 6  # slot 1 -- the last slot a full list reaches
Y_BOT = Y_TOP + SLOTS - 1  # 21 -- slot 16, where every list starts
Y_ENTRY = Y_BOT + 1  # 22 -- WRITER reads n / READER's inner loop
Y_MERGE = Y_BOT + 2  # 23 -- WRITER's two exit chutes merge here
Y_GATE = Y_BOT + 3  # 24 -- gate pipe row

W_X0, W_X1 = 0, 9  # WRITER room, interior x1..x8
R_X0, R_X1 = 12, 18  # READER room, interior x13..x17


def writer(c: Canvas) -> None:
    """Fill slot 16 with v[1], slot 15 with v[2], ... walking up until the backpack runs out."""
    c.room(W_X0, ROOM_TOP, W_X1 - W_X0 + 1, ROOM_BOT - ROOM_TOP + 1)

    for y in range(Y_TOP, Y_BOT + 1):
        # One lane per slot, alternating direction, with the loop test on the far end so that
        # "still counting" is the turn north into the next slot and "done" is straight ahead
        # into a chute. `a` and `d` swap roles with the lane direction; both mean north.
        if y % 2:
            c.text(2, y, ">rsma")  # eastbound
            c.put(7, y, "v")  # ... falls out east
        else:
            c.text(6, y, "<rsmd", dx=-1)  # westbound
            c.put(1, y, "v")  # ... falls out west

    # Loop entry, walked west: spawn runs east into `<` and comes back over its own `@`.
    # B keeps n for the whole fill (nothing on the lane touches it) so the gate can resend it.
    c.put(8, Y_ENTRY, "<")
    c.put(6, Y_ENTRY, "@")
    c.text(5, Y_ENTRY, "rMb", dx=-1)  # A = n, B = n, BP = n
    c.put(2, Y_ENTRY, "^")  # into slot 16

    c.put(7, Y_MERGE, "<")  # east chute turns west and merges with the west one
    c.put(1, Y_MERGE, "v")
    c.text(1, Y_GATE, ">Ws")  # A = n again, then the go-token
    c.put(8, Y_GATE, "^")  # riser back to the entry row


def reader(c: Canvas) -> None:
    """Emit n values, always taking the topmost pipe that has one. No addressing at all."""
    c.room(R_X0, ROOM_TOP, R_X1 - R_X0 + 1, ROOM_BOT - ROOM_TOP + 1)

    # A 6-cell loop, which is the floor: a cycle needs four turns, and `U` pays for one of them
    # by reading *and* turning away from the pipe it read (always east -- every pipe is on the
    # west face), while `d` pays for another by being the test. That leaves `s` and `m` as the
    # only cells doing nothing else.
    #
    # `d` runs before `m`, so the backpack has to start at n-1: the last lap emits and *then*
    # falls out. Testing after `m` instead would cost three cells on the entry path to build
    # n+1, and that showed up as a real regression on one- and two-element lists.
    c.text(14, Y_ENTRY, "Usdv")
    c.text(13, Y_MERGE, ">^m<")

    # Gate wait, walked west, then up into the loop.
    c.put(17, Y_GATE, "<")
    c.text(16, Y_GATE, "rbm", dx=-1)  # A = n, BP = n, BP = n-1
    c.put(13, Y_GATE, "^")

    # Spawn falls straight through the loop with an empty backpack and lands on the gate wait.
    c.put(13, Y_BOT, "@")
    c.put(17, Y_BOT, "v")


def build() -> str:
    c = Canvas()
    writer(c)
    reader(c)

    # Each I/O room owns the only pipe of its direction, so `r` in WRITER and `s` in READER are
    # unambiguous wherever they land.
    c.room(2, 0, 3, 3)
    c.put(3, 1, "I")
    c.pipe([(3, 2), (3, ROOM_TOP)])
    c.room(14, 0, 3, 3)
    c.put(15, 1, "O")
    c.pipe([(15, ROOM_TOP), (15, 2)])

    for y in range(Y_TOP, Y_BOT + 1):
        c.pipe([(W_X1, y), (R_X0, y)])
    c.pipe([(W_X1, Y_GATE), (R_X0, Y_GATE)])
    return c.render()


if __name__ == "__main__":
    print(build(), end="")
