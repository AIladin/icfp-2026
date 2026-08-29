"""Ephemeral pipes: run a room design before anybody routes or packs it.

The handover convention is `docs/vault/heap/Room handoff markers.md` — the designer ships one block
per room and marks each pipe attachment on the cell **immediately outside** the wall, `b` where a
pipe must begin and `B` where it must end. Such a block set does not load, so a logic bug in it
only surfaces after someone has spent an hour packing.

This module closes that gap by *drawing real pipes*: it pairs the markers, routes each pair through
free space, writes legal pipe glyphs onto the grid, and hands the result to the ordinary
``load_program``. There is deliberately no second execution path — what runs is a genuinely loadable
program, so the semantics are the machine's own.

**A pass proves the LOGIC, not the LAYOUT.** `s`, `r` and `q` take the *nearest* pipe, so a repack
that moves a room can silently re-point a send with no load error at all. ``Synthesis.warnings``
names every cell where that can happen.

Marker syntax. Two forms, and a rule that keeps them apart:

- **Letter pairs** (preferred): any letter on a blank cell orthogonally touching exactly one room
  border is a marker. Lowercase is the FROM end, uppercase the TO end, and the letter names the
  pipe — `a` … `A` is one pipe, `c` … `C` another. No label cell.
- **Labelled `b` / `B`** (the original form): a `b` or `B` marker with a one-character label — a
  digit or a letter — in one of its own four neighbours. `b1` … `B1` is one pipe.
- **Disambiguation**: a `b`/`B` marker that has a label character next to it is read the old way;
  a bare one is just the letter pair `b`/`B`. If that label is a letter whose opposite-case twin is
  also a marker elsewhere, the design reads two ways and it raises rather than picking one.
- **Reserved letters**: `v` and `V`. `v` is the pipe arrowhead the router itself writes, so neither
  case can name or label a pipe — a design that tries raises by name rather than misparsing.
- Every pipe needs exactly one FROM and one TO. Anything else is an error, never a guess.
- A letter outside a room that touches no room wall is not notation we understand: it raises.
  Inside a room a letter is an instruction, so markers are only ever looked for outside the walls.

**The exit-cell rule.** The cell straight out from a marker's wall is that pipe's own first (or
last) segment. The router reserves it for that pipe before anything is routed, and a second marker
sitting on it is rejected up front — a marker one cell out from another marker reads two ways.

Routing is a whole-design problem, not one pipe at a time: every exit cell is reserved, pipes are
taken most-constrained-first (short straight drops before long sprawling ones), and a failed pass is
retried under other orders before anything is reported. When it does give up it names the pipe, both
its markers, the cell it needed and the already-routed pipe sitting in it.
"""

import string
from dataclasses import dataclass

from .errors import LittlemanError
from .grid import Grid
from .load import _border_room, _find_rooms, _in_room, load_program
from .model import ARROWS, DELTAS, Cell, Program, Room

# Blank frame added round the design so pipes have somewhere to run.
MARGIN = 6
# How many DFS steps a single route may take before we give up rather than hang.
ROUTE_BUDGET = 200_000

_ARROW = {direction: char for char, direction in ARROWS.items()}
# `v` is a pipe arrowhead and `V` is its instruction twin: neither can name a pipe or label one.
# This is the complete reserved set — every other pipe glyph (`-` `|` `>` `<` `^`) is not a letter.
RESERVED_LETTERS = frozenset("vV")
_MARKER_LETTERS = frozenset(string.ascii_letters) - RESERVED_LETTERS
_LABELS = frozenset(string.digits + string.ascii_letters) - RESERVED_LETTERS - {"b", "B"}
_SIDES = ("east", "south", "west", "north")
# Alternative pipe orders tried before the router admits defeat, and the seed that makes it repeat.
# Rotations of the tight order come first — they are the targeted fix for "one pipe is in everyone
# else's way" — and then reproducible shuffles. See `_orderings`.
ROTATIONS = 24
SHUFFLES = 24
SEED = 20260725
_U64 = 0xFFFFFFFFFFFFFFFF

type Route = list[Cell]


class EphemeralError(LittlemanError):
    """The handoff markers cannot be turned into pipes."""


@dataclass(frozen=True, slots=True)
class Marker:
    """One pipe end: where it attaches, to which room, and which way the flow goes there."""

    cell: Cell
    label: str
    room: int
    # Flow direction at this cell: away from the wall for a FROM end, into it for a TO end.
    direction: int
    outgoing: bool
    # True for the labelled `b`/`B` form, False for a bare letter pair.
    legacy: bool


@dataclass(frozen=True, slots=True)
class Pair:
    """One pipe waiting to be routed, with both ends already placed on the padded canvas.

    ``exit_cell`` is the cell straight out from the FROM marker's wall. The pipe's first step is
    forced there — an arrowhead leaving a room points away from it — so that cell belongs to this
    pipe and nothing else may take it. ``entry_cell`` is the mirror at the TO end: not forced, since
    a pipe may bend into its last cell from either side, but reserving it too keeps a sprawl open.
    """

    label: str
    start: Marker
    end: Marker
    head: Cell
    tail: Cell
    exit_cell: Cell
    entry_cell: Cell
    want: int


class _Blocked(Exception):
    """One pipe failed under one ordering — raw material for a diagnostic, not a user-facing error."""

    def __init__(self, pair: Pair, reason: str, cells: list[Cell], detail: int = 0) -> None:
        super().__init__(reason)
        self.pair = pair
        self.reason = reason
        self.cells = cells
        self.detail = detail
        # Filled in by the caller, which knows what had already been routed when this one failed.
        self.owner: dict[Cell, str] = {}
        self.routed: list[str] = []


