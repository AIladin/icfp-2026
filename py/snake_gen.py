"""snake — 16x16 Snake on the LM-75.

Rooms
  IN     input room, pipe -> HUB
  BRAIN  the whole game
  exactly ONE pipe in (from HUB) and ONE pipe out (to HUB),
         so every r/s is unambiguous
  HUB    ring turnaround + router.  Tokens from BRAIN:
             < 1000  -> ring data, sent back to BRAIN
            == 1000  -> "draw prefix": the NEXT token is forwarded to DRAW
            == 2000  -> input request: pull one value from IN, send it to BRAIN
            == 3000  -> input request, multiplied by 16
  DRAW   1 in, 3 out (ADDR / DATA / SWAP).  Payloads arrive in pairs:
            p > 0 -> ADDR = p-1, next payload is the colour
            p = 0 -> SWAP,       next payload is the swap value

Ring record, in the order BRAIN reads and writes it:
    [V ...]  DX  HX  DP  HP  F  B1..BL  0
  DX  dx in {-1,0,1}                HX  head column 0..15
  DP  dy*16+dx in {-16,1,16,-1}     HP  head address 16*y+x
  F   fruit address + 1, or 0       Bi  body cell address + 1, TAIL FIRST, BL = head
  0   body end marker
"""

from plotter_gen.canvas import Canvas


def lit(n: int) -> str:
    return str(n) if 0 <= n <= 9 else "`" + str(n) + "`"


def expand(s: str) -> list[str]:
    out = []
    for tok in s.split():
        if tok.startswith("L"):
            out.append(lit(int(tok[1:])))
        elif tok == "@LOOP":
            out.append("@LOOP")
        else:
            out.append(tok)
    return out


# (name, code, kind, (ccw, straight, cw))  --  kind "j" uses targets[0]
# order matters: it is chosen so most control transfers are short hops downward
TAIL = "r s @LOOP s L2000 s"                       # echo F, body, marker, ask for V
SWAPT = "L1000 s 0 s L1000 s 1 s L2000 s"         # commit the frame, ask for V

# (name, code, kind, targets)
#   "j"    fall through to targets[0]
#   "x"    ends in X; targets = (ccw, straight, cw), None where impossible
#   "scan" ends in the scan gadget; targets = (marker-exit, collide-tail-code, collide-target)
#   "end"  park forever
# Block ORDER encodes the wire-routing rule: for an X, the cw target must come no
# later than the straight target, which must come no later than the ccw target.
def over_chain(sfx: str):
    """draw every body cell red, commit, and stop"""
    return [
        ("OVER" + sfx, "r r r r r", "j", ("RED" + sfx,)),
        ("RED" + sfx, "r", "x", ("REDB" + sfx, "REDEND" + sfx, None)),
        ("REDEND" + sfx, "L1000 s 0 s", "j", ("PARK" + sfx,)),
        ("PARK" + sfx, "", "end", ()),
        ("REDB" + sfx, "M L1000 s W s L1000 s L10 s", "j", ("RED" + sfx,)),
    ]


TAIL = "r s @LOOP s L2000 s"                       # echo F, body, marker, ask for V
SWAPT = "L1000 s 0 s L2000 s"                      # commit the frame, ask for V

# (name, code, kind, targets)
#   "j"    fall through to targets[0]
#   "x"    ends in X; targets = (ccw, straight, cw), None where impossible
#   "scan" ends in the scan gadget; targets = (marker-exit, collide-tail code, collide-target)
#   "end"  park forever
# Block ORDER is what makes the wires routable: for an X, the cw target must come no
# later than the straight target, which must come no later than the ccw target.
BLOCKS = [
    ("INIT", "L2000 s L3000 s 1 s r M s 1 s r + s M L1000 N s 1 + N s 0 s"
             " L1000 s 1 + N s L1000 s L11 s L1000 s 0 s L2000 s",
     "j", ("MAIN",)),

    ("MAIN", "1 M r -", "x", ("TICKA", "FRUITA", "DIRD")),

    ("DIRD", "- N", "x", ("DIRD2", "UP", None)),
    ("UP", "r 0 s r s r L16 N s r s " + TAIL, "j", ("MAIN",)),
    ("DIRD2", "+", "x", ("DIRD3", "RIGHT", None)),
    ("RIGHT", "r 1 s r s r 1 s r s " + TAIL, "j", ("MAIN",)),
    ("DIRD3", "+", "x", ("LEFT", "DOWN", None)),
    ("DOWN", "r 0 s r s r L16 s r s " + TAIL, "j", ("MAIN",)),
    ("LEFT", "r 1 N s r s r 1 N s r s " + TAIL, "j", ("MAIN",)),

    ("FRUITA", "L2000 s L3000 s r s r s r s r s r s @LOOP s", "j", ("FRUITB",)),
    ("FRUITB", "r M r + M 1 + N M L1000 s W s M L1000 s L10 s L1000 s 0 s"
               " r s r s r s r s r W s @LOOP s L2000 s", "j", ("MAIN",)),

    ("TICKA", "r s M r s +", "x", ("OOB1", "TICKA1B", "TICKA1B")),
    ("TICKA1B", "M L15 -", "x", ("OOB1", "TICKA2", "TICKA2")),
    ("TICKA2", "r s M r s +", "x", ("OOB2", "TICKA2B", "TICKA2B")),
    ("TICKA2B", "M L255 -", "x", ("OOB2", "TICKA3", "TICKA3")),
    ("TICKA3", "W M 1 + N M r s r s", "scan", ("TICKB", "@LOOP s", "OVERC")),
] + over_chain("C") + [

    ("TICKB", "r s M r + s r s M r + s M 1 + N M r ~", "x", (None, "GROW", "NOGROW")),
    ("NOGROW", "~ s L1000 s r s L1000 s 1 s @LOOP W s M 0 s"
               " L1000 s W s L1000 s L11 s " + SWAPT, "j", ("MAIN",)),
    ("GROW", "L1000 N s @LOOP W s M 0 s L1000 s W s L1000 s L11 s " + SWAPT,
     "j", ("MAIN",)),

    ("OOB2", "r s @LOOP s", "j", ("OVERB",)),
] + over_chain("B") + [
    ("OOB1", "r s r s r s @LOOP s", "j", ("OVERD",)),
] + over_chain("D")


