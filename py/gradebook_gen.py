"""Generate programs/gradebook.man.

Layout
------
HEAD is one wide room.  All eight pipes leave/enter its SOUTH wall, so
`Nearest pipe resolution` degenerates to "which column am I in".

    pipe        col   role
    IN   in      2    input room  -> HEAD
    OUT  out     5    HEAD -> output room
    MAIN in      8    ring relay -> HEAD
    MAIN out    11    HEAD -> ring relay
    STASH in    14
    STASH out   17
    CONST in    20
    CONST out   23

    r-zones: IN 1-4    MAIN 6-10   STASH 12-16  CONST 18+
    s-zones: OUT 1-7   MAIN 9-13   STASH 15-19  CONST 21+
    safe   : IO 1-4    MAIN 9-10   STASH 15-16  CONST 21+

Token encoding on the MAIN ring
-------------------------------
    marker      0
    student id  id            (1000..9999, positive)
    grade       g - 999       (-999..-899, negative)

so a single `X` classifies any token.  Ring content is

    [0, id_1, g_11-999 ... g_1K-999, id_2, ...]

CONST ring holds [N, rem] in that cyclic order (rem = ops left in round).
STASH is a scratch FIFO, empty between operations.
"""

from __future__ import annotations

WALL_TOP = 0
LEFT = 0
IW = 26  # interior width: interior columns 1..26
PIPE = {
    "IN": 2,
    "OUT": 5,
    "MAINI": 8,
    "MAINO": 11,
    "STASHI": 14,
    "STASHO": 17,
    "CONSTI": 20,
    "CONSTO": 23,
}


class Grid:
    def __init__(self) -> None:
        self.cells: dict[tuple[int, int], str] = {}

    def put(self, r: int, c: int, ch: str) -> None:
        if r < 0 or c < 0:
            raise ValueError(f"negative cell {r},{c}")
        old = self.cells.get((r, c))
        if old is not None and old != ch:
            raise ValueError(f"collision at ({r},{c}): {old!r} vs {ch!r}")
        self.cells[(r, c)] = ch

    def row(self, r: int, spec: dict[int, str]) -> None:
        for c, ch in spec.items():
            if len(ch) == 1:
                self.put(r, c, ch)
            else:  # multi-char run laid out eastwards from c
                for i, x in enumerate(ch):
                    self.put(r, c + i, x)

    def col(self, c: int, spec: dict[int, str]) -> None:
        for r, ch in spec.items():
            self.put(r, c, ch)

    def render(self) -> str:
        if not self.cells:
            return ""
        h = max(r for r, _ in self.cells) + 1
        w = max(c for _, c in self.cells) + 1
        lines = []
        for r in range(h):
            line = "".join(self.cells.get((r, c), " ") for c in range(w))
            lines.append(line.rstrip())
        return "\n".join(lines) + "\n"


def room(g: Grid, top: int, left: int, bottom: int, right: int) -> None:
    """Draw room walls (inclusive corners)."""
    for c in range(left + 1, right):
        g.put(top, c, "-")
        g.put(bottom, c, "-")
    for r in range(top + 1, bottom):
        g.put(r, left, "|")
        g.put(r, right, "|")
    for r, c in ((top, left), (top, right), (bottom, left), (bottom, right)):
        g.put(r, c, "+")


# ---------------------------------------------------------------- geometry --
# HEAD's south wall, left to right.  MAIN is deliberately leftmost: its r/s
# pair is the hottest loop in the program and wants the tightest zone.
P_MAINI, P_MAINO = 2, 7
P_STASHI, P_STASHO = 10, 13
P_IN, P_OUT = 16, 19
P_TMPI, P_TMPO = 22, 25
P_CONSTI, P_CONSTO = 28, 31
IWIDTH = 38  # HEAD interior columns 1..38

# safe zones: every `r` AND `s` in the range hits the ring named
Z_MAIN = (1, 5)
Z_STASH = (11, 12)
Z_IO = (17, 18)
Z_TMP = (23, 24)
Z_CONST = (29, 32)


def relay(g, top, left, width=4):
    """`r` then `s` forever.  Incoming pipe meets the top wall on the right
    half, outgoing leaves it on the left half; only one of each, so the
    nearest-pipe rule is moot inside."""
    room(g, top, left, top + 3, left + width + 1)
    a, b = top + 1, top + 2
    g.row(a, {left + 1: ">", left + width - 1: "@", left + width: "v"})
    g.row(b, {left + width: "<", left + width - 1: "r", left + 2: "s", left + 1: "^"})