@dataclass(frozen=True, slots=True)
class Synthesis:
    """A loadable program plus everything the designer has to be told about it."""

    source: str
    program: Program
    # Pipe index -> the marker label it was synthesised from.
    labels: dict[int, str]
    warnings: list[str]
    report: list[str]


def synthesise(source: str, *, min_lengths: dict[str, int] | None = None) -> Synthesis:
    """Turn the handoff markers into real pipes, load the result, and analyse its resolution.

    ``min_lengths`` maps a label to the minimum number of cells that pipe must have (a delay line
    needs capacity; everything else needs 2). A route is lengthened to meet it, or the whole thing
    raises — an ephemeral run with the wrong latency is worse than no run.
    """
    grid = Grid.parse(source)
    rooms = _find_rooms(grid)
    _reject_reserved(grid, rooms)
    markers, label_cells = _find_markers(grid, rooms)
    if not markers:
        raise EphemeralError(
            "no handoff markers outside a room wall — this program has nothing to synthesise "
            "(run it without --ephemeral-pipes)"
        )

    canvas = _canvas(grid, markers, label_cells)
    free = {
        (x, y)
        for y, row in enumerate(canvas)
        for x, char in enumerate(row)
        if char == " "
    }
    free -= {_shift(marker.cell) for marker in markers}

    pairs = _plan(_pairs(markers), min_lengths or {})
    _reject_exit_collisions(pairs, markers, free)
    cells, routes = _route_all(canvas, free, pairs)

    text = _trim(cells)
    program = load_program(text)
    labels = _match_labels(program, routes, text, cells)
    warnings, report = analyse(program, labels)
    return Synthesis(source=text, program=program, labels=labels, warnings=warnings, report=report)


# --------------------------------------------------------------------------- markers


def _find_markers(grid: Grid, rooms: list[Room]) -> tuple[list[Marker], set[Cell]]:
    """Every marker in the design, in either form, plus the cells that were read as labels.

    Inside a room every letter is an instruction, so only cells outside the walls are looked at.
    The labelled `b`/`B` form is resolved first because it is the one that consumes a neighbour;
    whatever is left over on a wall is a bare letter pair.
    """
    letters = _letter_cells(grid, rooms)
    attached = {cell for cell in letters if _touches_border(rooms, cell)}
    markers, label_cells = _legacy_markers(grid, rooms, attached)
    taken = {marker.cell for marker in markers} | set(label_cells)
    for cell in sorted(attached - taken, key=lambda c: c[::-1]):
        markers.append(_pair_marker(rooms, grid.at(*cell), cell))
    _reject_loose(grid, letters - attached, set(label_cells))
    return markers, set(label_cells)


def _reject_reserved(grid: Grid, rooms: list[Room]) -> None:
    """`v` / `V` in a marker position: name the letter and say it is reserved, never misparse it.

    `v` is the arrowhead the router itself writes, so it cannot also mean "a pipe starts here". A
    lone `v` against a wall is left alone — that is a hand-drawn pipe, which is legal. A `V` there
    is not a pipe glyph, not an instruction (it is outside every room) and not a marker, so the only
    thing it can be is somebody trying to name a pipe `v`.
    """
    spots = [
        (x, y)
        for y in range(grid.height)
        for x in range(grid.width)
        if grid.at(x, y) in RESERVED_LETTERS
        and not _in_room(rooms, x, y)
        and _touches_border(rooms, (x, y))
    ]
    upper = next((cell for cell in spots if grid.at(*cell) == "V"), None)
    if upper is None:
        return
    twin = next((cell for cell in spots if grid.at(*cell) == "v"), None)
    where = f", and its 'v' twin is at ({twin[0]},{twin[1]})" if twin is not None else ""
    raise EphemeralError(
        f"the 'V' at ({upper[0]},{upper[1]}) sits against a room wall where a marker goes{where} — "
        f"but 'v' and 'V' are RESERVED and can never name or label a pipe: 'v' is the arrowhead "
        f"glyph the router writes into the grid, so a 'v' marker would be indistinguishable from a "
        f"drawn pipe. Rename that pipe to any other letter; only v/V are taken."
    )


def _letter_cells(grid: Grid, rooms: list[Room]) -> set[Cell]:
    return {
        (x, y)
        for y in range(grid.height)
        for x in range(grid.width)
        if grid.at(x, y) in _MARKER_LETTERS and not _in_room(rooms, x, y)
    }


def _touches_border(rooms: list[Room], cell: Cell) -> bool:
    x, y = cell
    return any(_border_room(rooms, x + dx, y + dy) is not None for dx, dy in DELTAS)


def _pair_marker(rooms: list[Room], char: str, cell: Cell) -> Marker:
    """A bare letter: lowercase starts the pipe, uppercase ends it, the letter names it."""
    room, toward_wall = _attachment(rooms, char, *cell)
    outgoing = char.islower()
    direction = (toward_wall + 2) % 4 if outgoing else toward_wall
    return Marker(cell, char.lower(), room, direction, outgoing, legacy=False)


def _reject_loose(grid: Grid, loose: set[Cell], label_cells: set[Cell]) -> None:
    """A letter floating outside every room is either a label or a mistake — never ignored."""
    for cell in sorted(loose - label_cells, key=lambda c: c[::-1]):
        x, y = cell
        raise EphemeralError(
            f"the letter {grid.at(x, y)!r} at ({x},{y}) is outside every room but touches no room "
            f"wall — a marker sits on the cell immediately outside the border it attaches to, so "
            f"move it against the wall or delete it"
        )


