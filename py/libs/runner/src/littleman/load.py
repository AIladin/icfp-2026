"""Source text to a ``Program``: every structural rule is checked here, before any tick runs.

The contest server reports these failures as ``loadError`` with no test case run at all, so anything
this module lets through and the server rejects costs a submission round-trip. The four documented
pipe traps (docs/vault/heap/Pipes/Pipe drawing traps.md) are encoded as explicit checks.
"""

from .errors import LoadError
from .grid import Grid
from .model import ARROWS, DELTAS, MAX_DISPLAY, Cell, Display, Pipe, Program, Room

_DIGITS = "0123456789"
_INT64_MAX = 2**63 - 1


def load_program(source: str) -> Program:
    """Parse and validate a `.man` program. Raises ``LoadError`` on anything structural."""
    grid = Grid.parse(source)

    rooms = _find_rooms(grid)
    _reject_overlaps(rooms)
    _classify_io_rooms(grid, rooms)
    spawns = _find_spawns(grid, rooms)

    pipes = _find_pipes(grid, rooms)
    for index, pipe in enumerate(pipes):
        rooms[pipe.src_room].outgoing.append(index)
        rooms[pipe.dst_room].incoming.append(index)
    input_pipe, output_pipe = _check_io_pipes(rooms, pipes)
    displays = _display_ports(rooms, pipes)

    # Displays are rooms for every structural purpose but hold no little man, so their interiors
    # stay out of the tables the tick loop walks — a 64x64 one would add 4096 dead cells.
    room_of = {
        cell: index
        for index, room in enumerate(rooms)
        if room.kind != "display"
        for cell in room.interior_cells()
    }
    nearest_out, nearest_in, incoming_sorted = _pipe_tables(rooms, pipes)

    return Program(
        grid=grid,
        rooms=rooms,
        pipes=pipes,
        displays=displays,
        spawns=spawns,
        input_pipe=input_pipe,
        output_pipe=output_pipe,
        loads=_literal_loads(grid, room_of),
        room_of=room_of,
        nearest_out=nearest_out,
        nearest_in=nearest_in,
        incoming_sorted=incoming_sorted,
    )


def _find_rooms(grid: Grid) -> list[Room]:
    """Rectangles of `+`/`-`/`|` (rooms) and of `+`/`=`/`:` (LM-75 displays), outermost first.

    A `+` inside an already-accepted room is skipped: `+` is also the addition instruction, and a
    run like `+--+` written as code would otherwise look like a nested room.
    """
    rooms: list[Room] = []
    for y in range(grid.height):
        for x in range(grid.width):
            if grid.at(x, y) != "+":
                continue
            if any(room.contains_interior(x, y) for room in rooms):
                continue
            room = _box_from_corner(grid, x, y, "-", "|") or _box_from_corner(grid, x, y, "=", ":")
            if room is not None:
                rooms.append(room)
    return rooms


def _box_from_corner(grid: Grid, x0: int, y0: int, across: str, down: str) -> Room | None:
    """The smallest verified rectangle with this cell as its top-left corner, if any.

    The wall glyphs decide what it is: `-`/`|` is a room, `=`/`:` an LM-75 display.
    """
    x1 = _run_end(grid, x0, y0, 1, 0, across)
    y1 = _run_end(grid, x0, y0, 0, 1, down)
    if x1 is None or y1 is None or x1 - x0 < 2 or y1 - y0 < 2:
        return None
    if grid.at(x1, y1) != "+":
        return None
    if any(grid.at(x, y1) != across for x in range(x0 + 1, x1)):
        return None
    if any(grid.at(x1, y) != down for y in range(y0 + 1, y1)):
        return None
    if across == "-":
        return Room(x0, y0, x1, y1)
    if x1 - x0 - 1 > MAX_DISPLAY or y1 - y0 - 1 > MAX_DISPLAY:
        raise LoadError(
            f"the display at ({x0},{y0}) is {x1 - x0 - 1}x{y1 - y0 - 1}: "
            f"the LM-75 interior caps at {MAX_DISPLAY}x{MAX_DISPLAY}"
        )
    return Room(x0, y0, x1, y1, kind="display")


