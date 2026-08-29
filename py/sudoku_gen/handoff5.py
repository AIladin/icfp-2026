"""Emit the V5 room set for hand-packing: one block per room, with the pipe table.

Target 29x29 = 841. The budget is 833 cells, so there is ~8 cells of slack -- this one is tight.
Do NOT fold any room further: every fold adds turn cells to the critical path and costs more in
ticks than it saves in footprint (measured; see the log).
"""

import gen
from lay import serp
from v5rooms import HEAD2, cell, core

SPLIT = "rSrSrS"
ROW = "rM1{s" + "rr"
COL = "r" + "rM9+M1{s" + "r"
BOX = "rM3W/M6+M9*M" + "r+M3W/M1{s" + "r"
ADDER = "RMR+MR+s"

ROOMS = [
    ("SPLIT", lambda: serp(0, 0, SPLIT, per_row=6), "reads r c v, `S` broadcasts each to all four"),
    ("ROW", lambda: serp(0, 0, ROW, per_row=7), "1<<r, then discards c and v"),
    ("COL", lambda: serp(0, 0, COL, per_row=10), "discards r, 1<<(9+c), discards v"),
    ("BOX", lambda: serp(0, 0, BOX, per_row=12), "1<<(18+3*(r/3)+c/3) -- the critical path"),
    ("ADDER", lambda: serp(0, 0, ADDER, per_row=8), "`R` sums the three bits in any order"),
    ("CORE", lambda: core(0, 0, 1), "pair+parity from one `/`, then the 5-way decode"),
    ("CELL x5", lambda: cell(0, 0), "B = W_j, updated in place; returns W_j ^ m'"),
    ("HEAD2", lambda: serp(0, 0, HEAD2, per_row=16), "`& -` then the branchless verdict"),
]

PIPES = """
    #   from      to        min  note
    1   INPUT     SPLIT      2
    2   SPLIT     ROW        2   all four are one `S`: position irrelevant
    3   SPLIT     COL        2
    4   SPLIT     BOX        2
    5   SPLIT     CORE       2   carries r, c, v; CORE discards the first two
    6   ROW       ADDER      2   `R` reads any: position irrelevant
    7   COL       ADDER      2
    8   BOX       ADDER      2
    9   ADDER     CORE       2   CONSTRAINT: nearest to CORE's 4th `r` (the one before `{`)
   10   CORE      CELL1      2   CONSTRAINT: nearest to lane 1's `s`
   11   CORE      CELL2      2   ... lane 2, and so on. Same row = strictly nearest.
   12   CORE      CELL3      2
   13   CORE      CELL4      2
   14   CORE      CELL5      2
   15   CORE      HEAD2      2   the merge `s`, two rows below lane 5
   16   CELL1     HEAD2      2   `R` reads any: position irrelevant
   17   CELL2     HEAD2      2
   18   CELL3     HEAD2      2
   19   CELL4     HEAD2      2
   20   CELL5     HEAD2      2
   21   HEAD2     OUTPUT     2
"""

if __name__ == "__main__":
    total = 0
    for name, fn, note in ROOMS:
        gen.G.clear()
        fn()
        g = gen.render()
        w = max(len(line) for line in g.split("\n"))
        h = len(g.split("\n"))
        n = w * h * (5 if name.endswith("x5") else 1)
        total += n
        print(f"### {name}   {w} x {h}" + (f" x5 = {n}" if name.endswith("x5") else f" = {n}"))
        print(f"{note}\n")
        print(g + "\n")
    print(f"rooms {total} + I/O 18 + 21 minimal pipes 42 = {total + 60} cells")
    print("\nPIPES" + PIPES)
    print("CORE's two nearest-pipe constraints are the only ones. Everything else uses `S`")
    print("(writes every outgoing) or `R` (reads any incoming), which have no resolution at all.")