def build(head_rows: int):
    g = Grid()
    hb = head_rows + 1
    room(g, 0, 0, hb, IWIDTH + 1)

    # --- MAIN relay, directly under HEAD: the return leg is only 2 cells
    relay(g, hb + 3, 1)
    g.col(P_MAINI, {hb + 1: "^", hb + 2: "^"})

    # --- STASH / TMP / CONST relays and the I/O rooms
    for cin in (P_STASHI, P_TMPI, P_CONSTI):
        relay(g, hb + 3, cin - 1)
        if cin == P_STASHI:
            # STASH doubles as the counter pipe: AVG/TOP park `s` values in it
            # and read the count back with `q`, which costs no round trip.  The
            # pipe therefore has to be long enough to hold s <= 4 of them, and
            # the jog west also drags its HEAD-side column next to MAIN's.
            g.col(cin, {hb + 2: "^"})
            g.row(hb + 1, {cin: "<", cin - 1: "-", cin - 2: "^"})
        else:
            g.col(cin, {hb + 1: "^", hb + 2: "^"})
        g.col(cin + 3, {hb + 1: "v", hb + 2: "v"})
    room(g, hb + 3, P_IN - 1, hb + 5, P_IN + 1)
    g.put(hb + 4, P_IN, "I")
    room(g, hb + 3, P_OUT - 1, hb + 5, P_OUT + 1)
    g.put(hb + 4, P_OUT, "O")
    g.col(P_IN, {hb + 1: "^", hb + 2: "^"})
    g.col(P_OUT, {hb + 1: "v", hb + 2: "v"})

    # --- MAIN out: down col 7, east under the relays, then a boustrophedon
    #     folding ~88 cells (capacity 91, worst-case ring is 81 tokens) into
    #     four rows.  Col 5 is kept clear of every fold row so the riser has a
    #     lane home into the MAIN relay's floor.  Length is latency: every
    #     operation waits a revolution, so this is sized just big enough.
    E = 46
    g.col(P_MAINO, {hb + 1: "v", **{r: "|" for r in range(hb + 2, hb + 7)}})
    g.put(hb + 7, P_MAINO, ">")
    g.row(hb + 7, {c: "-" for c in range(P_MAINO + 1, E)})
    g.put(hb + 7, E, "v")
    g.put(hb + 8, E, "<")
    g.row(hb + 8, {c: "-" for c in range(6, E)})
    g.put(hb + 8, 5, "^")
    g.put(hb + 7, 5, "^")
    return g, hb



# ------------------------------------------------------------------- code --
# Zones implied by the pipe columns above:
#   MAIN  r 1-5  s 1-9      STASH r 7-12 s 11-15
#   IN    r 14-18  OUT s 17-21   TMP r 20-24 s 23-27   CONST r 26+ s 29+
#
# Column 44 is a return highway running north into row 1, a clean lane running
# west into OPLOOP's entry at (2,1).  Every operation ends by stepping on it.
#
# Registers, per operation:
#   GET/SET  B = queried id during the scan, BP = subject during the skip
#   AVG      TMP = subject, B = running sum
#   TOP      TMP = subject, B = best token, STASH = [best id] (+ the candidate)

