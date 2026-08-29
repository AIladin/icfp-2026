"""A narrow EMIT: the same seventeen lanes, folded from 200 columns into 64.

`lllm_gen5.room_emit` is 200x46 for one reason -- its three LM-75 sends live in column *zones*
20 / 100 / 180, because the loader picks a pipe by Manhattan distance and the zones have to be
far enough apart that `|x - col|` decides.  200 columns is a hard floor on `max(w, h)` for the
whole program, and it also makes the display pipes fragile: ADDR leaves at column 20 and DATA at
column 180, so whatever the packer does with the LM-75, one of the two is ~160 cells longer than
the other and `-181 < L_addr - L_data <= 160` is one routing decision away from breaking.

The zones do not need 80 columns of separation; they need *more separation than the row term*.
The room is 30 rows tall, so pins 14 columns apart on the south wall already decide every send by
at least 4 cells.  Everything else here is `lllm_gen5.room_emit` with its column constants pulled
in -- no lane was added, removed or reordered.

Run `uv run python lllm_gen8.py --audit` to print every send and receive with its margin.
"""

from __future__ import annotations

import sys

from lllm_gen5 import Grid, Room

# ------------------------------------------------------------------------------- column plan
# west turn 3 < ADDR 12 < A+10 22 < DATA 30 < SWAP 44 < CPU receives 52 < rejoin 58 < east 62
EMIT2_W, EMIT2_H = 64, 30
A_COL, D_COL, S_COL = 12, 30, 44  # the three send zones, and the three south pins
CPU_COL = 52  # where a receive from the CPU lives; SPLIT's receives live at 11/12
EAST = 62  # the column every lane turns south on
REJOIN = 58  # the commit lane's return north into row 14
ROW5 = 56  # the boot tail's turn south out of row 5
Q_COL, M_ROW = CPU_COL, 12  # incoming: CPU on the north wall, SPLIT on the west

# Each `s`/`r` cell, and the port it must reach.  Checked by `--audit` against the loader's rule.
INTENT = {
    (11, 2): "M", (30, 2): "t", (12, 6): "p", (52, 6): "Q", (30, 7): "t", (44, 8): "u",
    (12, 8): "M", (12, 10): "p", (30, 10): "t", (52, 11): "Q", (12, 11): "p", (30, 12): "t",
    (52, 13): "Q", (44, 15): "u", (12, 16): "M",
}  # fmt: skip