def _attachment(rooms: list[Room], char: str, x: int, y: int) -> tuple[int, int]:
    """Which room the marker touches, and the direction from the marker to that wall."""
    touching = []
    for direction, (dx, dy) in enumerate(DELTAS):
        room = _border_room(rooms, x + dx, y + dy)
        if room is not None:
            touching.append((room, direction))
    if not touching:
        raise EphemeralError(
            f"the {char!r} marker at ({x},{y}) touches no room wall — a marker goes on the cell "
            f"immediately outside the border it attaches to"
        )
    if len(touching) > 1:
        walls = ", ".join(f"room {room} to the {_SIDES[d]}" for room, d in touching)
        raise EphemeralError(
            f"the {char!r} marker at ({x},{y}) touches two room walls ({walls}) — leave a blank "
            f"cell between the blocks so the attachment is unambiguous"
        )
    return touching[0]


def _legacy_markers(
    grid: Grid, rooms: list[Room], attached: set[Cell]
) -> tuple[list[Marker], dict[Cell, Cell]]:
    """The labelled `b`/`B` form: a marker that has a label next to it, and the label it ate.

    A bare `b` or `B` is left for the letter-pair pass — it is simply the pipe named `b`.
    """
    markers: list[Marker] = []
    label_cells: dict[Cell, Cell] = {}
    for cell in sorted(attached, key=lambda c: c[::-1]):
        char = grid.at(*cell)
        if char not in ("b", "B"):
            continue
        label = _label_of(grid, rooms, cell, char, label_cells, attached)
        if label is None:
            continue
        room, toward_wall = _attachment(rooms, char, *cell)
        direction = toward_wall if char == "B" else (toward_wall + 2) % 4
        markers.append(Marker(cell, label, room, direction, char == "b", legacy=True))
    return markers, label_cells


def _label_of(
    grid: Grid,
    rooms: list[Room],
    cell: Cell,
    char: str,
    label_cells: dict[Cell, Cell],
    attached: set[Cell],
) -> str | None:
    x, y = cell
    found = [
        ((x + dx, y + dy), grid.at(x + dx, y + dy))
        for dx, dy in DELTAS
        if grid.at(x + dx, y + dy) in _LABELS and not _in_room(rooms, x + dx, y + dy)
    ]
    if not found:
        _reject_reserved_label(grid, rooms, cell, char)
        # No label: this is the letter pair `b`/`B`, handled by the caller's second pass.
        return None
    if len(found) > 1:
        where = ", ".join(f"{c!r} at ({p[0]},{p[1]})" for p, c in found)
        raise EphemeralError(
            f"the {char!r} marker at ({x},{y}) has {len(found)} labels next to it ({where}) — "
            f"a labelled marker takes exactly one; if those are letter-pair markers, leave a "
            f"blank cell between them"
        )
    at, label = found[0]
    _reject_two_readings(grid, cell, at, label, attached)
    if at in label_cells:
        owner = label_cells[at]
        raise EphemeralError(
            f"the label {label!r} at ({at[0]},{at[1]}) sits next to two markers, ({owner[0]},"
            f"{owner[1]}) and ({x},{y}) — give each marker its own label cell"
        )
    label_cells[at] = (x, y)
    return label


def _reject_reserved_label(grid: Grid, rooms: list[Room], cell: Cell, char: str) -> None:
    """`bv` is somebody labelling a pipe `v`. Say the letter is reserved instead of ignoring it."""
    x, y = cell
    for dx, dy in DELTAS:
        at = (x + dx, y + dy)
        if grid.at(*at) not in RESERVED_LETTERS or _in_room(rooms, *at):
            continue
        raise EphemeralError(
            f"the {grid.at(*at)!r} at ({at[0]},{at[1]}) is next to the {char!r} marker at "
            f"({x},{y}), which reads as a label — but 'v' and 'V' are RESERVED and can never name "
            f"or label a pipe: 'v' is the arrowhead glyph the router writes into the grid. Label "
            f"that pipe with a digit ({char}1) or any other letter."
        )


def _reject_two_readings(
    grid: Grid, marker: Cell, at: Cell, label: str, attached: set[Cell]
) -> None:
    """Refuse a `b`/`B` whose 'label' is itself half of a letter pair — that grid reads two ways."""
    if not label.isalpha():
        return
    other_case = label.swapcase()
    candidates = sorted(attached - {at}, key=lambda c: c[::-1])
    twin = next((c for c in candidates if grid.at(*c) == other_case), None)
    if twin is None:
        return
    char = grid.at(*marker)
    raise EphemeralError(
        f"the {label!r} at ({at[0]},{at[1]}) is one cell from the {char!r} marker at "
        f"({marker[0]},{marker[1]}), and that reads two ways:\n"
        f"  (1) labelled form — {label!r} is the label of that {char!r}, making one pipe "
        f"{char}{label}, and the {grid.at(*twin)!r} at ({twin[0]},{twin[1]}) is then an unpaired "
        f"marker;\n"
        f"  (2) letter-pair form — {label!r} is a marker in its own right, pairing with the "
        f"{grid.at(*twin)!r} at ({twin[0]},{twin[1]}), and the {char!r} is then a bare "
        f"{char.lower()!r} pipe needing its own {char.swapcase()!r}.\n"
        f"  fix: put a blank cell between the {label!r} and the {char!r}, or label the {char!r} "
        f"pipe with a digit ({char}1), which can never be mistaken for a letter pair"
    )