class Brain:
    """Lay BLOCKS out inside a room.

    columns:  x0   room wall
              x0+1 BUS    -- the single back-edge bus, all `^`, ending at MAIN
              x0+2 SPINE  -- `v` on entry rows, `>` on code rows
              x0+3 ..     -- block code, then wire columns to the right
    rows:     one code row per block, an entry row above it, an optional row above
              that for an X's ccw arm, an optional row below for the cw arm and for
              @LOOP gadgets, and an optional west row for a back-edge to MAIN.
    """

    def __init__(self, x0: int, y0: int):
        self.x0, self.y0 = x0, y0
        self.bus = x0 + 1
        self.spine = x0 + 2
        self.cells: dict[tuple[int, int], str] = {}
        self.btcols: set[int] = set()
        self.res: set[tuple[int, int]] = set()
        self.plan()

    # ---------- pass 1: rows ----------
    def plan(self):
        names = [b[0] for b in BLOCKS]
        self.code, self.row, self.westrow, self.entry = {}, {}, {}, {}
        y = self.y0 + 1
        for k, blk in enumerate(BLOCKS):
            name, src, kind, tg = blk
            body = expand(src)
            need_n = kind == "x" and tg[0] is not None
            need_w = kind == "j" and tg[0] == "MAIN" and names.index("MAIN") < k
            below = 0
            if kind == "scan":
                below = 3 if "@LOOP" in expand(tg[1]) else 2
            elif kind == "end" or "@LOOP" in body or (kind == "x" and tg[2] is not None):
                below = 1
            y += 1
            self.entry[name] = y
            y += 1
            if need_n:
                y += 1
            self.row[name] = y
            self.code[name] = (body, kind, tg)
            y += below
            if need_w:
                y += 1
                self.westrow[name] = y
        self.height = y - self.y0 + 2

    # ---------- helpers ----------
    def put(self, x, y, ch):
        if (x, y) in self.cells:
            raise ValueError(f"brain overwrite {x},{y}: {self.cells[(x, y)]!r} -> {ch!r}")
        self.cells[(x, y)] = ch
        self.res.add((x, y))

    def ok(self, cells, want) -> bool:
        for c in cells:
            if c in self.cells:
                if self.cells[c] != want:
                    return False
            elif c in self.res:
                return False
        return True

    def lay(self, cells, want):
        for c in cells:
            self.cells.setdefault(c, want)
            self.res.add(c)

    # ---------- pass 2: code ----------
    def emit(self, x, y, body):
        for ch in body:
            if len(ch) > 1 and ch != "@LOOP":
                # backticks pair vertically as well as horizontally, so no two literals
                # may share a delimiter column: slide right until both ends are free
                while x in self.btcols or x + len(ch) - 1 in self.btcols:
                    x += 1
                self.btcols.add(x)
                self.btcols.add(x + len(ch) - 1)
                for k, cc in enumerate(ch):
                    self.put(x + k, y, cc)
                x += len(ch)
                continue
            if ch == "@LOOP":
                self.put(x + 0, y, ">")
                self.put(x + 1, y, "r")
                self.put(x + 2, y, "N")
                self.put(x + 3, y, "X")
                self.put(x + 0, y + 1, "^")
                self.put(x + 1, y + 1, "s")
                self.put(x + 2, y + 1, "N")
                self.put(x + 3, y + 1, "<")
                x += 4
            else:
                self.put(x, y, ch)
                x += 1
        return x

    def build(self):
        self.exits = []
        for blk in BLOCKS:
            name, _, _, _ = blk
            body, kind, tg = self.code[name]
            y = self.row[name]
            self.put(self.spine, y, ">")
            x = self.emit(self.spine + 1, y, body)
            if kind == "end":
                self.put(x, y, "v")
                self.put(x, y + 1, "^")
                continue
            if kind == "scan":
                self.put(x + 1, y, ">")
                self.put(x + 4, y, "r")
                self.put(x + 5, y, "N")
                self.put(x + 6, y, "X")
                self.put(x + 0, y + 1, "v")
                self.put(x + 1, y + 1, "X")
                self.put(x + 2, y + 1, "~")
                self.put(x + 3, y + 1, "s")
                self.put(x + 4, y + 1, "N")
                self.put(x + 6, y + 1, "<")
                self.put(x + 0, y + 2, ">")
                xc = self.emit(x + 1, y + 2, expand(tg[1]))
                self.exits.append((x + 7, y, tg[0]))
                self.exits.append((xc, y + 2, tg[2]))
                continue
            if kind == "j":
                if name in self.westrow:
                    self.west_exit(name, x, y)
                else:
                    self.exits.append((x, y, tg[0]))
                continue
            xX = x - 1
            if tg[0]:
                self.put(xX, y - 1, ">")
                self.exits.append((xX + 1, y - 1, tg[0]))
            if tg[1]:
                self.exits.append((xX + 1, y, tg[1]))
            if tg[2]:
                self.put(xX, y + 1, ">")
                self.exits.append((xX + 1, y + 1, tg[2]))
        self.maxx = max(x for x, _ in self.cells)

    def west_exit(self, name, x, y):
        wy = self.westrow[name]
        self.put(x, y, "v")
        for cy in range(y + 1, wy):
            self.res.add((x, cy))
        self.put(x, wy, "<")
        for cx in range(self.bus + 1, x):
            self.res.add((cx, wy))
        self.buslow = max(getattr(self, "buslow", self.y0), wy)

    # ---------- pass 3: wires ----------
    def wire(self, order):
        base = self.maxx + 2
        for x, y, target in order:
            ty = self.entry[target]
            arrow = "v" if ty > y else "^"
            for xj in range(base, base + 400):
                run_e = [(cx, y) for cx in range(x, xj)]
                rows = range(y, ty) if ty > y else range(ty + 1, y + 1)
                run_v = [(xj, cy) for cy in rows]
                run_w = [(cx, ty) for cx in range(self.spine, xj)]
                if (self.ok(run_e, None) and self.ok(run_v, arrow)
                        and self.ok(run_w, "<") and self.ok([(xj, ty)], "<")):
                    break
            else:
                raise ValueError(f"no wire column for {target} from row {y}")
            self.res.update(run_e)
            self.lay(run_v, arrow)
            self.cells[(xj, ty)] = "<"
            self.res.add((xj, ty))
            self.lay(run_w, "<")
            self.enter(target, ty)
        # the back-edge bus
        top = self.entry["MAIN"]
        for cy in range(top + 1, self.buslow + 1):
            self.cells.setdefault((self.bus, cy), "^")
            self.res.add((self.bus, cy))
        self.cells[(self.bus, top)] = ">"
        self.enter("MAIN", top)
        self.maxx = max(x for x, _ in self.cells)
        self.width = self.maxx - self.x0 + 2

    def enter(self, target, ty):
        for cy in range(ty, self.row[target]):
            self.cells.setdefault((self.spine, cy), "v")
            self.res.add((self.spine, cy))

    def blit(self, c: Canvas):
        c.room(self.x0, self.y0, self.x0 + self.width - 1, self.y0 + self.height - 1)
        for (x, y), ch in self.cells.items():
            c.g[y][x] = ch
        c.g[self.row["INIT"]][self.spine] = "@"


