r"""Emit the `matmul` program.

Pipeline (see docs/vault/log/2026-07-25-matmul.md for the derivation):

    IN -> LOADER -> PADK -> TAIL -> [ring-back drum] -> MUL -> ACC -> OUT
                 \-> [A drum] ------------------------/      \-> ACCR (acc ring)

LOADER reads N M K, forwards A row-major raw into the A drum (plus one dummy), then forwards B
doubled (2*b) into PADK. PADK inserts PAD=1 after every K values; LOADER appends ENDPAD=3 at the
end. The ring therefore reads

    B[0][*] PAD B[1][*] PAD ... B[M-1][*] PAD ENDPAD

MUL holds a = A[i][t] in B, multiplies every even token, pushes it back on the ring, and forwards
2*a*b to ACC. On PAD it forwards the token itself (1) as a control word and pulls the next `a`; on
ENDPAD it forwards 3, which tells ACC to dump the row.

ACC keeps K accumulators plus an odd MARK=1 in its own ring. t=0 pushes fresh products (INIT), later
t accumulate, ENDPAD dumps acc>>1 to the output and empties the ring.
"""

from __future__ import annotations

ARROW = {(1, 0): ">", (-1, 0): "<", (0, 1): "v", (0, -1): "^"}
BODY = {(1, 0): "-", (-1, 0): "-", (0, 1): "|", (0, -1): "|"}


def sign(n: int) -> int:
    return (n > 0) - (n < 0)


class Canvas:
    def __init__(self) -> None:
        self.cells: dict[tuple[int, int], str] = {}

    def put(self, x: int, y: int, ch: str) -> None:
        old = self.cells.get((x, y))
        if old is not None and old != ch:
            raise ValueError(f"collision at ({x},{y}): {old!r} vs {ch!r}")
        self.cells[(x, y)] = ch

    def block(self, x: int, y: int, lines: list[str]) -> None:
        """A room interior; `.` is a nop, a space leaves the cell empty (also a nop)."""
        for dy, line in enumerate(lines):
            for dx, ch in enumerate(line):
                if ch != " ":
                    self.put(x + dx, y + dy, ch)

    def room(self, x: int, y: int, w: int, h: int) -> None:
        for i in range(w):
            self.put(x + i, y, "+" if i in (0, w - 1) else "-")
            self.put(x + i, y + h - 1, "+" if i in (0, w - 1) else "-")
        for j in range(1, h - 1):
            self.put(x, y + j, "|")
            self.put(x + w - 1, y + j, "|")

    def pipe(self, waypoints: list[tuple[int, int]]) -> int:
        """waypoints[0] is a source-room border cell, waypoints[-1] a destination border cell.

        Returns the number of carrying cells (capacity in values).
        """
        cells: list[tuple[int, int]] = [waypoints[0]]
        for (x0, y0), (x1, y1) in zip(waypoints, waypoints[1:]):
            if x0 != x1 and y0 != y1:
                raise ValueError(f"pipe leg ({x0},{y0})->({x1},{y1}) is not axis-aligned")
            step = (sign(x1 - x0), sign(y1 - y0))
            x, y = x0, y0
            while (x, y) != (x1, y1):
                x, y = x + step[0], y + step[1]
                cells.append((x, y))
        for i in range(1, len(cells) - 1):
            (px, py), (cx, cy), (nx, ny) = cells[i - 1], cells[i], cells[i + 1]
            din, dout = (cx - px, cy - py), (nx - cx, ny - cy)
            edge = i in (1, len(cells) - 2)
            self.put(cx, cy, ARROW[dout] if edge or din != dout else BODY[dout])
        return len(cells) - 2

    def render(self) -> str:
        w = max(x for x, _ in self.cells) + 1
        h = max(y for _, y in self.cells) + 1
        rows = ["".join(self.cells.get((x, y), " ") for x in range(w)).rstrip() for y in range(h)]
        return "\n".join(rows) + "\n"


def serpentine(x0: int, x1: int, y0: int, rows: int) -> list[tuple[int, int]]:
    """Boustrophedon waypoints; an R x C block stores R*C values in C columns of width."""
    pts: list[tuple[int, int]] = []
    for i in range(rows):
        y = y0 + i
        pts += [(x0, y), (x1, y)] if i % 2 == 0 else [(x1, y), (x0, y)]
    return pts


# --- room interiors ---------------------------------------------------------------------------
# `.` is a nop.  Coordinates in comments are interior, 1-based.

# LOADER 15x9. All three outgoing pipes on the south face: PA col 2, PK col 8, GT col 14, so only
# the column decides an `s` (PA x<=5, PK 6..11, GT x>=12). One incoming pipe -> every `r` is free.
LOADER = [
    "@rMrW*br...s*Mv",
    ".v............<",
    ".>rsmdv........",
    ".^...<v........",
    ".vs0..<........",
    ".W....>.>rM+smv",
    ".b....^vd.....<",
    ".>....^>...3sv.",
    "......Hs.....<.",
]
LOADER_PA, LOADER_GT, LOADER_PK = 2, 8, 14