def _run_end(grid: Grid, x: int, y: int, dx: int, dy: int, body: str) -> int | None:
    """Walk a wall of ``body`` glyphs from a corner; return the coordinate of the closing `+`."""
    for step in range(1, max(grid.width, grid.height) + 1):
        cx, cy = x + dx * step, y + dy * step
        char = grid.at(cx, cy)
        if char == "+":
            return cx if dx else cy
        if char != body:
            return None
    return None


def _reject_overlaps(rooms: list[Room]) -> None:
    for i, first in enumerate(rooms):
        for second in rooms[i + 1 :]:
            overlap_x = first.x0 <= second.x1 and second.x0 <= first.x1
            overlap_y = first.y0 <= second.y1 and second.y0 <= first.y1
            if overlap_x and overlap_y:
                raise LoadError(
                    f"rooms overlap: ({first.x0},{first.y0}) and ({second.x0},{second.y0})"
                )


def _classify_io_rooms(grid: Grid, rooms: list[Room]) -> None:
    """A 3x3 room whose one interior cell is `I` or `O` is the input / output room."""
    seen: dict[str, Cell] = {}
    for room in rooms:
        if room.kind == "display" or room.x1 - room.x0 != 2 or room.y1 - room.y0 != 2:
            continue
        char = grid.at(room.x0 + 1, room.y0 + 1)
        if char not in ("I", "O"):
            continue
        if char in seen:
            raise LoadError(f"more than one {char!r} room: {seen[char]} and ({room.x0},{room.y0})")
        seen[char] = (room.x0, room.y0)
        room.kind = "input" if char == "I" else "output"


def _find_spawns(grid: Grid, rooms: list[Room]) -> list[tuple[int, Cell]]:
    spawns: list[tuple[int, Cell]] = []
    for y in range(grid.height):
        for x in range(grid.width):
            if grid.at(x, y) != "@":
                continue
            index = next(
                (i for i, room in enumerate(rooms) if room.contains_interior(x, y)), None
            )
            if index is None:
                raise LoadError(
                    f"little man at ({x},{y}) is not inside a room "
                    f"(a malformed room border reads as no room at all)"
                )
            room = rooms[index]
            if room.kind == "display":
                raise LoadError(
                    f"little man at ({x},{y}) is inside the display at ({room.x0},{room.y0}) — "
                    f"an LM-75 is driven by pipes, not by a man"
                )
            if room.spawn is not None:
                raise LoadError(
                    f"room at ({room.x0},{room.y0}) has multiple '@'s — "
                    f"rooms start with at most one little man"
                )
            room.spawn = (x, y)
            spawns.append((index, (x, y)))
    return spawns


def _border_room(rooms: list[Room], x: int, y: int) -> int | None:
    return next((i for i, room in enumerate(rooms) if room.on_border(x, y)), None)


def _in_room(rooms: list[Room], x: int, y: int) -> bool:
    return any(room.on_border(x, y) or room.contains_interior(x, y) for room in rooms)