def _pairs(markers: list[Marker]) -> list[tuple[str, Marker, Marker]]:
    grouped: dict[str, list[Marker]] = {}
    for marker in markers:
        grouped.setdefault(marker.label, []).append(marker)
    pairs = []
    for label in sorted(grouped):
        group = grouped[label]
        if len({marker.legacy for marker in group}) > 1:
            raise EphemeralError(
                f"pipe {label!r} mixes the labelled 'b'/'B' form with the letter-pair form — "
                f"write both ends of one pipe the same way"
            )
        # Name the ends the way the designer wrote them, so the error points at their own glyphs.
        start, end = ("b", "B") if group[0].legacy else (label, label.upper())
        starts = [m for m in group if m.outgoing]
        ends = [m for m in group if not m.outgoing]
        if len(starts) != 1 or len(ends) != 1:
            raise EphemeralError(
                f"pipe {label!r} has {len(starts)} {start!r} and {len(ends)} {end!r} marker(s) — "
                f"a pipe is exactly one of each"
            )
        pairs.append((label, starts[0], ends[0]))
    return pairs


# --------------------------------------------------------------------------- routing


def _shift(cell: Cell) -> Cell:
    return (cell[0] + MARGIN, cell[1] + MARGIN)


def _canvas(grid: Grid, markers: list[Marker], label_cells: set[Cell]) -> list[list[str]]:
    """The design on a blank frame, with the markers and their labels erased.

    They are notation, not program text: the marker cell becomes the pipe's first or last cell, and
    the label cell becomes free space a pipe may route through.
    """
    width, height = grid.width + 2 * MARGIN, grid.height + 2 * MARGIN
    cells = [[" "] * width for _ in range(height)]
    for y in range(grid.height):
        for x in range(grid.width):
            cells[y + MARGIN][x + MARGIN] = grid.at(x, y)
    for cell in [m.cell for m in markers] + list(label_cells):
        x, y = _shift(cell)
        cells[y][x] = " "
    return cells


def _unshift(cell: Cell) -> Cell:
    return (cell[0] - MARGIN, cell[1] - MARGIN)


def _glyph_of(marker: Marker) -> str:
    """The character the designer actually typed, so an error points at their own grid."""
    if marker.legacy:
        return "b" if marker.outgoing else "B"
    return marker.label if marker.outgoing else marker.label.upper()


def _plan(pairs: list[tuple[str, Marker, Marker]], lengths: dict[str, int]) -> list[Pair]:
    """Place both ends of every pipe on the canvas and work out the cells they must leave through."""
    planned = []
    for label, start, end in pairs:
        # A letter pipe is named by its lowercase letter; `--pipe-length A=6` means the same thing.
        want = max(2, lengths.get(label, lengths.get(label.swapcase(), 2)))
        head, tail = _shift(start.cell), _shift(end.cell)
        out_x, out_y = DELTAS[start.direction]
        in_x, in_y = DELTAS[(end.direction + 2) % 4]
        planned.append(
            Pair(
                label=label,
                start=start,
                end=end,
                head=head,
                tail=tail,
                exit_cell=(head[0] + out_x, head[1] + out_y),
                entry_cell=(tail[0] + in_x, tail[1] + in_y),
                want=want,
            )
        )
    return planned


def _reject_exit_collisions(pairs: list[Pair], markers: list[Marker], free: set[Cell]) -> None:
    """The exit-cell rule, checked before a single pipe is drawn.

    The cell straight out from a FROM marker's wall is that pipe's first segment — no search can
    route around it. So a second marker sitting there, or a wall, or two pipes wanting the same
    cell, is a design error with a fix in the design, and saying so now beats a routing failure
    forty pipes later.
    """
    at_cell = {_shift(marker.cell): marker for marker in markers}
    for pair in pairs:
        cell = pair.exit_cell
        # A two-cell pipe: its exit *is* the far marker, which is exactly right.
        if cell == pair.tail:
            continue
        x, y = _unshift(cell)
        other = at_cell.get(cell)
        if other is not None:
            raise EphemeralError(
                f"the {_glyph_of(other)!r} marker at ({x},{y}) sits one cell out from the "
                f"{_glyph_of(pair.start)!r} marker at ({pair.start.cell[0]},{pair.start.cell[1]}), "
                f"and that reads two ways:\n"
                f"  (1) it is a marker of its own, ending or starting pipe {other.label!r};\n"
                f"  (2) it is the cell pipe {pair.label!r} has to leave through — an arrowhead "
                f"leaving a room points straight away from the wall, so that cell is pipe "
                f"{pair.label!r}'s own first segment.\n"
                f"  It cannot be both. Fix: slide one marker one cell along its wall, or leave a "
                f"blank cell between them."
            )
        if cell not in free:
            raise EphemeralError(
                f"pipe {pair.label!r} cannot leave its room: the cell straight out from the "
                f"{_glyph_of(pair.start)!r} marker at ({pair.start.cell[0]},{pair.start.cell[1]}) "
                f"is ({x},{y}), which is not blank. That cell is the pipe's own first segment and "
                f"must stay clear — move the marker along its wall, or open up ({x},{y})."
            )
    claimed: dict[Cell, Pair] = {}
    for pair in pairs:
        if pair.exit_cell == pair.tail:
            continue
        owner = claimed.setdefault(pair.exit_cell, pair)
        if owner is pair:
            continue
        x, y = _unshift(pair.exit_cell)
        raise EphemeralError(
            f"pipes {owner.label!r} and {pair.label!r} both have to leave through ({x},{y}) — "
            f"their FROM markers face the same cell, and it can only be one pipe's first segment. "
            f"Move one marker along its wall."
        )


