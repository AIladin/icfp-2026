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

VREQ = "2 s"                       # ask for the next input value -- always last
SWAP0 = "1 s 0 s"                  # commit the frame
GREEN = "1 s 8 s"                  # DATA 8 -> colour 10  (DRAW adds 2)
RED = "1 s 7 s"                    # DATA 7 -> colour 9

def apply_chain() -> list:
    """Lap 2 of a tick: rewrite HX/HP, replace F on a grow, move the body.

    ONE copy, where round 2 had two and round 3's first pass had two halves each.
    The two paths into it differ only in whether the self-collision scan has
    already echoed the body, and the scan can be made to echo WITHOUT matching:
    it compares each token against B, and the sentinel `B = -1` can never equal
    a body token (those are -(addr+2), so -257..-2), so entering with it walks
    the whole body, echoes it and falls out at the marker exactly as `@LOOP s`
    did.  So the grow arm of TCHK5 is three inline cells, `1 N M`, and both arms
    jump to the same TSCAN.

    The sentinel has to be NEGATIVE, which cost 7/14 the first time: the scan's
    inner branch is an `X` on `token XOR B` read by a man walking WEST, so ccw
    is SOUTH -- the match arm.  Two negatives XOR to a non-negative and miss it;
    `B = 1` XOR a negative token is negative, and every body cell "matched".

    That leaves the grow/move decision to be made again here, which is what the
    XOR was for all along -- but now both answers are ARM CODE on rows the
    branch already owns, converging on one `JOIN`, so it costs no block:

        grow   `1 N s`    F becomes -1, the tail stays
        move   `~ s r`    undo the XOR to recover F, echo it, drop B1
    """
    return [
        ("TAP", "s r s M r + M 1 + s r s M r + M L16 + s", "j", ("TAQ",)),
        ("TAQ", "M 2 - N M r ~", "x",
         (None, ("1 N s", "JOIN"), ("~ s r", "JOIN"))),
        ("JOIN", "@LOOP W s W s", "j", ("PAINT",)),
    ] + paint_chain("")


def over_chain(sfx: str) -> list:
    """The snake does not move: repaint it red, commit, and park.

    Still one copy per entry point.  A shared tail cycles: TCHK's wire to OVEC
    has to nest OUTSIDE TCHK3's wire to OVEB, so OVEB sits above OVEC, and then
    OVEB's own jump down to a shared tail crosses TCHK->OVEC.

    The entry block that used to sit in front of this one is gone.  Once the
    backpack collapsed the wall checks to a single branch point, its `discard`
    was `.` on the vertical side and four `r`s on the collision side -- and the
    scan gadget already has a row of its own to run inline code on, so the
    four `r`s live there and the vertical side needs no block at all.
    """
    return [
        # One block: the fruit repaint rides the ccw arm and drops back onto
        # the body loop's own `>`, so the branch and the loop share a row bill.
        ("OVF" + sfx, "r M 1 +", "paint",
         (None, "1 s W s W s 7 s", "M N", "1 s W s W s 7 s", SWAP0)),
    ]


def paint_chain(sfx: str) -> list:
    """Repaint the board from the record and commit: fruit red, body green.

    A = F+1 is zero when there is no fruit and negative when there is, so
    PFRUIT is the cw arm and lands before PBODY.  One copy per apply_chain --
    TAPM and TAPG are adjacent so their two wires nest, but a copy shared with
    FRUITB as well would cross the MAIN->TCHK wire.
    """
    return [
        ("PAINT" + sfx, "r s r s r s r s r s M 1 +", "paint",
         ("MAIN", "1 s W s W s 7 s", "M s N", "1 s W s W s 8 s",
          SWAP0 + " " + VREQ)),
    ]


