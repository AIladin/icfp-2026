"""Layout helpers: boustrophedon instruction rooms and straight pipes."""

from gen import col, put, room, row


def serp(r0: int, c0: int, instrs: str, per_row: int) -> tuple[int, int]:
    """A boustrophedon room holding `instrs`, spawn at the top-left.

    Interior layout, with `k` = per_row:

        col c0+1 : north return column
        col c0+2 : '@' / '>' on eastbound rows, 'v' on westbound rows
        cols c0+3 .. c0+2+k : instruction cells
        col c0+3+k : 'v' on eastbound rows, '<' on westbound rows

    Returns the room's bottom-right corner (r1, c1).
    """
    n = -(-len(instrs) // per_row)
    ci = c0 + 3
    ct = ci + per_row
    r1 = r0 + n + 2  # instruction rows + one return row
    c1 = ct + 1
    room(r0, c0, r1, c1)

    for i in range(n):
        r = r0 + 1 + i
        seg = instrs[per_row * i : per_row * (i + 1)]
        if i % 2 == 0:
            put(r, c0 + 2, "@" if i == 0 else ">")
            row(r, ci, seg)
            put(r, ct, "v")
        else:
            put(r, ct, "<")
            row(r, ct - len(seg), seg[::-1])
            put(r, c0 + 2, "v")
        put(r, c0 + 1, ">" if i == 0 else "^")

    # return row: walk west from wherever the last row exits, then climb
    rr = r0 + n + 1
    exit_col = ct if (n - 1) % 2 == 0 else c0 + 2
    put(rr, exit_col, "<")
    put(rr, c0 + 1, "^")
    col(c0 + 1, r0 + 2, "^" * (n - 1))
    return r1, c1


def hpipe(r: int, c0: int, c1: int) -> None:
    """Horizontal pipe on row r occupying cols c0..c1 inclusive, flowing east if
    c0 < c1 else west.  Caller guarantees both ends abut a room border."""
    if c0 < c1:
        put(r, c0, ">")
        row(r, c0 + 1, "-" * (c1 - c0 - 1))
        put(r, c1, ">")
    else:
        put(r, c0, "<")
        row(r, c1 + 1, "-" * (c0 - c1 - 1))
        put(r, c1, "<")


def vpipe(c: int, r0: int, r1: int) -> None:
    """Vertical pipe in column c occupying rows r0..r1 inclusive."""
    if r0 < r1:
        put(r0, c, "v")
        col(c, r0 + 1, "|" * (r1 - r0 - 1))
        put(r1, c, "v")
    else:
        put(r0, c, "^")
        col(c, r1 + 1, "|" * (r0 - r1 - 1))
        put(r1, c, "^")


def io_room(r0: int, c0: int, ch: str) -> None:
    """A 3x3 input ('I') or output ('O') room with top-left corner (r0, c0)."""
    room(r0, c0, r0 + 2, c0 + 2)
    put(r0 + 1, c0 + 1, ch)


DIRCH = {(0, 1): ">", (0, -1): "<", (1, 0): "v", (-1, 0): "^"}
BODY = {(0, 1): "-", (0, -1): "-", (1, 0): "|", (-1, 0): "|"}


def path_pipe(points: list[tuple[int, int]]) -> int:
    """A pipe along an orthogonal path of (row, col) waypoints, returning its length.

    `points[0]` must be the first pipe cell (its backward neighbour on the source room's
    border) and `points[-1]` the last (its forward neighbour on the destination's).
    Arrowheads go at the start and at every bend, body glyphs between -- which is exactly
    what the loader's pipe grammar wants, so a routed pipe never needs hand-fixing.
    """
    cells: list[tuple[int, int]] = []
    for (r0, c0), (r1, c1) in zip(points, points[1:]):
        dr = (r1 > r0) - (r1 < r0)
        dc = (c1 > c0) - (c1 < c0)
        if dr and dc:
            raise SystemExit(f"path_pipe: {(r0, c0)} -> {(r1, c1)} is not orthogonal")
        r, c = r0, c0
        while (r, c) != (r1, c1):
            cells.append((r, c, (dr, dc)))
            r, c = r + dr, c + dc
    last_dir = cells[-1][2] if cells else (0, 1)
    cells.append((points[-1][0], points[-1][1], last_dir))

    for i, (r, c, d) in enumerate(cells):
        turning = i == 0 or cells[i - 1][2] != d
        terminal = i == len(cells) - 1
        put(r, c, DIRCH[d] if (turning or terminal) else BODY[d])
    return len(cells)