def _find_pipes(grid: Grid, rooms: list[Room]) -> list[Pipe]:
    """Every pipe, walked from the arrowhead that leaves a room border — **greedily**.

    A bend can also sit next to a wall, so one cell can be both "cell #12 of a long pipe" and "a
    legal start for a new pipe out of the room behind it". Something has to break the tie, and the
    server breaks it by **claiming cells as it scans, in reading order**: the first candidate to
    reach a cell owns it, and later candidates starting on an owned cell are not pipes at all.

    Resolving that tie the other way — walk everything, then drop candidates that turned out to be
    interior to some other pipe — is order-independent and looks more principled, but it is not what
    the server does, and the difference is not cosmetic. It cost two submissions:

    - `matmul` 46x46 scored 18/20 with two step-caps. The server read a `<` at (13,4) as a pipe
      leaving the main room; we read it as cell #12 of a pipe starting at (16,11). Same two rooms,
      but the *attached segment* moved, so every `s` in that room re-bound to a different pipe.
    - `memory/banked2-sbs` was rejected outright with "a pipe flows out of the output room": a `^`
      one cell above the output room's corner is a legal start away from it, and it precedes the
      real pipe's start in reading order.

    Walking a candidate is still speculative: a malformed one is only fatal if no pipe ever claims
    its cell. Without that, tightly packed rooms are rejected — in an 8x8 `triangle` layout the
    second cell of a 2-cell pipe backs onto the other room's wall, and eagerly raising there reported
    it as a one-cell pipe. The server accepts those, and greedy order is why: the real pipe's start
    always precedes its own second cell. See `Pipe start scanning is greedy` in the vault.
    """
    claimed: set[Cell] = set()
    held: list[tuple[Cell, LoadError]] = []
    pipes: list[Pipe] = []
    for y in range(grid.height):
        for x in range(grid.width):
            direction = ARROWS.get(grid.at(x, y))
            # Pipes cannot be drawn inside a room: in there these glyphs are turn instructions,
            # and a turn one cell below the top wall would otherwise read as a pipe leaving it.
            if direction is None or _in_room(rooms, x, y) or (x, y) in claimed:
                continue
            dx, dy = DELTAS[direction]
            source = _border_room(rooms, x - dx, y - dy)
            if source is None:
                continue
            try:
                pipe = _walk_pipe(grid, rooms, (x, y), direction, source)
            except LoadError as error:
                held.append(((x, y), error))
                continue
            claimed.update(pipe.cells)
            pipes.append(pipe)

    for cell, error in held:
        if cell not in claimed:
            raise error
    return pipes


def _walk_pipe(grid: Grid, rooms: list[Room], start: Cell, direction: int, source: int) -> Pipe:
    cells = [start]
    x, y = start
    is_arrow = True
    limit = grid.width * grid.height + 2
    while len(cells) <= limit:
        dx, dy = DELTAS[direction]
        nx, ny = x + dx, y + dy
        room = _border_room(rooms, nx, ny)
        if room is not None:
            if not is_arrow:
                raise LoadError(
                    f"pipe from ({start[0]},{start[1]}) runs a body glyph into the wall at "
                    f"({nx},{ny}) — end with an arrowhead pointing into the room"
                )
            if room == source:
                raise LoadError(
                    f"pipe from ({start[0]},{start[1]}) runs back into its own room at ({nx},{ny})"
                )
            if len(cells) < 2:
                raise LoadError(
                    f"pipe at ({start[0]},{start[1]}) is one cell long — pipes need at least 2"
                )
            return Pipe(cells, source, room, direction)

        char = grid.at(nx, ny)
        if char in ARROWS:
            turned = ARROWS[char]
            if turned == (direction + 2) % 4:
                raise LoadError(
                    f"arrowhead {char!r} at ({nx},{ny}) points back along the flow of the pipe "
                    f"from ({start[0]},{start[1]})"
                )
            direction, is_arrow = turned, True
        elif char == ("-" if dy == 0 else "|"):
            is_arrow = False
        else:
            expected = "-" if dy == 0 else "|"
            raise LoadError(
                f"pipe from ({start[0]},{start[1]}) hits {char!r} at ({nx},{ny}): "
                f"expected an arrowhead or {expected!r}"
            )
        cells.append((nx, ny))
        x, y = nx, ny
    raise LoadError(f"pipe from ({start[0]},{start[1]}) never reaches a room")


def _check_io_pipes(rooms: list[Room], pipes: list[Pipe]) -> tuple[int | None, int | None]:
    input_pipe: int | None = None
    output_pipe: int | None = None
    for room in rooms:
        if room.kind in ("room", "display"):
            continue
        attached = room.outgoing + room.incoming
        if len(attached) > 1:
            raise LoadError(f"the {room.kind} room at ({room.x0},{room.y0}) has more than one pipe")
        if not attached:
            continue
        if room.kind == "input" and room.incoming:
            raise LoadError(f"the input room at ({room.x0},{room.y0}) has a pipe flowing into it")
        if room.kind == "output" and room.outgoing:
            raise LoadError(f"the output room at ({room.x0},{room.y0}) has a pipe flowing out of it")
        if room.kind == "input":
            input_pipe = room.outgoing[0]
        else:
            output_pipe = room.incoming[0]

    if input_pipe is not None and rooms[pipes[input_pipe].dst_room].kind == "output":
        raise LoadError("the input room's pipe flows straight into the output room")
    return input_pipe, output_pipe


