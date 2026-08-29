"""Emit the V4 room set as separate blocks with `b`/`B` pipe markers, for hand-packing.

    b = a pipe must BEGIN here (this room's outgoing pipe -- where `s` writes)
    B = a pipe must END here   (an incoming pipe -- where `r` / `R` reads)

Markers sit on the cell immediately OUTSIDE the wall, which is the pipe's own first or
last cell -- swap `b`/`B` for the arrowhead pointing away from / into the room and only
the middle of the run needs routing. See docs/vault/heap/Room handoff markers.md.

    uv run python sudoku_gen/handoff.py
"""

import gen
from head4 import head
from rooms4 import ADDER, BOX, COL, ROW, SPLIT, phase
from head4 import relay
from lay import serp


def block(build, marks: list[tuple[int, int, str]], title: str, note: str) -> str:
    gen.G.clear()
    build()
    for r, c, ch in marks:
        gen.put(r, c, ch)
    body = gen.render()
    gen.G.clear()
    return f"### {title}\n{note}\n\n```\n{body}\n```\n"


def linear(prog: str, per_row: int):
    return lambda: serp(1, 1, prog, per_row=per_row)


def main() -> None:
    out: list[str] = []

    # ---- rooms whose pipes may attach anywhere: one in, one out, so `r`/`s` cannot
    # ---- resolve to the wrong pipe no matter where the packer puts them.
    out.append(block(
        linear(SPLIT, 7),
        [(2, 0, "B"), (5, 4, "b"), (5, 6, "b"), (5, 8, "b"), (5, 10, "b")],
        "SPLIT   1 in, 4 out   -- markers may move to any wall",
        "Reads r, c, v and broadcasts each with `S`, then v a second time (PHASE needs two\n"
        "copies). `S` writes *every* outgoing pipe, so position is irrelevant -- but it also\n"
        "means SPLIT must have exactly these four and no more.",
    ))
    out.append(block(
        linear(ROW, 8),
        [(2, 0, "B"), (5, 5, "b")],
        "ROW     1 in, 1 out   -- markers may move to any wall",
        "`1<<r`, then discards c, v, v.",
    ))
    out.append(block(
        linear(COL, 11),
        [(2, 0, "B"), (5, 5, "b")],
        "COL     1 in, 1 out   -- markers may move to any wall",
        "Discards r, then `1<<(9+c)`, then discards v, v.",
    ))
    out.append(block(
        linear(BOX, 12),
        [(2, 0, "B"), (6, 5, "b")],
        "BOX     1 in, 1 out   -- markers may move to any wall",
        "`1<<(18 + 3*(r/3) + c/3)` via the folded divisor K = 54 + 9*(r/3), so the whole box\n"
        "exponent falls out of one `/`. This is the critical path: ~26 ticks, and every other\n"
        "room's work hides behind it.",
    ))
    out.append(block(
        lambda: phase(1, 1),
        [(3, 0, "B"), (8, 5, "b")],
        "PHASE   1 in, 1 out   -- markers may move to any wall",
        "Discards r and c, turns v into the ring skip count: skip = v - B, +9 when negative,\n"
        "then B = v+1. B starts at 0 and the phase is self-consistent from cold -- no seeding.",
    ))
    out.append(block(
        lambda: relay(1, 1),
        [(0, 3, "B"), (0, 4, "b")],
        "RELAY   1 in, 1 out   -- markers may move to any wall",
        "The ring's second room, a bare 6-cell shuttle. Its two pipes ARE the ring:\n"
        "their combined length must be >= 9 (>= 8 runs but costs 2.8% ticks, <= 7 deadlocks\n"
        "silently). The split is free -- 2+7 is exactly as fast as 6+6.",
    ))

    # ---- ADDER: `R` ignores position, but the leading `r` must reach PHASE.
    out.append(block(
        linear(ADDER_V4, 10),
        [(0, 4, "B"), (5, 9, "B"), (5, 11, "B"), (5, 13, "B"), (5, 6, "b")],
        "ADDER   4 in, 1 out   -- ONE placement constraint",
        "`r s` relays PHASE's skip straight through to HEAD, then `R M R + M R +` sums the\n"
        "three mask bits in whatever order they arrive (addition does not care, which is what\n"
        "makes `R` safe) and `s` sends the mask.\n"
        "\n"
        "CONSTRAINT: the leading `r` at the marked cell must resolve to PHASE. Keep PHASE's\n"
        "`B` on the north wall near it and the other three `B`s far away -- the three `R`s\n"
        "ignore position entirely, so only this one marker's placement matters.",
    ))

    # ---- HEAD: four pipes, fixed columns.
    out.append(block(
        head,
        [(14, 5, "b"), (14, 6, "B"), (14, 11, "B"), (11, 15, "b")],
        "HEAD    3 in, 2 out   -- COLUMNS ARE FIXED",
        "Reads the skip first and the mask second, so the 34-tick skip loop runs while BOX is\n"
        "still working and the mask arrives free. Verdict is branchless: the kernel leaves\n"
        "A = 0 when valid and negative on a duplicate, so `1 + (A >> 63)` is the answer.\n"
        "\n"
        "CONSTRAINT: all three south-wall markers must stay on ONE wall at these columns.\n"
        "With them on one wall the |dy| term cancels and the zones split purely by column:\n"
        "  r -> ring for x <= 8, ADDER for x >= 9      s -> ring for x <= 9, OUT for x >= 10\n"
        "Moving any of them to another wall splits the zones by ROW too, which pins the flow\n"
        "top-to-bottom and cost +22 ticks/round when measured. The OUT marker on the east wall\n"
        "may slide up or down a row or two; check with zones.py.",
    ))

    print("\n".join(out))


ADDER_V4 = "rs" + ADDER  # relay the skip, then sum the three bits

if __name__ == "__main__":
    main()
