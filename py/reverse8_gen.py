"""Emit `reverse-a-list` with 8 slots of two values each, instead of 16 of one.

A pipe holds one value per cell, so a 2-cell slot carries a *pair* -- and two registers are exactly
enough to reverse two values (`r M r s W s`). The pair comes back out b-then-a, and `U` still pops
slots topmost-first (= newest-filled first), so both levels of the reversal fall out of geometry.

Layout facts the cells depend on (verified against machine.py):
- spawn direction is EAST; `@` is a pass-through cell
- `d` turns CW when BP>0 (west->north), `a` CCW (east->north); straight when spent
- `x` always turns: BP low bit 1 -> CW, 0 -> CCW.  Entered heading west: odd->north, even->south
- `U` pops the topmost ready pipe and faces the man the way that pipe flows in (east here),
  so the loop can be entered from ANY direction
- `r`/`s` bind the nearest pipe cell by Manhattan distance; every pipe cell here is at x14/x15,
  so the row alone decides: y15 = n, y16 = go, y14 = odd, y6..13 = pair slots

The reader's go-gate sits ON the exit path: the man leaves the pop loop at `d` when BP hits 0,
walks straight into `r`(go) and blocks there until the next fill is complete.  The spawn joins
the same path from below.  One cycle, no crossing conflicts.

The writer's two parity branches merge heading east into a shared `a` at (10,14): BP>0 climbs
into the lanes, BP==0 (n=1 after `]`, or n=0) falls into the chute and sends go -- so a round
with no pairs cannot deadlock on the bottom lane's `r`.
"""

W, H = 23, 25
grid = [[" "] * W for _ in range(H)]


def put(x: int, y: int, s: str) -> None:
    for i, c in enumerate(s):
        if c != " ":
            grid[y][x + i] = c


def room(x0: int, y0: int, x1: int, y1: int) -> None:
    for x in range(x0, x1 + 1):
        grid[y0][x] = grid[y1][x] = "-"
    for y in range(y0, y1 + 1):
        grid[y][x0] = grid[y][x1] = "|"
    for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        grid[y][x] = "+"


# --- input room, pipe dropping into the writer's north wall ---------------------------------
room(2, 0, 4, 2)
put(3, 1, "I")
put(3, 3, "v")
put(3, 4, "v")

# --- writer: room x0-13, interior x1-12 / y6-17 ---------------------------------------------
room(0, 5, 13, 18)

# lanes y6..y13, bottom lane westbound, parity alternating up.  r M r s W s stores a pair
# swapped; m counts it; d/a climb north while BP>0 and fall straight into a chute when spent.
for y in range(6, 14):
    if y % 2:  # westbound: entered at x10 from below
        put(1, y, "vdmsWsrMr<")
    else:  # eastbound: entered at x2 from below
        put(2, y, ">rMrsWsmav")

# y14 -- odd branch (x turned the man north into x4): take v1 for the ninth pipe, halve, climb.
# The even branch joins at (9,14) heading east; both cross the shared guard `a` at (10,14).
put(5, 14, ">rs]")
put(9, 14, ">av")

# y15 -- entry, walked WEST off the riser bounce at (12,15): read n, send it on the n-pipe,
# BP = n, branch on parity.  Spawn at @(9,15) heads east and bounces off the same `<`.
put(5, 15, "xbsr@")
put(12, 15, "<")

# y16 -- even branch: halve, climb to join the odd row heading east.  The two `s` cells at the
# chute bottoms both bind the go-pipe (bottom pipe of the fan, so it is nearest from anywhere
# below the band): whichever chute the spent man falls down, he sends go mid-fall.
put(1, 16, "s")
put(5, 16, ">]")
put(9, 16, "^")
put(11, 16, "s")

# y17 -- riser corridor: both chutes turn east and climb x12 back to the entry bounce
put(1, 17, ">")
put(11, 17, ">")
put(12, 17, "^")

# --- 11 pipes: 8 pair slots (capacity 2), odd, n, go ----------------------------------------
for y in range(6, 17):
    put(14, y, ">>")

# --- reader: room x16-21, interior x17-20 / y6-18 -------------------------------------------
# Four interior columns: the entry chain lies over the pair-band rows (b/v/m carry no pipe
# binding, so they can sit on pipe rows).  The pop loop is a 2x3 block whose walk order is
# d-BEFORE-m, so the entry crosses one `m` after `b` to start at BP = n-1; then d sees n-k
# after pop k and exits exactly on pop n.
room(16, 5, 21, 19)

put(17, 13, ">bv")  # after r(n) heading north: turn east on the bottom pair row, BP = n
put(17, 15, "r")  # n-read: row y15 is the only row where the n-pipe is nearest
put(19, 14, "m")  # BP = n-1 on the drop into U
put(19, 15, "Uv")  # pop loop: U > v s < d m, 6 cells in 2x3, one pop per lap
put(17, 16, "r")  # go-gate: blocks here with the whole n/BP chain still AHEAD of him, so
#                   only 6 cells run after the go token lands (was 9 behind the old gate spot)
put(19, 16, "m")
put(20, 16, "s")
put(17, 17, "^")
put(18, 17, "<")  # exit man (heading west) and spawn (heading north) both turn up into the gate
put(19, 17, "d")
put(20, 17, "<")
put(17, 18, "@")
put(18, 18, "^")

# --- output room fed from the reader's south wall -------------------------------------------
put(20, 20, "v")
put(20, 21, "v")
room(19, 22, 21, 24)
put(20, 23, "O")

if __name__ == "__main__":
    print("\n".join("".join(row).rstrip() for row in grid))
