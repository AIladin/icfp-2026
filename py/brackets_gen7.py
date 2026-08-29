"""Generate programs/brackets.man.

Design (see docs/vault/log/2026-07-24-brackets.md):
  Room C: B = stack (base-4, 2 bits per open bracket), BP = scratch bit-decoder.
  Room P: B = i (1-based position counter), owns the output pipe.
  Signals C -> P:  1 = increment i, 0 = "emit i", -1 = "emit 0".
"""

from __future__ import annotations

GRID: dict[tuple[int, int], str] = {}


def put(r: int, c: int, ch: str) -> None:
    if (r, c) in GRID and GRID[(r, c)] != ch:
        raise ValueError(f"overwrite at {(r, c)}: {GRID[(r, c)]!r} -> {ch!r}")
    GRID[(r, c)] = ch


def h(r: int, c: int, s: str) -> None:
    for k, ch in enumerate(s):
        if ch != "\0":
            put(r, c + k, ch)


def v(r: int, c: int, s: str) -> None:
    for k, ch in enumerate(s):
        if ch != "\0":
            put(r + k, c, ch)


def room(r0: int, c0: int, r1: int, c1: int) -> None:
    """Room with corners at (r0,c0)-(r1,c1) inclusive."""
    for c in range(c0 + 1, c1):
        put(r0, c, "-")
        put(r1, c, "-")
    for r in range(r0 + 1, r1):
        put(r, c0, "|")
        put(r, c1, "|")
    for r, c in ((r0, c0), (r0, c1), (r1, c0), (r1, c1)):
        GRID[(r, c)] = "+"


def compress() -> None:
    """Drop rows holding only spaces/vertical bars and columns holding only
    spaces/dashes.  Both are pure travel, so removing them shrinks the
    bounding box without changing behaviour."""
    while True:
        rows = max(r for r, _ in GRID) + 1
        cols = max(c for _, c in GRID) + 1
        dead_r = [
            r
            for r in range(rows)
            if all(GRID.get((r, c), " ") in " |" for c in range(cols))
        ]
        dead_c = [
            c
            for c in range(cols)
            if all(GRID.get((r, c), " ") in " -" for r in range(rows))
        ]
        if not dead_r and not dead_c:
            return
        keep_r = [r for r in range(rows) if r not in set(dead_r)]
        keep_c = [c for c in range(cols) if c not in set(dead_c)]
        rmap = {r: i for i, r in enumerate(keep_r)}
        cmap = {c: i for i, c in enumerate(keep_c)}
        new = {
            (rmap[r], cmap[c]): ch
            for (r, c), ch in GRID.items()
            if r in rmap and c in cmap
        }
        GRID.clear()
        GRID.update(new)


def render() -> str:
    rows = max(r for r, _ in GRID) + 1
    cols = max(c for _, c in GRID) + 1
    return "\n".join(
        "".join(GRID.get((r, c), " ") for c in range(cols)).rstrip() for r in range(rows)
    )


def main() -> None:
    build()
    compress()
    out = render() + "\n"
    with open("../programs/brackets7.man", "w") as f:
        f.write(out)
    print(out)


C_R, C_C = 6, 1  # room C interior origin (grid coords)
P_R, P_C = 9, 33  # room P interior origin


def cc(r: int, c: int, s: str, *, down: bool = False) -> None:
    """Place a run inside room C (local coords)."""
    if down:
        v(C_R + r, C_C + c, s)
    else:
        h(C_R + r, C_C + c, s)


def pp(r: int, c: int, s: str, *, down: bool = False) -> None:
    if down:
        v(P_R + r, P_C + c, s)
    else:
        h(P_R + r, P_C + c, s)


def build_c2() -> None:
    """Room C, local coords: cc(r, c) -> grid (8+r, 1+c).

    Rows: 0 prologue+end-of-input, 1 turns, 2 read row + bit2, 3 head + bit5
    (closers), 4 bit5 (openers), 5 opener digits, 6 push lane, 7 pop
    arithmetic, 8 pop funnel.

    The per-character cycle is a closed ring, so it costs its own perimeter.
    Every subtree therefore sits as far WEST as the funnel allows: the drop
    columns are 10..14 instead of 12..16, which takes two ticks off each leg
    for every character that is not '('.
    """
    # --- prologue: swallow n on the way down the return column -------------
    cc(0, 0, "@v")
    cc(3, 1, "r")
    cc(6, 1, "<")
    # --- loop head: q and d live inside the climb column -------------------
    cc(6, 0, "^")
    cc(3, 0, "q")
    cc(2, 0, "d")  # BP>0 -> east onto the read row; BP==0 -> north to END
    cc(1, 0, ">")
    # --- end of input: once per case, so cells matter and ticks do not -----
    cc(1, 2, "^")
    cc(0, 2, ">")
    cc(0, 14, "WX")  # X on sign(S): >0 -> south, ==0 -> straight east
    cc(1, 15, "1s0sH", down=True)  # unclosed openers: bump i, then emit i
    cc(0, 16, "v")
    cc(1, 16, "1Nsh".replace("h", "H"), down=True)  # balanced: emit literal 0
    # --- read row ----------------------------------------------------------
    cc(2, 2, "rsbx")  # r=A:c  s=ping P  b=BP:c  x=bit0
    # '(' : bit0==0 -> north, then straight down its own column
    cc(1, 5, ">v")
    cc(5, 6, "1")
    # everything else: bit0==1 -> south, one shift, then bit1
    cc(3, 5, ">]x")  # bit1: 1 -> opener (south), 0 -> closer (north)
    # --- closers -----------------------------------------------------------
    cc(2, 7, ">]x")  # bit2: 0 -> ')' north, 1 -> south
    cc(1, 9, "v")  # ')' bounces back into its own x and leaves heading east
    cc(2, 11, "v")  # ')' drops down the column nearest the funnel
    cc(7, 11, "1")
    cc(8, 11, "<")
    cc(3, 9, ">]]]x")  # bit5: 0 -> ']' north, 1 -> '}' south
    cc(2, 13, ">v")  # ']' steps one column east and drops
    cc(7, 13, "32")  # '}' digit, then ']' digit
    cc(8, 13, "<<")
    # --- openers -----------------------------------------------------------
    cc(4, 7, ">]]]]x")  # bit5: 1 -> '{' south, 0 -> '[' north
    cc(5, 12, "3")  # '{' lands on its digit one row down
    cc(1, 12, "<")  # '[' climbs out over the closer chain and turns west
    cc(1, 10, "v")  # ... then drops down the column beside the push lane
    cc(5, 10, "2")
    # --- push lane, running west:  S = 3S + t ------------------------------
    cc(6, 6, "<")
    cc(6, 10, "<")
    cc(6, 12, "<")
    cc(6, 2, "M+++")
    # --- pop lane.  Bijective base 3, so a closer on an empty stack would
    # fake a match (-3 is divisible by 3); the X after the first W rejects
    # S == 0 before the division.
    cc(8, 9, "XW")  # S>0 -> north into the chain; S==0 -> west to the tail
    cc(8, 6, "Hs0")  # S == 0: closer on an empty stack, emit i
    cc(7, 1, "XNW/W3M-<")
    cc(7, 0, "^")
    cc(8, 1, ">0sH")  # remainder != 0: tell P to emit i


