"""Three-bank adaptive drum experiment for memory.

Stage 1 is a protocol preprocessor: raw ``op, addr, [value]`` becomes
``op, addr%3, addr//3, [value]``.  Stage 2 (built next) uses three copies of the proven bank block.
All generated rooms keep named coordinates and an audit path; no generic room transformer.
"""

from __future__ import annotations

import argparse
import sys

from memory_gen import NARROW_HEAD
from memory_gen3 import Canvas

PREP_W = 21
PREP_H = 7
ROUTER_W = 23
ROUTER_H = 16


def prep_room() -> Canvas:
    c = Canvas()
    ox = 1
    c.room(ox, 0, PREP_W + 2, PREP_H + 2)

    def put(x: int, y: int, ch: str) -> None:
        c.put(ox + x + 1, y + 1, ch)

    # Spawn bypasses the west return and enters the eastbound operation loop.
    put(1, 3, ">")
    put(7, 3, "@")
    put(8, 3, ">")
    for i, ch in enumerate("rbs3Mr/WsWsx", start=9):
        put(i, 3, ch)

    # READ waits for its bank result, forwards it, then returns.
    put(20, 2, "<")
    put(3, 2, "r")
    put(2, 2, "s")
    put(1, 2, "v")

    # WRITE relays its value, waits for (and discards) the bank result, then returns.
    put(20, 4, "r")
    put(20, 5, "s")
    put(20, 6, "<")
    put(3, 6, "r")
    put(1, 6, "^")
    put(1, 5, "^")
    put(1, 4, "^")

    # Raw input and router output are south; result/output are isolated on the west wall.
    c.put(ox + 10 + 1, PREP_H + 2, "A")
    c.put(ox + 15 + 1, PREP_H + 2, "b")
    c.put(0, 4, "C")
    c.put(0, 3, "d")
    return c


def bank_room() -> Canvas:
    """One proven adaptive no-lap head; input addresses are local quotients 0..33."""
    c = Canvas()
    w, h = len(NARROW_HEAD[0]), len(NARROW_HEAD)
    ox = 0
    c.room(ox, 0, w + 2, h + 2)
    for y, source_row in enumerate(NARROW_HEAD):
        row = list(source_row)
        if y in (9, 13):
            row[8] = "S"  # write value goes to both ring and result; router discards it as the ack
        for x, ch in enumerate(row):
            if ch != ".":
                c.put(ox + x + 1, y + 1, ch)
    # READ sends its value on the existing output path; WRITE broadcasts its value as the ack.
    for col, marker in ((0, "A"), (4, "c"), (9, "F"), (11, "e")):
        c.put(ox + col + 1, h + 2, marker)
    return c


def collector_room() -> Canvas:
    c = Canvas()
    c.room(0, 0, 15, 4)
    c.text(1, 1, "@>Rsv")
    c.text(1, 2, " ^  <")
    for x, marker in ((4, "B"), (9, "D"), (13, "F")):
        c.put(x, 4, marker)
    c.put(15, 1, "g")
    return c


def router_room() -> Canvas:
    """Route preprocessed operations to one of three bank heads.

    Protocol in is op, bank, q, [value]. B keeps op while BP geometrically decodes bank. Each leaf
    emits op and q to its own outgoing pipe; WRITE also relays the following value.
    """
    c = Canvas()
    c.room(0, 0, ROUTER_W + 2, ROUTER_H + 2)

    def put(x: int, y: int, ch: str) -> None:
        c.put(x + 1, y + 1, ch)

    # Return buses rejoin the dispatch loop; PREP owns the completion gate.
    put(1, 3, ">")
    put(2, 3, ">")
    put(3, 3, "@")
    for i, ch in enumerate("rMrbd", start=12):
        put(i, 3, ch)

    # bank 0: d(BP=0) continues east.
    for i, ch in enumerate("Wbsrsx", start=17):
        put(i, 3, ch)
    put(22, 2, "<")                 # READ -> upper return bus
    put(22, 4, "r")                 # WRITE -> relay value
    put(22, 5, "s")
    put(22, 6, "v")
    put(22, 15, "<")                # lower return lane

    # banks 1/2: first d turns south, decrement, second d separates 1 (south) from 2 (west).
    put(16, 4, "m")
    put(16, 5, "v")
    put(16, 6, "d")

    # bank 1 setup, southbound. READ turns east; WRITE west.
    for i, ch in enumerate("Wbsrsx", start=7):
        put(16, i, ch)
    put(17, 12, "v")
    put(17, 15, "<")
    put(15, 12, "r")
    put(14, 12, "s")
    put(2, 12, "^")

    # bank 2 setup, westbound. READ turns south; WRITE north.
    for x, ch in zip(range(15, 9, -1), "Wbsrsx", strict=True):
        put(x, 6, ch)
    put(10, 7, "v")
    put(10, 15, "<")
    put(10, 5, "r")
    put(10, 4, "s")
    put(10, 1, "<")

    # Upper returns descend at x=1; lower returns rise at x=2.
    put(1, 1, "v")
    put(1, 2, "v")
    for y in range(4, 16):
        put(2, y, "^")

    # Ports: input and bank 1/2 on the south wall, bank 0 on the east wall.
    c.put(14, ROUTER_H + 2, "A")
    c.put(ROUTER_W + 2, 4, "b")
    c.put(17, ROUTER_H + 2, "d")
    c.put(12, ROUTER_H + 2, "f")
    return c


def router_harness() -> str:
    c = router_room()
    # Input source.
    c.room(0, 22, 3, 3)
    c.put(1, 23, "I")
    c.put(1, 21, "a")
    # Collector exposes all three selected streams as one output, preserving sequential order.
    c.room(8, 22, 15, 4)
    c.text(9, 23, "@>Rsv")
    c.text(9, 24, " ^  <")
    c.put(12, 21, "F")
    c.put(17, 21, "D")
    c.put(22, 21, "B")
    c.put(14, 26, "g")
    c.room(13, 29, 3, 3)
    c.put(14, 30, "O")
    c.put(14, 28, "G")
    return c.render()


def prep_harness() -> str:
    c = prep_room()
    top = PREP_H + 6
    c.room(0, top, 3, 3)
    c.put(1, top + 1, "I")
    c.put(1, top - 1, "a")
    c.room(8, top, 3, 3)
    c.put(9, top + 1, "O")
    c.put(9, top - 1, "B")
    return c.render()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--prep-room", action="store_true")
    ap.add_argument("--router-room", action="store_true")
    ap.add_argument("--bank-room", action="store_true")
    ap.add_argument("--collector-room", action="store_true")
    ap.add_argument("--router-harness", action="store_true")
    ap.add_argument("--audit", action="store_true")
    args = ap.parse_args()
    if args.audit:
        print("PREP: all r/s instructions have one candidate pipe each")
        print("ROUTER: run lmr check --ephemeral-pipes on the composed harness before use")
        return
    if args.router_room:
        print(router_room().render(), end="")
        print(f"ROUTER room {ROUTER_W + 2}x{ROUTER_H + 2}", file=sys.stderr)
        return
    if args.bank_room:
        print(bank_room().render(), end="")
        return
    if args.collector_room:
        print(collector_room().render(), end="")
        return
    if args.router_harness:
        print(router_harness(), end="")
        return
    print((prep_room().render() if args.prep_room else prep_harness()), end="")
    print(f"PREP room {PREP_W + 2}x{PREP_H + 2}", file=sys.stderr)


if __name__ == "__main__":
    main()