def wire_order(b):
    """wire i must sit right of wire j when i's vertical span covers one of j's
    horizontal runs
    return an order in which every j comes before its i"""
    w = [(x, y, t, b.entry[t]) for (x, y, t) in b.exits]
    n = len(w)
    after = {i: set() for i in range(n)}
    for i in range(n):
        y, ty = w[i][1], w[i][3]
        span = set(range(y, ty) if ty > y else range(ty + 1, y + 1))
        for j in range(n):
            if i != j and (w[j][1] in span or w[j][3] in span):
                after[i].add(j)
    out, seen = [], {}

    def visit(u, stack):
        if seen.get(u) == 2:
            return
        if seen.get(u) == 1:
            raise ValueError(f"wire cycle: {[ (w[k][2], w[k][1]) for k in stack + [u] ]}")
        seen[u] = 1
        stack.append(u)
        for v in sorted(after[u]):
            visit(v, stack)
        stack.pop()
        seen[u] = 2
        out.append(u)

    for u in range(n):
        visit(u, [])
    return [b.exits[i] for i in out]


def build_brain():
    b = Brain(0, 0)
    b.build()
    b.wire(wire_order(b))
    return b


def hub(c: Canvas, X: int, Y: int) -> None:
    """ring turnaround + router.  box (X,Y)-(X+23,Y+11)
    interior local 1..22 x 1..10.
    BRAIN pipes on the top wall (cols 4 and 8), IN/DRAW on the bottom (cols 4 and 8),
    so a receive/send resolves purely by row: rows 1-5 -> BRAIN, rows 6-10 -> IN/DRAW."""
    c.room(X, Y, X + 23, Y + 11)

    def p(lx, ly, ch):
        c.put(X + lx, Y + ly, ch)

    def t(lx, ly, txt):
        for k, ch in enumerate(txt):
            p(lx + k, ly, ch)

    p(1, 2, "v")
    p(1, 3, "v")
    p(1, 4, "@")
    for ly in range(5, 11):
        p(1, ly, "^")
    t(2, 4, "`1000`Mr-X")               # cols 2..11
    t(8, 3, "s")
    p(10, 3, "+")
    p(11, 3, "<")
    p(12, 4, "r")
    p(22, 4, "v")
    p(22, 10, "<")
    p(8, 10, "s")
    t(11, 5, ">-X")                     # input arm, cols 11..13
    p(16, 5, "v")
    p(16, 6, "r")
    p(16, 7, ">")
    p(17, 7, "^")
    p(17, 3, "s")
    p(17, 2, "<")
    p(13, 6, "v")
    p(13, 8, ">")
    t(14, 8, "`16`Mr*")                 # cols 14..20
    p(21, 8, "^")
    p(21, 3, "s")
    p(21, 2, "<")