BLOCKS = [
    # ---------------------------------------------------------------- INIT
    # Build the record from `sx sy`, paint the head, commit frame 0.
    ("INIT",
     "2 s 3 s"                        # fetch sx, then sy*16 (raw, positive)
     " 2 N s"                          # DX' = -(dx)-1 = -2   (starts moving right)
     " r N M s"                        # HX' = -sx
     " L17 N s"                        # DP' = -(dy*16+dx)-16 = -17
     " r N + s"                        # HP' = -(sy*16 + sx)
     " M 2 - N M",                     # B = T = -(HP+2), the head's body token
     "j", ("INITB",)),
    # split off purely to keep BRAIN narrow -- INIT's single row was 50 cells
    # against the 41 the paint blocks need, and rows are free here
    ("INITB",
     "1 N s"                           # F  = -1, no fruit
     " W s"                            # B1 = T
     " W 0 s"                          # marker
     " 1 s W s W s 8 s"                # paint the head green
     + " " + SWAP0 + " " + VREQ,
     "j", ("MAIN",)),

    # ---------------------------------------------------------------- MAIN
    # V arrives LAST (see the note above), so open every round by passing the
    # whole record through untouched.  That both re-queues it for the branch
    # and clears the way to V.
    ("MAIN", "r s r s r s r s r s @LOOP s 1 M r -",
     "x", ("TCHK", "FRUITA", "DIRA")),

    # ------------------------------------------------- direction change
    # A = V-1, B = 1 on entry; V is 2/3/4/5 for up/right/down/left.  One block
    # instead of a seven-block if-chain: the four (DX', DP') pairs are packed
    # one byte per direction into a single literal, Z = -DX'*64 + -DP', and two
    # floored divisions unpack it -- `/` leaves the remainder in B, which is the
    # only reason both fields survive.  DX' is sent BEFORE the old DX is read,
    # because an `r` would clobber the quotient and B has to keep the remainder.
    # Split in two ON PURPOSE: all three literals sit on DIRA's row, and the
    # room's width is the MAX over rows, so keeping the unpack and the record
    # rewrite apart costs three rows and buys nine columns.
    ("DIRA",
     "- M 8 * M 1 {"                    # A = 256^(V-2)
     " M L257986880 /"                  # A = TABLE >> 8(V-2)
     " M L256 W /"                      # B = Z, the byte for this direction
     " W M L64 W /",                    # A = -DX', B = -DP'
     "j", ("DIRB",)),
    ("DIRB",
     "N s"                              # DX'
     " r r s"                           # drop the old DX, echo HX
     " r W N s"                         # drop the old DP, send DP'
     " r s r s @LOOP s " + VREQ,        # HP, F, body
     "j", ("MAIN",)),

    # ------------------------------------------------------ fruit spawn
    # Lap 1 asks for fx and fy*16 and echoes the record untouched.  Those two
    # answers are sent before the echo, so they arrive before it -- which is
    # why lap 2 can read them first.
    ("FRUITA", "2 s 3 s r s r s r s r s r s @LOOP s", "j", ("FRUITB",)),
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
    # newHX >> 4 is -1/0/1 for west-wall / in-range / east-wall, so ANDing it
    # with 1 gives one flag for both horizontal walls -- and parking that flag
    # in the backpack defers its branch until DP and HP have been read too.
    # That is what collapses the three game-over entry points to two: OVEC (the
    # one that had to discard "r r") no longer exists, and with it the third
    # copy of the whole chain, which the router will not let us share.
    ("TCHK", "r s M r s + M 1 + N M 4 W } M 1 & b"
             " r s M r s + M L16 + N", "x", ("OVFB", "TCHK4", "TCHK4")),
    ("TCHK4", "M L255 -", "x", ("OVFB", "TCHK5", "TCHK5")),
    # `a` turns ccw when the backpack is set, so the game-over arm is the CCW
    # one and the block order stays legal (`d` would put it on the cw arm,
    # which has to point at a block ABOVE the straight one).
    # B = T = -(newHP+1); A = F XOR T is 0 exactly when the head lands on the
    # fruit.  Both operands are negative, so the XOR is never negative and the
    # ccw arm is unreachable.  `?OVF` is the side-wall branch that used to be a
    # block of its own: `a` inline, ccw arm to the game-over chain, fall through
    # east into TCHK5's own code.
    ("TCHK5", "?OVFB W M 2 + N M r s ~", "x", (None, ("1 N M", "TSCAN"), "TSCAN")),
    # No grow: the tail vacates before the head lands, so B1 is echoed but
    # excluded from the collision test -- moving onto the cell the tail just
    # left is legal, and the public cases do exercise it twice.
    ("TSCAN", "r s", "scan", ("TAP", "@LOOP s r r r r", "OVFA")),
] + over_chain("A") + apply_chain() + over_chain("B")