def emit(g):
    R = g.row

    # ---- return highway and the round/op loop -----------------------------
    R(1, {35: "<", 24: "v"})
    R(2, {24: ">", 25: "1", 26: "M", 27: "r", 29: "s", 30: "r", 31: "X",
          32: "v"})
    R(3, {31: "<", 30: "-", 29: "s", 2: "v", 36: "x", 33: "v",
          37: ">", 38: "v"})
    R(7, {32: "<", 18: "r", 17: "-", 16: "v", 36: "x", 34: "v",
          37: ">", 38: "v"})
    R(8, {16: ">", 29: "s", 31: "v"})
    R(9, {31: "<", 2: "^"})

    # ---- opcode -> four ways, A still holds op on arrival -----------------
    R(5, {2: ">", 14: "r", 24: "b", 36: "x"})
    R(4, {36: "]"})
    R(6, {36: "]"})

    # ---- boot: cnt = N*(K+1) into BP, marker onto the ring ----------------
    R(10, {1: "@", 14: "r", 29: "s", 30: "M", 31: "0", 32: "v"})
    R(11, {32: "<", 31: "s", 18: "r", 17: "*", 16: "+", 15: "b", 14: "0",
           6: "s", 2: "v"})
    R(12, {2: ">", 5: "`999`", 10: "M", 20: "v"})
    R(13, {2: ">", 4: ">", 20: "v"})
    R(14, {16: "<", 15: "+", 6: "s", 5: "m", 4: "d", 1: "v"})
    R(15, {20: "<", 18: "r", 17: "-", 16: "X"})
    R(16, {16: "<", 6: "s", 5: "m", 2: "d", 1: "v"})
    R(17, {1: "v"})
    R(18, {1: ">", 35: "^"})

    # ---- FIND: GET and SET share the id scan and the subject skip ---------
    R(19, {38: "<", 23: "s", 18: "r", 17: "M", 2: "v"})
    R(20, {6: "<", 2: "v"})
    R(21, {2: ">", 3: "r", 4: "s", 5: "~", 6: "X", 7: "v"})
    R(22, {6: "<", 2: "^"})
    R(23, {7: ">", 18: "r", 19: "b", 20: "v"})
    R(24, {20: "<", 2: "v"})
    R(25, {2: "v"})
    R(26, {2: ">", 3: "r", 4: "m", 5: "d", 6: "v"})
    R(27, {5: "<", 4: "s", 2: "^", 22: ">", 30: "v"})
    R(28, {6: ">", 11: "s", 20: "r", 21: "b", 22: "x"})
    R(29, {22: "<", 11: "r", 6: "s", 5: "M", 2: "v"})
    R(30, {2: ">", 3: "`999`", 8: "+", 17: "s", 35: "^"})
    R(32, {30: "<", 11: "r", 2: "v"})
    R(33, {2: ">", 18: "r", 19: "M", 20: "v"})
    R(34, {20: "<", 14: "`999`", 13: "W", 12: "-", 6: "s", 2: "v"})
    R(35, {2: ">", 35: "^"})

    # ---- AVG --------------------------------------------------------------
    R(38, {34: "<", 18: "r", 13: "s", 12: "0", 11: "M", 2: "v"})
    R(41, {5: "<", 2: "v"})
    R(42, {2: ">", 3: "r", 4: "s", 5: "X", 6: "v"})
    R(43, {5: "<", 2: "^"})
    R(44, {6: "<", 2: "v"})
    R(45, {2: "v"})
    R(46, {5: "<", 2: "v", 14: "<"})
    R(47, {2: ">", 3: "r", 4: "s", 5: "X", 10: "v"})
    R(48, {5: ">", 11: "r", 13: "s", 14: "b", 15: "v"})
    R(49, {15: "<", 2: "v"})
    R(50, {2: "v"})
    R(51, {2: ">", 3: "r", 4: "m", 5: "d", 6: "v"})
    R(52, {5: "<", 4: "s", 2: "^"})
    R(53, {6: ">", 7: "s", 8: "+", 9: "M", 14: "^"})
    R(54, {10: ">", 11: "r", 12: "W", 13: "s", 26: "r", 27: "M", 29: "s",
           30: "r", 31: "s", 32: "v"})
    R(55, {32: "<", 12: "r", 11: "/", 10: "M", 4: "`999`", 3: "+", 2: "v"})
    R(56, {2: ">", 17: "s", 35: "^"})

    # ---- TOP --------------------------------------------------------------
    R(59, {33: "<", 18: "r", 17: "v"})
    R(60, {17: ">", 23: "s", 24: "0", 25: "v"})
    R(61, {25: "<", 13: "s", 6: "`0001`", 5: "N", 4: "M", 2: "v"})
    R(62, {5: "<", 2: "v"})
    R(63, {2: ">", 3: "r", 4: "s", 5: "X", 6: "v"})
    R(64, {5: "<", 2: "^"})
    R(65, {6: "<", 2: "v"})
    R(66, {2: "v"})
    R(67, {5: "<", 2: "v", 14: "<", 16: "<", 21: "<"})
    R(68, {2: ">", 3: "r", 4: "s", 5: "X", 18: "v"})
    R(69, {5: ">", 13: "s", 20: "r", 23: "s", 24: "b", 25: "v"})
    R(70, {25: "<", 2: "v"})
    R(71, {2: "v"})
    R(72, {2: ">", 3: "r", 4: "m", 5: "d", 6: "v"})
    R(73, {5: "<", 4: "s", 2: "^", 9: ">", 20: "v"})
    R(74, {6: ">", 7: "s", 8: "-", 9: "X", 19: "v"})
    R(75, {9: ">", 10: "+", 11: "M", 12: "r", 14: "^"})
    R(76, {20: "<", 12: "r", 11: "v"})
    R(77, {11: ">", 13: "s", 15: "v"})
    R(78, {15: "<", 12: "r", 10: "v"})
    R(79, {10: ">", 16: "^"})
    R(80, {18: ">", 20: "r", 24: "v"})
    R(81, {24: "<", 12: "r", 11: "v"})
    R(82, {11: ">", 17: "s", 35: "^"})
    # tie on the grade: keep the smaller id.  tok == best, so `+` rebuilds it
    # and the STASH parks it while the two ids are compared.
    R(84, {19: "<", 18: "+", 13: "s", 12: "r", 11: "M", 9: "v",
           22: ">", 24: "v"})
    R(85, {9: ">", 12: "r", 13: "-", 22: "X"})
    R(86, {24: "<", 15: "+", 13: "s", 11: "v"})
    R(87, {11: ">", 12: "r", 13: "M", 21: "^"})
    R(88, {22: "<", 13: "W", 11: "s", 9: "v"})
    R(89, {9: ">", 12: "r", 13: "M", 21: "^"})


if __name__ == "__main__":
    import sys

    # Rows are written with gaps for legibility; squeeze the empty ones out.
    # Safe because every jump either lands on a row that carries an
    # instruction or falls through empty cells, and removal preserves order.
    probe = Grid()
    emit(probe)
    used = sorted({r for r, _ in probe.cells})
    remap = {old: i + 1 for i, old in enumerate(used)}

    g, hb = build(len(used))
    plain = g.row
    g.row = lambda r, spec: plain(remap[r], spec)
    emit(g)
    sys.stdout.write(g.render())
