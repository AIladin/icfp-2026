"""`history-lesson`, second machine: a phrase dictionary held in a pipe ring.

[[Literal drum]] caps a cell at ~2.85 bits, so the only lever is sending fewer bits. `history_phrase`
gets 2810 characters down to ~2060 base-131 digits by pulling the 49 most common substrings out into
a dictionary. This file is the machine that reads that stream back.

Four rooms and a ring:

    DRUM  one literal per block, walked once            -> chunk values
    DEC   chunk / 131 until it runs dry                 -> one digit per value
    EXP   digit <= 91 : emit ASCII 31 + digit
          digit >= 92 : rotate the ring, unpack a word  -> characters
    RELAY closes the ring; `R` so the dictionary and the recycled words share one pipe

The ring is the whole reason this is cheap. A pipe cell holds an entire 64-bit value, so one cell is
one phrase: a word packed base-128 with raw ASCII, and unpacking it is the *same* `/` loop that
unpacks the drum. Flat phrases, so no grammar, no recursion, no stack.

Indices are **relative**: EXP never rewinds the ring, it just rotates forward by the encoded offset
and leaves it there, and the encoder tracks where the head ended up. That removes the sentinel and
the whole realign loop.

Two register idioms carry all four loops:

    `M` <literal> `W`   park A in B, load a constant, swap back — restores both registers at once
    `N` `X`             `X` splits three ways on sign; negating first puts the branch we want on the
                        turn and the exit on the straight-through, so no merge lane is needed
"""

from __future__ import annotations

import functools

from history_phrase import encode
from memory_gen import Canvas

LIMIT = 2**63 - 1
BLOCK_EXTRA = 3  # backtick, backtick, and the `s` that ships the block


# --- packing the digit stream into literal blocks ---------------------------------------------


def per_block(digits: int, base: int) -> int:
    """How many base-`base` digits a `digits`-digit literal can carry."""
    top = 10**digits - 1
    if top > LIMIT:
        return 0
    k = 0
    while base ** (k + 1) <= top + 1:
        k += 1
    return k


def plan_row(cells: int, base: int) -> list[int]:
    """The literal widths that carry the most digits in `cells` cells."""

    @functools.lru_cache(None)
    def best(room: int) -> tuple[int, tuple[int, ...]]:
        out = (0, ())
        for d in range(1, 19):
            if d + BLOCK_EXTRA > room or not per_block(d, base):
                continue
            carried, rest = best(room - d - BLOCK_EXTRA)
            if per_block(d, base) + carried > out[0]:
                out = (per_block(d, base) + carried, (d, *rest))
        return out

    return list(best(cells)[1])


def blocks(digits: list[int], base: int, widths: list[int]) -> list[tuple[int, str]]:
    """Chop the stream into literals of the given widths, most significant digit last.

    Digits run 1..base-1, so a literal's value hits zero exactly when it is spent — that is the
    terminator, and it costs nothing.
    """
    out: list[tuple[int, str]] = []
    pos = 0
    for width in widths:
        take = digits[pos : pos + per_block(width, base)]
        pos += len(take)
        value = 0
        for digit in reversed(take):
            value = value * base + digit
        out.append((width, f"{value:0{width}d}"))
        if pos >= len(digits):
            break
    if pos < len(digits):
        raise ValueError(f"{len(digits) - pos} digits did not fit")
    return out


# --- the rooms ---------------------------------------------------------------------------------
#
# Written as maps rather than `text()` calls: every one of these rooms is a knot of lanes, risers
# and three-way `X` branches, and the only way to keep it honest is to be able to read it.
# `.` is empty. Bands matter -- see EXP.

def dec_map(base: int) -> list[str]:
    """Chunk -> one digit per `s`.  Load the base, divide, branch on the quotient.

    The loop lane runs WEST, so its copy of the base is mirrored in the grid — a literal reads in
    walk order. `X` needs `N` in front of it because the branch we want on the *turn* is "keep
    dividing"; straight-through then falls out to fetch the next chunk.
    """
    return [
        f"@>`{base}`Mr    v",
        f".^XNW`{str(base)[::-1]}`sW/<",
        "..>N         ^",
    ]