def draw(c: Canvas, X: int, Y: int) -> None:
    """box (X,Y)-(X+10,Y+7).  ADDR on the top wall col 2, DATA on the right wall row 3,
    SWAP on the bottom wall col 2, HUB feed on the left wall row 2."""
    c.room(X, Y, X + 10, Y + 7)

    def p(lx, ly, ch):
        c.put(X + lx, Y + ly, ch)

    p(1, 1, "v")
    p(2, 1, "s")
    p(3, 1, "-")
    p(4, 1, "N")
    p(5, 1, "<")
    p(1, 2, "@")
    p(2, 2, "1")
    p(3, 2, "M")
    p(4, 2, "r")
    p(5, 2, "X")
    p(6, 2, "1")
    p(9, 2, "v")
    p(1, 3, "^")
    p(5, 3, ">")
    p(6, 3, "-")
    p(7, 3, "s")
    p(8, 3, "v")
    p(1, 4, "^")
    p(8, 4, "<")
    p(1, 5, "^")
    p(1, 6, "^")
    p(3, 6, "s")
    p(9, 6, "<")


def build() -> str:
    b = build_brain()
    D = b.width - 89                            # everything right of BRAIN slides with it
    c = Canvas(140 + D, max(118, b.height + 3))
    b.blit(c)

    def px(cells, final=None):
        c.pipe([(x + D, y) for x, y in cells], final=final)

    hub(c, 95 + D, 5)
    c.room(110 + D, 25, 112 + D, 27)
    c.put(111 + D, 26, "I")
    draw(c, 95 + D, 55)
    c.display(110 + D, 50, 127 + D, 67)

    # ring BRAIN -> HUB, the long way round (~180 cells of capacity)
    px([(x, 90) for x in range(89, 137)] + [(137, y) for y in range(90, 2, -1)]
       + [(x, 3) for x in range(136, 102, -1)] + [(103, 4)], final=(0, 1))
    px([(99, 4), (99, 3), (99, 2)] + [(x, 2) for x in range(98, 88, -1)], final=(-1, 0))
    px([(111, y) for y in range(24, 16, -1)] + [(112, 17), (113, 17)], final=(0, -1))
    px([(97, y) for y in range(17, 21)] + [(x, 20) for x in range(96, 91, -1)]
       + [(92, y) for y in range(21, 58)] + [(93, 57), (94, 57)], final=(1, 0))
    px([(97, y) for y in range(54, 44, -1)] + [(x, 45) for x in range(98, 127)]
       + [(126, y) for y in range(46, 50)], final=(0, 1))
    px([(x, 58) for x in range(106, 110)], final=(1, 0))
    px([(97, y) for y in range(63, 74)] + [(x, 73) for x in range(98, 119)]
       + [(118, y) for y in range(72, 67, -1)], final=(0, -1))
    return c.render()


if __name__ == "__main__":
    print(build(), end="")