def build_c() -> None:
    # --- loop head -------------------------------------------------------
    cc(0, 0, "@r")  # prologue: swallow the length prefix n
    cc(0, 4, "v")
    cc(0, 27, "<")  # return row 0 runs west into (0,4)
    cc(1, 4, "q")
    cc(2, 4, "a1srbv")  # a: BP>0 -> east; 1 s: ping P; r: A=c; b: BP=c
    # --- classification tree (every x is entered heading south) -----------
    cc(3, 9, "x")  # bit0: 1 -> west, 0 -> '(' east
    cc(3, 8, "v")
    cc(3, 20, "v")
    cc(4, 8, "]")
    cc(5, 8, "x")  # bit1: 1 -> opener west, 0 -> closer east
    cc(5, 2, "v")
    cc(5, 12, "v")
    cc(6, 2, "]]]]", down=True)  # BP = c>>5
    cc(6, 12, "]]]]", down=True)
    cc(10, 2, "x")  # bit5: 1 -> '{' west, 0 -> '[' east
    cc(10, 1, "v")
    cc(10, 3, "v")
    cc(10, 12, "x")  # bit5: 1 -> west (')' or '}'), 0 -> ']' east
    cc(10, 11, "v")
    cc(10, 16, "v")
    cc(11, 11, "]")
    cc(12, 11, "x")  # bit6: 1 -> '}' west, 0 -> ')' east
    cc(12, 6, "v")
    cc(12, 22, "v")
    # --- push leaves: A=t then S = 4S+t ----------------------------------
    cc(4, 20, "1++++M>", down=True)  # '('
    cc(11, 1, "3++++M", down=True)  # '{'
    cc(11, 3, "2++++M", down=True)  # '['
    cc(10, 20, ">")
    cc(23, 1, ">")
    cc(23, 3, ">")
    # --- pop leaves: A=t; check S%4==t; S/=4 ------------------------------
    for col, digit in ((6, "3"), (16, "2"), (22, "1")):
        cc(13, col, digit + "W-M4W/WNX", down=True)
        cc(22, col + 1, "0sH")  # mismatch: tell P to emit i
        cc(23, col, ">")
    # --- returns ---------------------------------------------------------
    cc(10, 27, "^")
    cc(23, 27, "^")
    # --- end of input ----------------------------------------------------
    cc(24, 4, ">WX1Ns H")  # X: S==0 -> east, emit -1 ("print 0")
    cc(25, 6, ">1s0sH")  # S>0 -> south then east: bump i, emit i


def build_p() -> None:
    """Three interior rows, eight columns.

    ``X`` reads the *sign of A*, so one instruction splits all three signals --
    positive (bump i), zero (emit i), negative (emit 0).  That drops the ``b``
    and ``d``/``x`` pair the old head needed and buys back a row and a column.
    """
    pp(0, 1, "@v")  # prologue drops onto its own '>' so it enters the head east
    pp(0, 4, ">0sH")  # A < 0: emit a literal 0
    pp(1, 0, ">")  # the i += 1 lane climbs back in here
    pp(1, 2, ">rXWsH")  # A == 0: W puts i in A, emit it
    pp(2, 0, "^M+1<")  # A > 0: i += 1, running west


def build() -> None:
    global C_R, C_C, P_R, P_C
    room(0, 0, 2, 2)
    put(1, 1, "I")
    v(3, 1, "vvvv")
    room(7, 0, 26, 25)
    C_R, C_C = 8, 1
    build_c2()
    room(0, 3, 4, 12)
    P_R, P_C = 1, 4
    build_p()
    v(5, 6, "^^")
    h(1, 13, ">>")
    room(0, 15, 2, 17)
    put(1, 16, "O")


if __name__ == "__main__":
    main()
