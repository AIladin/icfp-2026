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


# --------------------------------------------------------------------------
# The program, as a control-flow graph.  (name, code, kind, targets)
#
#   "j"     straight-line code, then jump to targets[0]
#   "x"     code, then X; targets = (ccw, straight, cw), None where impossible
#   "scan"  code, then the scan gadget: it walks ring tokens comparing each with
#           B, echoing as it goes.  targets = (marker-exit block, inline code to
#           run on a match, block to jump to after that code)
#   "end"   park forever
#
# Block ORDER is what makes the wires routable: for an X, the cw target must
# come no later than the straight target, which must come no later than the ccw
# target.
#
# ---- calling convention -------------------------------------------------
# One lap = BRAIN sends the record, HUB echoes it back.  A block reads the
# record in order and must send a replacement for every field, in the same
# order, or the next lap desynchronises.
#
#   DX  HX  DP  HP  F  B1..BL  0
#
# A body token is stored NEGATED, -(addr+1), which makes it simultaneously the
# ADDR payload for that cell -- so painting a cell costs no arithmetic.  F is
# -(fruitaddr+1), or -1000 for "no fruit"; -1000 can never collide with a real
# cell token, which is what makes the fruit test a bare XOR.
#
# `L512 s` (fetch the next input) MUST be the last send of a round: HUB blocks
# on the input room and round N+1's input is withheld until round N's frame
# commits, so asking any earlier deadlocks the draw traffic queued behind it.
#
# ---- drawing ------------------------------------------------------------
# Full repaint per frame.  SWAP payload 0 clears the next buffer and homes the
# cursor, so each frame is "paint everything, then swap" and no cell ever has
# to be erased individually.  That matters more than it sounds: erasing the
# vacated tail would need the tail address AND the new head address live at the
# same time, and there are only two general registers.

VREQ = "L512 s"                       # ask for the next input value -- always last
SWAP0 = "L256 s 0 s"                  # commit the frame
GREEN = "L256 s 8 s"                  # DATA 8 -> colour 10  (DRAW adds 2)
RED = "L256 s 7 s"                    # DATA 7 -> colour 9

def apply_chain(sfx: str, pre: str) -> list:
    """Lap 2 of a tick: rewrite HX/HP, replace F on a grow, move the body.

    `pre` finishes lap 1's record (the two callers have consumed different
    amounts of it).  Duplicated per caller for the same reason as paint_chain:
    Brain.wire() can only route a NON-CROSSING set of wires, so every jump has
    to nest inside the one above it.
    """
    return [
        ("TAP" + sfx, pre + " r s M r + s r s M r + s M 2 + N M r ~",
         "x", (None, "TAPG" + sfx, "TAPM" + sfx)),
        # drop B1 -- the tail vacates before the head lands
        ("TAPM" + sfx, "~ s r @LOOP W s W s", "j", ("PAINT" + sfx + "M",)),
    ] + paint_chain(sfx + "M") + [
        # grow: tail stays, fruit is eaten so F becomes -1000
        ("TAPG" + sfx, "1 N s @LOOP W s W s", "j", ("PAINT" + sfx + "G",)),
    ] + paint_chain(sfx + "G")


def over_chain(sfx: str, discard: str) -> list:
    """The snake does not move: repaint it red, commit, and park.

    One copy per entry point.  The three entries differ only in how much of the
    record lap 1 had already consumed, but they cannot share a chain: three
    wires fanning in from different rows to one block below them always contain
    each other's spans, and wire_order raises on that.  The groups are ordered
    so the wire that starts HIGHEST targets the LOWEST group.
    """
    return [
        ("OVE" + sfx, discard, "j", ("OVF" + sfx,)),
        ("OVF" + sfx, "r M 1 + N", "x", (None, "OVB" + sfx, "OVFR" + sfx)),
        ("OVFR" + sfx, "L256 s W s W s 7 s", "j", ("OVB" + sfx,)),
        ("OVB" + sfx, "r", "x", ("OVBC" + sfx, "OVEND" + sfx, None)),
        ("OVEND" + sfx, SWAP0, "j", ("PARK" + sfx,)),
        ("PARK" + sfx, "", "end", ()),
        ("OVBC" + sfx, "M L256 s W s " + RED, "j", ("OVB" + sfx,)),
    ]