# PADK 12x4: B=K, BP counts, emits PAD=1 after every K tokens. One in, one out.
PADK = [
    "@rMbv.......",
    ".v..<.......",
    ".>rsmd1sWbWv",
    ".^...<.....<",
]

TAIL = ["@>Rv", ".^s<"]  # merge loader stream + ring return with `R`
ACCR = ["@>rv", ".^s<"]  # the accumulator ring's second room

# MUL 18x5. North: ring-back(in) 12, ring-fwd(out) 13, GATE(in) 2. South: A-queue(in) 12, prod 13.
# rows 1-3 north band, rows 4-5 south band. Hot loop is the 10 cells
#   (15,2)r (14,2)s (13,2)v (13,3)b (13,4)x -> (14,4)* (15,4)s (16,4)^ (16,3). (16,2)<
MUL = [
    "@rv...>..>.....v..",
    "............vsr<..",
    "...v......<.b.....",
    "..>....rM^x]x*s^..",
    "...>s.^Mrs<.......",
]
MUL_RB, MUL_RF, MUL_GT, MUL_PA, MUL_PR = 18, 14, 5, 12, 13

# ACC 20x12.  Interior x15..34, y40..51 at the current placement.  Ports: prod(in) north x30,
# out south x16, accback(in) south x18, accfwd(out) south x24.  Pipe choice is pure geometry:
# `s` picks accfwd iff x >= 21, `r` picks prod iff |x-30|+(y-38) < |x-18|+(53-y).
#
# Four lanes.  ACCUM (x22..25, y44..46) is the tick bottleneck and is a minimal 10-cell ring:
#   r(prod) b x | M > r(accb) + ^ s(accf) <
# 7 instructions + 3 turns is the floor, so 10 cells is the floor -- 3 rows x 4 cols, with `x`
# doing double duty as the fourth corner.  INIT (x27..30, y45..48) runs 12; it only sees t=0.
ACC = [
    "....v...<........@v.",
    ".....>.........v....",
    "......vx^..v<.......",
    ".......]....s.......",
    ".......xbr<<1.......",
    "......rM..s.xbr<..<.",
    "......s>r+^.........",
    "v1Mx.^>....^........",
    "W..b........>s.^....",
    "}..r................",
    ">s>^<...............",
]
ACC_OUT, ACC_AF, ACC_AB, ACC_PR = 2, 10, 16, 16




# --- routing ----------------------------------------------------------------------------------

MAX_W, MAX_H = 120, 120


class Router:
    """BFS over free cells.  A pipe body must keep one cell of clearance from every room wall so a
    bend can never be read as a second pipe start (see `Pipe start scanning may be greedy`)."""

    def __init__(self, canvas: Canvas) -> None:
        self.c = canvas
        self.reserved: set[tuple[int, int]] = set()
        self.near_wall: set[tuple[int, int]] = set()
        for (x, y), ch in canvas.cells.items():
            if ch in "+-|=:":
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    self.near_wall.add((x + dx, y + dy))

    def route(self, start: tuple[int, int], goal: tuple[int, int], via: list[tuple[int, int]] | None = None) -> list[tuple[int, int]]:
        """Waypoints from a source border cell to a destination border cell, through `via` in order."""
        legs = [start, *(via or []), goal]
        path = [legs[0]]
        for i, (a, b) in enumerate(zip(legs, legs[1:])):
            leg = self._bfs(a, b, i > 0, i < len(legs) - 2)
            self.reserved |= set(leg)
            path += leg[1:]
        return path

    def _bfs(self, a: tuple[int, int], b: tuple[int, int], a_free: bool, b_free: bool) -> list[tuple[int, int]]:
        """Direction-aware BFS.  A bend is an arrowhead, and an arrowhead whose backward cell is a
        room border reads as a second pipe start -- so turns are banned on cells that back onto a
        wall (`Pipe start scanning may be greedy`)."""
        blocked = set(self.c.cells) | self.reserved
        walls = {c for c, ch in self.c.cells.items() if ch in "+-|=:"}
        dirs = ((1, 0), (-1, 0), (0, 1), (0, -1))
        seen: dict[tuple[int, int, int], tuple | None] = {}
        frontier = []
        for k, (dx, dy) in enumerate(dirs):
            n = (a[0] + dx, a[1] + dy)
            if n == b or n not in blocked:
                seen[(n[0], n[1], k)] = None
                frontier.append((n[0], n[1], k))
        budget = MAX_W * MAX_H * 4
        while frontier:
            budget -= len(frontier)
            if budget < 0:
                raise RuntimeError("router budget exhausted")
            nxt = []
            for state in frontier:
                x, y, k = state
                if (x, y) == b:
                    out = []
                    cur: tuple | None = state
                    while cur is not None:
                        out.append((cur[0], cur[1]))
                        cur = seen[cur]
                    return [a, *out[::-1]]
                back = (x - dirs[k][0], y - dirs[k][1])
                for k2, (dx, dy) in enumerate(dirs):
                    if k2 != k and back in walls:
                        continue  # no bend backing onto a wall
                    n = (x + dx, y + dy)
                    if not (0 <= n[0] < MAX_W and 0 <= n[1] < MAX_H):
                        continue
                    if n != b and n in blocked:
                        continue
                    if (n[0], n[1], k2) in seen:
                        continue
                    seen[(n[0], n[1], k2)] = state
                    nxt.append((n[0], n[1], k2))
            frontier = nxt
        raise RuntimeError(f"no route {a} -> {b}")