# A block reached by several wires normally needs only one entry row: the fan-ins
# that survive the router all nest (the shallowest caller's wire contains the
# others).  Name a block here to stack extra entry rows under it, deepest row for
# the shallowest caller, if a fan-in ever cycles.
EXTRA_ENTRIES: dict[str, int] = {"TSCAN": 1, "JOIN": 1, "OVFB": 2}


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
        self.code, self.row, self.westrow, self.entries = {}, {}, {}, {}
        y = self.y0 + 1
        for k, blk in enumerate(BLOCKS):
            name, src, kind, tg = blk
            body = expand(src)
            need_n = (kind == "paint" or (kind in ("x", "a") and tg[0] is not None)
                      or any(t.startswith("?") for t in body))
            need_w = (kind in ("j", "loop", "paint") and tg[0] == "MAIN"
                      and names.index("MAIN") < k)
            below = 0
            if kind == "scan":
                below = 3 if "@LOOP" in expand(tg[1]) else 2
            elif kind in ("loop", "paint") or "@LOOP" in body \
                    or (kind in ("x", "a") and tg[2] is not None):
                below = 1
            rows = []
            for _ in range(1 + EXTRA_ENTRIES.get(name, 0)):
                y += 1
                rows.append(y)
            self.entries[name] = rows
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
            if ch.startswith("?"):
                # a MID-ROW branch: `a` turns ccw (north) when the backpack is
                # set and falls through east when it is not, so the ccw arm can
                # be a `>` on the row above and the rest of the block just keeps
                # walking.  Worth a block: TCHKD was one `a` and cost three rows
                # -- an entry row, its own ccw row and a code row -- where
                # inlining costs only the ccw row TCHK5 did not already have.
                self.put(x, y, "a")
                self.put(x, y - 1, ">")
                self.exits.append((x + 1, y - 1, ch[1:]))
                x += 1
                continue
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
                self.put(x, y, "H")
                continue
            if kind == "paint":
                # A branch plus its body loop in ONE block.  The fruit repaint
                # rides the ccw arm on row y-1 and drops back onto the loop's
                # own `>` with a `v`; the no-fruit path walks blanks east into
                # that same cell.  Two blocks became one, 8 rows became 5.
                exit_t, fruit, head, walk, tail = tg
                self.put(x, y, "X")
                self.put(x, y - 1, ">")
                x3 = self.emit(x + 1, y - 1, expand(fruit))
                self.put(x3, y - 1, "v")
                self.loop_gadget(name, x3, y, head, walk, tail, exit_t)
                continue
            if kind == "loop":
                exit_t, head, walk, tail = tg
                self.loop_gadget(name, x, y, head, walk, tail, exit_t)
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
            # kind "x"/"a" is "ends in X"/"ends in a" -- no BLOCKS entry spells
            # the branch out, so emit it here.  Without it the man walks straight
            # off the end of the code and every branch silently falls through.
            self.put(x, y, "X" if kind == "x" else "a")
            xX = x
            if tg[0]:
                self.put(xX, y - 1, ">")
                self.exits.append((xX + 1, y - 1, tg[0]))
            if tg[1]:
                if isinstance(tg[1], tuple):
                    inline, tgt = tg[1]
                    self.exits.append(
                        (self.emit(xX + 1, y, expand(inline)), y, tgt))
                else:
                    self.exits.append((xX + 1, y, tg[1]))
            if tg[2]:
                self.put(xX, y + 1, ">")
                if isinstance(tg[2], tuple):
                    inline, tgt = tg[2]
                    self.exits.append(
                        (self.emit(xX + 1, y + 1, expand(inline)), y + 1, tgt))
                else:
                    self.exits.append((xX + 1, y + 1, tg[2]))
        self.maxx = max(x for x, _ in self.cells)

    def loop_gadget(self, name, x, y, head, walk, tail, exit_t):
        """Two-row in-place loop over the ring's body tokens, then the tail."""
        hd, wk = expand(head), expand(walk)
        assert all(len(t) == 1 for t in wk), wk
        k = len(wk) + 1
        assert k >= len(hd) + 2, (hd, wk)
        self.put(x, y, ">")
        self.put(x + 1, y, "r")
        for i, ch in enumerate(hd):
            self.put(x + 2 + i, y, ch)
        self.put(x + k, y, "X")
        self.put(x, y + 1, "^")
        for i, ch in enumerate(reversed(wk)):
            self.put(x + 1 + i, y + 1, ch)
        self.put(x + k, y + 1, "<")
        x2 = self.emit(x + k + 1, y, expand(tail))
        if exit_t is None:
            self.put(x2, y, "H")
        elif name in self.westrow:
            self.west_exit(name, x2, y)
        else:
            self.exits.append((x2, y, exit_t))

    def assign_entries(self):
        """Give each exit the entry row of its target, deepest row first."""
        by_t: dict[str, list[int]] = {}
        for i, (_, _, t) in enumerate(self.exits):
            by_t.setdefault(t, []).append(i)
        self.exit_ty = {}
        for t, idxs in by_t.items():
            rows = self.entries[t]
            idxs.sort(key=lambda i: self.exits[i][1])
            n = min(len(rows), len(idxs))
            for k, i in enumerate(idxs):
                self.exit_ty[i] = rows[n - 1 - k] if k < n else rows[0]

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
        for i in order:
            x, y, target = self.exits[i]
            ty = self.exit_ty[i]
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
        top = self.entries["MAIN"][0]
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
    w = [(x, y, t, b.exit_ty[i]) for i, (x, y, t) in enumerate(b.exits)]
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
    return out