def _reservations(pairs: list[Pair], *, ends: bool) -> dict[Cell, str]:
    """Cell -> the one pipe allowed to use it. Exit cells are reserved before anything is routed.

    That is the fix for the failure the router used to have: it took pipes one at a time, so an
    early route could sit down on a later pipe's exit cell and there was no way back. FROM exits are
    unconditional. TO entries are a preference — a pipe may bend into its last cell from the side —
    so they are reserved on the first pass and dropped on the second.
    """
    reserved = {pair.exit_cell: pair.label for pair in pairs if pair.exit_cell != pair.tail}
    if not ends:
        return reserved
    shared: set[Cell] = set()
    entries: dict[Cell, str] = {}
    for pair in pairs:
        cell = pair.entry_cell
        if cell in (pair.head, pair.tail) or cell in reserved or cell in shared:
            continue
        if entries.setdefault(cell, pair.label) != pair.label:
            # Two pipes would both like it: reserving it for either helps neither, so leave it open.
            del entries[cell]
            shared.add(cell)
    return reserved | entries


def _tightness(pair: Pair) -> tuple[int, int, str]:
    """Least freedom first: short before long, straight before bent, then by name for determinism."""
    (hx, hy), (tx, ty) = pair.head, pair.tail
    straight = 0 if hx == tx or hy == ty else 1
    return (abs(tx - hx) + abs(ty - hy), straight, pair.label)


def _xorshift(state: int) -> int:
    """One step of Marsaglia's xorshift64, shifts 13 / 7 / 17, truncated to 64 bits.

    THE ORDER THIS PRODUCES IS PART OF THE CONTRACT. `rs/crates/littleman/src/ephemeral.rs` runs the
    same generator with the same seed so both routers synthesise the same pipe graph; see
    ``docs/vault/heap/The retry order is a specification, not a shuffle.md``. It replaced
    ``random.Random(SEED).shuffle`` on 2026-07-25, which no other language can reproduce.
    """
    state ^= (state << 13) & _U64
    state ^= state >> 7
    state ^= (state << 17) & _U64
    return state


def _shuffles(pairs: list[Pair], rounds: int) -> list[list[Pair]]:
    """``rounds`` permutations of ``pairs``: Fisher-Yates, `i` from the end down, `j = rand % (i+1)`.

    One generator drives all the rounds, so round two continues where round one left off — and every
    round shuffles a *fresh* copy of the input order, not the previous permutation.
    """
    state = SEED
    out = []
    for _ in range(rounds):
        order = list(pairs)
        for i in range(len(order) - 1, 0, -1):
            state = _xorshift(state)
            j = state % (i + 1)
            order[i], order[j] = order[j], order[i]
        out.append(order)
    return out


def _orderings(pairs: list[Pair]) -> list[list[Pair]]:
    """Orders to try, best guess first. Label order is kept as one of them, never as the only one.

    The first three are the good guesses and are what almost every design routes on. The tail is
    there for the sprawls that do not: rotations of the tight order (which move exactly one pipe out
    of everyone else's way, the usual reason a pass fails) and then reproducible shuffles. Order
    matters only in that the *first* one to succeed wins, so lengthening the tail can turn a failure
    into a success but can never do the reverse.
    """
    tight = sorted(pairs, key=_tightness)
    orders = [tight, tight[::-1], sorted(pairs, key=lambda pair: pair.label)]
    orders += [tight[cut:] + tight[:cut] for cut in range(1, min(len(tight), ROTATIONS + 1))]
    orders += _shuffles(pairs, SHUFFLES)
    seen: set[tuple[str, ...]] = set()
    unique = []
    for order in orders:
        key = tuple(pair.label for pair in order)
        if key in seen:
            continue
        seen.add(key)
        unique.append(order)
    return unique


def _route_all(
    canvas: list[list[str]], free: set[Cell], pairs: list[Pair]
) -> tuple[list[list[str]], dict[str, Route]]:
    """Route every pipe, retrying under other orders before giving up — and never giving up quietly."""
    best: tuple[int, str] | None = None
    for ends in (True, False):
        reserved = _reservations(pairs, ends=ends)
        for order in _orderings(pairs):
            try:
                return _attempt(canvas, free, order, reserved)
            except _Blocked as blocked:
                message, retry = _diagnose(blocked, free, pairs)
                if not retry:
                    raise EphemeralError(message) from None
                if best is None or len(blocked.routed) >= best[0]:
                    best = (len(blocked.routed), message)
    assert best is not None
    raise EphemeralError(best[1])


def _attempt(
    canvas: list[list[str]], free: set[Cell], order: list[Pair], reserved: dict[Cell, str]
) -> tuple[list[list[str]], dict[str, Route]]:
    """One full pass over the pipes in one order, on its own copy of the canvas."""
    blocked_for = {
        label: {cell for cell, owner in reserved.items() if owner != label}
        for label in {pair.label for pair in order}
    }
    cells = [row[:] for row in canvas]
    left = set(free)
    owner: dict[Cell, str] = {}
    routes: dict[str, Route] = {}
    for pair in order:
        try:
            route = _draw(cells, left - blocked_for[pair.label], pair)
        except _Blocked as blocked:
            blocked.owner = owner
            blocked.routed = list(routes)
            raise
        routes[pair.label] = route
        left -= set(route)
        owner |= dict.fromkeys(route, pair.label)
    return cells, routes


