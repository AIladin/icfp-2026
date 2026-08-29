"""reverse-a-list, 8 paired slots, 21 wide: the riser column folded into bottom corridor rows.

Same machine as reverse8_gen (pairs in 2-cell slots, go-gate on the reader's exit path), with
two structural changes that delete the writer's return-riser column x12:

- The entry row runs EASTBOUND, so the returning man enters it from the west corridor and no
  east-side bounce column is needed.  `x` heading east turns odd(bit1)->SOUTH, even->NORTH.
- The pipe stack reorders to pairs(y6-13), n(y15), odd(y16), go(y17): U skips the empty n row
  on its way down, odd still pops last, and each control row sits exactly on the pipe its `s`
  or `r` must bind.  y14 and y18 are pipe-free corridor rows (even-route and chute-merge).

Width 21 = writer 13 + pipe channel 2 + reader 6.  Height budget has ~5 free rows before 21
binds, which is what pays for the two extra corridor rows.
"""

W, H = 21, 25
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


# --- input room, pipe into the writer's north wall ------------------------------------------
room(2, 0, 4, 2)
put(3, 1, "I")
put(3, 3, "v")
put(3, 4, "v")

# --- writer: room x0-12, interior x1-11 / y6-18 ---------------------------------------------
room(0, 5, 12, 19)

# lanes y6..y13, bottom lane westbound, identical to the 22-wide build
for y in range(6, 14):
    if y % 2:
        put(1, y, "vdmsWsrMr<")
    else:
        put(2, y, ">rMrsWsmav")

# y14 -- even corridor: halve, run east, climb into the bottom lane.  The odd branch joins the
# same `^` heading north.
put(6, 14, ">]")
put(10, 14, "^")

# y15 -- entry, EASTBOUND: the tail delivers the man to (2,15) heading north, `>` turns him in.
# Spawn @(1,15) walks straight into the entry; the west chute falls over the @ harmlessly.
put(1, 15, "@>rsbx")

# y16 -- odd branch (x turned him south): take v1 for the odd pipe, halve, `a` climbs north
# while BP>0 and falls east into the chute when n=1 leaves zero pairs.
put(6, 16, ">rs]av")

# y18 -- chute merge: both chutes send go on this row (go is the bottom pipe, nearest from
# here), then converge on the `^` at x3 and ride the tail x3/x2 back up to the entry.
put(3, 17, "<")
put(2, 17, "^")
put(1, 18, ">s^")
put(10, 18, "s<")

# --- 11 pipes: 8 pair slots (capacity 2), then n, odd, go -----------------------------------
for y in list(range(6, 14)) + [15, 16, 17]:
    put(13, y, ">>")

# --- reader: room x15-20, interior x16-19 / y6-18 -------------------------------------------
room(15, 5, 20, 19)

put(16, 14, ">")  # after r(n) heading north: turn east, BP = n-1 on the drop into U
put(17, 14, "b")
put(18, 14, "v")
put(16, 15, "r")  # n-read: y15 is the n-pipe row
put(18, 15, "m")
put(16, 16, "^")
put(18, 16, "U")  # pop loop: U v s < d m, one pop per lap, d exits west on pop n
put(19, 16, "v")
put(16, 17, "r")  # go-gate: y17 is the go-pipe row; blocks with the n/BP chain still ahead
put(18, 17, "m")
put(19, 17, "s")
put(16, 18, "^")
put(17, 18, "@")  # spawn bounces east off `<`, back over @, up into the gate
put(18, 18, "d")
put(19, 18, "<")

# --- output room fed from the reader's south wall -------------------------------------------
put(19, 20, "v")
put(19, 21, "v")
room(18, 22, 20, 24)
put(19, 23, "O")

if __name__ == "__main__":
    print("\n".join("".join(row).rstrip() for row in grid))