def _display_ports(rooms: list[Room], pipes: list[Pipe]) -> list[Display]:
    """Which side each pipe lands on, which is the LM-75's opcode.

    > Top: ADDR. Left: DATA. Bottom: SWAP. Attaching multiple pipes to the same side, attaching a
    > pipe to the right side, or attaching a pipe to the corner is a load error.
    > — language-reference#The LM-75 Display
    """
    displays: list[Display] = []
    for index, room in enumerate(rooms):
        if room.kind != "display":
            continue
        if room.outgoing:
            pipe = pipes[room.outgoing[0]]
            raise LoadError(
                f"a pipe flows out of the display at ({room.x0},{room.y0}) from "
                f"({pipe.source[0]},{pipe.source[1]}) — an LM-75 only consumes values"
            )
        ports: dict[str, int] = {}
        for pipe_index in room.incoming:
            x, y = pipes[pipe_index].entry
            side = _display_side(room, x, y)
            if side in ports:
                raise LoadError(
                    f"two pipes attach to the {side} side of the display at ({room.x0},{room.y0}); "
                    f"the second lands at ({x},{y})"
                )
            ports[side] = pipe_index
        displays.append(
            Display(
                room=index,
                width=room.x1 - room.x0 - 1,
                height=room.y1 - room.y0 - 1,
                addr=ports.get("ADDR"),
                data=ports.get("DATA"),
                swap=ports.get("SWAP"),
            )
        )
    return displays


def _display_side(room: Room, x: int, y: int) -> str:
    if x in (room.x0, room.x1) and y in (room.y0, room.y1):
        raise LoadError(
            f"a pipe attaches to the corner ({x},{y}) of the display at ({room.x0},{room.y0})"
        )
    if y == room.y0:
        return "ADDR"
    if y == room.y1:
        return "SWAP"
    if x == room.x0:
        return "DATA"
    raise LoadError(
        f"a pipe attaches to the right side ({x},{y}) of the display at "
        f"({room.x0},{room.y0}) — that side takes no pipe"
    )


def _pipe_tables(
    rooms: list[Room], pipes: list[Pipe]
) -> tuple[dict[Cell, int], dict[Cell, int], dict[int, list[int]]]:
    """Per-cell nearest-pipe lookups, so the tick loop never measures a distance.

    > The distance to a pipe is the Manhattan distance from the operation to the pipe segment that
    > is attached to the current room ... If multiple pipes are equally close, the pipe whose
    > segment comes first in reading order wins. — language-reference#Which pipe do I talk to?
    """
    nearest_out: dict[Cell, int] = {}
    nearest_in: dict[Cell, int] = {}
    incoming_sorted: dict[int, list[int]] = {}
    for index, room in enumerate(rooms):
        # A display has no interior cells a man can stand on, so it needs none of these.
        if room.kind == "display":
            continue
        incoming_sorted[index] = sorted(
            room.incoming, key=lambda i: (pipes[i].dest[1], pipes[i].dest[0])
        )
        sources = [pipes[i].source for i in room.outgoing]
        dests = [pipes[i].dest for i in room.incoming]
        for cell in room.interior_cells():
            if room.outgoing:
                nearest_out[cell] = _nearest(cell, room.outgoing, sources)
            if room.incoming:
                nearest_in[cell] = _nearest(cell, room.incoming, dests)
    return nearest_out, nearest_in, incoming_sorted


def _nearest(cell: Cell, indices: list[int], segments: list[Cell]) -> int:
    x, y = cell
    best = min(
        range(len(indices)),
        key=lambda i: (
            abs(segments[i][0] - x) + abs(segments[i][1] - y),
            segments[i][1],
            segments[i][0],
        ),
    )
    return indices[best]