def _draw(cells: list[list[str]], free: set[Cell], pair: Pair) -> Route:
    """Route one pipe and write its glyphs. Returns the cells, source first."""
    if pair.exit_cell == pair.tail:
        route = [pair.head, pair.tail]
    elif pair.exit_cell not in free:
        raise _Blocked(pair, "exit", [pair.exit_cell])
    else:
        rest = _route(free | {pair.tail}, pair.exit_cell, pair.tail, pair.want - 1, pair)
        route = [pair.head, *rest]

    if len(route) < pair.want:
        raise _Blocked(pair, "short", route, detail=pair.want)
    for cell, glyph in zip(route, _glyphs(route, pair.end.direction), strict=True):
        cells[cell[1]][cell[0]] = glyph
    return route


def _route(free: set[Cell], start: Cell, goal: Cell, want: int, pair: Pair) -> Route:
    """A simple path of at least ``want`` cells from ``start`` to ``goal`` through ``free``."""
    dist = _distances(free, goal)
    if start not in dist:
        raise _Blocked(pair, "unreachable", [start, goal])
    target = max(dist[start] + 1, want)
    # A grid is bipartite, so every simple path between two cells has the same length parity.
    target += (target - dist[start] - 1) % 2
    return _walk(free, dist, start, goal, target, pair)


def _distances(free: set[Cell], goal: Cell) -> dict[Cell, int]:
    """Breadth-first distance to ``goal`` for every reachable free cell."""
    seen = {goal: 0}
    frontier = [goal]
    while frontier:
        nxt = []
        for x, y in frontier:
            for dx, dy in DELTAS:
                cell = (x + dx, y + dy)
                if cell in free and cell not in seen:
                    seen[cell] = seen[(x, y)] + 1
                    nxt.append(cell)
        frontier = nxt
    return seen


def _walk(
    free: set[Cell], dist: dict[Cell, int], start: Cell, goal: Cell, target: int, pair: Pair
) -> Route:
    """Depth-first search for a simple path of exactly ``target`` cells, distance-pruned."""
    path = [start]
    seen = {start}
    stack = [iter(_options(dist, start, target - 1, seen))]
    budget = ROUTE_BUDGET
    while stack:
        budget -= 1
        if budget < 0:
            raise _Blocked(pair, "budget", [start, goal], detail=target)
        cell = next(stack[-1], None)
        if cell is None:
            stack.pop()
            seen.discard(path.pop())
            continue
        path.append(cell)
        seen.add(cell)
        if len(path) == target and cell == goal:
            return path
        stack.append(iter(_options(dist, cell, target - len(path), seen)))
    raise _Blocked(pair, "length", [start, goal], detail=target)


def _options(dist: dict[Cell, int], cell: Cell, remaining: int, seen: set[Cell]) -> list[Cell]:
    """Free neighbours that can still reach the goal in exactly ``remaining`` more steps.

    ``remaining`` counts steps left from ``cell``, so a neighbour has ``remaining - 1`` — and since
    a grid is bipartite, one that cannot spend exactly that many is pruned on parity, not tried.
    """
    x, y = cell
    left = remaining - 1
    out = []
    for dx, dy in DELTAS:
        step = (x + dx, y + dy)
        reach = dist.get(step)
        if step in seen or reach is None or reach > left or (left - reach) % 2:
            continue
        # Landing on the goal early strands the path: it may only be entered on the last step.
        if reach == 0 and left != 0:
            continue
        out.append(step)
    # Closing on the goal first keeps the drawing tidy and the search shallow.
    return sorted(out, key=lambda c: dist[c])


# --------------------------------------------------------------------------- diagnostics


def _where(marker: Marker) -> str:
    return f"{_glyph_of(marker)!r} at ({marker.cell[0]},{marker.cell[1]}) on room {marker.room}"


def _descend(dist: dict[Cell, int], start: Cell, goal: Cell) -> Route:
    """One shortest path from ``start`` to ``goal``, read straight off a distance map."""
    path = [start]
    cell = start
    while cell != goal and len(path) <= len(dist):
        x, y = cell
        options = [(x + dx, y + dy) for dx, dy in DELTAS if (x + dx, y + dy) in dist]
        cell = min(options, key=lambda step: dist[step])
        path.append(cell)
    return path


def _diagnose(blocked: _Blocked, free: set[Cell], pairs: list[Pair]) -> tuple[str, bool]:
    """The failure report, and whether another pipe ordering could plausibly rescue it.

    Every coordinate here is in the *design's* own frame, not the padded canvas — the human has to
    be able to point at the cell in their own file.
    """
    pair = blocked.pair
    lines, retry = _explain(blocked, free)
    header = (
        f"ephemeral routing failed on pipe {pair.label!r}: no route from the FROM marker "
        f"{_where(pair.start)} to the TO marker {_where(pair.end)}"
    )
    if blocked.routed:
        order = ", ".join(repr(label) for label in blocked.routed)
        lines.append(
            f"  {len(blocked.routed)} of {len(pairs)} pipes were routed first, in this order: "
            f"{order}"
        )
    return "\n".join([header, *lines]), retry