def paint_chain(sfx: str) -> list:
    """Repaint the board from the record and commit: fruit red, body green.

    Every caller gets its OWN copy.  One shared PAINT would need a long back
    edge from the tick blocks up past the MAIN->TCHK wire, and Brain.wire()
    cannot order two wires that each cross the other -- wire_order raises.
    Duplicating six cells of code is free; footprint is worth nothing here.
    """
    return [
        # A = F + 1000: zero when there is no fruit, positive when there is, so
        # "fruit" is the CW arm and PFRUIT lands before PBODY.
        ("PAINT" + sfx, "r s r s r s r s r s M 1 + N",
         "x", (None, "PBODY" + sfx, "PFRUIT" + sfx)),
        ("PFRUIT" + sfx, "L256 s W s W s 7 s", "j", ("PBODY" + sfx,)),
        ("PBODY" + sfx, "r", "x", ("PBODYC" + sfx, "PEND" + sfx, None)),
        ("PEND" + sfx, "s " + SWAP0 + " " + VREQ, "j", ("MAIN",)),
        ("PBODYC" + sfx, "M s L256 s W s " + GREEN, "j", ("PBODY" + sfx,)),
    ]


BLOCKS = [
    # ---------------------------------------------------------------- INIT
    # Build the record from `sx sy`, paint the head, commit frame 0.
    ("INIT",
     "L512 s L768 s"                 # fetch sx, then sy*16
     " 1 s"                            # DX = 1  (the snake starts moving right)
     " r M s"                          # HX = sx
     " 1 s"                            # DP = 1
     " r + s"                          # HP = sy*16 + sx
     " M 2 + N M"                      # B = T = -(HP+2), the head's body token
     " 1 N s"                          # F  = -1, no fruit
     " W s"                            # B1 = T
     " W 0 s"                          # marker
     " L256 s W s W s 8 s"            # paint the head green
     + " " + SWAP0 + " " + VREQ,
     "j", ("MAIN",)),

    # ---------------------------------------------------------------- MAIN
    # V arrives LAST (see the note above), so open every round by passing the
    # whole record through untouched.  That both re-queues it for the branch
    # and clears the way to V.
    ("MAIN", "r s r s r s r s r s @LOOP s 1 M r -",
     "x", ("TCHK", "FRUITA", "DIRD")),

    # ------------------------------------------------- direction change
    # A = V-1, B = 1 on entry.  V is 2/3/4/5 for up/right/down/left.
    # No frame is committed.  Interleaved on purpose: for an X the straight
    # target must come before the ccw one or the wires cannot be ordered.
    ("DIRD", "- N", "x", ("DIRD2", "UP", None)),
    ("UP", "r 0 s r s r L16 N s r s r s @LOOP s " + VREQ, "j", ("MAIN",)),
    ("DIRD2", "+", "x", ("DIRD3", "RIGHT", None)),
    ("RIGHT", "r 1 s r s r 1 s r s r s @LOOP s " + VREQ, "j", ("MAIN",)),
    ("DIRD3", "+", "x", ("LEFT", "DOWN", None)),
    ("DOWN", "r 0 s r s r L16 s r s r s @LOOP s " + VREQ, "j", ("MAIN",)),
    ("LEFT", "r 1 N s r s r 1 N s r s r s @LOOP s " + VREQ, "j", ("MAIN",)),

    # ------------------------------------------------------ fruit spawn
    # Lap 1 asks for fx and fy*16 and echoes the record untouched.  Those two
    # answers are sent before the echo, so they arrive before it -- which is
    # why lap 2 can read them first.
    ("FRUITA", "L512 s L768 s r s r s r s r s r s @LOOP s", "j", ("FRUITB",)),
    ("FRUITB", "r M r + M 2 + N M"      # B = -(16*fy + fx + 1)
               " r s r s r s r s"       # DX HX DP HP unchanged
               " r W s"                 # drop the old F, send the new one
               " @LOOP s",
     "j", ("PAINTF",)),
] + paint_chain("F") + [

    # -------------------------------------------------------------- tick
    # Lap 1 validates and changes NOTHING, so a wall hit or a self collision
    # still leaves the whole pre-tick snake in the ring for the red repaint.
    # Lap 2 applies the move.  Lap 3 paints.
    ("TCHK", "r s M r s +", "x", ("OVEC", "TCHK2", "TCHK2")),
    ("TCHK2", "M L15 -", "x", ("OVEC", "TCHK3", "TCHK3")),
    ("TCHK3", "r s M r s +", "x", ("OVEB", "TCHK4", "TCHK4")),
    ("TCHK4", "M L255 -", "x", ("OVEB", "TCHK5", "TCHK5")),
    # B = T = -(newHP+1); A = F XOR T is 0 exactly when the head lands on the
    # fruit.  Both operands are negative, so the XOR is never negative and the
    # ccw arm is unreachable.
    ("TCHK5", "W M 2 + N M r s ~", "x", (None, "TAPG", "TSCAN")),
    # No grow: the tail vacates before the head lands, so B1 is echoed but
    # excluded from the collision test -- moving onto the cell the tail just
    # left is legal, and the public cases do exercise it twice.
    ("TSCAN", "r s", "scan", ("TAPN", "@LOOP s", "OVEA")),
] + over_chain("A", "r r r r") + apply_chain("N", "s") \
  + apply_chain("G", "@LOOP s") \
  + over_chain("B", ".") + over_chain("C", "r r")


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
            # kind "x" is "ends in X" -- but no BLOCKS entry spells the X out, so
            # emit it here.  Without it the man walks straight off the end of the
            # code and every branch silently takes its `straight` target.
            self.put(x, y, "X")
            xX = x
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
                # the spine cell of an entry row belongs to enter(): it must end up
                # `v` so a man arriving west along run_w drops into the block, and so
                # the MAIN bus head `>` at (bus, ty) hands over to it.  Laying `<`
                # there instead makes the man bounce between bus and spine forever.
                run_w = [(cx, ty) for cx in range(self.spine + 1, xj)]
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
        self.cells[(self.spine, ty)] = "v"       # forced: see the note in wire()
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

    # column 1 is the loop join.  `@` is a NO-OP when you step on it, so the join
    # cell must be a real `>`; the spawn gets its own stub down column 2 instead.
    # column 1 is the loop join.  `@` is a NO-OP when you step on it, so the join
    # cell must be a real `>`; the spawn gets its own stub down column 2 instead.
    p(1, 1, "@")                        # spawns heading east
    p(2, 1, "v")                        # ... and drops down column 2
    p(1, 2, "v")
    p(1, 3, "v")
    p(1, 4, ">")                        # THE JOIN: every return path restarts here
    for ly in range(5, 11):
        p(1, ly, "^")
    p(2, 10, "<")                       # spawn stub rejoins the `^` column

    # 256 is the smallest protocol constant that still beats the largest ordinary
    # ring datum (HP = 255).  It was 1000, which cost one extra column in every
    # one of the ~40 places BLOCKS spells it out.
    t(2, 4, "`256`Mr-X")                # cols 2..10; B = 256, A = token - 256
    p(9, 3, "+")                        # ccw: ring data, restore A and echo it
    p(7, 3, "s")
    p(10, 3, "<")
    p(11, 4, "r")                       # straight: draw prefix, forward the next token
    p(22, 4, "v")
    p(22, 10, "<")
    p(8, 10, "s")
    t(10, 5, ">-X")                     # cw: input request; A = token - 512
    p(15, 5, "v")                       # ... == 0: one raw input value
    p(15, 6, "r")
    p(15, 7, ">")
    p(16, 7, "^")
    p(16, 3, "s")
    p(16, 2, "<")
    p(12, 6, "v")                       # ... > 0: one input value, times 16
    p(12, 8, ">")
    t(13, 8, "`16`Mr*")                 # cols 13..19
    p(20, 8, "^")
    p(20, 3, "s")
    p(20, 2, "<")


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
    p(1, 2, ">")                        # THE JOIN -- see hub(); `@` cannot close a loop
    p(7, 4, "@")                        # spawn rides the existing row-4 return west
    p(2, 2, "2")
    p(3, 2, "M")
    p(4, 2, "r")
    p(5, 2, "X")
    p(6, 2, "0")                        # SWAP payload 0: clear next + home cursor
    p(9, 2, "v")
    p(1, 3, "^")
    p(5, 3, ">")
    p(6, 3, "+")
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
    # ADDR and DATA are deliberately the SAME LENGTH.  The display applies ADDR
    # before DATA within a tick, so an ADDR must not arrive after the DATA it
    # positions: with lengths La and Ld the driver has to leave `La - Ld` ticks
    # between the two sends.  At La=43, Ld=4 that was 39 ticks of margin nobody
    # had written down -- it held only because HUB upstream is slow, and any
    # repack that let payloads bunch up broke frames.  Equal lengths reduce the
    # whole constraint to "sent in the right order", which DRAW guarantees.
    # ADDR runs north of the display, DATA folds south of it, so they never
    # cross -- and they come out 20 and 22 cells, i.e. La - Ld <= 0.
    px([(97, y) for y in range(54, 48, -1)] + [(x, 49) for x in range(98, 112)],
       final=(0, 1))                                            # ADDR, 20 cells
    px([(106, 58), (107, 58)] + [(107, y) for y in range(59, 72)]
       + [(108, 71), (109, 71)] + [(109, y) for y in range(70, 66, -1)]
       + [(109, 66)], final=(1, 0))                             # DATA, 22 cells
    px([(97, y) for y in range(63, 74)] + [(x, 73) for x in range(98, 119)]
       + [(118, y) for y in range(72, 67, -1)], final=(0, -1))
    return c.render()


if __name__ == "__main__":
    print(build(), end="")