DEC_IN, DEC_OUT = 3, 13  # interior columns for the chunk pipe in and the digit pipe out


def exp_map() -> list[str]:
    """EXP, 44 x 12.  Column 1 is INIT's return bus, column 2 is MAIN's.

    Rows 0-4 fill the ring: read a length, then that many characters, `V*128 + c` each time.
    Rows 5-11 are the main loop: `X` on `v - 92` sends a character north to the direct lane and a
    phrase south to the ring.  `a` rotates the ring by the *relative* offset and leaves it there --
    the encoder tracks the head, so there is no sentinel and no realign.

    Two rows were folded out of the first draft, and both are worth the trick:
    - the accumulator's `a` turns **north**, so its return lane is the same row that already carries
      the entry west to the lane head. One lane, two callers, no riser.
    - the fall-through under the outer `X` was a bare pass-through row; the turn west does the job.

    Every `r`/`s` west of column 22 talks to the stream and the output, every one east of it to the
    ring, and the generator asserts that rather than trusting the drawing.
    """
    rows = [[" "] * 44 for _ in range(12)]

    def put(y: int, x: int, text: str) -> None:
        for i, ch in enumerate(text):
            rows[y][x + i] = ch

    put(0, 0, "@>rbM9W-NX")  # A = length; X: >0 a phrase (south), 0 the end marker (east)
    put(0, 30, "`1996`Ns")  # ... and on the way out, seed the ring's year slot
    put(0, 42, "v")
    for y in range(1, 7):
        rows[y][1] = "^"  # INIT bus, back up to (1,0)
    put(1, 9, "0")  # A = 0, then turn west into the accumulator
    put(1, 34, "<")  # the push loops home along row 1; the `0` it crosses is harmless
    put(2, 3, "v")
    put(2, 9, "<")
    put(2, 15, "<")  # ... and the accumulator's own return, folded onto the same lane
    put(3, 3, ">M`128`*Mr+ma")  # V = V*128 + c; `a` turns north, back onto row 2
    put(3, 33, "s^")  # the packed word, into the ring

    put(4, 29, "v")
    put(4, 34, "<")  # rotate's return lane, clear of everything else
    put(5, 30, ">rsm^")  # rotate one place
    put(6, 2, ">rM`92`W/XWM`31`+sv")  # MAIN: `/` splits, and B holds what each side wanted
    put(6, 30, "^")  # `a` rises to the rotate loop from here
    put(6, 32, ">M1W-sM1+v")  # THE YEAR: push -(y+1) back, keep -y, hand it to the output pipe
    put(7, 11, ">Wb")
    put(7, 29, ">a")  # a: rotate again while the offset is left, else fall through and read
    put(7, 31, "rX")  # X on the sign: a phrase is positive, the year is negative
    put(8, 3, "v")
    put(8, 24, "W`821`Ms<")  # phrase, walked WEST: push it back, then B = 128 for the unpack
    put(9, 3, ">/Ws`128`WXv")  # unpack: divide until the word runs dry
    put(10, 3, "^")
    put(10, 13, "<")
    put(10, 14, "v")
    put(10, 21, "s")  # the year's digits leave here, west of the unpack return's lane
    put(10, 41, "<")
    put(11, 2, "^")
    put(11, 14, "<")
    put(11, 20, "<")
    put(11, 42, "<")
    for y in range(7, 11):
        rows[y][2] = "^"  # MAIN bus
    return ["".join(r) for r in rows]


EXP_MAP = exp_map()
EXP_STREAM, EXP_OUT = 3, 9  # west-wall rows: digits in, characters out
EXP_RING_IN, EXP_RING_OUT = 7, 3  # east-wall rows


RELAY_MAP = ["@>rv", ".^s<"]