def _explain(blocked: _Blocked, free: set[Cell]) -> tuple[list[str], bool]:
    pair = blocked.pair
    if blocked.reason == "exit":
        return _explain_exit(blocked)
    if blocked.reason == "unreachable":
        return _explain_unreachable(blocked, free)
    goal = _unshift(pair.tail)
    return (
        [
            f"  it needs a {blocked.detail}-cell route into ({goal[0]},{goal[1]}) and the free "
            f"space left will not carry one"
            + ("" if blocked.reason != "budget" else f" (gave up after {ROUTE_BUDGET} steps)"),
            f"  asked-for minimum length: {pair.want} cells",
            "  fix: ask for a different --pipe-length, or open a blank row or column near the "
            "receiving room so the pipe has somewhere to fold",
        ],
        True,
    )


def _explain_exit(blocked: _Blocked) -> tuple[list[str], bool]:
    pair = blocked.pair
    x, y = _unshift(pair.exit_cell)
    lines = [
        f"  the cell straight out from its FROM marker is ({x},{y}); an arrowhead leaving a room "
        f"points away from the wall, so that cell is pipe {pair.label!r}'s own first segment"
    ]
    culprit = blocked.owner.get(pair.exit_cell)
    if culprit is None:
        lines.append("  it is not free, and no already-routed pipe is in it")
        lines.append(f"  fix: clear ({x},{y}), or slide the FROM marker one cell along its wall")
        return lines, False
    lines.append(f"  pipe {culprit!r} was routed first and is sitting in it")
    lines.append(
        f"  fix: slide one of the two markers one cell along its wall, or leave a blank column for "
        f"pipe {culprit!r} to detour through"
    )
    return lines, True


def _explain_unreachable(blocked: _Blocked, free: set[Cell]) -> tuple[list[str], bool]:
    start, goal = blocked.cells
    sx, sy = _unshift(start)
    gx, gy = _unshift(goal)
    lines = [
        f"  no free path from its exit cell ({sx},{sy}) to the TO marker at ({gx},{gy})",
    ]
    open_dist = _distances(free | {goal}, goal)
    if start not in open_dist:
        lines.append(
            "  and none exists on an empty grid either — the two rooms are not connected by blank "
            "cells at all"
        )
        lines.append("  fix: leave a blank row or column between the blocks")
        return lines, False
    corridor = _descend(open_dist, start, goal)
    blockers = sorted({blocked.owner[cell] for cell in corridor if cell in blocked.owner})
    if not blockers:
        lines.append(
            "  the corridor is clear on an empty grid, so what closed it is the exit cells reserved "
            "for other pipes"
        )
        lines.append(
            "  fix: widen the gap between the blocks, or move the markers whose exits crowd this "
            "corridor"
        )
        return lines, True
    named = ", ".join(repr(label) for label in blockers)
    lines.append(f"  the only corridor between them is blocked by already-routed pipe(s): {named}")
    lines.append(
        f"  fix: widen that corridor by one cell, or move pipe {blockers[0]!r} out of it — the "
        f"router already retried other pipe orders and none of them cleared it"
    )
    return lines, True


def _glyphs(route: Route, entry: int) -> list[str]:
    """Pipe glyphs for a route: a body along a straight run, an arrowhead at every bend.

    The first and last cells are always arrowheads — the first so the pipe reads as leaving its
    room, the last so it points into the receiving one (that terminal arrowhead may itself be the
    final bend).
    """
    directions = [_direction(route[i], route[i + 1]) for i in range(len(route) - 1)] + [entry]
    glyphs = [_ARROW[directions[0]]]
    for index in range(1, len(route)):
        turn = directions[index] != directions[index - 1]
        last = index == len(route) - 1
        if turn or last:
            glyphs.append(_ARROW[directions[index]])
            continue
        glyphs.append("-" if directions[index] in (0, 2) else "|")
    return glyphs


def _direction(here: Cell, there: Cell) -> int:
    return DELTAS.index((there[0] - here[0], there[1] - here[1]))


def _trim(cells: list[list[str]]) -> str:
    text = "\n".join("".join(row).rstrip() for row in cells)
    grid = Grid.parse(text)
    x0, y0, x1, y1 = grid.content_box()
    if x1 < x0:
        return ""
    return "\n".join(row[x0 : x1 + 1].rstrip() for row in grid.rows[y0 : y1 + 1]) + "\n"


def _match_labels(
    program: Program, routes: dict[str, Route], text: str, cells: list[list[str]]
) -> dict[int, str]:
    """Pipe index -> label, matched on the source cell after the canvas was trimmed."""
    x0, y0, _, _ = Grid.parse("\n".join("".join(row).rstrip() for row in cells)).content_box()
    by_source = {(route[0][0] - x0, route[0][1] - y0): label for label, route in routes.items()}
    labels = {}
    for index, pipe in enumerate(program.pipes):
        label = by_source.get(pipe.source)
        if label is not None:
            labels[index] = label
    return labels


# --------------------------------------------------------------------------- analysis


def analyse(program: Program, labels: dict[int, str]) -> tuple[list[str], list[str]]:
    """Per-room resolution report, plus every warning a repack could turn into a wrong answer.

    Both come from the loader's own ``nearest_out`` / ``nearest_in`` tables, so this is what the
    machine will actually do — with the synthesised geometry.
    """
    warnings: list[str] = []
    report: list[str] = []
    for index, room in enumerate(program.rooms):
        if room.kind == "display":
            continue
        warnings += _side_warnings(program, labels, index, room)
        lines = _room_report(program, labels, index, room, warnings)
        if lines:
            report.append(_room_header(program, labels, index, room))
            report += lines
    return warnings, report


