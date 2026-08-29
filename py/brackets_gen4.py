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
    with open("../programs/brackets.man", "w") as f:
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
    # prologue + loop head (return column is c1, joining at (2,1))
    cc(0, 0, "@v")
    cc(1, 1, "r")
    # Head sits one column west so column 4 empties out entirely and compress()
    # can delete it: 22 wide -> 21, footprint 484 -> 441.  The return lane climbs
    # column 1 and turns east at the '>'; the prologue drops down column 2 and
    # gets its own BP test ('a', entered heading south) before joining the read row.
    # q and d live *in* the climb column, stacked, so the head costs no columns of
    # its own: the returning man walks q, then d turns him east straight onto the
    # read row.  Columns 3 and 4 empty out and compress() deletes both.
    cc(4, 0, "q")
    cc(3, 0, "d")  # BP>0 -> east (read row); BP==0 -> north to END
    cc(2, 0, ">")
    cc(2, 4, "^")  # end-of-input: travel east, then north
    cc(7, 1, "<")  # prologue drops down column 2 and turns into the climb here
    # end of input, on rows 0/1
    cc(0, 4, ">WX1NsH")  # X: S==0 -> straight, emit -1 => P prints 0
    cc(1, 6, ">1s0sH")  # S>0  -> south, bump i then emit i
    # main lane
    cc(3, 4, "rsbx")  # r=A:c  s=ping P  b=BP:c  x=bit0
    cc(2, 7, ">v")  # '(' : bit0==0 -> north, then down column 8
    cc(4, 7, ">")  # bit0==1 -> south
    cc(4, 10, "]x")  # bit1: 1 -> opener (south), 0 -> closer (north)
    # closer subtree, rows 3-5
    cc(3, 11, ">]x")  # bit2: 0 -> ')' north, 1 -> south
    cc(2, 13, ">")
    cc(2, 19, "v")  # ')' column
    cc(4, 13, ">]]]x")  # bit5: 0 -> ']' north, 1 -> '}' south
    cc(3, 17, ">")
    cc(3, 18, "v")  # ']' column
    # '}' needs no turn cell: bit5=1 already sends it south down column 17
    # opener subtree, row 5
    cc(5, 11, ">]]]]x")  # bit5: 1 -> '{' south (col 16), 0 -> '[' north
    cc(3, 15, "v<")  # '[' walks north over the ']'s, turns west then drops
    # push lane, row 7, running west:  S = 3S + t
    cc(6, 8, "1")
    cc(6, 15, "23")
    cc(7, 4, "M+++<")
    cc(7, 15, "<<")
    cc(7, 0, "^")
    # pop lane.  Bijective base 3, so `)` on an empty stack would fake a match
    # (-3 is divisible by 3); the X after the first W rejects S == 0 first.
    cc(8, 17, "321")
    cc(9, 13, "HsXW<<<")  # X: S>0 -> north; S==0 -> west, A is already 0
    cc(8, 7, "XNW/W3M-<")  # entered northbound at col 15, then west
    cc(8, 0, "^")
    cc(9, 4, "Hs0<")  # remainder != 0: tell P to emit i


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
    """Four interior rows instead of five: one row off the whole program.

    Row 1 is the "emit i" tail, row 2 the head, row 3 the "emit 0" tail, row 4
    the i += 1 lane running back west into the climb at column 0.
    """
    pp(0, 0, "@v")  # prologue drops onto its own '>' so it enters the head east
    pp(1, 0, ">>rbdx")  # d: BP>0 -> south (bump i); x: 0 -> north, -1 -> south
    pp(0, 5, ">WsH")  # signal 0: W puts i in A, emit it
    pp(2, 4, "1>0sH")  # signal -1: emit a literal 0
    pp(3, 0, "^")
    pp(3, 2, "M+<")  # i += 1, running west, then north into the head


def build() -> None:
    global C_R, C_C, P_R, P_C
    room(0, 0, 2, 2)
    put(1, 1, "I")
    v(3, 1, "vvvvv")
    room(8, 0, 27, 25)
    C_R, C_C = 9, 1
    build_c2()
    room(0, 5, 5, 15)
    P_R, P_C = 1, 6
    build_p()
    v(6, 8, "^^")
    h(1, 16, ">>")
    room(0, 18, 2, 20)
    put(1, 19, "O")


if __name__ == "__main__":
    main()