def room_emit2(g: Grid, x0: int, y0: int) -> Room:
    """257 raster words, then two pixels and maybe a SWAP per interpreted tick."""
    r = Room(g, x0, y0, EMIT2_W, EMIT2_H, name="EMIT")
    A, D, S = A_COL, D_COL, S_COL

    # ---- boot: BP = 257, then into the raster loop
    w = r.walk(0, 1, "E")
    w.lit(257).cell("b")
    w.to(r.ix(7), r.iy(1)).turn("S")
    w.to(r.ix(7), r.iy(3))
    r.put(7, 3, ">")
    r.at(8, 3, "E").to(r.ix(9), r.iy(3))
    r.put(9, 3, ">")
    r.put(10, 3, "a")  # BP > 0 -> counter-clockwise -> north into the body
    r.put(10, 2, ">")
    w = r.at(11, 2, "E")
    w.cell("r")  # base colour from SPLIT
    w.to(r.ix(D), r.iy(2)).cell("s")  # DATA
    w.to(r.ix(EAST), r.iy(2)).turn("S")
    w.to(r.ix(EAST), r.iy(4)).turn("W")
    w.to(r.ix(CPU_COL), r.iy(4)).cell("m")
    w.to(r.ix(9), r.iy(4)).turn("N")

    # ---- boot tail: paint the man, commit frame 1, seed A = index and B = its colour
    r.put(11, 3, "v")
    r.at(11, 4, "S").to(r.ix(11), r.iy(5))
    r.put(11, 5, ">")
    w = r.at(12, 5, "E")
    w.to(r.ix(ROW5), r.iy(5)).turn("S").turn("W")
    w.to(r.ix(CPU_COL), r.iy(6)).ops("r")  # manpos from CPU
    w.to(r.ix(CPU_COL - 2), r.iy(6)).ops("M")
    w.to(r.ix(A), r.iy(6)).cell("s")  # ADDR = manpos
    w.to(r.ix(A - 2), r.iy(6)).cell("9")
    w.to(r.ix(8), r.iy(6)).turn("S")
    w.to(r.ix(8), r.iy(7)).turn("E")
    w = r.at(9, 7, "E")
    w.to(r.ix(D), r.iy(7)).cell("s")  # DATA = 9
    w.to(r.ix(D + 2), r.iy(7)).cell("1")
    w.to(r.ix(EAST), r.iy(7)).turn("S")
    w.to(r.ix(EAST), r.iy(8)).turn("W")
    w.to(r.ix(S), r.iy(8)).cell("s")  # SWAP = 1  -> frame 1
    w.to(r.ix(12), r.iy(8)).cell("r")  # initial base colour, from SPLIT
    w.to(r.ix(10), r.iy(8)).cell("W")  # A = manpos, B = its colour
    w.to(r.ix(3), r.iy(8)).turn("S")
    w.to(r.ix(3), r.iy(10))
    r.put(3, 10, ">")

    # ---- main loop, one pass per interpreted tick
    w = r.at(4, 10, "E")
    w.to(r.ix(A), r.iy(10)).cell("s")  # ADDR = curpos
    w.to(r.ix(A + 10), r.iy(10)).cell("W")  # A = base colour, B = curpos
    w.to(r.ix(D), r.iy(10)).cell("s")  # DATA = base colour (erase the man)
    w.to(r.ix(EAST), r.iy(10)).turn("S").turn("W")
    w.to(r.ix(CPU_COL), r.iy(11)).cell("r")  # delta from CPU
    w.to(r.ix(CPU_COL - 2), r.iy(11)).ops("+M")  # A = newpos, B = newpos
    w.to(r.ix(A), r.iy(11)).cell("s")  # ADDR = newpos
    w.to(r.ix(A - 2), r.iy(11)).cell("9")
    w.to(r.ix(8), r.iy(11)).turn("S")
    w.to(r.ix(8), r.iy(12)).turn("E")
    w = r.at(9, 12, "E")
    w.to(r.ix(D), r.iy(12)).cell("s")  # DATA = 9 (paint the man)
    w.to(r.ix(EAST), r.iy(12)).turn("S").turn("W")
    w.to(r.ix(CPU_COL), r.iy(13)).cell("r")  # the round's commit flag
    w.to(r.ix(6), r.iy(13)).turn("S")
    w.to(r.ix(6), r.iy(14)).turn("E")
    w = r.at(7, 14, "E")
    w.to(r.ix(A), r.iy(14)).cell("X")  # flag > 0 -> clockwise -> the commit lane
    r.put(A, 15, ">")
    cw = r.at(A + 1, 15, "E").cell("1")
    cw.to(r.ix(S), r.iy(15)).cell("s")  # SWAP = 1
    cw.to(r.ix(REJOIN), r.iy(15)).turn("N")
    r.put(REJOIN, 14, ">")
    w = r.at(A + 1, 14, "E")
    w.to(r.ix(EAST), r.iy(14)).turn("S")
    w.to(r.ix(EAST), r.iy(16)).turn("W")
    w.to(r.ix(12), r.iy(16)).cell("r")  # the new cell's base colour, from SPLIT
    w.to(r.ix(10), r.iy(16)).cell("W")  # A = newpos, B = its colour
    w.to(r.ix(3), r.iy(16)).turn("N")
    w.to(r.ix(3), r.iy(11))

    r.mark("Q", "N", Q_COL)  # position / delta / flag, from CPU
    r.mark("M", "W", M_ROW)  # base colours, from SPLIT
    r.port("p", "S", A_COL)  # the three LM-75 pipes
    r.port("u", "S", S_COL)
    r.port("t", "S", D_COL)
    return r


def audit() -> int:
    """Every `s`/`r` in the narrow room, the port it reaches, and the margin over the runner-up."""
    g = Grid(200, 100)
    r = room_emit2(g, 4, 4)
    pins = [(ch, px, py) for ch, px, py in r.ports]
    for ch, px, py in pins:
        if g.at(px, py) == " ":
            g.put(px, py, ch)
    ins = [p for p in pins if p[0].isupper()]
    outs = [p for p in pins if p[0].islower()]
    bad = 0
    for y in range(r.h):
        for x in range(r.w):
            ch = g.at(r.ix(x), r.iy(y))
            if ch not in "srqRSU":
                continue
            cands = ins if ch in "rRqU" else outs
            ranked = sorted(
                (abs(r.ix(x) - px) + abs(r.iy(y) - py), i) for i, (_, px, py) in enumerate(cands)
            )
            got = cands[ranked[0][1]][0]
            margin = ranked[1][0] - ranked[0][0]
            want = INTENT.get((x, y))
            flag = "" if want == got and margin > 0 else "   <-- WRONG"
            bad += flag != ""
            print(f"  ({x:3d},{y:3d}) {ch} -> {got}  want {want}  margin {margin:3d}{flag}")
    print(f"EMIT {r.w}x{r.h} (was 200x30), {len(INTENT)} pipe ops, {bad} wrong")
    return bad


if __name__ == "__main__":
    raise SystemExit(audit() if "--audit" in sys.argv else audit())