def build_brain():
    b = Brain(0, 0)
    b.build()
    b.assign_entries()
    b.wire(wire_order(b))
    return b


def hub(c: Canvas, X: int, Y: int) -> None:
    """ring turnaround + router.  box (X,Y)-(X+18,Y+11), interior 1..17 x 1..10.

    Four pipe segments, all of them load-bearing for `s`/`r` resolution:
        BRAIN out (3,-1)   BRAIN in (9,-1)   DRAW out (3,12)   IN in (15,12)

    Round 2's HUB was 24 wide and that width WAS the band, so it was the grid.
    Five columns came out of it three ways:
      * `` `16` M r * `` becomes `r M 4 W {` -- a shift, no literal, two cells;
      * the three service paths return up columns whose only glyph is the `^`
        at the bottom, so the draw-forward run crosses them on BLANK cells --
        a man walking east over a blank keeps walking east.  Nothing has to be
        routed around anything;
      * the draw-forward run then turns down at 17 instead of 22.
    The bindings are all decided by 5 or more, which is what pays for the
    narrowing: the two input `r`s sit at columns 13 and 10 against an IN segment
    at 15 and a BRAIN segment at 9.
    """
    c.room(X, Y, X + 18, Y + 11)

    def p(lx, ly, ch):
        c.put(X + lx, Y + ly, ch)

    def t(lx, ly, txt):
        for k, ch in enumerate(txt):
            p(lx + k, ly, ch)

    # column 1 is the loop join.  `@` is a NO-OP when you step on it, so the join
    # cell must be a real `>`; the spawn gets its own stub down column 2 instead.
    p(1, 1, "@")
    p(2, 1, "v")
    p(1, 2, "v")
    p(1, 3, "v")
    p(1, 4, ">")                        # THE JOIN: every return path restarts here
    for ly in range(5, 11):
        p(1, ly, "^")
    p(2, 10, "<")                       # spawn stub rejoins the `^` column

    t(2, 4, "1Mr-X")                    # cols 2..6; B = 1, A = token - 1
    p(5, 3, "+")                        # ccw: ring data, restore A and echo it
    p(3, 3, "s")
    p(6, 3, "<")
    p(7, 4, "r")                        # straight: draw prefix, forward the next
    p(17, 4, "v")
    p(17, 10, "<")
    p(4, 10, "s")
    t(6, 5, ">-X")                      # cw: input request; A = token - 3
    p(13, 5, "v")                       # ... == 0: one raw input value
    p(13, 7, "r")
    p(13, 8, ">")
    p(14, 8, "^")
    p(14, 3, "s")
    p(14, 2, "<")
    p(8, 9, ">")                        # ... > 0: one input value, times 16
    t(10, 9, "rM4W{")                   # cols 10..14
    p(15, 9, "^")
    p(15, 3, "s")
    p(15, 2, "<")


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


RING = 171          # BRAIN -> HUB ring capacity; 30-cell snakes need all of it