# --- layout -----------------------------------------------------------------------------------

ROOMS = {
    "IN": (0, 0, 3, 3),
    "LOADER": (20, 0, 17, 11),
    "PADK": (38, 0, 14, 6),
    "TAIL": (42, 14, 6, 5),
    "MUL": (20, 29, 20, 7),
    "ACC": (14, 38, 22, 13),
    "ACCR": (20, 53, 6, 4),
    "OUT": (11, 53, 3, 3),
}
# The ring drum is a tall block to the RIGHT of MUL/ACC, filled bottom-up (waypoints reversed) so
# it can exit at its top-left and drop into MUL's north face.  20 x 21 = 294; ring needs
# M*(K+1)+1 = 273.
RB_DRUM = (42, 55, 21, 21)
PA_DRUM = (2, 20, 13, 14)  # 19 x 14 = 266; A queue needs N*M+1 = 257
GATE_DELAY = (32, 22, 13, 14)  # 11 x 14 = 154; MUL must not touch the ring until PADK has drained


def build() -> tuple[str, dict[str, int]]:
    c = Canvas()
    for name, (x, y, w, h) in ROOMS.items():
        c.room(x, y, w, h)
    c.put(1, 1, "I")
    c.put(ROOMS["OUT"][0] + 1, ROOMS["OUT"][1] + 1, "O")
    for lines, name in ((LOADER, "LOADER"), (PADK, "PADK"), (TAIL, "TAIL"), (MUL, "MUL"), (ACC, "ACC"), (ACCR, "ACCR")):
        x, y, _, _ = ROOMS[name]
        c.block(x + 1, y + 1, lines)

    rb, pa = serpentine(*RB_DRUM)[::-1], serpentine(*PA_DRUM)
    gd = serpentine(*GATE_DELAY)
    router = Router(c)
    router.reserved = set(_cells(rb)) | set(_cells(pa)) | set(_cells(gd))
    caps: dict[str, int] = {}

    def wire(name, start, goal, drum=None, via=None, via2=None):
        if drum is None:
            path = router.route(start, goal, via)
        else:
            head = router.route(start, drum[0], via)
            tail_ = router.route(drum[-1], goal, via2)
            router.reserved -= set(_cells(drum))
            path = head[:-1] + _cells(drum) + tail_[1:]
        caps[name] = c.pipe(path)

    wire("in", (2, 2), (20, 5))
    wire("A", (22, 10), (32, 35), drum=pa, via=[(22, 12), (2, 12)], via2=[(2, 36), (32, 36)])
    wire("gate", (28, 10), (25, 29), drum=gd, via=[(28, 12), (32, 12)], via2=[(22, 28), (25, 28)])
    wire("pk", (34, 10), (44, 5), via=[(34, 12), (44, 12)])
    wire("padk", (51, 3), (47, 16), via=[(53, 3), (53, 16)])
    wire("rf", (34, 29), (42, 16), via=[(34, 16)])
    wire("ring", (44, 18), (38, 29), drum=rb,
         via=[(44, 20), (56, 20), (56, 41)],
         via2=[(38, 21)])
    wire("prod", (33, 35), (30, 38), via=[(33, 37), (30, 37)])
    wire("accf", (24, 50), (24, 53))
    wire("accb", (25, 55), (18, 50), via=[(27, 55), (27, 57), (18, 57), (18, 51)])
    wire("out", (16, 50), (11, 54), via=[(16, 52), (9, 52), (9, 54)])
    return c.render(), caps


def _cells(waypoints: list[tuple[int, int]]) -> list[tuple[int, int]]:
    out = [waypoints[0]]
    for (x0, y0), (x1, y1) in zip(waypoints, waypoints[1:]):
        step = (sign(x1 - x0), sign(y1 - y0))
        x, y = x0, y0
        while (x, y) != (x1, y1):
            x, y = x + step[0], y + step[1]
            out.append((x, y))
    return out


if __name__ == "__main__":
    import sys

    text, caps = build()
    lines = text.splitlines()
    w, h = max(len(line) for line in lines), len(lines)
    sys.stderr.write(f"{caps}\nfootprint {max(w, h)}^2 = {max(w, h) ** 2}\n")
    sys.stdout.write(text)