def _name(program: Program, labels: dict[int, str], index: int) -> str:
    pipe = program.pipes[index]
    label = labels.get(index, "?")
    return f"pipe {label!r} (room {pipe.src_room} -> room {pipe.dst_room})"


def _side(room: Room, cell: Cell) -> str:
    x, y = cell
    if y == room.y0 - 1:
        return "north"
    if y == room.y1 + 1:
        return "south"
    if x == room.x0 - 1:
        return "west"
    if x == room.x1 + 1:
        return "east"
    return "off-wall"


def _segment(program: Program, room_index: int, pipe_index: int) -> Cell:
    pipe = program.pipes[pipe_index]
    return pipe.source if pipe.src_room == room_index else pipe.dest


def _side_warnings(
    program: Program, labels: dict[int, str], index: int, room: Room
) -> list[str]:
    sides: dict[str, list[int]] = {}
    for pipe_index in room.outgoing + room.incoming:
        side = _side(room, _segment(program, index, pipe_index))
        sides.setdefault(side, []).append(pipe_index)
    warnings = []
    for side, group in sides.items():
        if len(group) < 2:
            continue
        named = ", ".join(_name(program, labels, i) for i in group)
        warnings.append(
            f"WARN room {index} at ({room.x0},{room.y0}) has {len(group)} pipes on its {side} "
            f"side: {named} — their order along that wall decides who wins a nearest-pipe tie, so "
            f"the packer has to be told it"
        )
    return warnings


def _room_header(program: Program, labels: dict[int, str], index: int, room: Room) -> str:
    kind = "" if room.kind == "room" else f" [{room.kind}]"
    out = ", ".join(labels.get(i, "?") for i in room.outgoing) or "-"
    into = ", ".join(labels.get(i, "?") for i in room.incoming) or "-"
    return f"room {index}{kind} ({room.x0},{room.y0})-({room.x1},{room.y1})  out={out} in={into}"


def _room_report(
    program: Program, labels: dict[int, str], index: int, room: Room, warnings: list[str]
) -> list[str]:
    lines = []
    for cell in room.interior_cells():
        char = program.grid.at(*cell)
        if char not in "srq":
            continue
        outgoing = char == "s"
        table = program.nearest_out if outgoing else program.nearest_in
        chosen = table.get(cell)
        candidates = room.outgoing if outgoing else room.incoming
        if chosen is None:
            lines.append(f"  {char!r} at ({cell[0]},{cell[1]}) -> NO PIPE")
            continue
        ranked = sorted(
            ((_walk_distance(program, index, i, cell), i) for i in candidates),
            key=lambda pair: (pair[0], _segment(program, index, pair[1])[::-1]),
        )
        note = _resolution_note(program, labels, index, cell, char, ranked, warnings)
        lines.append(f"  {char!r} at ({cell[0]},{cell[1]}) -> {_name(program, labels, chosen)}{note}")
    return lines


def _walk_distance(program: Program, room_index: int, pipe_index: int, cell: Cell) -> int:
    x, y = _segment(program, room_index, pipe_index)
    return abs(x - cell[0]) + abs(y - cell[1])


def _resolution_note(
    program: Program,
    labels: dict[int, str],
    index: int,
    cell: Cell,
    char: str,
    ranked: list[tuple[int, int]],
    warnings: list[str],
) -> str:
    if len(ranked) < 2:
        return "  (the room's only one — unambiguous)"
    (best, winner), (second, runner_up) = ranked[0], ranked[1]
    if best == second:
        warnings.append(
            f"WARN AMBIGUOUS {char!r} at ({cell[0]},{cell[1]}) in room {index} is {best} cells "
            f"from {_name(program, labels, winner)} and {second} from "
            f"{_name(program, labels, runner_up)}; reading order picks "
            f"{labels.get(winner, '?')!r} — any repack can flip it"
        )
        return f"  (TIED at {best} with {labels.get(runner_up, '?')!r}, broken by reading order)"
    return f"  ({best} cells vs {second} to {labels.get(runner_up, '?')!r} — hold this ordering)"


BANNER = (
    "ephemeral pipes: the pipes below were SYNTHESISED from handoff markers. A pass proves the "
    "LOGIC, not the LAYOUT — real routing moves every pipe segment, and s/r/q take the nearest "
    "pipe, so a repack can silently re-point a send.\n"
    "And local proves less than it looks: on 2026-07-25 a 46x46 matmul repack passed 7/7 public "
    "and 95/95 fuzzed cases under both lm and lmr, and the server still returned 18/20 — it had "
    "loaded a different pipe graph than either local loader. Ephemeral pipes are a cheap early "
    "filter for logic errors, never a substitute for `icfp submit --wait`."
)


def pipe_graph(program: Program, labels: dict[int, str]) -> list[str]:
    """The resolved edge list: which room-to-room edge each pipe forms, and where it attaches.

    This is the artifact to diff against the server when a repack regresses for no local reason.
    """
    lines = []
    for index, pipe in enumerate(program.pipes):
        label = labels.get(index, "?")
        src, dst = program.rooms[pipe.src_room], program.rooms[pipe.dst_room]
        lines.append(
            f"pipe {label!r} #{index}: room {pipe.src_room}{_kind(src)} {pipe.source} "
            f"[{_side(src, pipe.source)}] -> room {pipe.dst_room}{_kind(dst)} {pipe.dest} "
            f"[{_side(dst, pipe.dest)}], {len(pipe.cells)} cell(s)"
        )
    return lines


def _kind(room: Room) -> str:
    return "" if room.kind == "room" else f"[{room.kind}]"