def route(pts: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Corner points -> the cell list `Canvas.pipe` wants.  Consecutive points
    must share a row or a column; the corner itself is emitted once."""
    cells = [pts[0]]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        assert x0 == x1 or y0 == y1, ((x0, y0), (x1, y1))
        sx, sy = (x1 > x0) - (x1 < x0), (y1 > y0) - (y1 < y0)
        while (x0, y0) != (x1, y1):
            x0, y0 = x0 + sx, y0 + sy
            cells.append((x0, y0))
    return cells


# ---------------------------------------------------------------------------
# The band east of BRAIN.  Everything is an offset from B = BRAIN's width, i.e.
# from the first free column, so narrowing BRAIN slides the whole band west
# without touching a single pipe length.
#
# Round 2 left the four rooms in a ROW: HUB, then DRAW, then the display east of
# DRAW so that ADDR could go over the top and SWAP under the bottom.  That costs
# 11 (DRAW) + gap + 18 (display) = 33 columns.  With BRAIN down to 73 rows there
# are 20 spare rows, so the band is a COLUMN instead: HUB, DRAW, display stacked,
# ADDR going round DRAW's east side and DATA/SWAP round its west.  The band is
# then as wide as HUB alone.
#
# Every room keeps its pipe segments at the SAME OFFSET from its own corner --
# HUB's four at local (4,-1) (8,-1) (2,12) (18,12), DRAW's at (-1,2) (2,-1)
# (11,3) (2,8) -- so no `s`/`r` in either room can re-resolve.  Only the pipe
# ROUTES change, and the lengths are held: ring 171, ring-in 13, HUB->DRAW 49,
# and ADDR <= DATA <= SWAP so the display's fixed ADDR-DATA-SWAP order needs no
# margin from the driver.
HUBX, HUBY = 1, 5                    # HUB   B+1 .. B+19, rows 5..16
INX, INY = 15, 19                    # input room B+15 .. B+17, rows 19..21
DRWX, DRWY = 3, 24                   # DRAW  B+3 .. B+13, rows 24..31
DSPX, DSPY = 2, 37                   # 16x16 display, B+2 .. B+19, rows 37..54
LEG = 20                             # the ring's vertical leg, B+20


def build() -> str:
    b = build_brain()
    B = b.width
    c = Canvas(B + LEG + 1, max(b.height, 62))
    b.blit(c)

    hub(c, B + HUBX, HUBY)
    draw(c, B + DRWX, DRWY)
    c.display(B + DSPX, DSPY, B + DSPX + 17, DSPY + 17)
    c.room(B + INX, INY, B + INX + 2, INY + 2)
    c.put(B + INX + 1, INY + 1, "I")

    def px(pts, final, want=None):
        cells = route([(B + dx, y) for dx, y in pts])
        assert want is None or len(cells) == want, (want, len(cells))
        c.pipe(cells, final=final)

    # Ring BRAIN -> HUB, exactly 171 cells: five serpentine rows in the band
    # under the display, then north up the free column east of it, then west
    # along row 0 into HUB's top wall.  A shorter ring deadlocks a 15-cell snake
    # -- see [[A bursty producer needs ring-out slack]].
    px([(0, 56), (1, 56), (19, 56), (19, 57), (1, 57), (1, 58), (19, 58),
        (19, 59), (1, 59), (1, 60), (19, 60), (LEG, 60), (LEG, 0), (10, 0),
        (10, 4)], final=(0, 1), want=RING)
    px([(4, 4), (4, 0), (0, 0), (0, 4)], final=(-1, 0), want=13)          # ring in
    px([(16, 18), (16, 17)], final=(0, -1), want=2)                       # IN -> HUB
    # HUB -> DRAW, 48 cells.  Two folded rows of padding, because capacity here
    # is the only slack the draw burst has; the corridor column B+0 is left to
    # the ring and to SWAP.
    px([(4, 17), (4, 18), (13, 18), (13, 19), (1, 19), (1, 20), (10, 20),
        (10, 21), (2, 21), (2, 26)], final=(1, 0), want=48)
    # ADDR 29 <= DATA 35 <= SWAP 40, so the display's fixed ADDR-DATA-SWAP order
    # needs no timing margin from DRAW.  ADDR climbs out of DRAW's north wall and
    # drops down the free column east of IN; DATA leaves the east wall, crosses
    # back west ABOVE the display and takes the one column between it and the
    # corridor; SWAP takes the corridor itself, all the way under the display.
    px([(5, 23), (5, 22), (18, 22), (18, 36)], final=(0, 1), want=29)
    px([(14, 27), (15, 27), (15, 35), (1, 35), (1, 46)], final=(1, 0), want=35)
    px([(5, 32), (5, 34), (0, 34), (0, 55), (11, 55)], final=(0, -1), want=40)
    return c.render()


if __name__ == "__main__":
    print(build(), end="")