def _literal_loads(grid: Grid, room_of: dict[Cell, int]) -> dict[tuple[int, int, int], int]:
    """What each digit and backtick loads into A, per walk direction.

    A cell missing from this table loads nothing: that is exactly a digit belonging to a literal
    along the walk axis, a backtick that does not delimit along it, and an empty literal.
    """
    loads: dict[tuple[int, int, int], int] = {}
    matched: set[Cell] = set()
    covered_h: set[Cell] = set()
    covered_v: set[Cell] = set()

    for y in range(grid.height):
        line = [grid.at(x, y) for x in range(grid.width)]
        for lo, hi in _pair_backticks(line, 0, y, room_of):
            matched.update({(lo, y), (hi, y)})
            covered_h.update({(x, y) for x in range(lo + 1, hi)})
            digits = "".join(c for c in line[lo + 1 : hi] if c in _DIGITS)
            _record(loads, digits, (hi, y), (lo, y), forward=0, backward=2)

    for x in range(grid.width):
        column = [grid.at(x, y) for y in range(grid.height)]
        for lo, hi in _pair_backticks(column, 1, x, room_of):
            matched.update({(x, lo), (x, hi)})
            covered_v.update({(x, y) for y in range(lo + 1, hi)})
            digits = "".join(c for c in column[lo + 1 : hi] if c in _DIGITS)
            _record(loads, digits, (x, hi), (x, lo), forward=1, backward=3)

    for y in range(grid.height):
        for x in range(grid.width):
            char = grid.at(x, y)
            if char == "`" and (x, y) not in matched:
                raise LoadError(f"unmatched backtick at ({x},{y})")
            if char not in _DIGITS:
                continue
            value = int(char)
            if (x, y) not in covered_h:
                loads[(x, y, 0)] = value
                loads[(x, y, 2)] = value
            if (x, y) not in covered_v:
                loads[(x, y, 1)] = value
                loads[(x, y, 3)] = value
    return loads


def _pair_backticks(
    line: list[str], axis: int, other: int, room_of: dict[Cell, int]
) -> list[tuple[int, int]]:
    """Pair backticks along one axis, sequentially, **within one room**. A bad span is a load error.

    Two rules, and each was paid for by a submission:

    - A span of anything but digits and spaces is an error, not something to skip. Confirmed
      2026-07-25 by `history-lesson`, whose data drum had backticks two rows apart in a column with
      an `s` between them — every one of them already paired *horizontally* — and the server said
      `expected a digit or a space between backticks, but found 's'`.
    - Backticks in **different rooms never pair**. Confirmed the same day by the packed version of
      the same program: a backtick in DEC and one in YEAR, nine rows apart with two room borders
      between them, which the server accepts and this function used to reject. A literal belongs to
      a room; it cannot straddle a wall.

    A backtick left over at the end is not an error here — it may still pair on the other axis, and
    one that pairs on neither is caught as unmatched.
    """
    pairs: list[tuple[int, int]] = []
    pending: int | None = None
    for index, char in enumerate(line):
        if char != "`":
            continue
        cell = (index, other) if axis == 0 else (other, index)
        room = room_of.get(cell)
        if pending is None or room is None or room != room_of.get(
            (pending, other) if axis == 0 else (other, pending)
        ):
            pending = index
            continue
        for offset, span in enumerate(line[pending + 1 : index], start=pending + 1):
            if span not in _DIGITS and span != " ":
                x, y = (offset, other) if axis == 0 else (other, offset)
                raise LoadError(
                    f"expected a digit or a space between backticks, "
                    f"but found {span!r} at ({x}, {y})"
                )
        pairs.append((pending, index))
        pending = None
    return pairs


def _record(
    loads: dict[tuple[int, int, int], int],
    digits: str,
    closing_forward: Cell,
    closing_backward: Cell,
    *,
    forward: int,
    backward: int,
) -> None:
    """A literal loads when the man steps onto its *closing* backtick — which end that is depends
    on the direction he walks, and the digits read in that order."""
    if not digits:
        return
    ahead, behind = int(digits), int(digits[::-1])
    if ahead > _INT64_MAX or behind > _INT64_MAX:
        raise LoadError(
            f"numeric literal {digits!r} at ({closing_backward[0]},{closing_backward[1]}) "
            f"does not fit in 64 bits read in both directions"
        )
    loads[(closing_forward[0], closing_forward[1], forward)] = ahead
    loads[(closing_backward[0], closing_backward[1], backward)] = behind
