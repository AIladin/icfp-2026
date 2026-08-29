"""snake gen96 — commit a clean tick on TAP's incoming wire.

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

# Ask for the next input value.  It has to be the LAST send of a round -- HUB
# blocks on the input room and round N+1's input is withheld until round N's
# frame commits -- and it used to be spelled out at the end of all four blocks
# that jump to MAIN.  MAIN issuing it once instead is the same point in the ring
# order (the previous block's last send is still the one before it) and takes
# two cells off the PAINT rows, which are what set BRAIN's width.
VREQ = "2 s"
SWAP0 = "1 s 0 s"                  # commit the frame
GREEN = "1 s 9 s"                  # DATA 9 -> colour 10  (DRAW adds 1)
RED = "1 s 8 s"                    # DATA 8 -> colour 9
BLACK = "1 s N s"                  # DATA -1 -> colour 0: prefix 1 survives `s`

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
        # The scan came out clean, so the frame is real: SWAP it, close lap 1
        # with the marker (A is still 0), and only THEN ask for the next input.
        ("TAP", "s " + VREQ
         + " r s M r + M 1 + s r s M r + M L16 + s", "j", ("TAQ",)),
        ("TAQ", "", "x",
         (None, ("1 N s", "JOIN"), ("~ s r", "JOIN"))),
        # append the new head to the body, paint it green, commit.  `1 s` is
        # HUB's draw prefix and the payload that follows it is DRAW's: negative
        # is an ADDR (the body token IS the address), positive is a colour.
        ("JOIN", "@LOOP W s W s", "j", ("MAIN",)),
    ]


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
         (None, "1 s W s W s 8 s", "M N", "1 s W s W s 8 s", SWAP0)),
    ]


# `paint_chain` -- the full repaint, five blocks of it -- is gone.  A frame is
# now "erase the vacated tail, paint the new head, commit": ten ring tokens,
# constant in snake length, where the repaint cost four tokens per body cell.
# The only full repaint left is the red one on game over, which happens once.


BLOCKS = [
    # ---------------------------------------------------------------- INIT
    # Build the record from `sx sy`, paint the head, commit frame 0.
    ("INIT",
     ">"                                # one harmless step buys west-INITB room
     " 2 s 3 s"                        # fetch sx, then sy*16 (raw, positive)
     " 2 N s"                          # DX' = -(dx)-1 = -2   (starts moving right)
     " r N M s"                        # HX' = -sx
     " L17 N s"                        # DP' = -(dy*16+dx)-16 = -17
     " r N + s"                        # HP' = -(sy*16 + sx)
     " M 1 N s"                        # preserve -HP; F = -1, no fruit
     " 2 N + s",                       # B1 = -2 + -HP; INITB restores B=T
     "j", ("INITB",)),
    # split off purely to keep BRAIN narrow -- INIT's single row was 50 cells
    # against the 41 the paint blocks need, and rows are free here
    # ... and INITB carries the frame-0 commit plus a whole extra echo lap.
    # INIT is the one place VREQ cannot ride the last lap: frame 0 must commit
    # before round 1's input is unlocked, and the record has to be BUILT before
    # it can be committed.  So round 0 pays one lap that no other round pays.
    ("INITB",
     "M 0 s"                           # restore B=T, then marker
     " 1 s W s W s 9 s"                # paint the head green
     + " " + SWAP0
     + " " + VREQ                      # frame 0 is out, so V1 is unlocked
     + " r s r s r s r s r s @LOOP s", # ... and now the record, behind V1
     "westinit", ("MAIN",)),

    # ---------------------------------------------------------------- MAIN
    # V is the FIRST token in the ring, because every round issues its VREQ
    # between the second-to-last lap's record and the last lap's.  So MAIN no
    # longer has to pass the record through to reach V: it reads one token and
    # branches, and the record is read by whichever block the branch picks.
    # Three laps a round became two.
    #
    #   cw  (direction) `M 2 s 1 W` -- V-1 has to survive the literal 2, so
    #       duplicate it into B, load 2 over A, send, then rebuild B = 1.
    #   str (fruit)     `2 s 3 s`   -- ask for fx and fy now; they land in the
    #       ring behind the record FRUITA is about to read, which is exactly
    #       where FRUITA2 wants them.
    ("MAIN", "1 M r -",
     "x", ("TCHK", ("2 s 3 s", "FRUITA"), ("M 2 s 1 W", "DIRA"))),

    # ------------------------------------------------- direction change
    # A = V-1, B = 1 on entry; V is 2/3/4/5 for up/right/down/left.  One block
    # instead of a seven-block if-chain: the four (DX', DP') pairs are packed
    # one byte per direction into a single literal, Z = -DP'*3 + -DX', and a
    # floored division unpacks it -- `/` leaves the remainder in B, which is the
    # only reason both fields survive.  DX' is sent BEFORE the old DX is read,
    # because an `r` would clobber the quotient and B has to keep the remainder.
    # Split in two ON PURPOSE: all three literals sit on DIRA's row, and the
    # room's width is the MAX over rows, so keeping the unpack and the record
    # rewrite apart costs three rows and buys nine columns.
    ("DIRA",
     "L761345281 }"                     # A = TABLE >> 8(V-2); B came from entry
     " M L255 &"                        # A = Z, the byte for this direction
     " M 3",                            # DIRB swaps/divides after the drop
     "j", ("DIRB",)),
    ("DIRB",
     "W / W N s"                        # divide Z by 3, swap remainder, then DX'
     " r r s"                           # drop the old DX, echo HX
     " r W N s"                         # drop the old DP, send DP'
     " r s r s @LOOP s",                 # HP, F, body
     "westdir", ("MAIN",)),

    # ------------------------------------------------------ fruit spawn
    # Lap 1 asks for fx and fy*16 and echoes the record untouched.  Those two
    # answers are sent before the echo, so they arrive before it -- which is
    # why lap 2 can read them first.
    # A spawn REPLACES the fruit (`snake_ref.py:26`), so with incremental
    # drawing the old fruit's pixel has to be erased -- the full repaint used to
    # cover this for free, and it is the one case the 14-case set caught.
    # `1 s W s 1 s N s` is exactly the erase pair; it is conditional because
    # F = -1 means "no fruit" and -1 is DRAW's black payload, not an address.
    ("FRUITA", "r s r s r s r s r s M 1 +", "cond",
     ("1 s W s 1 s N s", "@LOOP s", "FRUITA2")),
    # Split in two, and the split is what sets BRAIN's WIDTH: a room is as wide
    # as its widest row, this row was 40 cells against the next widest 38, and
    # the wire columns start two to the right of whichever row is longest.  The
    # halves cost two rows, which are free while BRAIN is under the 62 the band
    # below the display forces anyway.  B carries the new fruit token across the
    # jump -- a wire is `<`/`^`/`v` and touches no register.
    # The tail of lap 1: fx and fy are sitting in the ring right behind the
    # record FRUITA just consumed, so the new fruit token can be built, painted
    # and COMMITTED here -- which is what frees lap 2 to open with VREQ.
    ("FRUITA2", "r M r + M 2 + N M"     # B = -(16*fy + fx + 2)
                " 1 s W s W s 8 s"      # paint it red
                " " + SWAP0             # commit the frame ...
                + " " + VREQ,           # ... then ask for the next input
     "westfruit", ("FRUITB",)),
    # Lap 2 is now nothing but the record rewrite; B carries the new fruit
    # token across the jump, since a wire is `<`/`^`/`v` and touches no register.
    ("FRUITB", "r s r s r s r s"        # DX HX DP HP unchanged
               " r W s"                 # drop the old F, send the new one
               " @LOOP s",
     "j", ("MAIN",)),


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
    ("TCHK", "s M r s + M 4 W } M 1 + ~ b"
             " r s M r s + M L16 + N", "x", ("OVFB", "TCHK4", "TCHK4")),
    # The preserving bound check runs on the shared incoming wire. Division by
    # 256 leaves newHP as B's remainder on the valid arm; only X remains here.
    ("TCHK4", "", "x", ("OVFB", "TCHK5", None)),
    # `a` turns ccw when the backpack is set, so the game-over arm is the CCW
    # one and the block order stays legal (`d` would put it on the cw arm,
    # which has to point at a block ABOVE the straight one).
    # B = T = -(newHP+1); A = F XOR T is 0 exactly when the head lands on the
    # fruit.  Both operands are negative, so the XOR is never negative and the
    # ccw arm is unreachable.  `?OVF` is the side-wall branch that used to be a
    # block of its own: `a` inline, ccw arm to the game-over chain, fall through
    # east into TCHK5's own code.
    # Both arms now DRAW, because the frame has to commit in lap 1 for lap 2 to
    # open with VREQ -- and T is live here and dead after the scan.  Painting the
    # head before the collision is known is safe: a self-collision means the new
    # head IS a body cell, so OVFA's red repaint covers the green, and the SWAP
    # that would have published it is on the clean exit only.
    #   grow (straight)  paint the head, then B = -1, the scan sentinel
    #   move (cw)        erase the vacated tail first (`s s` = once to DRAW as an
    #                    ADDR, once to the ring as the record echo -- the token
    #                    must stay in the record so a game-over repaint still
    #                    paints the tail red), then paint the head.  B stays T.
    ("TCHK5", "?OVFB W M 2 + N M r s ~", "x",
     (None,
      ("1 s W s W s 9 s 1 N M", "TSCAN"),
      ("1 s r s s 1 s N s 1 s W s W s 9 s", "TSCAN"))),
    # No grow: the tail vacates before the head lands, so B1 is echoed but
    # excluded from the collision test -- moving onto the cell the tail just
    # left is legal, and the public cases do exercise it twice.
    # The leading `r s` is gone: B1 is read and echoed by TCHK5's move arm now
    # (it needed the address for the erase), and on the grow arm B = -1 so the
    # gadget testing B1 too costs nothing.
    ("TSCAN", "", "scan", ("TAP", "@LOOP s r r r r", "OVFA")),
] + over_chain("A") + apply_chain() + over_chain("B")



# A block reached by several wires normally needs only one entry row: the fan-ins
# that survive the router all nest (the shallowest caller's wire contains the
# others).  Name a block here to stack extra entry rows under it, deepest row for
# the shallowest caller, if a fan-in ever cycles.
EXTRA_ENTRIES: dict[str, int] = {}


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
            need_n = (kind in ("paint", "cond")
                      or (kind in ("x", "a") and tg[0] is not None)
                      or any(t.startswith("?") for t in body))
            need_w = (kind in ("j", "loop", "paint") and tg[0] == "MAIN"
                      and names.index("MAIN") < k)
            below = 0
            if kind == "scan":
                below = 3 if "@LOOP" in expand(tg[1]) else 2
            elif kind == "cond":
                below = 1 if "@LOOP" in expand(tg[1]) else 0
            elif kind in ("loop", "paint", "westdir", "westinit") or "@LOOP" in body \
                    or (kind in ("x", "a") and tg[2] is not None):
                below = 1
            rows = []
            # INIT is entered only by the room spawn. DIRB and FRUITA2 are entered
            # directly from their predecessors' east ends and execute west.
            if name not in ("INIT", "INITB", "DIRB", "FRUITA2"):
                for _ in range(1 + EXTRA_ENTRIES.get(name, 0)):
                    # INITB's mirrored marker loop occupies only columns 4..6
                    # on its lower row. MAIN's entry occupies only the bus and
                    # spine at columns 1..2, so those two rows can be shared.
                    if name != "MAIN":
                        y += 1
                    rows.append(y)
            self.entries[name] = rows
            if name != "INIT":
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
            if name == "TCHK4":
                # Its west-running `256` literal is installed after all wires,
                # but reserve the delimiter columns before later blocks emit.
                delimiters = {self.spine + 20, self.spine + 24}
                assert not (delimiters & self.btcols)
                self.btcols.update(delimiters)
            if kind == "westinit":
                # INIT drops into the right end. The long commit/echo row runs
                # west, then joins MAIN directly down the spine.
                x = self.initb_entry
                self.put(x, y, "<")
                # INIT arrives with A=T and dead B. Memorise T, then load marker 0.
                for ch in expand("M 0 s 1 s W s W s 9 s 1 s 0 s 2 s r s r s r s r s r s"):
                    x -= 1
                    self.put(x, y, ch)
                x -= 1
                self.put(x, y, "<")
                self.put(x - 1, y, "r")
                self.put(x - 2, y, "X")
                self.put(x - 2, y + 1, ">")
                self.put(x - 1, y + 1, "s")
                self.put(x, y + 1, "^")
                x -= 3
                self.put(x, y, "s")
                assert x == self.spine
                # After sending the marker on the spine, continue west onto the
                # bus, drop one row, and enter MAIN through its shared entry.
                self.put(self.bus, y, "v")
                self.res.add((self.bus, y))
                # MAIN's normal entry/spine cells are laid when wires are built.
                continue
            if kind == "westfruit":
                # FRUITA's joined conditional arms drop into the right end.
                # Lay the straight-line FRUITA2 sequence in semantic order while
                # the man walks west, then use the normal router for FRUITB.
                x = self.fruita2_entry
                self.put(x, y, "<")
                for ch in body:
                    assert len(ch) == 1, ch
                    x -= 1
                    self.put(x, y, ch)
                # The endpoint is already close to the spine, so an ordinary
                # east/vertical/west wire has no legal column. Turn down on the
                # next cell and join FRUITB's existing entry row directly.
                x -= 1
                self.put(x, y, "v")
                ty = self.entries[tg[0]][0]
                self.put(x, ty, "<")
                for cx in range(self.spine + 1, x):
                    self.put(cx, ty, "<")
                self.enter(tg[0], ty)
                continue
            if kind == "westdir":
                # DIRA drops into the right end. Execute DIRB right-to-left.
                x = self.dirb_entry
                self.put(x, y, "<")
                for ch in expand("W / W N s r r s r W N s r s r s"):
                    x -= 1
                    self.put(x, y, ch)
                # Mirrored @LOOP. Two negations make a body token negative
                # again, so X turns south; marker 0 continues west.
                x -= 1
                self.put(x, y, "<")
                self.put(x - 1, y, "r")
                self.put(x - 2, y, "X")
                self.put(x - 2, y + 1, ">")
                self.put(x - 1, y + 1, "s")
                self.put(x, y + 1, "^")
                x -= 3
                self.put(x, y, "s")
                # Marker 0 leaves X still heading west. Continue on this row
                # straight to the back-edge bus instead of paying a westrow.
                for cx in range(self.bus + 1, x):
                    self.res.add((cx, y))
                self.cells[(self.bus, y)] = "^"
                self.res.add((self.bus, y))
                self.buslow = max(getattr(self, "buslow", self.y0), y)
                continue
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
            if kind == "cond":
                # A conditional PREFIX, not a branch: the ccw arm runs `pre` on
                # the row above and drops back onto row y with a `v`, and the
                # straight arm walks blanks east into the same cell.  Both then
                # run `post`.  One row, where two blocks would have cost six.
                pre, post, tgt = tg
                self.put(x, y, "X")
                self.put(x, y - 1, ">")
                x3 = self.emit(x + 1, y - 1, expand(pre))
                self.put(x3, y - 1, "v")
                assert name not in self.westrow, name
                x4 = self.emit(x3, y, expand(post))
                if tgt == "FRUITA2":
                    self.put(x4, y, "v")
                    self.put(x4, y + 1, "v")
                    self.fruita2_entry = x4
                else:
                    self.exits.append((x4, y, tgt))
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
                if tg[0] == "INITB":
                    self.put(x, y, "v")
                    self.initb_entry = x
                elif tg[0] == "DIRB":
                    self.put(x, y, "v")
                    self.dirb_entry = x
                elif name in self.westrow:
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
        # A wire is `east to xj, vertical, west back to the spine`, so it costs
        # the BRAIN man `(xj - exit) + dy + (xj - spine)` ticks EVERY time the
        # block is entered -- and 64% of his ticks were wire glyphs because xj
        # was pinned to `maxx + 2`, the far side of the widest row in the room.
        # Nothing forces that: search from the exit column outwards and take the
        # first column where all three runs are free.  A fall-through to the
        # block below now turns down on the spot instead of walking to column 38
        # and back.  `ok()` is what keeps it honest -- a column that would cross
        # live code simply fails and the search moves east.
        base = self.maxx + 2
        for i in order:
            x, y, target = self.exits[i]
            ty = self.exit_ty[i]
            arrow = "v" if ty > y else "^"
            for xj in range(max(x, self.spine + 2), base + 400):
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
            if target == "DIRA":
                # This entry leg is paid on every direction change. Execute the
                # shift-count prelude while already walking west instead of
                # walking five inert arrows and then the same five cells east.
                prelude = "-M8*M"
                assert xj - len(prelude) > self.spine
                for k, ch in enumerate(prelude, 1):
                    self.cells[(xj - k, ty)] = ch
            elif target == "TCHK":
                # MAIN is the only caller. Pull the first record receive onto
                # the last inert entry arrow; TCHK's code starts with its echo.
                self.cells[(self.spine + 1, ty)] = "r"
            elif target == "TAQ":
                # Execute TAQ's direction-independent prefix on the final
                # seven entry arrows; only its sign branch remains in the row.
                prelude = "M2-NMr~"
                for k, ch in enumerate(prelude):
                    self.cells[(self.spine + len(prelude) - k, ty)] = ch
            elif target == "TAP":
                # The collision scan has exited cleanly. Commit its frame on
                # four arrows this one-caller entry already walks.
                prelude = "1s0s"
                for k, ch in enumerate(prelude):
                    self.cells[(self.spine + len(prelude) - k, ty)] = ch
            self.enter(target, ty)

        # TCHK's two valid arms share this entry row. Execute the complete
        # register-preserving upper-bound test on arrows both callers already
        # walk. The physical literal is `652`, read westward as 256.
        ty = self.entries["TCHK4"][0]
        start = self.spine + 25
        for k, ch in enumerate("M`256`W/N"):
            cell = (start - k, ty)
            assert self.cells.get(cell) == "<", (cell, self.cells.get(cell))
            self.cells[cell] = ch

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
    """ring turnaround + router.  box (X,Y)-(X+16,Y+8), interior 1..15 x 1..7.

    Pins, all four load-bearing for `s`/`r` resolution:
        ring in (5,-1)   ring-in out (2,-1)   feed out (6,9)   input in (15,9)

    Re-laid for SHORT PATHS, not for width.  HUB was 19x12 and cost the ring
    ~17 ticks a token because the common echo walked `1 M r - X` out and a
    five-cell return back -- 12 cells -- and the draw forward walked east to
    column 17, down six rows and back west to column 4: **45 ticks per payload,
    five payloads a frame**.  It was the co-bottleneck with BRAIN.

    Three changes:
      * the dispatch is a bare `r X` on the token's own sign, so ring data (all
        <= 0) turns ccw and echoes in **6 ticks**.  The `1 M ... -` that made
        room for a token-1 test moved onto the command arm, where it is paid
        by 11 tokens a round instead of every token;
      * the marker (the one 0) goes straight, one cell east, and turns north
        onto the SAME `<` return, so it costs 8;
      * the draw forward reads at column 7, turns west on the next row and
        sends at column 6 before continuing to the join. Compared with gen66,
        the send is one tick later but the complete HUB lap is one tick shorter.
    The two input arms keep the long way round -- one token a round each -- and
    their `r`s have to sit low and east, because `r` picks the nearer of the
    ring (top) and the input (bottom) and that binding is decided by ROW.
    """
    c.room(X, Y, X + 16, Y + 8)

    def p(lx, ly, ch):
        c.put(X + lx, Y + ly, ch)

    def t(lx, ly, txt):
        for k, ch in enumerate(txt):
            p(lx + k, ly, ch)

    # column 1 is the join.  `@` is a NO-OP when you step on it, so the join
    # cell is a real `>` and the spawn gets a two-cell stub on row 7.
    p(1, 1, "v")
    p(1, 2, ">")                        # THE JOIN: every return path restarts here
    for ly in range(3, 8):
        p(1, ly, "^")
    p(2, 7, "@")
    p(3, 7, "<")                        # spawn walks east one cell, turns back

    t(2, 1, "s<<")                      # cols 2..4: echo, and the two return arms
    t(2, 2, "rX")                       # cols 2..3; the join `>` is at 1
    p(4, 2, "^")                        # marker: straight, then north onto row 1

    t(3, 3, ">M2-X")                    # cols 3..7; A = 2 - token
    # cw (token 1): the payload is the next ring value; straight down to the feed
    p(7, 4, "r")
    p(7, 5, "<")
    p(6, 5, "s")                       # send, then keep walking west to the join
    # straight (token 2): read directly, then share command 3's top return
    p(14, 3, "r")
    p(15, 7, "^")
    for ly in range(2, 7):
        p(15, ly, "^")
    p(15, 1, "<")
    # ccw (token 3): the same, times 16
    p(7, 2, ">")
    p(9, 2, "v")
    p(9, 6, ">")
    t(10, 6, "rM4W{")                   # cols 10..14, then the shared `^` at 15


DRAW_PINS = {"ADDR": (2, -1), "DATA": (11, 3), "SWAP": (2, 8)}
DRAW_SENDS = {"ADDR": (2, 1), "DATA": (9, 5), "SWAP": (2, 5)}


def draw(c: Canvas, X: int, Y: int) -> None:
    """box (X,Y)-(X+10,Y+7).  ADDR on the top wall col 2, DATA on the right wall row 3,
    SWAP on the bottom wall col 2, HUB feed on the top wall col 1.

    FOUR payload classes out of two branches.  Incremental drawing needs colour 0
    (black) to erase the vacated tail, and colour 0 is not reachable from a
    positive payload when the colour arm adds a constant.  It IS reachable from
    the one negative value no body token can take: tokens are -(addr+2), i.e.
    -257..-2, so p = -1 is free and means "black".

      B = -1, A = p, first branch on A = p+1
        p <= -2   ccw/north   ADDR = -(p+1) - 1 = -p-2   (the token IS the address)
        p == -1   straight    DATA = 0                   (erase)
        p >=  0   cw/south    second branch on A = p
                    p == 0    straight (west)  SWAP = 1  (preserve the next buffer)
                    p >  0    cw/north         DATA = p+1

    Every crossing is on a BLANK cell -- a man walking over a blank keeps his
    heading -- so the three return paths share columns 7 and 9 and row 6 with
    nothing to route around.  The room did not have to grow.

    Colours are p+1 now, not p+2: green 10 is the digit `9` and red 9 is `8`,
    both still single characters, so BRAIN gains no backtick columns.
    """
    c.room(X, Y, X + 10, Y + 7)

    def p(lx, ly, ch):
        c.put(X + lx, Y + ly, ch)

    # row 1 -- the ADDR arm, walked WEST out of the first branch
    p(1, 1, "v")
    p(2, 1, "s")                        # ADDR
    p(5, 1, "+")
    p(6, 1, "N")
    p(7, 1, "<")
    # row 2 -- the join and the first branch
    p(1, 2, ">")                        # THE JOIN -- see hub(); `@` cannot close a loop
    p(2, 2, "1")
    p(3, 2, "N")
    p(4, 2, "M")                        # B = -1
    p(5, 2, "r")
    p(6, 2, "-")                        # A = p + 1
    p(7, 2, "X")
    p(9, 2, "v")                        # erase falls east then south to the DATA `s`
    p(1, 3, "^")
    # row 4 -- the colour arm, walked EAST out of the second branch
    p(1, 4, "^")
    p(5, 4, ">")
    p(6, 4, "-")                        # A = p + 1, the colour
    p(9, 4, "v")
    # row 5 -- the second branch, walked WEST; SWAP falls out of its west end
    p(1, 5, "^")
    p(2, 5, "s")                        # SWAP
    p(3, 5, "1")
    p(5, 5, "X")
    p(6, 5, "+")                        # A = p
    p(7, 5, "<")
    p(9, 5, "s")                        # DATA
    # row 6 -- the shared return
    p(1, 6, "^")
    p(8, 6, "@")                        # spawn walks east into the return's own `<`
    p(9, 6, "<")


# BRAIN -> HUB, in cells.  Ring capacity is `ring_out + ring_in + 1` tokens, and
# it has to hold a whole round's traffic: HUB blocks on the input room until the
# frame commits, and everything BRAIN sends meanwhile queues behind the request.
# The full repaint made that four tokens per body cell, which is why 171 was
# needed.  An incremental frame is ten tokens whatever the snake's length, so the
# requirement collapses to the record itself -- L + 7 tokens, 37 for the longest
# snake in the case set.
#
# The ring is also LATENCY, paid once per lap and three times per round, so this
# is the biggest single tick lever left: 184 cells of round trip against a record
# that needs 37.  Undersizing deadlocks silently and presents as a step cap --
# `serpent 30` and `long snake` are the cases that catch it.
RING = 57
RING_IN = 5


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
# Every room uses explicit audited pin positions, so no `s`/`r` can silently
# re-resolve. Only the pipe routes change, and all semantic lengths are asserted:
# and ADDR <= DATA <= SWAP so the display's fixed ADDR-DATA-SWAP order needs no
# margin from the driver.
HUBX, HUBY = 1, 5                    # HUB   B+1 .. B+17, rows 5..13
INX, INY = 15, 16                    # input room B+15 .. B+17, rows 16..18
DRWX, DRWY = 3, 24                   # DRAW  B+3 .. B+13, rows 24..31
DSPX, DSPY = 2, 36                   # 16x16 display, B+2 .. B+19, rows 36..53
BAND = 20                            # the band is B+0 .. B+19; nothing is east of it
ROWS = 55                            # the band's own height: SWAP runs under the display to row 54


def build(audit: bool = False) -> str:
    b = build_brain()
    B = b.width
    c = Canvas(B + BAND, max(b.height, ROWS))
    b.blit(c)

    hub(c, B + HUBX, HUBY)
    draw(c, B + DRWX, DRWY)
    c.display(B + DSPX, DSPY, B + DSPX + 17, DSPY + 17)
    c.room(B + INX, INY, B + INX + 2, INY + 2)
    c.put(B + INX + 1, INY + 1, "I")

    boxes = {
        "BRAIN": (0, 0, b.width - 1, b.height - 1),
        "HUB": (B + HUBX, HUBY, B + HUBX + 16, HUBY + 8),
        "DRAW": (B + DRWX, DRWY, B + DRWX + 10, DRWY + 7),
        "IN": (B + INX, INY, B + INX + 2, INY + 2),
    }
    laid: list[tuple[str, tuple[int, int], tuple[int, int], int]] = []

    def px(pts, final, want=None, name=""):
        cells = route([(B + dx, y) for dx, y in pts])
        assert want is None or len(cells) == want, (want, len(cells))
        c.pipe(cells, final=final)
        laid.append((name, cells[0], cells[-1], len(cells)))

    # Ring BRAIN -> HUB.  The whole ring now lives in the four free rows ABOVE
    # HUB: three serpentine rows and a drop into HUB's top wall.  It used to
    # serpentine below the display and come back up the column east of it, which
    # cost five rows at the bottom of the band AND the column -- so shortening it
    # takes the grid down in both dimensions as well as cutting the latency.
    # A pipe START has to leave its room's wall, not run alongside it: HUB's
    # ring-in segment at (4,4) must step NORTH first or the loader never attaches
    # the pipe to HUB and BRAIN loads with no incoming pipe at all.
    px([(0, 2), (11, 2), (11, 1), (1, 1), (1, 0), (18, 0), (18, 4), (6, 4)],
       final=(0, 1), want=RING, name="ring")
    px([(3, 4), (3, 3), (0, 3)], final=(-1, 0), want=RING_IN, name="ring-in")
    # IN sits directly below HUB. The two cells step north from IN's top wall
    # and attach to HUB's bottom wall; neither segment runs along its own room.
    px([(16, 15), (16, 14)], final=(0, -1), want=2, name="input")
    # HUB -> DRAW, 13 cells. The send happens before HUB's return walk; the route
    # goes around ADDR's west end into DRAW's top wall. It was 48
    # -- two folded rows of padding -- because the full repaint burst was four
    # tokens per body cell and this pipe was the only place to hold them.  An
    # incremental frame is five payloads, so the padding is pure LATENCY on the
    # one path that gates the next round: HUB cannot hand over round N+1's input
    # until round N's SWAP has reached the display.
    px([(7, 14), (7, 21), (4, 21), (4, 23)], final=(0, 1), want=13, name="feed")
    # ADDR 27 <= DATA 32 <= SWAP 32, so the display's fixed ADDR-DATA-SWAP order
    # needs no timing margin from DRAW.  ADDR climbs out of DRAW's north wall and
    # drops down the free column east of IN; DATA leaves the east wall, crosses
    # back west ABOVE the display and takes the one column between it and the
    # corridor; SWAP takes the corridor itself, all the way under the display.
    px([(5, 23), (5, 22), (17, 22), (17, 35)], final=(0, 1), want=27, name="ADDR")
    px([(14, 27), (15, 27), (15, 35), (1, 35), (1, 43)], final=(1, 0), want=32, name="DATA")
    px([(5, 32), (5, 34), (0, 34), (0, 54), (4, 54)], final=(0, -1), want=32, name="SWAP")
    if audit:
        report(c, boxes, laid)
    return c.render()


def report(c: Canvas, boxes: dict, laid: list) -> None:
    """Every `s` / `r`, the pipe it binds to, and the margin over the runner-up.

    The binding rule is Manhattan distance to the pipe segment ATTACHED TO THIS
    ROOM, ties broken in reading order -- so a margin of 0 is a coin flip the
    next repack loses.  DRAW's three sends are the ones to watch: this is the
    room whose interior was re-laid.
    """
    print("room  cell        op  ->pipe    dist  runner-up  margin")
    for room, (x0, y0, x1, y1) in boxes.items():
        attached = []
        for name, src, dst, _n in laid:
            for cell, way in ((src, "out"), (dst, "in")):
                x, y = cell
                edge = (x0 <= x <= x1 and y in (y0 - 1, y1 + 1)) or \
                       (y0 <= y <= y1 and x in (x0 - 1, x1 + 1))
                if edge:
                    attached.append((name, way, cell))
        for y in range(y0 + 1, y1):
            for x in range(x0 + 1, x1):
                op = c.g[y][x]
                if op not in ("s", "r", "q"):
                    continue
                way = "out" if op == "s" else "in"
                cand = sorted(
                    (abs(px - x) + abs(py - y), py, px, nm)
                    for nm, w, (px, py) in attached if w == way)
                assert cand, f"{room} {op} at ({x},{y}) has no {way} pipe"
                best = cand[0]
                second = cand[1] if len(cand) > 1 else None
                margin = (second[0] - best[0]) if second else 99
                flag = "  <-- TIE" if margin == 0 else ""
                print(f"{room:6}({x:3},{y:3})  {op}   {best[3]:8} {best[0]:4}"
                      f"  {second[3] if second else '-':9} {margin:4}{flag}")
    print("pipes: " + ", ".join(f"{n}={k}" for n, _s, _d, k in laid))


if __name__ == "__main__":
    import sys
    if "--audit" in sys.argv:
        build(audit=True)
    else:
        print(build(), end="")