def room_map(c: Canvas, x0: int, y0: int, rows: list[str]) -> None:
    c.room(x0, y0, len(rows[0]) + 2, len(rows) + 2)
    for y, line in enumerate(rows):
        for x, ch in enumerate(line):
            if ch not in ". ":
                c.put(x0 + 1 + x, y0 + 1 + y, ch)


def drum(c: Canvas, w_int: int, digits: list[int], base: int) -> int:
    """The boustrophedon of literals; returns the room height.

    Westbound rows are the mirror of eastbound ones *and shifted one column*, so no column ever
    carries a backtick in one direction and an `s` in the other — see
    [[Backtick pairing is sequential per axis]].
    """
    widths = plan_row(w_int - 3, base)
    per_row = sum(per_block(d, base) for d in widths)
    nrows = -(-len(digits) // per_row)
    # Every backtick column must hold an EVEN number of them, or the last one pairs with a backtick
    # in the machinery below and the span across the room border is a load error. Eastbound and
    # westbound rows own disjoint columns, so both counts have to be even: rows a multiple of four.
    # Rounding up to a multiple of four is the blunt way to get that, and it wastes up to three
    # rows -- three points of side. Instead, when the count is not already even on both sides, the
    # last two rows (one of each direction) are shifted clear of the standard pattern: their
    # backticks then sit alone in their own columns and pair on no vertical span at all.
    stagger = 1 if nrows % 4 else 0
    digits = digits + [1] * (nrows * per_row - len(digits))  # 1 is a space, and we pass before it
    packed = blocks(digits, base, widths * nrows)
    rows = [packed[i : i + len(widths)] for i in range(0, len(packed), len(widths))]
    c.room(0, 0, w_int + 2, len(rows) + 2)

    tail = set(range(len(rows) - 2, len(rows))) if stagger else set()
    for i, row in enumerate(rows):
        y, east = i + 1, i % 2 == 0
        off = stagger if i in tail else 0
        x = 2 + off if east else w_int - 1 - off
        for width, text in row:
            if east:
                c.text(x, y, "`" + text + "`s")
                x += width + BLOCK_EXTRA
            else:
                c.text(x - width - 2, y, "s`" + text[::-1] + "`")
                x -= width + BLOCK_EXTRA
        c.put(1 if east else w_int, y, "@" if i == 0 else ">" if east else "<")
        c.put(w_int if east else 1, y, "H" if i == len(rows) - 1 else "v")
    return len(rows) + 2


def build(text: str, side: int = 86, rounds: int = 50) -> str:
    digits, base, _ = encode(text, rounds)
    c = Canvas()
    w_int = side - 2
    drum_h = drum(c, w_int, digits, base)
    # Two rows of band, not three: the drum-to-DEC pipe only needs its two cells, and the ring's
    # long leg runs horizontally at x >= 20, clear of it. One row of height for nothing.
    top = drum_h + 2

    dec_x, exp_x = 0, 22
    room_map(c, dec_x, top, dec_map(base))
    room_map(c, exp_x, top, EXP_MAP)
    exp_e = exp_x + len(EXP_MAP[0]) + 1  # EXP's east wall
    relay_x = exp_e + 3
    # RELAY is as tall as EXP purely so the ring's return leg can reach it on EXP's own row
    room_map(c, relay_x, top, RELAY_MAP + ["." * 4] * (len(EXP_MAP) - len(RELAY_MAP)))

    c.room(17, top + 9, 3, 3)
    c.put(18, top + 10, "O")

    def row(r: int) -> int:
        """EXP interior row -> absolute y."""
        return top + 1 + r

    c.pipe([(DEC_IN, drum_h - 1), (DEC_IN, top)])
    # DEC's east wall and EXP's stream row are three rows apart, so this one turns twice
    c.pipe(
        [(dec_x + 15, row(1)), (dec_x + 18, row(1))]
        + [(dec_x + 18, row(EXP_STREAM)), (exp_x, row(EXP_STREAM))]
    )
    c.pipe([(exp_x, row(EXP_OUT)), (19, row(EXP_OUT))])
    c.pipe([(relay_x, row(EXP_RING_IN)), (exp_e, row(EXP_RING_IN))])
    # the ring has to hold every phrase at once, so it takes the long way round through the band
    # Every bend that turns *north* directly above EXP would have the room's own wall behind it and
    # be read as a second pipe start ([[Pipe start scanning may be greedy]]) — which would move the
    # ring's source segment to the west side and break the bands. So it climbs clear of EXP first.
    c.pipe(
        [(exp_e, row(EXP_RING_OUT)), (exp_e + 2, row(EXP_RING_OUT)), (exp_e + 2, top - 1)]
        + [(exp_x - 2, top - 1), (exp_x - 2, top - 2), (relay_x + 2, top - 2), (relay_x + 2, top)]
    )
    return c.render()


if __name__ == "__main__":
    import pathlib
    import sys

    print(build(pathlib.Path(sys.argv[1]).read_text()), end="")


# --- YEAR ---------------------------------------------------------------------------------------
#
# The years 1996.. are a counter, not data, so the drum carries one code for each and this room
# counts them out. It is spliced into the OUTPUT pipe -- EXP -> YEAR -> O -- which is what makes it
# cheap: EXP needs no third pipe pair (and so no third band), only nine cells to notice the year and
# hand it over. Everything else happens here, where A and B are free.
#
# A character arrives positive and is passed straight through. The year arrives as -y, and every
# digit comes out of a division that was already being paid for, with its ASCII offset folded into
# the dividend -- see [[Fold the offset into the divisor]]:
#
#     floor((y + 48*d) / d) == floor(y/d) + 48        and the remainder is untouched,
#                                                     because 48*d is a multiple of d
YEAR_EMIT = [
    "N",  # A = y
    "M", "`48000`", "+", "M", "`1000`", "W", "/", "s", "W",  # thousands, already ASCII
    "M", "`4800`", "+", "M", "`100`", "W", "/", "s", "W",  # hundreds
    "M", "`480`", "+", "M", "`10`", "W", "/", "s", "W",  # tens, and B keeps the units
    "M", "`48`", "+", "s",  # units: the one offset with no division to hide in
]


def serpentine(tokens: list[str], xmin: int, xmax: int, rows: list[int], start: int):
    """Lay a straight-line program along alternating rows, never splitting a literal across a turn.

    A [[Numeric literals|literal cannot straddle a fold]] — the man leaves the row mid-number and the
    load silently becomes something else — so a token that will not fit is pushed to the next row.
    Walking west, a token's characters go in at *decreasing* x in their normal order, because that
    is the order he reads them.
    """
    cells: dict[tuple[int, int], str] = {}
    row, x, east = 0, start, True
    for token in tokens:
        if (x + len(token) - 1 > xmax) if east else (x - len(token) + 1 < xmin):
            cells[(x, rows[row])] = "v"
            row += 1
            cells[(x, rows[row])] = "<" if east else ">"
            east = not east
            x += 1 if east else -1
        for ch in token:
            cells[(x, rows[row])] = ch
            x += 1 if east else -1
    return cells, x, rows[row], east


def columns_ok(rows: list[str]) -> bool:
    """No column may pair two backticks across anything but digits and spaces.

    Folding a program into lanes lines its literals up vertically, and the loader pairs backticks on
    both axes independently — see [[Backtick pairing is sequential per axis]]. Cheaper to check than
    to reason about.
    """
    width = max(len(r) for r in rows)
    for x in range(width):
        column = [r[x] if x < len(r) else " " for r in rows]
        ticks = [y for y, ch in enumerate(column) if ch == "`"]
        for lo, hi in zip(ticks[::2], ticks[1::2]):
            if any(ch not in "0123456789 " for ch in column[lo + 1 : hi]):
                return False
    return True


def year_room(width: int) -> list[str]:
    """Pass characters through; count out a year when one arrives as a negative value.

    Column 1 is the way home, so the emitter is kept east of it. The fold point is tried at several
    widths because it decides which columns the literals land in, and those must not stack.
    """
    for margin in range(0, 9):
        rows = _year_room(width, margin)
        if columns_ok(rows):
            return rows
    raise RuntimeError("no fold width lays the YEAR emitter out legally")


def _year_room(width: int, margin: int) -> list[str]:
    lanes = [0, 3, 4, 5]
    grid = [[" "] * width for _ in range(6)]
    for i, ch in enumerate("@>rX"):
        grid[1][i] = ch  # X: positive is a character (south), negative is the year (north)
    for i, ch in enumerate("^s<"):
        grid[2][1 + i] = ch  # character: ship it and go round again
    grid[0][3] = ">"

    # xmin is 3, not 2: a westward fold lands on the cell it stops at, and column 1 is the way home
    body, x, y, east = serpentine(YEAR_EMIT, 3, width - 2 - margin, lanes, 4)
    for (cx, cy), ch in body.items():
        grid[cy][cx] = ch
    grid[y][x] = "v" if y != lanes[-1] else "<"
    if y != lanes[-1]:  # drop to the last lane and run home along it
        y += 1
        grid[y][x] = "<"
    for cx in range(2, x):
        grid[y][cx] = " " if grid[y][cx] == " " else grid[y][cx]
    grid[y][1] = "^"
    for cy in range(2, y):
        grid[cy][1] = "^"
    return ["".join(r).rstrip() or " " for r in grid]


def year_demo() -> str:
    """A standalone, runnable YEAR room so the geometry can be read and checked.

    SRC feeds it a character, a year, a character, a year — years arrive negative — and the output
    should read `H1996I1997`. Build with `uv run python -c "import history_gen2 as g;
    print(g.year_demo(), end='')"`.
    """
    # SRC's literals sit entirely west of YEAR's, because a backtick over a backtick with a room
    # border between them is a load error ([[Backtick pairing is sequential per axis]]) and the two
    # rooms' backtick columns are otherwise dense enough to collide at every offset.
    rows = year_room(26)
    east = 30 + len(rows[0]) + 1  # YEAR's east wall
    c = Canvas()
    room_map(c, 0, 0, ["@`72`s`1996`Ns`73`s`1997`NsH".ljust(28)])
    room_map(c, 30, 5, rows)
    c.room(east + 4, 8, 3, 3)
    c.put(east + 5, 9, "O")
    c.pipe([(4, 2), (4, 4), (35, 4), (35, 5)])  # SRC floor, east along the gap, into YEAR
    c.pipe([(east, 9), (east + 4, 9)])
    return c.render()


def year_drum(
    text: str, side: int = 84, rounds: int = 41,
    stream: tuple[list[int], int] | None = None,
) -> str:
    """Just the drum, carrying the year-folded stream, for placing by hand.

    The years are one code each instead of four characters, so this is the drum the machine wants
    once the YEAR room is wired in: `EXP -> YEAR -> O`, with the year riding in the ring as a
    negative word. See `programs/year-room.man` for the emitter.

    `stream` overrides the built-in encoder with a precomputed (digits, base) — used by
    `history_sweep`, whose phrase search beats BPE's stream by ~45 digits.
    """
    if stream is not None:
        digits, base = stream
        phrases = list(range(base - 93))  # only the count matters here
    else:
        digits, base, phrases = encode(text, rounds, years=True)
    c = Canvas()
    rows = drum(c, side - 2, digits, base)
    grid = c.render()
    stats = (
        f"# {len(digits)} base-{base} digits, {len(phrases)} phrases, "
        f"{rows - 2} rows of {sum(per_block(d, base) for d in plan_row(side - 5, base))}\n"
    )
    return stats + grid


def scaffold(text: str, side: int = 84, rounds: int = 41) -> str:
    """Every room placed, no pipes — just labelled endpoints, for wiring by hand.

    A lowercase letter marks where a pipe must LEAVE a room (the cell outside its wall) and the
    matching capital marks where it must ARRIVE. Six rooms, five pipes:

        a A   DRUM  -> DEC     chunks
        b B   DEC   -> EXP     one base-133 digit per value
        c C   EXP   -> YEAR    characters, and the year as a negative
        d D   YEAR  -> O       characters, years spelt out
        e E   EXP   -> RELAY   the ring, out.  Needs >= 41 cells: take the long way round
        f F   RELAY -> EXP     the ring, back.  Two cells is fine

    The ring's two legs together must hold every phrase at once — see the log for the measured
    floor. Bends that turn north directly above a room get re-read as a second pipe start, so climb
    clear of the wall before turning.
    """
    from littleman import load_program

    def ticks(rows: list[str]) -> set[int]:
        return {x for r in rows for x, ch in enumerate(r) if ch == "`"}

    digits, base, _ = encode(text, rounds, years=True)
    year = year_room(22)
    dec = dec_map(base)
    # Stacked rooms must not share a backtick column either: the pair would span the wall between
    # them ([[Backtick pairing is sequential per axis]]).
    for dec_x in range(0, 12):
        for year_x in range(0, 12):
            if {dec_x + 1 + t for t in ticks(dec)} & {year_x + 1 + t for t in ticks(year)}:
                continue
            for exp_x in range(27, 34):
                c = Canvas()
                drum_h = drum(c, side - 2, digits, base)
                top = drum_h + 2
                exp_e = exp_x + len(EXP_MAP[0]) + 1
                if exp_e + 9 > side - 1 or max(dec_x + 21, year_x + len(year[0]) + 2) > exp_x - 2:
                    continue
                room_map(c, dec_x, top, dec)
                c.room(dec_x + 18, top, 3, 3)
                c.put(dec_x + 19, top + 1, "O")
                room_map(c, year_x, top + 6, year)
                room_map(c, exp_x, top, EXP_MAP)
                room_map(c, exp_e + 3, top, RELAY_MAP)
                spots = {
                    "a": (dec_x + 3, drum_h), "A": (dec_x + 3, top - 1),
                    "b": (dec_x + 16, top + 2), "B": (exp_x - 1, top + 2),
                    "c": (exp_x - 1, top + 9), "C": (year_x + len(year[0]) + 2, top + 9),
                    "d": (dec_x + 19, top + 5), "D": (dec_x + 19, top + 3),
                    "e": (exp_e + 1, top + 1), "E": (exp_e + 6, top - 1),
                    "f": (exp_e + 2, top + 4), "F": (exp_e + 1, top + 4),
                }
                if any(spot in c.cells for spot in spots.values()):
                    continue
                try:  # the markers are not instructions, so validate the rooms without them
                    load_program(c.render())
                except Exception:
                    continue
                for label, (x, y) in spots.items():
                    c.put(x, y, label)
                return c.render()
    raise RuntimeError("no arrangement clears the drum's backtick columns")


def build_years(
    text: str, side: int = 85, rounds: int = 41,
    stream: tuple[list[int], int] | None = None,
) -> str:
    """The whole machine with the year counter: six rooms, six pipes.

    Same room placement search as `scaffold`, plus the wiring. The ring's long leg takes the two
    band rows above the machinery — it has to hold every phrase *and* the year at once, because
    INIT pushes them all in before reading one back.
    """
    from littleman import load_program

    def ticks(rows: list[str]) -> set[int]:
        return {x for r in rows for x, ch in enumerate(r) if ch == "`"}

    digits, base = stream if stream is not None else encode(text, rounds, years=True)[:2]
    year = year_room(22)
    dec = dec_map(base)
    del ticks  # rooms may share backtick columns: pairing resets at a wall (loader fix, a970acb)
    # O sits at the far west, clear of the DEC -> EXP run, with YEAR's output climbing past it in
    # column 1.
    for dec_x in range(4, 14):
        for year_x in (0, 1):
            for exp_x in range(27, 34):
                c = Canvas()
                drum_h = drum(c, side - 2, digits, base)
                top = drum_h + 2
                exp_e = exp_x + len(EXP_MAP[0]) + 1
                relay_x = exp_e + 3
                if relay_x + 5 > side - 1 or max(dec_x + 17, year_x + len(year[0]) + 2) > exp_x - 2:
                    continue
                c.room(0, top, 3, 3)
                c.put(1, top + 1, "O")
                room_map(c, dec_x, top, dec)
                room_map(c, year_x, top + 6, year)
                room_map(c, exp_x, top, EXP_MAP)
                room_map(c, relay_x, top, RELAY_MAP)
                sweep = dec_x + 5
                try:
                    c.pipe([(dec_x + 3, drum_h - 1), (dec_x + 3, top)])
                    c.pipe([(dec_x + 15, top + 2), (exp_x, top + 2)])
                    c.pipe([(exp_x, top + 9), (year_x + len(year[0]) + 1, top + 9)])
                    c.pipe([(1, top + 6), (1, top + 2)])
                    c.pipe([(relay_x, top + 3), (exp_e, top + 3)])
                    # west along the lower band row first, back east along the upper one: the
                    # climb out of EXP then stops a row short of the return leg instead of
                    # crossing it.
                    c.pipe(
                        [(exp_e, top + 1), (exp_e + 1, top + 1), (exp_e + 1, top - 1)]
                        + [(sweep, top - 1), (sweep, top - 2), (relay_x + 2, top - 2)]
                        + [(relay_x + 2, top)]
                    )
                    grid = c.render()
                    load_program(grid)
                except Exception:
                    continue
                return grid
    raise RuntimeError("no arrangement wires up")


def rooms(text: str, side: int = 85, rounds: int = 41) -> str:
    """Every room, spread out, for packing by hand. Pipe endpoints marked lowercase -> capital.

        a A  DRUM  -> DEC     chunks
        b B  DEC   -> EXP     one base-133 digit per value
        c C  EXP   -> YEAR    characters, and the year as a negative
        d D  YEAR  -> O       characters, years spelt out
        e E  EXP   -> RELAY   the ring OUT.  >= 41 cells: INIT fills it before reading any of it
        f F  RELAY -> EXP     the ring BACK.  two cells is fine

    The rooms are staggered horizontally so no two share a backtick column — stacked rooms that do
    will pair one across the wall between them and fail to load
    ([[Backtick pairing is sequential per axis]]). Re-check that after moving anything.
    """
    digits, base, _ = encode(text, rounds, years=True)
    c = Canvas()
    y = drum(c, side - 2, digits, base) + 3
    c.put(3, y - 2, "a")
    c.put(3, y - 1, "A")

    def block(x0: int, rows: list[str], marks: dict[str, tuple[int, int]]) -> int:
        room_map(c, x0, y, rows)
        for label, (mx, my) in marks.items():
            c.put(x0 + mx, y + my, label)
        return y + len(rows) + 4

    def ticks(rows: list[str], x0: int) -> set[int]:
        return {x0 + 1 + x for r in rows for x, ch in enumerate(r) if ch == "`"}

    used: set[int] = {x for (x, _), ch in c.cells.items() if ch == "`"}

    def place(rows: list[str], marks: dict[str, tuple[int, int]], lo: int, hi: int) -> int:
        nonlocal y, used
        for x0 in range(lo, hi):
            if not ticks(rows, x0) & used:
                used |= ticks(rows, x0)
                return block(x0, rows, marks)
        raise RuntimeError("nowhere to put a room without sharing a backtick column")

    y = place(dec_map(base), {"A": (3, -1), "b": (16, 2)}, 3, 30)
    y = place(EXP_MAP, {"B": (-1, 3), "c": (-1, 9), "e": (46, 2), "F": (46, 5)}, 3, 34)
    y = place(year_room(22), {"C": (24, 3), "d": (2, -1)}, 3, 55)
    y = place(RELAY_MAP, {"E": (2, -1), "f": (-1, 2)}, 3, 55)
    c.room(40, y, 3, 3)
    c.put(41, y + 1, "O")
    c.put(41, y - 1, "D")
    return c.render()
